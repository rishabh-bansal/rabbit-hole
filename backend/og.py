"""Share image (Open Graph / X card) for Rabbit Hole, drawn with Pillow from a saved race.

1200x630 PNG in the Claude Design style: the question, the winning chain, both clocks and the
brand logos (from @lobehub/icons). Used by /api/og.png for link previews on X and elsewhere.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).with_name("assets")
W, H = 1200, 630
INK, NIGHT, PEARL, HAZE, FOG, MUTE, EMBER = "#111110", "#191816", "#F5F4F0", "#A6A9A3", "#C8CAC4", "#55574F", "#D6B28A"
LINE = (245, 244, 240, 38)


@lru_cache(maxsize=None)
def font(kind: str, size: int, weight: int, width: int = 100) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(ASSETS / "fonts" / ("HubotSans.ttf" if kind == "hub" else "InstrumentSans.ttf")), size)
    f.set_variation_by_axes([width, weight])
    return f


@lru_cache(maxsize=None)
def logo(name: str, height: int) -> Image.Image:
    im = Image.open(ASSETS / "logos" / f"{name}.png").convert("RGBA")
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


def fmt(x: float) -> str:
    if x < 60:
        return f"{int(x * 10) / 10:.1f} s"
    m, s = divmod(int(x * 10) / 10, 60)
    return f"{int(m)}:{s:04.1f}"


def mark(d: ImageDraw.ImageDraw, x: int, y: int, s: int) -> None:
    k = s / 30
    def ring(cy, r, a):
        col = (214, 178, 138, int(255 * a))
        d.ellipse([x + (15 - r) * k, y + (cy - r) * k, x + (15 + r) * k, y + (cy + r) * k], outline=col, width=max(2, round(2 * k)))
    ring(15, 13.5, 1); ring(17.2, 9.4, .6); ring(19.4, 5.3, .35)
    d.ellipse([x + 13 * k, y + 19 * k, x + 17 * k, y + 23 * k], fill=EMBER)


def split_long(d, word, f, max_w):
    """Break a single word that is wider than the box (e.g. Llanfairpwllgwyngyll…) into pieces."""
    parts, cur = [], ""
    for ch in word:
        if cur and d.textlength(cur + ch, font=f) > max_w:
            parts.append(cur); cur = ch
        else:
            cur += ch
    return parts + [cur]


def wrap_tokens(d, tokens, f, max_w):
    lines, cur, w = [[]], 0, 0
    sp = d.textlength(" ", font=f)
    for text, col in tokens:
        words = [p for wd in text.split() for p in (split_long(d, wd, f, max_w) if d.textlength(wd, font=f) > max_w else [wd])]
        for word in words:
            ww = d.textlength(word, font=f)
            need = (sp if lines[-1] else 0) + ww
            if w + need > max_w and lines[-1]:
                lines.append([]); w = 0; need = ww
            lines[-1].append((word, col, ww)); w += need
    return lines, sp


def paste(img, im, x, y):
    img.alpha_composite(im, (round(x), round(y)))


def render(summary: dict | None, kicker: str = "Latest race") -> bytes:
    img = Image.new("RGBA", (W, H), INK)
    d = ImageDraw.Draw(img)
    # header
    mark(d, 56, 48, 30)
    d.text((98, 50), "Rabbit Hole", font=font("hub", 22, 600), fill=PEARL)
    site = "airabbithole.pages.dev"
    d.text((W - 56 - d.textlength(site, font=font("ins", 20, 500)), 52), site, font=font("ins", 20, 500), fill=FOG)

    lanes = (summary or {}).get("lanes", {})
    cb = lanes.get("cerebras")
    if not summary or not cb:  # no finished race yet: a generic card
        d.text((56, 170), "How are two things", font=font("hub", 78, 500), fill=PEARL)
        d.text((56, 258), "connected?", font=font("hub", 78, 500), fill=PEARL)
        d.text((56, 368), "An AI plays the Wikipedia game. Same model, two chips.", font=font("ins", 28, 400), fill=HAZE)
        footer(img, d)
        return png(img)

    # left: kicker + question
    d.text((56, 128), kicker, font=font("ins", 20, 500), fill=HAZE)
    tokens = [("How is", HAZE), (summary["start"], PEARL), ("connected to", HAZE), (summary["target"] + "?", PEARL)]
    box_h = 222  # between the kicker and the clocks
    for size in (52, 46, 40, 36, 32, 28):  # shrink until the whole question fits
        qf = font("hub", size, 500)
        lines, sp = wrap_tokens(d, tokens, qf, 560)
        lh = round(size * 1.08)
        if len(lines) * lh <= box_h:
            break
    max_lines = box_h // lh
    if len(lines) > max_lines:  # still too long at the smallest size: cut the last line with an ellipsis
        lines = lines[:max_lines]
        last = lines[-1]
        while last and sum(w for _, _, w in last) + sp * len(last) + d.textlength("…", font=qf) > 560:
            last.pop()
        last.append(("…", HAZE, d.textlength("…", font=qf)))
    y = 162
    for line in lines:
        x = 56
        for word, col, ww in line:
            d.text((x, y), word, font=qf, fill=col); x += ww + sp
        y += lh
    # clocks
    ty = 400
    d.line([(56, ty), (616, ty)], fill=LINE, width=1)
    d.line([(336, ty), (336, ty + 120)], fill=LINE, width=1)
    paste(img, logo("cerebras-color", 26), 56, ty + 20); paste(img, logo("cerebras-text", 20), 88, ty + 23)
    d.text((56, ty + 56), fmt(cb["seconds"]), font=font("hub", 56, 500), fill=EMBER)
    paste(img, logo("nvidia-color", 26), 360, ty + 20); paste(img, logo("nvidia-text", 17), 392, ty + 25)
    gpu, outcome = lanes.get("gpu"), (summary.get("outcome") or {}).get("gpu")
    if gpu:
        d.text((360, ty + 56), fmt(gpu["seconds"]), font=font("hub", 56, 500), fill=HAZE)
    elif outcome == "lane_timeout":
        d.text((360, ty + 56), "5:00", font=font("hub", 56, 500), fill=HAZE)
        d.text((360 + d.textlength("5:00", font=font("hub", 56, 500)) + 10, ty + 86), "still thinking", font=font("ins", 20, 500), fill=HAZE)
    else:
        d.text((360, ty + 70), "did not finish", font=font("ins", 26, 500), fill=HAZE)

    # right: the chain
    px, py, pw, ph = 660, 120, 484, 412
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=24, fill=NIGHT)
    for (ax, ay, dx, dy) in ((px + pw + 12, py - 12, -1, 1), (px - 12, py + ph + 12, 1, -1)):
        d.line([(ax, ay), (ax + 22 * dx, ay)], fill=EMBER, width=2); d.line([(ax, ay), (ax, ay + 22 * dy)], fill=EMBER, width=2)
    path = cb["path"]
    steps = list(enumerate(path))
    if len(steps) > 7:
        steps = steps[:3] + [(-1, "…")] + steps[-3:]
    row = min(62, (ph - 56) / len(steps))
    y = py + 28 + ((ph - 56) - row * len(steps)) / 2
    tf, nf = font("hub", 28, 500), font("hub", 16, 700)
    for k, (i, title) in enumerate(steps):
        last = i == len(path) - 1
        if i >= 0:
            d.text((px + 32, y + row / 2 - 9), f"{i + 1:02d}", font=nf, fill=EMBER)
        t = title
        while d.textlength(t, font=tf) > pw - 110 and len(t) > 4:
            t = t[:-2]
        if t != title:
            t = t.rstrip() + "…"
        d.text((px + 76, y + row / 2 - 17), t, font=tf, fill=EMBER if last else PEARL)
        if k < len(steps) - 1:
            d.line([(px + 32, y + row), (px + pw - 32, y + row)], fill=LINE, width=1)
        y += row
    footer(img, d)
    return png(img)


def footer(img, d):
    y = 572
    x = 56
    paste(img, logo("kimi-color", 24), x, y - 2); x += 32
    d.text((x, y), "Kimi K3.1 Pro", font=font("ins", 19, 500), fill=FOG); x += d.textlength("Kimi K3.1 Pro", font=font("ins", 19, 500)) + 24
    paste(img, logo("cerebras-color", 24), x, y - 2); paste(img, logo("cerebras-text", 18), x + 30, y + 1); x += 30 + logo("cerebras-text", 18).width + 24
    paste(img, logo("nvidia-color", 24), x, y - 2); paste(img, logo("nvidia-text", 15), x + 30, y + 3); x += 30 + logo("nvidia-text", 15).width + 24
    paste(img, logo("openclaw-color", 24), x, y - 2); paste(img, logo("openclaw-text", 15), x + 30, y + 3)
    tag = "#KimiOnCerebras"
    d.text((W - 56 - d.textlength(tag, font=font("ins", 19, 600)), y), tag, font=font("ins", 19, 600), fill=HAZE)


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    import json, sys
    s = json.loads(Path(sys.argv[1]).read_text())["summary"] if len(sys.argv) > 1 else None
    Path(sys.argv[2] if len(sys.argv) > 2 else "og-test.png").write_bytes(render(s))
