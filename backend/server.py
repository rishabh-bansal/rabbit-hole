"""Rabbit Hole server: runs the two-lane race and streams events to the browser (SSE)."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, Response, StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import race as race_mod  # noqa: E402
from race import Lane, run_lane  # noqa: E402
from wiki import Wiki  # noqa: E402

app = FastAPI(title="Rabbit Hole")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
wiki = Wiki()

OPENCLAW = os.getenv("OPENCLAW_URL")  # e.g. http://127.0.0.1:18789/v1 ; unset = call providers directly (dev)
OC_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
LANE_TIMEOUT = float(os.getenv("RH_LANE_TIMEOUT", "300"))
FAST_MODEL = os.getenv("RH_CEREBRAS_MODEL", "moonshotai-kimi-k3.1-pro-trial")


# Models a race can use. Both lanes always run the SAME model; the GPU lane exists only when a free
# GPU host serves that model (today only Kimi K3.1 Pro, on NVIDIA's API catalog free tier).
MODELS = {
    "kimi-k3.1-pro": {"label": "Kimi K3.1 Pro", "cerebras": FAST_MODEL, "agent": os.getenv("RH_CEREBRAS_AGENT", "racer-cerebras"),
                      "story_agent": "storyteller", "extra": {"reasoning_effort": "low"},
                      "gpu": {"model": "moonshotai/kimi-k3.1-pro", "agent": "racer-nvidia", "extra": {"reasoning_effort": "low"}}},
    "gpt-oss-120b": {"label": "GPT-OSS 120B", "cerebras": "gpt-oss-120b", "agent": "racer-gptoss",
                     "story_agent": "storyteller-gptoss", "extra": {"reasoning_effort": "low"}, "gpu": None,
                     "off": "Off for now: our free Cerebras key allows only 5 requests a minute for this model, too few for a race."},
    "qwen-3.8-27b": {"label": "Qwen 3.8 27B", "cerebras": "qwen-3.8-27b", "agent": "racer-qwen",
                     "story_agent": "storyteller-qwen", "extra": {}, "gpu": None},
}
_avail: dict = {"at": 0.0, "ids": {k for k, m in MODELS.items() if not m.get("off")}}


async def _available() -> set[str]:
    """Which registry models Cerebras serves right now (cached 2 min; on errors keep the last answer)."""
    if time.time() - _avail["at"] < 120:
        return _avail["ids"]
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://api.cerebras.ai/v1/models", headers={"Authorization": f"Bearer {os.getenv('CEREBRAS_API_KEY', '')}"})
            served = {m["id"] for m in r.json().get("data", [])} if r.status_code == 200 else None
        if served is not None:
            _avail["ids"] = {k for k, m in MODELS.items() if m["cerebras"] in served and not m.get("off")}
    except Exception:  # noqa: BLE001
        pass
    _avail["at"] = time.time()
    return _avail["ids"]


async def _default_model() -> str | None:
    ids = await _available()
    return next((k for k in MODELS if k in ids), None)


def lanes(mk: str, with_gpu: bool) -> list[Lane]:
    m = MODELS[mk]
    out = []
    if OPENCLAW:  # production: both lanes go through the OpenClaw gateway, one agent per provider and model
        out.append(Lane("cerebras", f"{m['label']} · Cerebras", OPENCLAW, OC_TOKEN, "openclaw/" + m["agent"]))
        if with_gpu and m["gpu"]:
            out.append(Lane("gpu", f"{m['label']} · NVIDIA GPU", OPENCLAW, OC_TOKEN, "openclaw/" + m["gpu"]["agent"]))
        return out
    out.append(Lane("cerebras", f"{m['label']} · Cerebras", "https://api.cerebras.ai/v1", os.getenv("CEREBRAS_API_KEY", ""), m["cerebras"], m["extra"]))
    if with_gpu and m["gpu"]:
        out.append(Lane("gpu", f"{m['label']} · NVIDIA GPU", "https://integrate.api.nvidia.com/v1", os.getenv("NVIDIA_API_KEY", ""),
                        m["gpu"]["model"], m["gpu"]["extra"]))
    return out


@app.get("/api/models")
async def models():
    ids = await _available()
    return {"default": await _default_model(),
            "models": [{"id": k, "label": m["label"], "available": k in ids, "gpu": bool(m["gpu"]), "note": m.get("off")} for k, m in MODELS.items()]}


RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)


def save_run(rid: str, body, history: list[dict]) -> None:
    """Keep every race so it can be replayed exactly as it happened (atomic write)."""
    lanes_done = {e["lane"]: e for e in history if e.get("type") == "lane_done"}
    summary = {
        "id": rid, "start": body.start, "target": body.target, "created": time.time(),
        "lanes": {k: {"seconds": v["seconds"], "hops": v["hops"], "path": [p["title"] for p in v["path"]]} for k, v in lanes_done.items()},
        "outcome": {e["lane"]: e["type"] for e in history if e.get("type") in ("lane_timeout", "lane_error", "lane_stopped")},
        "aborted": any(e.get("type") == "race_aborted" for e in history),
        "model": getattr(body, "model", None) or "kimi-k3.1-pro",
        "model_label": MODELS.get(getattr(body, "model", None) or "kimi-k3.1-pro", {}).get("label", "Kimi K3.1 Pro"),
        "gpu_note": next((e.get("gpu_note") for e in history if e.get("type") == "race_started" and e.get("gpu_note")), None),
        "story": next((e["text"] for e in history if e.get("type") == "story"), ""),
    }
    tmp = RUNS / f".{rid}.tmp"
    tmp.write_text(json.dumps({"summary": summary, "events": history}))
    os.replace(tmp, RUNS / f"{rid}.json")


_sum_cache: dict = {"key": None, "list": []}


def _summaries() -> list[dict]:
    """All saved race summaries, newest first. Re-read only when the runs folder changes."""
    try:
        key = (RUNS.stat().st_mtime_ns, len(list(RUNS.glob("*.json"))))
    except OSError:
        return []
    if key != _sum_cache["key"]:
        out = []
        for f in sorted(RUNS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                sm = json.loads(f.read_text())["summary"]
                if isinstance(sm, dict) and isinstance(sm.get("lanes"), dict):
                    out.append(sm)
            except Exception:  # noqa: BLE001 - a broken file never breaks the list
                continue
        _sum_cache.update(key=key, list=out)
    return _sum_cache["list"]


def _finished(sm: dict) -> bool:
    return bool((sm.get("lanes") or {}).get("cerebras"))


@app.get("/api/runs")
async def list_runs(limit: int = 30):
    """Public list of past races. Races where Cerebras didn't finish stay on disk as a record but
    are never shown (they're almost always the shared endpoint being overloaded, not a result)."""
    limit = max(1, min(limit, 100))
    return {"runs": [sm for sm in _summaries() if _finished(sm)][:limit]}


@app.get("/api/runs/{rid}")
async def get_run(rid: str):
    f = RUNS / f"{Path(rid).name}.json"
    if not f.exists():
        raise HTTPException(404, "unknown run")
    try:
        return json.loads(f.read_text())
    except Exception:  # noqa: BLE001
        raise HTTPException(404, "unknown run") from None


def _summary(rid: str) -> dict | None:
    f = RUNS / f"{Path(rid).name}.json"
    try:
        return json.loads(f.read_text())["summary"] if f.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _featured() -> dict | None:
    """The race to show on the home page preview: latest race that Cerebras finished."""
    return next((sm for sm in _summaries() if _finished(sm)), None)


@app.get("/api/runs/{rid}/summary")
async def run_summary(rid: str):
    s = _summary(rid)
    if not s:
        raise HTTPException(404, "unknown run")
    return s


@app.get("/api/featured")
async def featured():
    return _featured() or {}


_og_cache: dict[str, bytes] = {}


@app.get("/api/og.png")
async def og_image(run: str = ""):
    """Link-preview image: a specific race (?run=ID) or the latest one."""
    from og import render
    s = _summary(run) if run else _featured()
    key = (s or {}).get("id", "none") + ("|r" if run else "|l")
    if key not in _og_cache:
        if len(_og_cache) > 300:
            _og_cache.clear()
        _og_cache[key] = await asyncio.to_thread(render, s, "Replay" if run else "Latest race")
    return Response(_og_cache[key], media_type="image/png",
                    headers={"Cache-Control": f"public, max-age={86400 if run else 600}"})


SURPRISE = [
    ("Taylor Swift", "Mitochondria"), ("Pizza", "Black hole"), ("Cat", "Moon"), ("Coffee", "French Revolution"),
    ("Minecraft", "Ancient Egypt"), ("Banana", "Albert Einstein"), ("Lego", "Roman Empire"), ("Shrek", "Quantum mechanics"),
    ("Chess", "Volcano"), ("Penguin", "Internet"), ("Sushi", "World War II"), ("Beyoncé", "Photosynthesis"),
    ("Football", "Shakespeare"), ("Chocolate", "Mars"), ("Dinosaur", "Bitcoin"), ("Harry Potter", "Electricity"),
]


PAIRS_FILE = ROOT / "surprise_pairs.json"
_pairs: list[dict] = json.loads(PAIRS_FILE.read_text()) if PAIRS_FILE.exists() else []


@app.get("/api/surprise")
async def surprise():
    """Two well-known topics from different worlds that are exactly two clicks apart on Wikipedia
    (surprising, but reachable). Built offline by make_pairs.py; falls back to any two groups."""
    import random
    if _pairs:
        p = random.choice(_pairs)
        start, target = p["start"], p["target"]
    else:
        from topics import TOPICS
        ga, gb = random.sample(list(TOPICS), 2)
        start, target = random.choice(TOPICS[ga]), random.choice(TOPICS[gb])
    # start loading the first page now, so the race begins the moment the countdown ends
    _spawn_warm(start, target)
    return {"start": start, "target": target}


_warm_tasks: set[asyncio.Task] = set()
_warm_hits: dict[str, list[float]] = {}


def _spawn_warm(start: str, target: str) -> None:
    if len(_warm_tasks) >= 4 or _busy():  # never compete with a live race for Wikipedia
        return
    t = asyncio.create_task(_warm(start, target))
    _warm_tasks.add(t)
    t.add_done_callback(_warm_tasks.discard)


@app.get("/api/warm")
async def warm(request: Request, start: str = "", target: str = ""):
    """The page calls this once a typed topic checks out, so Wikipedia is already fetched at Start."""
    ip, now = _client_ip(request), time.time()
    hits = [t for t in _warm_hits.get(ip, []) if now - t < 60]
    if 0 < len(start) <= 120 and len(target) <= 120 and len(hits) < 20:
        hits.append(now)
        _spawn_warm(start, target or start)
    _warm_hits[ip] = hits
    if len(_warm_hits) > 5000:
        _warm_hits.clear()
    return Response(status_code=204)


async def _warm(start: str, target: str) -> None:
    try:
        await asyncio.gather(wiki.body_links(start), wiki.target_redirects(target))
    except Exception:  # noqa: BLE001
        pass


@app.get("/api/stats")
async def stats():
    """Time saved by Cerebras across all races: how much longer the GPU side took (a GPU that gave
    up counts as the time it had spent when it stopped)."""
    saved, races_n = 0.0, 0
    for sm in _summaries():
        try:
            lanes_ = sm["lanes"]
            cb = lanes_.get("cerebras")
            if not cb:
                continue
            gpu = (lanes_.get("gpu") or {}).get("seconds")
            if gpu is None and (sm.get("outcome") or {}).get("gpu") == "lane_timeout":
                gpu = LANE_TIMEOUT
            if gpu is not None:
                saved += max(0.0, float(gpu) - float(cb["seconds"]))
                races_n += 1
        except Exception:  # noqa: BLE001
            continue
    return {"seconds_saved": round(saved, 1), "races": races_n}


async def tell_story(start: str, target: str, path: list[dict], mk: str = "kimi-k3.1-pro") -> str:
    """Kimi on Cerebras (through OpenClaw) turns the chain into a 3-sentence mini story."""
    from openai import AsyncOpenAI
    if OPENCLAW:
        client, model = AsyncOpenAI(base_url=OPENCLAW, api_key=OC_TOKEN, timeout=40, max_retries=1), "openclaw/" + MODELS[mk]["story_agent"]
    else:
        client, model = AsyncOpenAI(base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY", ""), timeout=40, max_retries=1), MODELS[mk]["cerebras"]
    chain = " → ".join(p["title"] for p in path)
    notes = "\n".join(f"- {p['title']}: {p['reason']}" for p in path[1:])
    try:
        r = await client.chat.completions.create(model=model, max_tokens=1200, messages=[
            {"role": "system", "content": "Write exactly 3 short, vivid, accurate sentences explaining how the first topic connects to the last through this chain of Wikipedia articles. Mention each article in order. Plain text only: no markdown, no asterisks, no preamble."},
            {"role": "user", "content": f"Question: how is {start} connected to {target}?\nChain: {chain}\nNotes:\n{notes}"}])
        import re
        text = (r.choices[0].message.content or "").strip()
        return re.sub(r"[*_`#]+", "", text).strip()  # the page shows plain text
    except Exception:  # noqa: BLE001
        return ""
    finally:
        await client.close()


class RaceIn(BaseModel):
    start: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=120)
    model: str | None = Field(default=None, max_length=40)


# ---- protection for free credits (Cerebras trial, NVIDIA free credits, Wikipedia) ----
PER_IP_PER_HOUR = int(os.getenv("RH_PER_IP_PER_HOUR", "4"))
DAILY_RACES = int(os.getenv("RH_DAILY_RACES", "120"))
GPU_DAILY = int(os.getenv("RH_GPU_DAILY", "40"))            # NVIDIA free credits are the scarcest
REPLAY_ONLY_FILE = ROOT / "REPLAY_ONLY"                    # touch this file to stop live races instantly
_ip_hits: dict[str, list[float]] = {}
_day = {"date": "", "races": 0, "gpu": 0}


def _client_ip(request: Request) -> str:
    """The visitor's IP. Only our Cloudflare Pages proxy (which knows the shared secret) may tell us;
    otherwise use the connection address (Caddy's X-Forwarded-For via uvicorn's proxy headers).
    Headers like CF-Connecting-IP are ignored: anyone hitting the server directly could fake them."""
    secret = os.getenv("RH_PROXY_SECRET", "")
    if secret and request.headers.get("x-rh-proxy") == secret and request.headers.get("x-rh-client-ip"):
        return request.headers["x-rh-client-ip"][:64]
    return request.client.host if request.client else "?"


_auto_pause = {"until": 0.0}   # set when the Cerebras key/model stops working; expires on its own


def _paused() -> bool:
    return REPLAY_ONLY_FILE.exists() or os.getenv("RH_REPLAY_ONLY") == "1" or time.time() < _auto_pause["until"]


def _auto_pause_now() -> None:
    _auto_pause["until"] = time.time() + 1800  # 30 minutes, then the next race re-checks


def _quota_check(request: Request) -> None:
    """Raises if live races are paused, the day is used up, or this visitor is over the hourly limit.
    Costs nothing and records nothing, so it runs before any Wikipedia or Cerebras work."""
    if _paused():
        raise HTTPException(503, {"code": "paused", "message": "Live races are paused for today. Replays keep playing."})
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, races=0, gpu=0)
    if _day["races"] >= DAILY_RACES:
        raise HTTPException(503, {"code": "paused", "message": "We hit today’s limit. Replays keep playing, and live races are back tomorrow."})
    ip, now = _client_ip(request), time.time()
    hits = [t for t in _ip_hits.get(ip, []) if now - t < 3600]
    _ip_hits[ip] = hits
    if len(hits) >= PER_IP_PER_HOUR:
        wait = max(1, int((3600 - (now - min(hits))) / 60) + 1)
        raise HTTPException(429, {"code": "ip_limit", "limit": PER_IP_PER_HOUR, "minutes": wait,
                                  "message": f"Each visitor gets {PER_IP_PER_HOUR} live races an hour, so the free credits last."})


def _quota_commit(request: Request, needs_gpu: bool = True) -> bool:
    """Count a race that is really starting. Returns whether the GPU lane may run today."""
    _ip_hits.setdefault(_client_ip(request), []).append(time.time())
    if len(_ip_hits) > 20000:
        cutoff = time.time() - 3600
        for k in [k for k, v in _ip_hits.items() if not v or v[-1] < cutoff]:
            _ip_hits.pop(k, None)
    _day["races"] += 1
    gpu_ok = needs_gpu and _day["gpu"] < GPU_DAILY
    if gpu_ok:
        _day["gpu"] += 1
    return gpu_ok


races: dict[str, dict] = {}
current: str | None = None

# ---- pre-flight: is the system responsive before we make a visitor wait? ----
_health: dict[str, dict[str, float]] = {k: {"ok": 0.0, "busy": 0.0, "down": 0.0} for k in MODELS}
_racing_model = {"k": "kimi-k3.1-pro"}
race_mod.on_fast_answer = lambda: _health[_racing_model["k"]].update(ok=time.time())


async def _ping_cerebras(mk: str) -> str:
    """'ok', 'busy' (queue full) or 'down' for one model. A real answer in the last 45 s counts as ok."""
    from openai import AsyncOpenAI, AuthenticationError, NotFoundError, PermissionDeniedError, RateLimitError
    h = _health[mk]
    if time.time() - h["ok"] < 45:
        return "ok"
    if time.time() - h["busy"] < 30:  # don't add to an overloaded queue on every click
        return "busy"
    if time.time() - h["down"] < 30:
        return "down"
    client = AsyncOpenAI(base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY", ""), timeout=15, max_retries=0)
    try:
        for attempt in range(3):
            try:
                await client.chat.completions.create(model=MODELS[mk]["cerebras"], max_tokens=8,
                                                     messages=[{"role": "user", "content": "Reply with: ok"}])
                h["ok"] = time.time()
                return "ok"
            except RateLimitError:
                await asyncio.sleep(1.5 + attempt)
            except (AuthenticationError, PermissionDeniedError):
                _auto_pause_now()  # key access gone: replays only, re-checked in 30 min
                h["down"] = time.time()
                return "down"
            except NotFoundError:  # this model is gone (e.g. the hackathon trial ended): only this model is off
                h["down"] = time.time()
                _avail["ids"].discard(mk)
                return "down"
            except Exception:  # noqa: BLE001
                h["down"] = time.time()
                return "down"
        h["busy"] = time.time()
        return "busy"
    finally:
        await client.close()


async def _ping_gateway() -> bool:
    if not OPENCLAW:
        return True
    import httpx
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(OPENCLAW.rstrip("/") + "/models", headers={"Authorization": f"Bearer {OC_TOKEN}"})
            return r.status_code < 500
    except Exception:  # noqa: BLE001
        return False


def _busy() -> bool:
    return bool(current and current in races and not races[current]["done"].is_set())


@app.get("/api/status")
async def status():
    """Quick system check the page can show before a race (cached, cheap)."""
    mk = await _default_model()
    h = _health.get(mk) if mk else None
    state = "down" if not h else "ok" if time.time() - h["ok"] < 120 else ("busy" if time.time() - h["busy"] < 90 else "unknown")
    return {"cerebras": state, "busy": _busy()}


@app.get("/api/health")
async def health():
    return {"ok": True, "mode": "openclaw" if OPENCLAW else "direct", "today": _day,
            "replay_only": _paused(),
            "default_model": await _default_model(),
            "busy": _busy(), "live": _live()}


def _live() -> dict | None:
    if _busy():
        r = races[current]
        return {"id": current, "start": r["start"], "target": r["target"], "elapsed": round(time.time() - r["t0"], 1)}
    return None


def _prune_races() -> None:
    """Keep the last 20 finished races in memory for late viewers; older ones replay from disk."""
    finished = [k for k, r in races.items() if r["done"].is_set() and k != current]
    for k in finished[:-20]:
        races.pop(k, None)


@app.post("/api/race")
async def start_race(body: RaceIn, request: Request):
    global current
    if _busy():
        raise HTTPException(429, {"code": "busy", "message": "Someone is racing right now.", "live": _live()})
    _quota_check(request)  # paused / daily / per-visitor: free to check, so do it before any real work
    try:
        for field, t in (("start", body.start), ("target", body.target)):
            info = await wiki.resolve(t)
            if not info["exists"]:
                raise HTTPException(422, {"code": "bad_input", "field": field, "kind": "missing", "value": t,
                                          "message": f"No Wikipedia article called “{t}”.", "options": await wiki.suggest(t)})
            if info["disambiguation"]:
                raise HTTPException(422, {"code": "bad_input", "field": field, "kind": "ambiguous", "value": t,
                                          "message": f"“{t}” is ambiguous. Be more specific:", "options": await wiki.senses(info["title"])})
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        raise HTTPException(503, {"code": "wiki_down", "message": "Wikipedia isn’t answering right now. Try again in a moment."}) from None
    mk = body.model or await _default_model()
    if not mk or mk not in MODELS or mk not in await _available():
        raise HTTPException(422, {"code": "model_unavailable", "message": "That model isn’t available on Cerebras right now. Pick another one."})
    body.model = mk
    # pre-flight: don't start a race the system can't run (and don't count it against the visitor)
    if not await _ping_gateway():
        raise HTTPException(503, {"code": "engine_down", "message": "The race engine is restarting. Try again in a minute."})
    cb = await _ping_cerebras(mk)
    if cb != "ok":
        raise HTTPException(503, {"code": "cerebras_busy" if cb == "busy" else "cerebras_down", "model": MODELS[mk]["label"],
                                  "message": f"{MODELS[mk]['label']} on Cerebras isn’t answering right now."})
    if _busy():  # someone started while we were checking
        raise HTTPException(429, {"code": "busy", "message": "Someone is racing right now.", "live": _live()})
    _quota_check(request)
    has_gpu_host = bool(MODELS[mk]["gpu"])
    gpu_ok = _quota_commit(request, needs_gpu=has_gpu_host)
    _racing_model["k"] = mk
    rid = uuid.uuid4().hex[:10]
    history: list[dict] = []
    done = asyncio.Event()
    t0 = time.time()
    _prune_races()
    races[rid] = {"history": history, "done": done, "t0": t0, "start": body.start, "target": body.target}
    current = rid
    story_task: dict = {"t": None}

    async def make_story(path):
        await emit({"type": "story_started"})
        story = await tell_story(body.start, body.target, path, mk)
        if story:
            await emit({"type": "story", "text": story})

    async def emit(e: dict):
        e = {**e, "wall": round(time.time() - t0, 2)}
        if e.get("type") == "lane_error" and e.get("lane") == "cerebras" and e.get("auth"):
            _auto_pause_now()  # the key/model stopped working (e.g. hackathon access ended): replays only for a while
        e.pop("auth", None)
        history.append(e)
        if e.get("type") == "lane_done" and story_task["t"] is None:  # story as soon as the first lane wins
            story_task["t"] = asyncio.create_task(make_story(e["path"]))

    async def run():
        chosen = lanes(mk, with_gpu=gpu_ok)
        tasks: dict[str, asyncio.Task] = {}

        async def capped(l):
            try:
                return await asyncio.wait_for(run_lane(l, wiki, body.start, body.target, emit), LANE_TIMEOUT)
            except asyncio.TimeoutError:
                await emit({"type": "lane_timeout", "lane": l.id, "after": LANE_TIMEOUT})
                return None
            except asyncio.CancelledError:
                await emit({"type": "lane_stopped", "lane": l.id, "t": round(time.time() - t0, 2)})
                raise

        try:
            await emit({"type": "race_started", "start": body.start, "target": body.target, "gpu_paused": not gpu_ok,
                        "gpu_note": None if has_gpu_host else "no_host", "model": mk, "model_label": MODELS[mk]["label"],
                        "lanes": [{"id": l.id, "label": l.label} for l in chosen]})
            tasks = {l.id: asyncio.create_task(capped(l)) for l in chosen}
            if "cerebras" in tasks:
                try:
                    res = await asyncio.shield(tasks["cerebras"])
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    res = {"type": "lane_error", "error": str(exc)[:240]}
                if not res or res.get("type") != "lane_done":
                    # the fast lane couldn't run: stop everything now instead of making people wait 5 minutes
                    for k, t in tasks.items():
                        if k != "cerebras" and not t.done():
                            t.cancel()
                    await emit({"type": "race_aborted", "reason": (res or {}).get("error") or "Cerebras ran out of time."})
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            if story_task["t"]:
                try:
                    await asyncio.wait_for(asyncio.shield(story_task["t"]), 45)
                except Exception:  # noqa: BLE001 - a slow story never holds the race slot
                    story_task["t"].cancel()
        except asyncio.CancelledError:
            for t in tasks.values():
                t.cancel()
            if story_task["t"]:
                story_task["t"].cancel()
            raise
        finally:
            await emit({"type": "race_done"})
            done.set()
            try:
                save_run(rid, body, history)
            except Exception:  # noqa: BLE001
                pass
            await wiki.asave()

    races[rid]["task"] = asyncio.create_task(run())
    return {"race_id": rid}


@app.get("/api/race/{rid}/events")
async def events(rid: str, request: Request):
    r = races.get(rid)
    if not r:
        raise HTTPException(404, "unknown race")

    async def gen():
        sent, idle = 0, 0
        yield f"data: {json.dumps({'type': 'sync', 'wall': round(time.time() - r['t0'], 2)})}\n\n"
        while True:
            while sent < len(r["history"]):
                yield f"data: {json.dumps(r['history'][sent])}\n\n"
                sent += 1
            if r["done"].is_set() and sent >= len(r["history"]):
                break
            if await request.is_disconnected():
                break
            idle += 1
            if idle % 150 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/logos/{name}")
async def logo(name: str):
    f = ROOT.parent / "web" / "logos" / Path(name).name
    if f.suffix != ".svg" or not f.exists():
        raise HTTPException(404, "no such logo")
    return FileResponse(f, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/")
async def index():
    return FileResponse(ROOT.parent / "web" / "index.html")
