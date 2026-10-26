# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
source .venv/bin/activate        # venv already created; recreate with: python3 -m venv .venv
pip install -r requirements.txt   # add new tool dependencies here
```

New API keys go in `.env` and get a matching commented entry in `.env.example`. Run tools as `python tools/<script>.py`.

## Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**

- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**

- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself
- Example: If you need to pull data from a website, don't attempt it directly. Read `workflows/scrape_website.md`, figure out the required inputs, then execute `tools/scrape_single_site.py`

**Layer 3: Tools (The Execution)**

- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:

- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)
- Example: You get rate-limited on an API, so you dig into the docs, discover a batch endpoint, refactor the tool to use it, verify it works, then update the workflow so this never happens again

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. That said, don't create or overwrite workflows without asking unless I explicitly tell you to. These are your instructions and need to be preserved and refined, not tossed after one use.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:

1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

This loop is how the framework improves over time.

## File Structure

**What goes where:**

- **Deliverables**: Final outputs go to cloud services (Google Sheets, Slides, etc.) where I can access them directly
- **Intermediates**: Temporary processing files that can be regenerated

**Directory layout:**

```
.tmp/           # Temporary files (scraped data, intermediate exports). Regenerated as needed.
tools/          # Python scripts for deterministic execution
workflows/      # Markdown SOPs defining what to do and how
.env            # API keys and environment variables (NEVER store secrets anywhere else)
credentials.json, token.json  # Google OAuth (gitignored)
```

**Core principle:** Local files are just for processing. Anything I need to see or use lives in cloud services. Everything in `.tmp/` is disposable.

## Bottom Line

You sit between what I want (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.

## Video Factory (this project's main job)

Free AI video content factory: brand kit + topic → finished, on-brand social videos (LinkedIn, Instagram, TikTok/Shorts, web), in English, Arabic or Russian.

**Entry points**
- New client or product → `workflows/onboard_brand.md` (creates `brands/<slug>/`)
- "Make a video about X for <brand>" → `workflows/make_video.md` (master SOP)
- "Make a post / carousel / post visual about X for <brand>" → `workflows/make_post.md` (`/post`): 3 copy+visual variants, the user picks one, then delivery
- Formats, hooks, platform specs, scene library → `workflows/video_playbook.md`
- Several videos on topics the user lists ("three explainer videos: X, Y, Z") → `workflows/video_series.md` (`/series`): ask once, series bible, all scripts, then production
- A week or month of posts where Claude picks the topics → `workflows/content_calendar.md` (agent `content-planner`)
- Post stats from the user → `workflows/review_performance.md` (writes `brands/<slug>/performance.md`)
- Slash commands: `/video <brand> <topic>`, `/post <brand> <topic>`, `/series <brand> <topics>`, `/onboard-brand`, `/content-calendar <brand> <period>`
- After changing any tool or scene → `python tools/smoke_test.py --quick` must pass (this includes the post tools `tools/*_post.py`, `tools/post_html.py` and `hyperframes/templates/`)
- The local web app (type `vg` in a terminal) → `workflows/app.md`. It runs the same workflows headless (`claude -p`) and animates them live. Keep `tools/events.py` calls in place when editing tools.

**When the user sends a request**, infer goal, platform, aspects and language from the brief and brand profile. Ask once, and only for blocking gaps (event date/time/link, unknown facts). The user reviews only the final video, so run QA yourself (`video-qa-reviewer`) before showing anything.

**Agents** (`.claude/agents/`): `content-planner` (series) → `video-strategist` → `video-scriptwriter` → (tools) → `video-qa-reviewer`; `remotion-motion-designer` only for new or broken scenes. Posts: `post-copywriter` → `post-designer` → (tools) → `video-qa-reviewer` (Posts / stills). HyperFrames renders posts and Remotion renders videos. **Skills**: project-local `remotion-*` skills (official, from remotion-dev/skills), plus the global `social-content`, `marketing-psychology` and `copywriting` skills for post copy.

**Hard rules**
- **Free only.** No paid APIs or credits, including the connected Higgsfield/Freepik MCPs. Every AI step has a free fallback; ship with the fallback rather than spend.
- **Local-only, no accounts** (user's choice, 2026-10-21): no HF token, Kaggle, Pexels or Pixabay. Local models live in `.tmp/models/` (`tools/setup_local_models.py`). Anonymous free providers may still be tried first; `FACTORY_OFFLINE=1` makes it fully local.
- Facts come only from `brands/<slug>/profile.md`. Never invent numbers, clients, quotes or event details.
- Storyboards must PASS `tools/validate_storyboard.py` before rendering.
- Remotion licence: free for individuals and companies of up to 3 people. Larger teams need a Remotion company licence.
- Deliverables go to `output/<date>_<brand>_<slug>/` (local, per the user's choice). `.tmp/videos/` holds run folders and is disposable.

**Layout**: `brands/` (kits), `config/factory.json` (voices, pacing, free Space lists, loudness), `schemas/storyboard.schema.json` (contract), `studio/` (Remotion: `src/scenes/*`, `render.mjs`), `hyperframes/` (pinned HyperFrames CLI, `templates/post.css`, vendored GSAP; posts via `tools/render_post.py`), `schemas/post.schema.json` (post contract), `assets/music/` (royalty-free library).
