---
name: series
description: Make a series of videos from topics the user gives (e.g. "three explainer videos: topic X, Y, Z"). Asks the important questions once, writes a series bible and every script, then produces every episode. Use when the user lists several topics for one brand or says "/series".
argument-hint: <brand-slug> <language/goal> topics: 1) ... 2) ... 3) ...
---

# /series

Arguments: `$ARGUMENTS`

1. Read `workflows/video_series.md` and follow it exactly.
2. **Ask before writing anything:** one AskUserQuestion round, covering audience/level, format, length/platform, tone/voice, visual style, on-screen help, series identity and whether the user wants to review the scripts. Skip anything the brief or `brands/<slug>/profile.md` already answers. If the app runs you headless (no AskUserQuestion), use the `@@QUESTION` line from `app/server/prompts/headless.md`, asking one question per turn.
3. Write `brands/<slug>/series/<series-slug>/bible.md` + `series.json`, then all the storyboards (`video-strategist` → `video-scriptwriter`, each validated), then produce each episode with `workflows/make_video.md` from step 4.
4. Finish with each episode's output folder, the posting order, and the fallbacks used.
