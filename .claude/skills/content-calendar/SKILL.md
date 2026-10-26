---
name: content-calendar
description: Plan and produce a series of social videos for one brand over a period (content calendar). Use when the user says "/content-calendar <brand> <period>" or asks for a week or month of posts.
argument-hint: <brand-slug> [period, e.g. "2 weeks"] [posts per week] [themes/events]
---

# /content-calendar

Arguments: `$ARGUMENTS`.

1. Read `workflows/content_calendar.md` and follow it.
2. Spawn the `content-planner` agent, then show the user one compact table to approve. That's the only approval for the plan.
3. Save the approved items to `brands/<slug>/calendar.json`, then make them one at a time with `workflows/make_video.md`, updating each item's status.
4. After posting, run `workflows/review_performance.md` so the next plan learns from the results.
