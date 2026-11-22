# Rabbit Hole — design round 2

> **Revision (latest, overrides the sections below):** the decorative layer has been removed, so these pieces now rely on type and hairlines only.
> - **Countdown:** no start lights, just the numeral and the pair. "Go" stays ember.
> - **Surprise me:** a small pill centred directly under Start the race, on mobile and desktop. It is 34 px tall inside a 44 px tap area, with a night background, a hairline outline, a small grey shuffle icon and "Surprise me" in 14 px. On hover the outline brightens and the fill turns smoke. Start the race is the only full-size button (full width of the form on desktop). Topics still roll and drop in, then the countdown plays.
> - **Example pairs:** inline underlined text links after "Try", not pills.
> - **Hall of fame:** one trophy-case box inside Recent races, under its heading and above the list. It is not three separate tiles.
>   - **Box:** a night surface, 16 px radius and a hairline, with the header "Hall of fame" on the left and "best of 6 races" on the right.
>   - **Top-edge effect:** a 1px ember line at 28% runs along the top, and a brighter ember highlight glides along it every 6 s.
>   - **Mobile:** three ruled rows. Each row has a 32 px smoke disc with an ember icon, the award name (12 px haze) above the race title (14 px, one line), and the value on the right (Hubot 20 px).
>   - **Desktop:** three columns split by hairlines. Each column has a 28 px disc plus the award name, the value (Hubot 30 px), then the race title on one line.
>   - **Hover:** the row or column gets a faint lift in fill, and its value turns ember. Each row or column opens that race's replay.
>   - **Reduce motion:** the gliding highlight and transitions are off.
> - **Recent races table (desktop):** a real aligned table. Every row shares one column template: race `1fr`, clicks 56 px, Cerebras 84 px, NVIDIA GPU 150 px, when 96 px, replay button 28 px, with a 24 px gap.
>   - **Header row:** 12 px haze labels, with the Cerebras and NVIDIA logos in their column headers.
>   - **Race cell:** two lines. "Pizza → Black hole" (16 px, the arrow in muted grey) above "via Pizza theorem · Geometry · …" (13 px haze), both one line with an ellipsis.
>   - **Numbers:** right-aligned with tabular figures. The Cerebras time is pearl (not ember), and the GPU result is in words ("Stopped at 5:00", "Ended with an error").
>   - **Rows:** separated by hairlines. Hover fills the row with night, and the round replay button fills pearl. Each row has an aria-label that reads the whole result.
>   - **Show all:** a "Show all 6 races →" link under the table.
>   - **Under 760 px:** only the race and Cerebras time columns remain.
> - **Recent races list (mobile):** each row is one 2×2 grid, so both lines align.
>   - **Line 1:** the race on the left, and the Cerebras logo plus time (16 px, tabular) on the right.
>   - **Line 2:** "4 clicks · 12 min ago" on the left (13 px haze), and the NVIDIA logo plus "stopped at 5:00" or "ended with an error" on the right (12 px haze).
>   - **Removed:** the header row and the play buttons.
>   - **Tap:** fills the row with night. Each row has a full aria-label, and a "Show all 6 races →" link sits under the list.
> - **Valid topic:** the plain one-line description in haze, with no ✓.
> - **Footer:** "Looking to contribute? GitHub →" is a single row (mobile) or a hairline-outlined button (desktop). Logos sit in one wrapping row at 85% opacity, with no cells or borders.
> - **Replay teaser:** sits between hairlines, not in a box.


## Final polish (latest; overrides anything above)
- **Numbers use Instrument Sans with tabular figures, not Hubot Sans.** Hubot draws zero with a slash, so "0:31.2" reads like "θ:31.2". Clocks, times, award values and step numbers all use Instrument Sans (weight 500). Hubot stays for headings and wordmarks.
- **Headings:** every h1/h2/h3 uses `text-wrap: balance`, and short article names in questions are `white-space: nowrap`, so no orphans like "Black / hole?".
- **One-line race names** (hall of fame, recent races, desktop table): render as from, a muted "→", then to. Each end truncates on its own with `max-width: 62%`, so both ends stay visible ("Llanfairpwllgw… → List of peo…"), and a short end like "Coffee" is never squeezed.
- **Names in images** (share image, link preview, video end card): cap each article name at 30 characters, cutting at a word boundary, plus "…". Single words over 22 characters are cut at 22, so nothing breaks mid-word.
- **Example pairs:** hairline chips with a 34 px pill inside a 44 px tap target. One swipeable row on mobile, one centred row (up to 940 px) on desktop. The selected pair gets a brighter hairline.
- **Mobile race:** the thinking-notes toggle sits in the trail header ("Trail · each step is a real link" … Thinking notes). There is no sticky footer, and the small print sits after the trail.
- **Desktop race:** lane padding is 26/40/18 px, lane gap 20 px and trail rows 8 px, so every moment fits 1440×810. The header shows "Live" while racing and "Finished" once both lanes have ended.
- **Link preview bottom row:**
  - the Cerebras time (124 px, never wraps)
  - the NVIDIA result (34 px, never wraps)
  - on the right, stacked: logos, then airabbithole.pages.dev (22 px), then #KimiOnCerebras (20 px)
  - question sizes are 68, 56 or 46 px by length, always balanced and at most 2 lines
- **Hackathon stripe:** sits above every app screen. The state and input sheets leave it out to keep the focus on the state.
- **Reference screenshots:** `screens/*.png`, rendered from these boards with the real fonts and logos.

Read `HANDOFF.md` first; everything there still applies. This file covers only the new pieces. The new boards are in `design/`, and the logos (colour icons plus wordmarks from @lobehub/icons, recoloured for the dark ground) are in `logos/`.

| File | What it shows |
|---|---|
| MobileHome / Ask | Home with every new piece: stripe, Surprise me, hall of fame, recent races, footer. Both are interactive: Start and Surprise me play the full sequence. |
| MobileInput / DesktopInput | Topic fields: suggestions while typing, valid, typo, ambiguous, Surprise me landing |
| CountdownMobile / CountdownVideo | 3-2-1 Go, looping so you can watch it |
| CountdownStill | The countdown with reduce motion on |
| LinkPreviews | 1200×630 template: Replay, Latest race, GPU error, long titles, fallback |
| StressMobile / StressMedia | Long titles and a 12-click chain on race, answer, lists, share image and video end card |

## 1. Countdown (about 1 s, the race is already running behind it)
- An ink overlay at 92% covers the race screen. Three start lights sit above a huge Hubot Sans 500 numeral, and the pair ("Pizza → Black hole") sits below.
- Timing: 3 at 0 ms, 2 at 250, 1 at 500, Go at 750. Each numeral scales from 1.5 to 1 and fades over 260 ms with `cubic-bezier(.19,1,.22,1)`.
- The lights fill pearl one by one, and all three turn ember on Go. "Go" is ember and slightly smaller. Then the overlay fades out over about 300 ms.
- Sizes: phone numeral 220–240 px, desktop 320 px, video 560 px.
- Reduce motion keeps the same timing, but numerals swap in place with no scale and no fade.
- Give the overlay `aria-live="assertive"`.

## 2. Surprise me
- Its own button, the same height as Start the race and sitting beside it.
  - Start the race is the primary pearl button. Surprise me is the secondary smoke `#2A2926` button with an ember dice icon.
  - Under the pair, one line: "Surprise me picks two topics from different worlds and starts right away."
- When pressed:
  1. The dice spins once (600 ms) while both fields roll through random topics every 70 ms.
  2. About 650 ms in, the real pair lands: each field drops 10 px into place, and both fields get an ember ring with their "✓ description" lines.
  3. About 450 ms later the countdown starts.
- Example pairs stay as plain chips. Surprise me is no longer one of them.

## 3. Hall of fame (above Recent races)
- Three trophy cards on the night surface, each with:
  - a 1px ember line on the top edge
  - a very slow sheen that sweeps across every 7–8 s (off under reduce motion)
  - an ember icon and award name
  - the value in Hubot 34–44 px
  - the race title on one line with an ellipsis
- Each card opens that race's replay. On mobile the cards scroll sideways with scroll snap; on desktop they sit in a 3-column row.
- Awards:
  - **Fastest find**: stopwatch icon, e.g. 29.4 s, Pizza → Black hole
  - **Deepest rabbit hole**: the rings mark, e.g. 12 clicks, the Llanfair… race (using the real deepest race makes this award more interesting than 4 clicks)
  - **Most waiting saved**: hourglass icon, e.g. 4 min 30 s
- A possible 4th later: "Longest leap", the most surprising single click, if the agent can score it.

## 4. Live topic suggestions
- **Dropdown:** opens 6 px under the field on the night surface with a hairline and a soft shadow.
  - Each row shows the title (the typed part in bold) and Wikipedia's one-line description: below the title on mobile, right-aligned on desktop.
  - Rows are 52–56 px tall, the first row is highlighted, and arrow keys plus Enter work.
- **Valid:** "✓ {description}" in 13 px under the field, with the ✓ in ember.
- **Typo:** the field gets an ember ring, then the line "No Wikipedia article called “X”." followed by a one-tap chip "Did you mean **Y**?".
- **Ambiguous:** "“Mercury” has several meanings. Pick one:" followed by a list of meanings with descriptions.
- **Blocked Start:** the button is disabled (smoke background, haze text) with a reason under it, e.g. "Fix “Pizzza” to start".

## 5. Footer
1. **GitHub card:** a night surface with the GitHub mark, "Looking to contribute?", "Rabbit Hole is open source. Issues and PRs welcome." and "GitHub →" in ember. On hover the ring turns ember. Link: github.com/rishabh-bansal/rabbit-hole.
2. **Credit line**, word for word as in the round-2 brief.
3. **Logo row:** Claude, Kimi K3.1 Pro, Cerebras, NVIDIA, OpenClaw. Each sits in an equal cell between hairlines, with a 20 px colour icon plus its wordmark, centred.
   - To make the row look even, the wordmark heights are tuned by eye: Claude 16, Kimi 16 (+ "K3.1 Pro" in 14 px haze), cerebras 18 (lowercase reads small), NVIDIA 13 (all-caps reads big), OpenClaw 15.
   - Mobile uses a 2-column grid of 56 px cells.

## 6. Link preview (1200×630, readable at about 500 px wide)
- **Top:** the Rabbit Hole mark and a "Replay" or "Latest race" tag (none on the fallback).
- **Middle:** the question in Hubot 500 at 68 px, clamped to 2 lines and shrinking to 62, then 44 px, as it gets longer. Below it, the chain in 26 px with " → " between steps, clamped to 2 lines.
- **Bottom:**
  - the Cerebras time as the hero (124 px, ember)
  - the NVIDIA result in 40 px haze: "5:00 still thinking", a time, or "did not finish"
  - on the right: the Kimi, Cerebras, NVIDIA and OpenClaw icons, then "airabbithole.pages.dev · #KimiOnCerebras"
- **Fallback:** "How are two things connected?" at 84 px and one line of explanation.

## 7. Hackathon stripe
- A 36 px night bar above everything on the home, race, answer and replay screens: "Built for the Cerebras × Kimi hackathon. Sign up now →".
- 13 px haze text with an underlined pearl link. It wraps to 2 lines on narrow phones.
- Hide it in the video cards and film mode.
- The link is set to `#` on every board: **put in the hackathon sign-up URL.**

## 8. Long content rules
- Single huge words break anywhere (`overflow-wrap: anywhere`).
- **Race screen:** the question wraps freely. Trail titles clamp to 2 lines and reasons to 1. With more than 5 steps, keep the last 4 and fold the rest into a "Show N earlier steps" row.
- **Answer page:** always lists the full chain, and titles wrap.
- **Lists:** recent-race titles clamp to 2 lines on mobile and 1 on desktop. Hall-of-fame titles are 1 line.
- **Share image, link preview and video end card:** keep the first 2 steps, then "… N more", then the last 3. Each step is one line with an ellipsis. The question shrinks and clamps (2 lines in the preview, 4 in the share image).
- **Sample steps:** the middle steps of the Llanfair chain in the stress boards are placeholders. Use the real ones.

## Numbers used
- Pizza race: 29.4 s.
- Odometer: 24 min over 6 races (the race screen starts at 19 min 29 s over 5 and grows to 24 min).
- Coffee: the GPU lane ended with an error.
- Surprise examples: Super Mario → Mitochondria, Frida Kahlo → Black hole, Surfing → Mount Everest.
