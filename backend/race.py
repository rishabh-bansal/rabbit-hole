"""Rabbit Hole race engine: an AI agent plays the Wikipedia game.

Each hop is one model call through an OpenAI-compatible endpoint (the OpenClaw gateway in
production; a provider directly during development). The model sees the current page's body
links and calls the `go_to` tool with the next page and a one-line reason.

Rules enforced in code (not by the model): only links on the current page are allowed, no page
is visited twice, and if the target is linked from the current page the agent clicks it.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from openai import (APIConnectionError, APIError, APIStatusError, AsyncOpenAI, AuthenticationError,
                    PermissionDeniedError, RateLimitError)

from wiki import Wiki

MAX_HOPS = 12
MAX_LINKS_SHOWN = 400
QUEUE_RETRY_SECONDS = 60
# The fast lane normally answers in 2-10 s. If one call takes longer than this, the provider is
# overloaded (OpenClaw keeps retrying 429s inside a single call), so give up instead of waiting.
FAST_CALL_CAP = float(os.getenv("RH_FAST_CALL_CAP", "45"))
on_fast_answer: Callable[[], None] | None = None  # set by the server: records "Cerebras is answering"

SYSTEM = """You are playing the Wikipedia game. Goal: reach the TARGET article from the START article
by clicking links inside articles. You are on one article and see its links. Pick the single link
most likely to get closer to the target (think: broad hub topics like countries, sciences, history
often bridge distant subjects). Never pick a page already visited. Call the go_to tool exactly once.
The reason must be one short, plain-English sentence explaining how that page connects the current
page to the next step toward the target (it becomes part of the explanation shown to the user)."""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "go_to",
        "description": "Click a link on the current page.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "exact link title from the list"},
                "reason": {"type": "string", "description": "one short sentence: why this link"},
                "thinking": {"type": "string", "description": "2-3 short sentences: which 2-4 links you weighed and why you chose this one"},
            },
            "required": ["title", "reason", "thinking"],
        },
    },
}]

Emit = Callable[[dict], Awaitable[None]]


@dataclass
class Lane:
    id: str            # "cerebras" | "gpu"
    label: str         # shown on screen
    base_url: str
    api_key: str
    model: str
    extra: dict = field(default_factory=dict)       # e.g. {"reasoning_effort": "low"}
    headers: dict = field(default_factory=dict)


def _match(choice: str, links: list[str]) -> str | None:
    c = choice.strip().strip('"').replace("_", " ").lower()
    for l in links:
        if l.lower() == c:
            return l
    for l in links:  # tolerate small differences ("The Beatles" vs "Beatles")
        if l.lower().removeprefix("the ") == c.removeprefix("the "):
            return l
    return None


async def _call(client: AsyncOpenAI, lane: Lane, messages: list[dict]):
    """One model call; retries Cerebras-style 429 queue rejections quickly."""
    start = time.perf_counter()
    retried = False
    while True:
        try:
            return await client.chat.completions.create(
                model=lane.model, messages=messages, tools=TOOLS, tool_choice="required",
                max_tokens=2500, temperature=0.4, extra_headers=lane.headers or None, **lane.extra)
        except RateLimitError:
            if time.perf_counter() - start > QUEUE_RETRY_SECONDS:
                raise
            await asyncio.sleep(1.0 + random.random())  # gentle: Cerebras asked participants not to hammer the queue
        except (APIStatusError, APIConnectionError) as exc:
            # a provider hiccup (5xx or dropped connection): retry once; the lane's 5-minute cap still applies
            if retried or (isinstance(exc, APIStatusError) and exc.status_code < 500):
                raise
            retried = True
            await asyncio.sleep(2.0)


async def run_lane(lane: Lane, wiki: Wiki, start: str, target: str, emit: Emit) -> dict:
    client = AsyncOpenAI(base_url=lane.base_url, api_key=lane.api_key, timeout=300, max_retries=0)
    t0 = time.perf_counter()
    base = {"lane": lane.id}
    try:
        cur = (await wiki.resolve(start))["title"]
        tgt = await wiki.resolve(target)
        targets = {t.lower() for t in await wiki.target_redirects(tgt["title"])}
        path = [{"title": cur, "reason": "start"}]
        visited = {cur.lower()}
        start_info = await wiki.resolve(cur)
        await emit({**base, "type": "lane_started", "page": cur, "target": tgt["title"],
                    "summary": start_info.get("summary", ""), "url": start_info.get("url")})
        model_ms = 0
        tokens = 0
        for hop in range(MAX_HOPS):
            links = await wiki.body_links(cur)
            hit = next((l for l in links if l.lower() in targets), None)
            if hit:  # the target is one click away: take it (rule, no model call)
                path.append({"title": tgt["title"], "reason": f"{cur} links directly to {tgt['title']}."})
                await emit({**base, "type": "hop", "page": tgt["title"], "reason": path[-1]["reason"],
                            "hop": hop + 1, "ms": 0, "auto": True, "url": tgt.get("url"),
                            "summary": tgt.get("summary", ""), "t": time.perf_counter() - t0, "ai": round(model_ms / 1000, 2)})
                break
            options = [l for l in links if l.lower() not in visited][:MAX_LINKS_SHOWN]
            if not options:
                raise RuntimeError(f"dead end at {cur}")
            user = (f"TARGET: {tgt['title']} — {tgt.get('summary', '')}\n"
                    f"CURRENT ARTICLE: {cur}\n"
                    f"VISITED (do not pick): {', '.join(p['title'] for p in path)}\n"
                    f"LINKS ON THIS PAGE ({len(options)}): " + " | ".join(options))
            await emit({**base, "type": "thinking", "page": cur, "hop": hop + 1, "options": len(options),
                        "t": time.perf_counter() - t0, "ai": round(model_ms / 1000, 2)})
            h0 = time.perf_counter()
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
            if lane.id == "cerebras":
                try:
                    resp = await asyncio.wait_for(_call(client, lane, msgs), FAST_CALL_CAP)
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Cerebras didn't answer for {int(FAST_CALL_CAP)} s. Its shared endpoint is overloaded right now.") from None
                if on_fast_answer:
                    on_fast_answer()
            else:
                resp = await _call(client, lane, msgs)
            ms = int((time.perf_counter() - h0) * 1000)
            model_ms += ms
            usage = getattr(resp, "usage", None)
            tokens += getattr(usage, "completion_tokens", 0) or 0
            calls = resp.choices[0].message.tool_calls or []
            args = {}
            if calls:
                try:
                    args = json.loads(calls[0].function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
            nxt = _match(args.get("title", ""), options) or options[0]
            reason = (args.get("reason") or "").strip()[:240]
            thinking = (args.get("thinking") or "").strip()[:600]
            nxt_info = await wiki.resolve(nxt)
            nxt = nxt_info["title"]
            visited.add(nxt.lower())
            path.append({"title": nxt, "reason": reason})
            await emit({**base, "type": "hop", "page": nxt, "reason": reason, "thinking": thinking, "hop": hop + 1, "ms": ms,
                        "summary": nxt_info.get("summary", ""), "url": nxt_info.get("url"),
                        "t": time.perf_counter() - t0, "ai": round(model_ms / 1000, 2)})
            cur = nxt
            if cur.lower() in targets:
                break
        else:
            raise RuntimeError("hop limit reached")
        result = {**base, "type": "lane_done", "path": path, "seconds": round(time.perf_counter() - t0, 2),
                  "model_seconds": round(model_ms / 1000, 2), "completion_tokens": tokens, "hops": len(path) - 1}
        await emit(result)
        return result
    except (APIError, RuntimeError, Exception) as exc:  # noqa: BLE001
        err = {**base, "type": "lane_error", "error": str(exc)[:240], "t": time.perf_counter() - t0,
               "auth": isinstance(exc, (AuthenticationError, PermissionDeniedError))}
        await emit(err)
        return err
    finally:
        await client.close()
