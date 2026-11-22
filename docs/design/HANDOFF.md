# Rabbit Hole — design handoff for Claude Code

Live app: airabbithole.pages.dev. This folder is the full design. Apply it to the existing app as a **visual + UX change only**. Keep the existing race engine, API, replay storage, limits logic and routes.

## What's in here
- `design/*.dc.html` — every screen. They are HTML mockups written in a small template format (`<x-dc>` markup, `{{ holes }}`, `<sc-if>`, `<sc-for>`, a `class Component` script). Read them as exact specs for layout, copy, sizes and colours, then rebuild them in the app's own framework. `support.js` is the design tool's runtime and is not included; you don't need it.
- `design/canvas.json` — board layout (which screen is which).
- `logos/` — official logos, recoloured for dark backgrounds (Cerebras icon and wordmark, NVIDIA, Kimi, OpenClaw).

| File | Screen |
|---|---|
| MobileHome | Mobile home: From/To fields, examples, auto-playing replay, recent races |
| Mobile | Mobile live race: two stacked clocks, lane switch, current page, trail |
| MobileAnswer | Mobile answer: times, Kimi's story, linked chain, Post on X |
| MobileReplay | Mobile replay: "Replay · not live" band, pause, 1×/2×/5×, scrubber, Copy link |
| MobileStates | 6 mobile states: race running, 4/hour limit, replay-only, GPU resting, bad input, mid-race error |
| Main | Desktop race. Fully animated with real timings. Props: `mode` live/replay, `gpu` on/paused (one-lane), `thinking`, `speed`, `moment` |
| Ask | Desktop home |
| Answer | Desktop answer + story + Post on X |
| States | Desktop busy/limit/error states |
| ShareCard | 1200×675 share image |
| VideoIntro / VideoEnd | 1920×1080 cards for the muted X video |

**Mobile is the primary design.** Most visitors arrive from X on a phone, so build mobile first and don't just shrink desktop.

## Design system (based on Orrery, toned down)
Colours:
- ink `#111110` (page), night `#191816` (surfaces, inputs), smoke `#2A2926` (selected chips/segments)
- text pearl `#F5F4F0`, secondary haze `#A6A9A3`, tertiary fog `#C8CAC4`, muted numbers `#55574F`
- hairlines `rgba(245,244,240,0.10)`, inner rules `rgba(245,244,240,0.07)`
- ember `#D6B28A`: only for the winning time, the odometer, "direct link" and focus rings
- Lanes are identified by **logo**, never by colour fills. Cerebras `#F15A29` and NVIDIA `#76B900` appear only inside their logos and a 6px status dot.

Type (Google Fonts):
- `Hubot Sans` (wdth 100–125, wght 500–700): clocks and big headings only, weight 500, normal width, `font-variant-numeric: tabular-nums` on every clock
- `Instrument Sans` 400–700: everything else, sentence case
- No tracked all-caps labels, no uppercase headings

Sizes:
- Mobile: H1 22–30px, clocks 40px, body 15px, labels 13px
- Desktop: clocks `clamp(56px, 6vw, 88px)`, current page 28px

Layout:
- Rows separated by hairlines, not boxed cards
- Radius 12–14px, primary button = pearl fill with ink text, 52px tall on mobile
- Touch targets ≥ 44px

## Behaviour and copy (keep the wording)
- **Model:** every lane says "running Kimi K3.1 Pro" with the Kimi logo. Small print: "Same model in both lanes. Only the chip differs. Clocks are real elapsed time."
- **Race start:** both clocks start and both lanes say "Reading the page…" for about 2 s.
- **Thinking:** "Thinking about N links…" with the real N for each page.
- **Direct hit:** the status turns ember ("Direct link to Black hole. Clicking."), and that trail step gets a "Direct link" tag.
- **Win:** "Found it in 4 clicks" plus "4 clicks · 19.3 s AI thinking · 29.5 s total".
- **Story:** "Kimi is writing the story…" appears until the story arrives, then "Read the story →". The answer page shows the 3 sentences.
- **GPU stopped:** "Stopped at 5 minutes — Still not there. It was still deciding where to go from Pizza." Clock goes grey at 5:00.0. While it's still running after Cerebras wins, the page label reads "Still on page 1".
- **Thinking notes:** the toggle is off by default. When on, each trail step shows its short note in italic quotes under the one-line reason, which is always visible.
- **Odometer:** "Waiting saved by Cerebras: X min Y s over N races". It grows live while the GPU lane is still running after Cerebras finishes. A stopped GPU counts as 5:00.
- **Replay:** always labelled ("Replay · recorded … · not live" band plus a Replay tag). Speeds 1×, 2×, 5×. The scrubber has a tick where Cerebras finished. Copy link opens that exact race. When live races are busy or paused, auto-play the latest replay.
- **Post on X:** opens `https://x.com/intent/post?text=` + encodeURIComponent of:
  ```
  How is {A} connected to {B}?
  {chain joined with " → "}
  Kimi K3.1 Pro on @Cerebras: {t}. On GPUs: still not there after 5 min.
  airabbithole.pages.dev @Kimi_Moonshot #KimiOnCerebras
  ```
- **Every state has a way out:** watch live, play a replay, or browse past races. No dead ends.

## Motion
- Easing `cubic-bezier(.19,1,.22,1)`
- New trail step fades and slides up 8px over 0.6 s
- Win block rises in over 0.7 s
- Screen sections fade up 16px over 0.9 s, staggered 80 ms
- Live dot breathes (opacity 0.3 → 1)
- Buttons scale to 0.98 when pressed
- Video end card: chain steps drop in one by one, 250 ms apart
- Turn all of it off under `prefers-reduced-motion`

## Sample content to replace with real data
Wikipedia link counts per page, click times inside each race, thinking notes, the story text, "12 min ago"-style timestamps, the 23-min cooldown, the bad-input examples. The race totals are real: Pizza 29.5 s, Cat → Moon 40.5 s, Coffee → French Revolution 40.8 s, with the GPU stopped at 5 min in each.
