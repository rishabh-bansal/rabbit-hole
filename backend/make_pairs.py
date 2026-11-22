"""Find "far, but not too far" Surprise me pairs: topics from different worlds that are exactly two
clicks apart on Wikipedia (start -> some article -> target), but not linked directly.

How: for each target, fetch the articles that link to it (backlinks). A pair (A, B) qualifies when
one of A's body links is a backlink of B, and that bridge really links to B in its body text (the
part the AI sees). Writes surprise_pairs.json and warms wiki_cache.json for every start page.

Usage: python make_pairs.py [max_pairs]
"""

import asyncio
import json
import random
import sys
from pathlib import Path

from topics import TOPICS
from wiki import Wiki

OUT = Path(__file__).with_name("surprise_pairs.json")
MAX_PAIRS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
PER_START = 3


async def backlinks(w: Wiki, title: str, pages: int = 6) -> set[str]:
    out, cont = set(), {}
    for _ in range(pages):
        d = await w._get({"action": "query", "list": "backlinks", "bltitle": title, "blnamespace": 0, "bllimit": "max",
                          "blfilterredir": "nonredirects", **cont})
        out |= {b["title"] for b in d.get("query", {}).get("backlinks", [])}
        if "continue" not in d:
            break
        cont = {"blcontinue": d["continue"]["blcontinue"]}
    return out


async def main() -> None:
    w = Wiki()
    groups = list(TOPICS)
    owner = {t: g for g, ts in TOPICS.items() for t in ts}
    everything = [t for ts in TOPICS.values() for t in ts]
    print(f"{len(everything)} topics; warming body links…", flush=True)
    links = {}
    for i, t in enumerate(everything):
        try:
            links[t] = {l.lower(): l for l in await w.body_links(t)}
        except Exception as e:  # noqa: BLE001
            print("  skip", t, e)
        if i % 20 == 0:
            print(f"  {i}/{len(everything)}", flush=True); w.save()
    w.save()
    print("fetching backlinks…", flush=True)
    back, redirects = {}, {}
    for i, t in enumerate(everything):
        try:
            back[t] = {b.lower() for b in await backlinks(w, t)}
            redirects[t] = {r.lower() for r in await w.target_redirects(t)}
        except Exception as e:  # noqa: BLE001
            print("  skip", t, e)
        if i % 20 == 0:
            print(f"  {i}/{len(everything)}", flush=True)

    random.seed(7)
    cands = [(a, b) for a in everything for b in everything if owner[a] != owner[b] and a in links and b in back]
    random.shuffle(cands)
    pairs, per_start, per_target = [], {}, {}
    for a, b in cands:
        if len(pairs) >= MAX_PAIRS:
            break
        if per_start.get(a, 0) >= PER_START or per_target.get(b, 0) >= PER_START:
            continue
        if links[a].keys() & redirects[b]:
            continue  # directly linked: too easy
        bridges = [links[a][k] for k in links[a].keys() & back[b]]
        random.shuffle(bridges)
        via = None
        for x in bridges[:4]:  # confirm the bridge links to the target in its body (what the AI sees)
            try:
                body = {l.lower() for l in await w.body_links(x)}
            except Exception:  # noqa: BLE001
                continue
            if body & redirects[b]:
                via = x
                break
        if via:
            pairs.append({"start": a, "target": b, "via": via})
            per_start[a] = per_start.get(a, 0) + 1
            per_target[b] = per_target.get(b, 0) + 1
            print(f"  {len(pairs):3d}. {a} → {via} → {b}", flush=True)
    w.save()
    OUT.write_text(json.dumps(pairs, indent=1, ensure_ascii=False))
    print(f"wrote {len(pairs)} pairs to {OUT.name}")
    await w.close()


if __name__ == "__main__":
    asyncio.run(main())
