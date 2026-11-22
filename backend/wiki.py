"""Live Wikipedia access for the agent: canonical titles, summaries and body-only links.

Uses the MediaWiki Action API with a descriptive User-Agent (anonymous clients without one are
throttled to ~10 requests/min), at most 3 concurrent requests, Retry-After on 429, and an
in-memory cache so demo pages are fetched once.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote

import httpx

API = "https://en.wikipedia.org/w/api.php"
CACHE_FILE = Path(__file__).with_name("wiki_cache.json")
UA = "RabbitHole/1.0 (Wikipedia-game AI demo; https://airabbithole.pages.dev; https://github.com/rishabh-bansal/rabbit-hole) httpx"

# Sections whose links are not part of the article body.
STOP_SECTIONS = {"see also", "references", "notes", "external links", "further reading",
                 "bibliography", "sources", "citations", "footnotes", "works cited"}
# Elements whose links we skip entirely.
SKIP_CLASSES = ("navbox", "reflist", "references", "hatnote", "mw-references-wrap", "metadata",
                "sistersitebox", "side-box", "ambox", "noprint", "mw-editsection", "portalbox", "authority-control")


class _BodyLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.skip_depth = 0           # >0 while inside a skipped element
        self.stack: list[bool] = []   # per open tag: did it start a skip?
        self.stopped = False
        self.in_heading = False
        self.heading = ""

    def handle_starttag(self, tag, attrs):
        if self.stopped:
            return
        a = dict(attrs)
        cls = a.get("class") or ""
        starts_skip = any(c in cls for c in SKIP_CLASSES) or tag in ("sup", "style")
        if tag not in ("br", "img", "wbr", "hr", "meta", "link", "input"):
            self.stack.append(starts_skip)
            if starts_skip:
                self.skip_depth += 1
        if tag in ("h2", "h3"):
            self.in_heading, self.heading = True, ""
        if tag == "a" and not self.skip_depth:
            href = a.get("href") or ""
            if href.startswith("/wiki/") and "redlink" not in (a.get("class") or ""):
                t = unquote(href[6:].split("#")[0]).replace("_", " ")
                if t and ":" not in t:
                    self.links.append(t)

    def handle_endtag(self, tag):
        if tag in ("h2", "h3") and self.in_heading:
            self.in_heading = False
            if self.heading.strip().lower() in STOP_SECTIONS:
                self.stopped = True
        if self.stack and tag not in ("br", "img", "wbr", "hr", "meta", "link", "input"):
            if self.stack.pop():
                self.skip_depth -= 1

    def handle_data(self, data):
        if self.in_heading:
            self.heading += data


BAD_TITLE = re.compile(r"[|#<>\[\]{}\x00-\x1f]")
MAX_LINKS, MAX_INFO, MAX_REDIRECTS = 4000, 12000, 4000


def norm(title: str) -> str:
    """Wikipedia titles are case-sensitive except for the first letter; '_' means space."""
    t = re.sub(r"\s+", " ", title.replace("_", " ")).strip()
    return t[:1].upper() + t[1:]


def _trim(d: dict, cap: int) -> None:
    """Keep caches bounded: drop the oldest quarter when a cache grows past its cap."""
    if len(d) > cap:
        for k in list(d)[: cap // 4]:
            d.pop(k, None)


def _retry_after(value: str | None) -> float:
    try:
        return min(30.0, max(1.0, float(value)))
    except (TypeError, ValueError):
        return 5.0


class Wiki:
    def __init__(self, user_agent: str = UA) -> None:
        self._http = httpx.AsyncClient(headers={"User-Agent": user_agent}, timeout=httpx.Timeout(40, connect=10))
        self._sem = asyncio.Semaphore(3)
        self._inflight: dict[str, asyncio.Future] = {}
        self._links: dict[str, list[str]] = {}
        self._info: dict[str, dict] = {}
        self._redirects: dict[str, set[str]] = {}
        self._cache_file = CACHE_FILE
        try:
            data = json.loads(self._cache_file.read_text())
            self._links = data.get("links", {})
            # re-key by normalised title (older caches used lower-case keys, which mixed up "IT" and "It")
            self._info = {norm(v["title"]): v for v in data.get("info", {}).values() if isinstance(v, dict) and v.get("title")}
            self._redirects = {k: set(v) for k, v in data.get("redirects", {}).items()}
        except Exception:  # noqa: BLE001 - no cache yet
            pass

    def save(self) -> None:
        """Persist fetched pages so demo races never wait on Wikipedia (atomic write)."""
        try:
            data = json.dumps({"links": self._links, "info": self._info,
                               "redirects": {k: sorted(v) for k, v in self._redirects.items()}})
            tmp = self._cache_file.with_suffix(".tmp")
            tmp.write_text(data)
            os.replace(tmp, self._cache_file)
        except Exception:  # noqa: BLE001
            pass

    async def asave(self) -> None:
        await asyncio.to_thread(self.save)

    async def _get(self, params: dict) -> dict:
        """Both lanes ask for the same pages at the same moment: share one request per page."""
        key = json.dumps(params, sort_keys=True)
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(self._fetch(params))
            self._inflight[key] = task
            task.add_done_callback(lambda _t: self._inflight.pop(key, None))
        return await asyncio.shield(task)

    async def _fetch(self, params: dict) -> dict:
        params = {"format": "json", "formatversion": 2, **params}
        for attempt in range(4):
            try:
                async with self._sem:
                    r = await self._http.get(API, params=params)
            except httpx.TransportError:
                if attempt == 3:
                    raise
                await asyncio.sleep(1 + attempt)
                continue
            if r.status_code == 429 and attempt < 3:
                await asyncio.sleep(_retry_after(r.headers.get("retry-after")))
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("Wikipedia rate limit")

    async def resolve(self, title: str) -> dict:
        key = norm(title)
        if key in self._info:
            return self._info[key]
        if not key or BAD_TITLE.search(key) or len(key) > 255:  # "A|B" would look up two pages at once
            return {"title": key, "exists": False, "disambiguation": False, "url": "", "summary": ""}
        d = await self._get({"action": "query", "titles": title, "redirects": 1,
                             "prop": "pageprops|extracts|info", "exintro": 1, "explaintext": 1,
                             "exsentences": 2, "ppprop": "disambiguation", "inprop": "url"})
        page = (d.get("query", {}).get("pages") or [{}])[0]
        info = {
            "title": page.get("title", title),
            "exists": not page.get("missing", False) and "invalid" not in page,
            "disambiguation": "disambiguation" in (page.get("pageprops") or {}),
            "url": page.get("fullurl") or "https://en.wikipedia.org/wiki/" + page.get("title", title).replace(" ", "_"),
            "summary": re.sub(r"\s+", " ", page.get("extract", "")).strip()[:300],
        }
        self._info[key] = info
        self._info[norm(info["title"])] = info
        _trim(self._info, MAX_INFO)
        return info

    async def body_links(self, title: str) -> list[str]:
        canon = (await self.resolve(title))["title"]
        if canon in self._links:
            return self._links[canon]
        d = await self._get({"action": "parse", "page": canon, "prop": "text", "redirects": 1,
                             "disableeditsection": 1, "disabletoc": 1})
        p = _BodyLinks()
        await asyncio.to_thread(p.feed, d.get("parse", {}).get("text", ""))  # big pages: keep the event loop free
        seen, out = set(), []
        for t in p.links:
            k = t.lower()
            if k not in seen and k != canon.lower():
                seen.add(k)
                out.append(t)
        self._links[canon] = out
        _trim(self._links, MAX_LINKS)
        return out

    async def target_redirects(self, title: str) -> set[str]:
        canon = (await self.resolve(title))["title"]
        if canon in self._redirects:
            return self._redirects[canon]
        d = await self._get({"action": "query", "titles": canon, "prop": "redirects", "rdlimit": "max"})
        page = (d.get("query", {}).get("pages") or [{}])[0]
        names = {canon} | {r["title"] for r in page.get("redirects", [])}
        self._redirects[canon] = names
        _trim(self._redirects, MAX_REDIRECTS)
        return names

    async def suggest(self, text: str) -> list[str]:
        """Up to 3 article titles close to what was typed (for "Did you mean …?")."""
        try:
            d = await self._get({"action": "opensearch", "search": text, "limit": 3, "namespace": 0, "redirects": "resolve"})
            return [t for t in (d[1] if isinstance(d, list) and len(d) > 1 else [])][:3]
        except Exception:  # noqa: BLE001
            return []

    async def senses(self, title: str) -> list[str]:
        """Up to 3 specific meanings listed on a disambiguation page."""
        try:
            base = title.split(" (")[0].lower()
            links = await self.body_links(title)
            picks = [l for l in links if l.lower().startswith(base + " (") or l.lower().startswith(base + " ")]
            return (picks or links)[:3]
        except Exception:  # noqa: BLE001
            return []

    async def close(self) -> None:
        self.save()
        await self._http.aclose()
