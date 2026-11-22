# Reddit post for r/cerebras (Reddit prize)

**Where:** https://www.reddit.com/r/cerebras · **Flair:** "Kimi K3.1 Pro Hackathon" (required for the Reddit prize)
**Attach:** the 60 s demo video (upload it to Reddit directly, so it plays inline). No keys or personal info on screen.

## Title (pick one)
- I made an AI play the Wikipedia game: Kimi K3.1 Pro races itself on Cerebras vs NVIDIA GPUs
- How is Pizza connected to Black holes? I let Kimi K3.1 Pro click through Wikipedia to find out (Cerebras vs GPU)
- Rabbit Hole: the Wikipedia game, but an AI plays it, live on Cerebras

## Body

**Rabbit Hole** is the Wikipedia game, played by an AI. You give it two topics, and Kimi K3.1 Pro
clicks through real Wikipedia links until it gets from one to the other. It explains every click in
one line, and writes a 3-sentence story of the chain at the end.

The twist: the **same model races itself on two kinds of hardware at once**. One lane runs on
Cerebras, the other on NVIDIA GPUs, through the same OpenClaw agent. Every click needs the model to
read a page of 200 to 600 links and decide, so speed compounds.

Real races from the site:

- Pizza → Pizza theorem → Geometry → General relativity → Black hole: **Cerebras 29.4 s**, GPU one click in and still thinking at 5:00
- Ballet → Italian Renaissance → Venice: **Cerebras 26.6 s**, GPU still thinking at 5:00
- Cat → Diana (mythology) → Lunar phase → Moon: **Cerebras 36.7 s**, GPU still thinking at 5:00

**Try it:** https://airabbithole.pages.dev (type any two topics, hit Surprise me, or watch replays of past races)
**Code:** https://github.com/rishabh-bansal/rabbit-hole (MIT)

How it works:
- **Agent:** OpenClaw runs two agents with the same model. The page streams every click live, and each race is saved so it can be replayed exactly.
- **Rules in code, not in the prompt:** only links that exist on the current page, no page twice, and if the target is linked it clicks it directly.
- **Live topic checks** use Wikipedia's own search in your browser, so typos get "did you mean" without spending any AI tokens.
- **Link previews** are generated per race, so a shared replay shows its own chain and times.

Honest notes:
- Both lanes run the exact same model, Kimi K3.1 Pro. Only the hardware differs, and the clocks are real elapsed time.
- The GPU lane uses NVIDIA's **free** API catalog tier. A lot of its time is spent waiting in NVIDIA's free queue, so this isn't a measurement of a paid GPU host. The site labels it that way.
- The shared hackathon endpoint has been busy today. If a live race can't start, the site says so up front and offers a replay instead of making you wait.

Built with Claude for the Kimi K3.1 Pro × Cerebras × OpenClaw hackathon. I'd love to hear which two topics you think are hardest to connect. Drop them in the comments and I'll race them.

---

# Discord "share-your-demo" entry (fields the organisers ask for)

**Project Name:** Rabbit Hole
**Team Members:** <your X handle> / <your Reddit handle>
**Project Description:** The Wikipedia game, but an AI plays it. Kimi K3.1 Pro clicks through real Wikipedia links to connect any two topics, explaining every step, while the same model races itself on Cerebras and on NVIDIA GPUs through OpenClaw. Every race is saved and replayable, with a shareable link preview and a short AI-written story of the chain.
**Demo Video:** <link to the X post or the uploaded video> (60 s)
**GitHub Repository:** https://github.com/rishabh-bansal/rabbit-hole
**Live:** https://airabbithole.pages.dev
