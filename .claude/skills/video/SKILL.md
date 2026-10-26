---
name: video
description: Make a finished social video for a brand in the free video factory. Use when the user says "/video <brand> <topic>" or asks for a promo, educational, event, story or tutorial video for a brand.
argument-hint: <brand-slug> <topic and any brief lines>
---

# /video

Arguments: `$ARGUMENTS`. The first word is the brand slug and the rest is the topic and brief. Missing lines are inferred.

1. Read `workflows/make_video.md` and follow it end to end. It is the master SOP.
2. If `brands/<slug>/` doesn't exist, run `/onboard-brand` first (`workflows/onboard_brand.md`).
3. Infer goal, platforms, aspects and language from the topic and `brands/<slug>/profile.md`. Ask once, and only for blocking gaps: event date/time/link, an unknown fact, or an unclear language.
4. Free only, and facts only from `profile.md`. The storyboard must pass `tools/validate_storyboard.py`. Run QA with `video-qa-reviewer` yourself before showing anything; the user approves only the final video.
5. Finish with the output folder, MP4 paths, `post.md`, and any fallbacks used.
