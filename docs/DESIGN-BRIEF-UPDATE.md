# Rabbit Hole — update for the design (add to the first brief)

The app is now live at **airabbithole.pages.dev**, and real people will use it from the X post.
Please design for these things too.

## 1. One correction: "Show the thinking"
The AI doesn't stream its thoughts word by word. Instead, every click comes with a short
**thinking note** ("I weighed Ancient Egypt, Dog and Lion; Egypt has moon gods, so…"), shown
under that step. The toggle (off by default) shows or hides these notes inside each lane's trail.
Each step always shows its one-line reason either way.

## 2. Moments inside a race
- **Before the first step:** both clocks start, and both lanes say "reading the page…" for a couple of seconds.
- **Thinking:** "thinking about 270 links…" (the number is real and changes per page).
- **Direct hit:** when the current page links straight to the target, the AI clicks it instantly.
  Show that last step as a special "direct link!" moment.
- **Winning:** "found it in 3 clicks", with small stats: clicks · AI thinking time · total time.
- **Giving up:** the GPU lane is stopped at 5 minutes: "still not there after 5 min — stopped".
  This happens in most races, so it needs to look intentional and funny, not like a crash.
- **The story arrives a few seconds after the win:** show "Kimi is writing the story…", then
  the 3-sentence story. It belongs with the answer/share card.

## 3. Busy and limit states (to protect free credits; visitors will hit these)
Each should feel friendly and always offer something to watch (a replay), never a dead end:
- **A race is already running:** only one live race at a time. Offer to watch the race that's running.
- **Personal limit:** each visitor gets 4 live races per hour → "enjoy the replays, come back soon".
- **Daily limit reached / live races paused:** the site switches to replay-only mode and says so.
- **GPU side paused:** when the GPU's daily budget runs out, races run with only the Cerebras lane.
  The layout must still look good with one lane, with a small note that the GPU side is resting.
- **Bad input:** "No Wikipedia article called X" or "X is ambiguous, be more specific".
- **Something broke mid-race:** a lane can end with an error message.

## 4. Replays
Every finished race is saved. Clicking a past race replays it exactly as it happened, at real
speed or faster (e.g. 2×, 5×). A replay must be clearly labelled "Replay" so nobody mistakes it
for a live race. When live races are busy, the page automatically plays the latest replay.
A link can open a replay directly, so people can share a specific race.

## 5. Share
- **Share card image:** the question, the chain, both times, the story's first line,
  "Kimi K3.1 Pro · Cerebras · OpenClaw", #KimiOnCerebras, airabbithole.pages.dev.
- **"Post on X" button:** opens X with a ready-made post (the chain, both times, the link,
  @Cerebras @Kimi_Moonshot #KimiOnCerebras).

## 6. The odometer
Always visible: "⏱ Waiting saved by Cerebras: 11 min 55 s over 3 races", growing after every
race. A GPU lane that gave up counts as 5 minutes.

## 7. Two video cards (for the 60-second muted X video)
Please also design two full-screen 16:9 cards in the same style:
- **Intro card:** "How is Pizza connected to Black holes?" plus the line "Same AI. Same question.
  Two different chips." (Cerebras orange vs NVIDIA GPU green).
- **End card:** the winning chain as the hero (the Rabbit Hole map fits well here), the two times,
  and airabbithole.pages.dev.

## 8. Real numbers you can use in mockups
- Pizza → Pizza theorem → Geometry → General relativity → Black hole: Cerebras 29.5 s, GPU stopped at 5 min
- Cat → Ancient Egypt → Solar deity → Moon: Cerebras 40.5 s, GPU stopped at 5 min
- Coffee → Haitian Revolution → French Revolution: Cerebras 40.8 s, GPU stopped at 5 min
- Each click takes Cerebras about 2–10 s. On the GPU, the first click alone can take 2–5 minutes.
