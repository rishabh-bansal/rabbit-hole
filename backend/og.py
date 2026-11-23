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


def cap(name: str, n: int = 30, word: int = 22) -> str:
    """Names in images: at most 30 characters (cut at a word boundary), single words at most 22."""
    words = [w if len(w) <= word else w[:word] + "…" for w in name.split()]
    out = " ".join(words)
    if len(out) <= n:
        return out
    cut = out[:n].rsplit(" ", 1)[0] if " " in out[:n] else out[:n]
    return cut.rstrip(" ,;:-") + "…"


def chain_text(path: list[str]) -> list[str]:
    names = [cap(x) for x in path]
    if len(names) > 6:
        names = names[:2] + [f"… {len(names) - 5} more"] + names[-3:]
    return names


def tag(d, text, right, top):
    f = font("ins", 20, 600)
    w = d.textlength(text, font=f)
    d.rounded_rectangle([right - w - 28, top, right, top + 38], radius=8, outline=(245, 244, 240, 110), width=2)
    d.text((right - w - 14, top + 7), text, font=f, fill=PEARL)


def render(summary: dict | None, kicker: str = "Latest race") -> bytes:
    img = Image.new("RGBA", (W, H), INK)
    d = ImageDraw.Draw(img)
    mark(d, 60, 50, 32)
    d.text((104, 52), "Rabbit Hole", font=font("ins", 26, 600), fill=PEARL)
    lanes = (summary or {}).get("lanes", {})
    cb = lanes.get("cerebras")
    if not summary or not cb:  # no finished race yet
        d.text((60, 250), "How are two things connected?", font=font("ins", 76, 600), fill=PEARL)
        d.text((60, 352), "Watch an AI race itself through Wikipedia, link by link, on Cerebras and on NVIDIA GPUs.", font=font("ins", 25, 400), fill=FOG)
        brand_stack(img, d, None)
        return png(img)
    tag(d, kicker, W - 60, 48)

    # the question: 68 / 56 / 46 px, at most 2 lines
    tokens = [("How is", HAZE), (cap(summary["start"]), PEARL), ("connected to", HAZE), (cap(summary["target"]) + "?", PEARL)]
    for size in (68, 56, 46, 40):
        qf = font("ins", size, 600)
        lines, sp = wrap_tokens(d, tokens, qf, W - 120)
        if len(lines) <= 2:
            break
    lines = lines[:2]
    lh = round(size * 1.06)
    y = 150 if len(lines) == 2 else 175
    for line in lines:
        x = 60
        for word, col, ww in line:
            d.text((x, y), word, font=qf, fill=col); x += ww + sp
        y += lh
    # the chain, at most 2 lines
    cf = font("ins", 25, 400)
    clines, csp = wrap_tokens(d, [(" → ".join(chain_text(cb["path"])), FOG)], cf, W - 120)
    y += 10
    for line in clines[:2]:
        d.text((60, y), " ".join(w for w, _, _ in line), font=cf, fill=FOG); y += 34

    # bottom row: Cerebras time (hero), NVIDIA result, brand stack
    by = 426
    paste(img, logo("cerebras-color", 24), 60, by); d.text((92, by), "Cerebras", font=font("ins", 21, 600), fill=PEARL)
    hero = fmt(cb["seconds"])
    hf = font("hub", 124, 500)
    d.text((54, by + 26), hero, font=hf, fill=EMBER)
    gx = 60 + d.textlength(hero, font=hf) + 36
    gpu, outcome = lanes.get("gpu"), (summary.get("outcome") or {}).get("gpu")
    paste(img, logo("nvidia-color", 22), gx, by + 62); d.text((gx + 30, by + 61), "NVIDIA GPU", font=font("ins", 20, 600), fill=PEARL)
    d.text((gx + 30 + d.textlength("NVIDIA GPU  ", font=font("ins", 20, 600)), by + 62), "free tier", font=font("ins", 18, 500), fill=HAZE)
    if not gpu and summary.get("gpu_note") == "no_host":  # NVIDIA's free tier doesn't serve this model: same model or no lane
        d.text((gx, by + 92), "doesn’t serve " + (summary.get("model_label") or "this model"), font=font("ins", 28, 400), fill=HAZE)
    else:
        gtxt = fmt(gpu["seconds"]) if gpu else "5:00 still thinking" if outcome == "lane_timeout" else "did not finish" if outcome == "lane_error" else "resting today"
        d.text((gx, by + 92), gtxt, font=font("ins", 34, 400), fill=HAZE)
    brand_stack(img, d, summary.get("model") or "kimi-k3.1-pro")
    return png(img)


MODEL_LOGO = {"kimi-k3.1-pro": "kimi-color", "gpt-oss-120b": "openai", "qwen-3.8-27b": "qwen-color"}


def brand_stack(img, d, mk: str | None):
    right = W - 60
    x = right
    names = ["openclaw-color", "nvidia-color", "cerebras-color", MODEL_LOGO.get(mk or "kimi-k3.1-pro", "kimi-color")]
    for name in names:
        im = logo(name, 26)
        x -= im.width
        paste(img, im, x, 466)
        x -= 12
    site = "airabbithole.pages.dev"
    f1, f2 = font("ins", 22, 600), font("ins", 20, 400)
    d.text((right - d.textlength(site, font=f1), 504), site, font=f1, fill=PEARL)
    tg = "#KimiOnCerebras" if (mk or "kimi-k3.1-pro") == "kimi-k3.1-pro" else "Powered by Cerebras"
    d.text((right - d.textlength(tg, font=f2), 538), tg, font=f2, fill=HAZE)


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    import json, sys
    s = json.loads(Path(sys.argv[1]).read_text())["summary"] if len(sys.argv) > 1 else None
    Path(sys.argv[2] if len(sys.argv) > 2 else "og-test.png").write_bytes(render(s))
