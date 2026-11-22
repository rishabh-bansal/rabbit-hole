# Rabbit Hole — design brief

**One line:** *The Wikipedia game — but an AI plays it.* Ask how any two things are connected
("How is Pizza connected to Black holes?") and watch an AI agent race through real Wikipedia
articles, link by link, until it gets there.

**Quick references for people:** "WikiRacing / The Wiki Game, played by AI." "A speedrun, but the
runner is an AI." "Like watching a GPS route itself through all of human knowledge."

## Why it exists
1. **It's genuinely fun and useful.** You get a surprising, sourced chain of how two ideas connect
   (Pizza → Pizza theorem → Geometry → General relativity → Black hole), with a one-line reason for
   each jump and a link to every real article. Great for curious people, students, trivia, settling
   arguments.
2. **It shows why AI speed matters.** The same AI (Kimi K3.1 Pro) races itself on two kinds of
   hardware at once: **Cerebras** vs **NVIDIA GPUs**. Each click requires the AI to read the page and
   think, so speed compounds: Cerebras usually finishes in ~15–30 seconds while the GPU version is
   still thinking about the first page. That race is the emotional hook.

It's a hackathon entry (Cerebras × Kimi K3.1 Pro × OpenClaw). The AI agent runs on OpenClaw. It will be
shown in a 60-second muted video on X and used by people who click the link.

## The experience
- **Ask:** two inputs read as a sentence — "How is ___ connected to ___?" — plus a few tempting
  example pairs (Pizza → Black hole, Taylor Swift → Quantum mechanics, Cat → Moon, Coffee → French
  Revolution, Minecraft → Ancient Egypt). One clear "Race" action.
- **The race (hero screen):** two lanes side by side, same question, same AI:
  - Left: Cerebras (orange). Right: NVIDIA GPU (green).
  - Each lane: a big running stopwatch, the article it's on right now (title + first lines), a live
    status ("reading the page…", "thinking about 270 links…", "opening the next page…"), and the trail
    of articles it has clicked so far, each with its one-line reason.
  - Small stats per lane: clicks so far, time spent thinking.
  - The **DONE moment** when a lane reaches the target must feel great. The other lane visibly still
    stuck on page 1 is the joke, keep it legible.
  - A lane can also end as "gave up after 5 minutes" or an error.
- **The answer:** when the winner finishes, a beautiful, shareable card: the chain from start to
  target with the reasons, links to each article, total time on each chip. Easy to screenshot or share.
- **Past runs:** a gallery of previous races (question, winner time vs other time, number of clicks,
  when). Click one to **replay** it at real speed (or faster), exactly as it happened, without running
  the AI again. Visitors should land on something exciting even before they type anything.
- **"Show the thinking" (optional, off by default):** a toggle that reveals the AI's live reasoning
  in each lane as it streams, so people can watch the two chips think side by side in real time.

## Feel
Fast, playful, a little like a racing game or a speedrun overlay, but clean and credible (it is also
a real research tool). Dark mode friendly. Must read instantly with the sound off and in a 16:9
screen recording: big clocks, big article titles, obvious winner. Works on mobile for people clicking
from X. Credit "Kimi K3.1 Pro · Cerebras · OpenClaw" tastefully; be honest in the small print that
clocks are real elapsed time and that both lanes use the same model.

## Facts to respect
- Real Wikipedia articles only; every step must be a link that exists on the previous page.
- Both lanes always run the same model; only the hardware differs.
- A race takes ~10–60 s on Cerebras and 1–5+ minutes on the GPU side.

## Extra features to design (the builder loves these)
- **Rabbit Hole map:** instead of a plain list, the winning chain draws itself as a glowing path
  across a constellation of articles (each article a star, each click a line). The losing lane's path
  stays short and dim. This is the hero visual and must be very screenshot-friendly.
- **Why-it's-connected story:** when the race ends, the AI turns the chain into a 3-sentence mini
  story ("Pizza hides a geometry theorem…"), so the result feels like an insight, not a list.
- **Share card:** one click makes a clean image of the result (question, chain/map, both clocks,
  "Kimi K3.1 Pro · Cerebras · OpenClaw", #KimiOnCerebras) ready to post on X. Every user becomes a mini-ad.
- **Surprise me:** one button that picks two wildly unrelated topics (Taylor Swift → Mitochondria) and
  races them. Lowers the effort for visitors and produces funny chains.
- **Time-saved odometer:** a running total across all races: "Hours of waiting saved by Cerebras so
  far" (sum of how much longer the GPU side took). Always visible, ticking up after each race.
