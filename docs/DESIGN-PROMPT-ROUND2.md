# Rabbit Hole: design round 2 (paste into Claude Design with your existing Rabbit Hole design)

Your Rabbit Hole design is live at airabbithole.pages.dev and people love it. We added a few new
pieces since your handoff. They work, but they were placed quickly without your eye. Please design
them properly so they belong to the same system (Orrery-based, ink background, pearl text, ember
only for wins and highlights, Hubot Sans for clocks and headings, Instrument Sans for everything
else, mobile first). Design the experience end to end; how it's built is our problem.

## New pieces to design

### 1. The 3-2-1 countdown
When someone presses Start the race (or Surprise me), a very fast countdown plays, about one second
in total: 3, 2, 1, Go. It is pure drama: the race is already starting behind it. It should feel like
the start of a race, punchy and confident, never in the way. It also appears at the start of our
60-second X video, so it must look great full screen at 16:9 as well as on a phone.
Show what it looks like under "reduce motion" too (the numbers still appear, without movement).

### 2. "Surprise me" deserves its own button
Right now Surprise me is just another chip in the row of example pairs (Pizza → Black hole,
Cat → Moon, ...), only tinted. It does something different: it picks two random well-known topics
from different worlds (a pop star and a cell part, a food and a planet) and starts the race right
away. Design a button that makes that obvious and tempting, on mobile and desktop, next to the form
and the example pairs. Think about a small moment when it's pressed (the two picked topics landing
in the From and To fields before the countdown).

### 3. Hall of fame at the top of Recent races
Above the list of recent races we now highlight the standout races as cards:
- Fastest find (e.g. Pizza → Black hole, 29.4 s, 4 clicks)
- Deepest rabbit hole (most clicks, e.g. Pizza → Black hole, 4 clicks)
- Most waiting saved (biggest gap between Cerebras and the GPU, e.g. Pizza → Black hole, 4 min 30 s)
Each card opens that race's replay. We want them to feel special (a subtle effect, an icon each),
like trophies, but calm and premium, not a casino. Mobile: they can scroll sideways. Desktop: a row.
Feel free to suggest a better set of 3 awards if you have one.

### 4. Live topic suggestions while typing
The From and To fields now check Wikipedia as you type:
- A suggestion list drops down under the field: article title plus Wikipedia's one-line
  description ("Taylor Swift · American singer-songwriter (born 1989)").
- After you pick or type a valid topic: a small confirmation under the field ("✓ Italian dish").
- Typo: "No Wikipedia article called “Pizzza”. Did you mean Pizza?" with a one-tap fix.
- Ambiguous: "“Mercury” has several meanings. Pick one:" with options (Mercury (planet),
  Mercury (element), Mercury (mythology)).
- Start is blocked until both topics are valid.
Please design the dropdown, the confirmation, and both error states for mobile and desktop.

### 5. Footer: "Built with Claude", the logo row, and "Looking to contribute?"
The bottom of the home page now has three parts:
- A credit line: "Built with Claude. Powered by Kimi K3.1 Pro on Cerebras, raced against the same
  model on NVIDIA GPUs, run by an OpenClaw agent. Every step is a real link on Wikipedia."
- A row of brand logos: Claude, Kimi K3.1 Pro, Cerebras, NVIDIA, OpenClaw (colour icons plus
  wordmarks from @lobehub/icons). They must sit together as one calm, even row (the wordmarks have
  very different shapes: lowercase "cerebras", all-caps "NVIDIA").
- "Looking to contribute? GitHub →": the project is open source at
  github.com/rishabh-bansal/rabbit-hole. Make this an inviting button for developers, not a
  footnote.
Mobile and desktop.

### 7. Hackathon stripe at the very top
A thin bar above everything: "Built for the Cerebras × Kimi hackathon. Sign up now →", linking to
the hackathon's sign-up page. It should invite people to join without shouting, fit on one line on
a 375 px phone (or wrap gracefully), and stay out of the video cards and film mode.

### 8. Everything must survive long content
Real races produce long and odd titles: "Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch",
"List of people who have walked on the Moon", "History of science and technology in the United
Kingdom", and chains of up to 12 clicks. Please show, for the race screen, answer page, recent
races, hall of fame, share image, link preview and video end card, how long titles wrap or
truncate and how a 12-step chain collapses (we currently keep the first 2 and last 3 with "…" in
the images, and shrink the question text until it fits).

### 6. Link preview image (the card people see when the link is shared on X, WhatsApp, Slack)
1200×630. It is generated automatically from real race data, so design it as a template:
- Home page link: the latest race ("Latest race").
- A replay link: that specific race ("Replay").
Content: Rabbit Hole mark, the question "How is Cat connected to Moon?", the chain of articles
(2 to 7 steps; long chains may collapse the middle with "…"), the Cerebras time (the hero number)
vs the NVIDIA GPU result ("5:00 still thinking", or a time, or "did not finish"), and the logos of
Kimi K3.1 Pro, Cerebras, NVIDIA and OpenClaw, plus airabbithole.pages.dev and #KimiOnCerebras.
It must read at thumbnail size in an X feed (it often shows around 500 px wide).
Also a fallback version for when there is no race yet: "How are two things connected?".

## Real content to use
- Pizza → Pizza theorem → Geometry → General relativity → Black hole: Cerebras 29.4 s, GPU stopped at 5:00
- Cat → Ancient Egypt → Solar deity → Moon: Cerebras 40.5 s, GPU stopped at 5:00
- Coffee → Haitian Revolution → French Revolution: Cerebras 40.8 s, GPU ended with an error
- Waiting saved by Cerebras so far: about 24 min over 6 races
- A long one for stress tests: Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch → Anglesey → Wales → United Kingdom → … → Exploration of the Moon → List of people who have walked on the Moon (12 clicks, 52.6 s)
- Surprise me examples: Super Mario → Mitochondria, Frida Kahlo → Black hole, Surfing → Mount Everest

## Keep
Everything else from your first design stays as it is (race screen, replay, answer page, states,
video cards). Keep the same wording rules: sentence case, no tracked caps, lanes identified by
logo not colour, ember only for wins and highlights. Logos come from @lobehub/icons (colour
icons, plus the Claude, Cerebras, NVIDIA and OpenClaw wordmarks).
