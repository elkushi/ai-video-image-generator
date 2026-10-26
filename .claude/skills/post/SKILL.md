---
name: post
description: Make a social post (single image or carousel, copy plus visual) for a brand in the factory, as 3 variants to pick from. Use when the user says "/post <brand> <topic>" or asks for a LinkedIn/Instagram post, a carousel, a post visual or post copy for a brand.
argument-hint: <brand-slug> <topic and any brief lines>
---

# /post

Arguments: `$ARGUMENTS`. The first word is the brand slug and the rest is the topic and brief. Missing lines are inferred.

1. Read `workflows/make_post.md` and follow it end to end. It is the master SOP.
2. If `brands/<slug>/` doesn't exist, run `/onboard-brand` first (`workflows/onboard_brand.md`).
3. Infer goal, platforms (default LinkedIn and Instagram), language, format (single or carousel) and aspect (default 4x5) from the topic and `brands/<slug>/profile.md`. Ask once, and only for blocking gaps: event date/time/link, an unknown fact, or an unclear language.
4. Free only, and facts only from `profile.md`. `post.json` must pass `tools/validate_post.py`. Run QA with `video-qa-reviewer` (Posts / stills) before showing anything.
5. Show the 3 variants (`previews/contact.jpg` plus one line each) and ask which one to deliver. Then run `tools/deliver_post.py --pick <X>` and finish with the output folder, files and `post.md`.
