# Workflow: The Factory app (local web UI)

## What it is
A local web app (`app/`) that drives the same workflows as the chat, but with forms, smart questions, uploads and a live animation of the agents and tools. Start it by typing **`vg`** in any terminal (`~/.local/bin/vg`). It opens http://127.0.0.1:8787.

| Command | Does |
|---|---|
| `vg` | starts the app (rebuilds the UI if it changed) and opens the browser |
| `vg stop` / `vg status` / `vg logs` | stop / check / follow `.tmp/app/server.log` |
| `vg dev` | hot-reload mode for UI work (http://127.0.0.1:5173) |
| `./factory.sh [dev\|stop]` | the same, from the repo |

## How it works
- **Backend** (`app/server/`, FastAPI, same `.venv`) runs one job at a time (RAM).
  - A job is a headless Claude Code session: `claude -p … --output-format stream-json`, using the user's Claude login. There's no API key, and `apiKeySource` shows `none`.
  - It runs with `--strict-mcp-config` (no MCP servers, so paid connectors can't be called), an allow-list of tools, and `app/server/prompts/headless.md` appended to the system prompt.
- **Events:**
  - `stream_parser.py` maps Claude's stream to agent and tool events: `Agent` calls with `subagent_type`, `task_started` / `task_notification`, Bash calls to `tools/*.py`, text, and the result.
  - The Python tools emit exact progress through `tools/events.py`: stages, per-scene voice, per-image, render % with fps and ETA, QA checks and delivery. That goes to `<run>/events.jsonl`, and to `.tmp/app/jobs/<id>/tool_events.jsonl` when `FACTORY_JOB` is set.
  - Both streams merge into `.tmp/app/jobs/<id>/events.jsonl`, which the UI tails over SSE.
- **Intake questions:** `POST /api/intake/questions` runs `claude -p --json-schema app/server/schemas/intake.json` with `prompts/intake.md` (~60 s). It returns AskUserQuestion-style cards, plus an "understood" summary.
- **Questions during a run:** headless Claude can't call AskUserQuestion. It ends its turn with `@@QUESTION {json}`; the job becomes `waiting`, and the answer resumes the same session (`--resume`).
- **Job kinds:** video, series (`/series`), onboard (new brand → `/onboard-brand` then `/video`), revise (gallery "Request changes"), calendar (content-planner with `schemas/calendar_plan.json`), performance (learn from stats), post (`/post`, structured result `schemas/post_result.json`), onboard-only (new brand from a guide, or update an existing kit from a new guide).
- **Posts** (`workflows/make_post.md`, rendered by HyperFrames, not Remotion):
  - Intake with `kind: "post"` uses `prompts/intake_post.md` (goal, platforms, single vs carousel, visual preference, CTA and fact gaps).
  - `POST /api/jobs/post` (Brief + `post_format` auto|single|carousel, `aspect`, `motion`) runs `/post` up to the previews and stops. `job.result` = `{run: ".tmp/posts/<name>", summary, variants[{id, angle, why}]}`; if Claude returns no structured result, `jobs.py` fills it from the run seen in the tool events.
  - The Runs page then shows the variant picker: `GET /api/posts/<name>` (post.json + `previews/index.json` + picked/output). "Pick this one" calls `POST /api/posts/<name>/pick {variant, copy?}`, which writes `copy_edits.json` and runs `tools/deliver_post.py` synchronously (no Claude, a few seconds). "Regenerate" calls `POST /api/posts/<name>/revise {feedback, variants?}`, a new post job on the same run folder.
  - The Gallery lists post folders (`output/<name>/post.json`, no MP4 needed) with `kind: "post"`, slide images, `cover.jpg`, `carousel.pdf` and `motion.mp4` if rendered.
- **Brands from a guide:** `POST /api/brands {name, website?, notes?, uploads?}` starts an onboard-only job (`workflows/onboard_brand.md` from the uploaded guide PDF, logos and fonts, finishing with a test post). `POST /api/brands/<slug>/guide {uploads, notes?}` updates an existing kit from a new guide and keeps the approved facts. Any company works; nothing in the app is brand-specific.

## Pages
Create (Video | Series | Post, brief, brand, uploads, smart questions; `/?mode=post&brand=<slug>` preselects) · Variant picker on a finished post run (3 cards, slides, editable copy per platform, pick, regenerate) · Live runs (factory floor / graph, timeline with ETAs, live feed, question cards) · Gallery (players per aspect, post copy with copy buttons, QA and transcript, script, strategy, revise) · Brands (new brand from guide, update from guide, make a post) · Calendar (plan → approve → make) · Stats (add numbers, median views per format, "learn").

## Quirks (2026-10-21)
- Headless Bash calls must match the allow-list in `app/server/settings.py`. Compound commands (`cd x && …`, pipes) are denied, which is why `headless.md` says to call `.venv/bin/python tools/<x>.py` directly. Denials show up in the job's `usage.denials`. Extend the list when a legitimate command is denied.
- Background subagents report their end through `task_notification`; foreground ones through their tool_result. The parser handles both.
- ETAs before a stage starts come from the median of past runs' `events.jsonl` (`/api/timings`). New installs use the defaults in `app/web/src/lib/nodes.ts`.
- Don't `pkill -f` the server from a shell whose own command line contains the pattern; it kills the shell. Use `./factory.sh stop` (pidfile + `fuser 8787/tcp`).
- `.tmp/app/jobs/demo-replay` is a recorded run for previewing the live view without spending Claude usage.

## HyperFrames (post renderer, added 2026-10-26)
- `hyperframes/` holds the pinned CLI (`hyperframes@0.8.201` in `package.json`, Apache-2.0), a vendored `vendor/gsap.min.js` (no CDN, works offline) and `templates/post.css`. The tools call `hyperframes/node_modules/.bin/hyperframes` directly; there is no global install. After a fresh clone: `cd hyperframes && npm install`.
- Telemetry is off (`hyperframes telemetry disable`, stored in the user config), and `render_post.py` also sets `HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1`. Never use `hyperframes cloud`, `publish`, `lambda` or `auth` (accounts and paid services).
- It renders with the system Chrome (`/usr/bin/google-chrome`) in screenshot mode. `npx hyperframes doctor` checks Chrome, ffmpeg and memory.
- The global skills `hyperframes`, `hyperframes-cli`, `hyperframes-registry` and `media-use` (in `~/.claude/skills/`) are reference material for custom layouts. Their HeyGen/cloud options don't apply here: free and local only.

## Post troubleshooting
- **Low RAM** (doctor warns below about 1 GB free, and each Chrome uses about 256 MB): close other apps, or render one variant at a time with `render_post.py <run> --variant A`. `--motion` is the heaviest step.
- **Snapshot failed / fewer PNGs than slides:** `render_post.py` exits 2 with the CLI's error tail, and the job's render node turns red. Re-run once (Chrome start-up can time out under memory pressure). If it repeats, open the project in `.tmp/posts/<run>/hf/previews/` and run `hyperframes/node_modules/.bin/hyperframes check .tmp/posts/<run>/hf/previews` for the exact error (often custom HTML).
- **FLUX quota gone** (about 2 GPU-minutes a day, anonymous): photo slides fall back to title cards (a `fallback` event on the images node). That is expected, not a failure; use kit assets, or try again the next day.
- **Pick fails with 400:** the response carries `deliver_post.py`'s error. Usually the previews were deleted (`.tmp` cleaned); re-run the post job or `render_post.py` on the run.
- **Post not in the Gallery:** the Gallery needs `output/<name>/post.json`, which only a pick writes.

