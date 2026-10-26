# Workflow: Review performance (learn what goes viral for this brand)

## Objective
Close the loop. Record how posted videos actually performed, find the patterns (format, hook formula, length, language, platform), and feed them back into the brand's planning and the playbook. The next videos are then made from evidence, not guesses.

## Inputs
- The video(s): an output folder name, or a calendar item id.
- Stats per platform, pasted as text or sent as screenshots of the post insights. Collect whatever is available:
  - views / impressions
  - average watch time, or retention %
  - likes, comments, shares, saves
  - follows, and link clicks / registrations
- How long the post has been up. Compare posts at the same age: 48 h or 7 days.

## Steps
1. **Record.** Write `output/<run>/stats.json`:
   - `{"platform", "posted_at", "measured_at", "age_h", "views", "avg_watch_s", "retention", "likes", "comments", "shares", "saves", "follows", "clicks"}`
   - one entry per platform; missing fields are `null`
2. **Derive.** Take these from the run's `storyboard.json` and `strategy.md`:
   - goal, format and hook formula
   - hook text
   - length, language, aspect and visual style
   - fallbacks used
3. **Log.** Append one row per video and platform to `brands/<slug>/performance.md`, creating it from `brands/_template/performance.md` if it's missing. Columns:

   | date | run | platform | goal | format | hook formula | length | lang | views | watch % | shares + saves | notes |
   |---|---|---|---|---|---|---|---|---|---|---|---|

   "Watch %" is average watch time ÷ length. Shares and saves are the strongest signals for reach.
4. **Find patterns (once ≥ 5 rows).** Compare by format, hook formula, length band (<20 s, 20–40 s, >40 s), language and platform. Use medians, not single hits, and say how many videos each claim rests on. Rewrite the "What works for this brand" section at the top of `performance.md`. It holds 3–6 bullets, each with its evidence: "3-tips on LinkedIn: median 2.1k views vs 900 for promos (n=4 vs 3)".
5. **Generalise carefully.** If a pattern holds across ≥ 2 brands, or matches a known platform behaviour, add a dated line to the learnings log in `workflows/video_playbook.md`. Brand-specific findings stay in `performance.md`.
6. **Tell the user** the 2–3 takeaways and what will change in the next plan. `video-strategist` and `content-planner` read `performance.md` automatically.

## Edge cases
- **Too little data** (< 5 videos, or < 500 views each): record it, but don't claim patterns. Say "not enough data yet".
- **Paid boosts** distort reach: mark the row `boosted` in notes and leave it out of the patterns.
- **Screenshots:** read the numbers carefully, and ask once if a key number is unreadable. Never estimate.
