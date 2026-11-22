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

from race import Lane, run_lane  # noqa: E402
from wiki import Wiki  # noqa: E402

app = FastAPI(title="Rabbit Hole")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
wiki = Wiki()

OPENCLAW = os.getenv("OPENCLAW_URL")  # e.g. http://127.0.0.1:18789/v1 ; unset = call providers directly (dev)
OC_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
LANE_TIMEOUT = float(os.getenv("RH_LANE_TIMEOUT", "300"))
FAST_MODEL = os.getenv("RH_CEREBRAS_MODEL", "moonshotai-kimi-k3.1-pro-trial")


def lanes() -> list[Lane]:
    if OPENCLAW:  # production: both lanes go through the OpenClaw gateway, one agent per provider
        return [
            Lane("cerebras", "Kimi K3.1 Pro · Cerebras", OPENCLAW, OC_TOKEN, "openclaw/" + os.getenv("RH_CEREBRAS_AGENT", "racer-cerebras")),
            Lane("gpu", "Kimi K3.1 Pro · NVIDIA GPU", OPENCLAW, OC_TOKEN, "openclaw/racer-nvidia"),
        ]
    effort = {} if "qwen" in FAST_MODEL else {"reasoning_effort": "low"}
    return [
        Lane("cerebras", "Kimi K3.1 Pro · Cerebras", "https://api.cerebras.ai/v1", os.getenv("CEREBRAS_API_KEY", ""), FAST_MODEL, effort),
        Lane("gpu", "Kimi K3.1 Pro · NVIDIA GPU", "https://integrate.api.nvidia.com/v1", os.getenv("NVIDIA_API_KEY", ""), "moonshotai/kimi-k3.1-pro", {"reasoning_effort": "low"}),
    ]


RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)


def save_run(rid: str, body, history: list[dict]) -> None:
    """Keep every finished race so it can be replayed exactly as it happened."""
    lanes_done = {e["lane"]: e for e in history if e.get("type") == "lane_done"}
    summary = {
        "id": rid, "start": body.start, "target": body.target, "created": time.time(),
        "lanes": {k: {"seconds": v["seconds"], "hops": v["hops"], "path": [p["title"] for p in v["path"]]} for k, v in lanes_done.items()},
        "outcome": {e["lane"]: e["type"] for e in history if e.get("type") in ("lane_timeout", "lane_error")},
        "story": next((e["text"] for e in history if e.get("type") == "story"), ""),
    }
    (RUNS / f"{rid}.json").write_text(json.dumps({"summary": summary, "events": history}))


@app.get("/api/runs")
async def list_runs(limit: int = 30):
    files = sorted(RUNS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:limit]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text())["summary"])
        except Exception:  # noqa: BLE001
            continue
    return {"runs": out}


@app.get("/api/runs/{rid}")
async def get_run(rid: str):
    f = RUNS / f"{rid.replace('/', '')}.json"
    if not f.exists():
        raise HTTPException(404, "unknown run")
    return json.loads(f.read_text())


def _summary(rid: str) -> dict | None:
    f = RUNS / f"{Path(rid).name}.json"
    try:
        return json.loads(f.read_text())["summary"] if f.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _featured() -> dict | None:
    """The race to show on the home page preview: latest race that Cerebras finished."""
    for f in sorted(RUNS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        s = _summary(f.stem)
        if s and s.get("lanes", {}).get("cerebras"):
            return s
    return None


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


@app.get("/api/surprise")
async def surprise():
    """Two well-known topics from different worlds (food vs space, pop stars vs history, ...)."""
    import random
    from topics import TOPICS
    ga, gb = random.sample(list(TOPICS), 2)
    return {"start": random.choice(TOPICS[ga]), "target": random.choice(TOPICS[gb])}


@app.get("/api/stats")
async def stats():
    """Time saved by Cerebras across all races: how much longer the GPU side took (a GPU that gave
    up counts as the time it had spent when it stopped)."""
    saved, races_n = 0.0, 0
    for f in RUNS.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        lanes = d["summary"]["lanes"]
        cb = lanes.get("cerebras")
        if not cb:
            continue
        gpu = lanes.get("gpu", {}).get("seconds")
        if gpu is None and d["summary"]["outcome"].get("gpu") == "lane_timeout":
            gpu = LANE_TIMEOUT
        if gpu is not None:
            saved += max(0.0, gpu - cb["seconds"])
            races_n += 1
    return {"seconds_saved": round(saved, 1), "races": races_n}


async def tell_story(start: str, target: str, path: list[dict]) -> str:
    """Kimi on Cerebras (through OpenClaw) turns the chain into a 3-sentence mini story."""
    from openai import AsyncOpenAI
    if OPENCLAW:
        client, model = AsyncOpenAI(base_url=OPENCLAW, api_key=OC_TOKEN, timeout=90, max_retries=3), "openclaw/storyteller"
    else:
        client, model = AsyncOpenAI(base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY", ""), timeout=90, max_retries=3), FAST_MODEL
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
    lanes: list[str] = Field(default_factory=lambda: ["cerebras", "gpu"])


# ---- protection for free credits (Cerebras trial, NVIDIA free credits, Wikipedia) ----
PER_IP_PER_HOUR = int(os.getenv("RH_PER_IP_PER_HOUR", "4"))
DAILY_RACES = int(os.getenv("RH_DAILY_RACES", "120"))
GPU_DAILY = int(os.getenv("RH_GPU_DAILY", "40"))            # NVIDIA free credits are the scarcest
REPLAY_ONLY_FILE = ROOT / "REPLAY_ONLY"                    # touch this file to stop live races instantly
_ip_hits: dict[str, list[float]] = {}
_day = {"date": "", "races": 0, "gpu": 0}


def _client_ip(request: Request) -> str:
    secret = os.getenv("RH_PROXY_SECRET", "")
    if secret and request.headers.get("x-rh-proxy") == secret and request.headers.get("x-rh-client-ip"):
        return request.headers["x-rh-client-ip"]  # visitor IP from our Cloudflare Pages proxy
    return (request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


def _check_quota(request: Request) -> bool:
    """Raises if this visitor or the day is over budget. Returns whether the GPU lane may run."""
    if REPLAY_ONLY_FILE.exists() or os.getenv("RH_REPLAY_ONLY") == "1":
        raise HTTPException(503, {"code": "paused", "message": "Live races are paused for today. Replays keep playing."})
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, races=0, gpu=0)
    if _day["races"] >= DAILY_RACES:
        raise HTTPException(503, {"code": "paused", "message": "We hit today’s limit. Replays keep playing, and live races are back tomorrow."})
    ip, now = _client_ip(request), time.time()
    hits = [t for t in _ip_hits.get(ip, []) if now - t < 3600]
    if len(hits) >= PER_IP_PER_HOUR:
        wait = max(1, int((3600 - (now - min(hits))) / 60) + 1)
        raise HTTPException(429, {"code": "ip_limit", "limit": PER_IP_PER_HOUR, "minutes": wait,
                                  "message": f"Each visitor gets {PER_IP_PER_HOUR} live races an hour, so the free credits last."})
    hits.append(now)
    _ip_hits[ip] = hits
    _day["races"] += 1
    gpu_ok = _day["gpu"] < GPU_DAILY
    if gpu_ok:
        _day["gpu"] += 1
    return gpu_ok


races: dict[str, dict] = {}
current: str | None = None


@app.get("/api/health")
async def health():
    return {"ok": True, "mode": "openclaw" if OPENCLAW else "direct", "today": _day,
            "replay_only": REPLAY_ONLY_FILE.exists() or os.getenv("RH_REPLAY_ONLY") == "1",
            "fast_model": os.getenv("RH_CEREBRAS_AGENT", "racer-cerebras") if OPENCLAW else FAST_MODEL,
            "busy": bool(current and not races[current]["done"].is_set()), "live": _live()}


def _live() -> dict | None:
    if current and not races[current]["done"].is_set():
        r = races[current]
        return {"id": current, "start": r["start"], "target": r["target"], "elapsed": round(time.time() - r["t0"], 1)}
    return None


@app.post("/api/race")
async def start_race(body: RaceIn, request: Request):
    global current
    if current and not races[current]["done"].is_set():
        raise HTTPException(429, {"code": "busy", "message": "Someone is racing right now.", "live": _live()})
    for t in (body.start, body.target):
        info = await wiki.resolve(t)
        field = "start" if t is body.start else "target"
        if not info["exists"]:
            raise HTTPException(422, {"code": "bad_input", "field": field, "kind": "missing", "value": t,
                                      "message": f"No Wikipedia article called “{t}”.", "options": await wiki.suggest(t)})
        if info["disambiguation"]:
            raise HTTPException(422, {"code": "bad_input", "field": field, "kind": "ambiguous", "value": t,
                                      "message": f"“{t}” is ambiguous. Be more specific:", "options": await wiki.senses(info["title"])})
    if current and not races[current]["done"].is_set():  # someone started while we were checking Wikipedia
        raise HTTPException(429, {"code": "busy", "message": "Someone is racing right now.", "live": _live()})
    gpu_ok = _check_quota(request)  # after input checks, so a typo doesn't use up a visitor's races
    if not gpu_ok:
        body.lanes = [l for l in body.lanes if l != "gpu"]
    rid = uuid.uuid4().hex[:10]
    q: asyncio.Queue = asyncio.Queue()
    history: list[dict] = []
    done = asyncio.Event()
    t0 = time.time()
    races[rid] = {"queue": q, "history": history, "done": done, "t0": t0, "start": body.start, "target": body.target}
    current = rid

    story_task = {"t": None}

    async def make_story(path):
        await emit({"type": "story_started"})
        story = await tell_story(body.start, body.target, path)
        if story:
            await emit({"type": "story", "text": story})

    async def emit(e: dict):
        e = {**e, "wall": round(time.time() - t0, 2)}
        if e.get("type") == "lane_error" and e.get("lane") == "cerebras" and any(
                k in e.get("error", "").lower() for k in ("401", "403", "model_not_found", "does not exist", "no access")):
            REPLAY_ONLY_FILE.touch()  # hackathon access ended: switch the site to replays automatically
        history.append(e)
        await q.put(e)
        if e.get("type") == "lane_done" and story_task["t"] is None:  # story as soon as the first lane wins
            story_task["t"] = asyncio.create_task(make_story(e["path"]))

    async def run():
        chosen = [l for l in lanes() if l.id in body.lanes]
        await emit({"type": "race_started", "start": body.start, "target": body.target, "gpu_paused": not gpu_ok,
                    "lanes": [{"id": l.id, "label": l.label} for l in chosen]})
        async def capped(l):
            try:
                return await asyncio.wait_for(run_lane(l, wiki, body.start, body.target, emit), LANE_TIMEOUT)
            except asyncio.TimeoutError:
                await emit({"type": "lane_timeout", "lane": l.id, "after": LANE_TIMEOUT})
        await asyncio.gather(*(capped(l) for l in chosen))
        wiki.save()
        if story_task["t"]:
            await story_task["t"]
        await emit({"type": "race_done"})
        done.set()
        save_run(rid, body, history)

    races[rid]["task"] = asyncio.create_task(run())
    return {"race_id": rid}


@app.post("/api/race/{rid}/stop")
async def stop_race(rid: str):
    r = races.get(rid)
    if r and not r["done"].is_set():
        r["task"].cancel()
        r["done"].set()
    return {"stopped": True}


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
