# AI Video & Image Generator

A Claude Code project that turns a brand kit and a topic into finished short videos and image posts for LinkedIn, Instagram Reels, TikTok, YouTube Shorts and the web. It writes the script, makes the voice, visuals and music, renders every aspect ratio, checks the result and writes the post copy.

Videos come out in English, Arabic or Russian. Arabic captions run right to left.

The tools call no paid APIs. Every AI step has a free or local fallback, so a run finishes even when the online services are down or out of quota.

## How it works

The project follows a simple split: Claude makes the decisions, Python scripts do the work.

| Layer | What it is | Where |
|---|---|---|
| Workflows | Plain-language SOPs: inputs, steps, tools, known quirks | `workflows/` |
| Agents | Claude subagents: strategist, scriptwriter, QA reviewer, motion designer, content planner | `.claude/agents/` |
| Tools | Python scripts for voice, images, rendering, QA and delivery | `tools/` |

One video goes through these steps:

```
brief ─► strategy.md ─► storyboard.json ─► validate ─► voice ─► visuals, music, SFX ─► Remotion render ─► QA ─► output/
         (agents)       (agent)            (tools, free and local)                                    (tool + agent)
```

1. `new_project.py` creates a run folder and copies the brand kit into it.
2. The `video-strategist` agent picks the audience, angle, format, hook and CTA.
3. The `video-scriptwriter` agent writes `storyboard.json`: voiceover, on-screen text and scene types for each scene.
4. `validate_storyboard.py` checks it against `schemas/storyboard.schema.json` before anything slow runs.
5. `run_video.py` makes the voice, fetches or generates visuals, picks music, builds Remotion props and renders a half-scale preview.
6. `qa_frames.py` builds a contact sheet and checks duration, audio, loudness and black frames. It transcribes the voice with local Whisper and compares it with the script.
7. The `video-qa-reviewer` agent reads the QA output and returns SHIP or a fix list. There are at most 2 fix rounds.
8. `run_video.py --final` renders every aspect at full quality, normalises loudness to −14 LUFS and delivers to `output/`.

The same pipeline also makes image posts and carousels (`workflows/make_post.md`, rendered with HyperFrames).

## Stack

- **Orchestration:** Claude Code (agents, skills, slash commands)
- **Tools:** Python 3.11+ (edge-tts, Piper, faster-whisper, rembg, Pillow, Playwright, gradio_client)
- **Rendering:** Remotion 4 (React, headless Chrome), ffmpeg
- **Local AI:** stable-diffusion.cpp with DreamShaper 8 LCM, Real-ESRGAN, Depth-Anything-V2
- **Web app:** FastAPI backend, React + Vite frontend. It runs Claude Code headless (`claude -p`) and shows each agent and tool live.

| Step | First choice | Fallback |
|---|---|---|
| Voice | edge-tts (online, free) | Piper (offline) for the whole video |
| AI images | Hugging Face Space FLUX.1-schnell (anonymous quota) | local stable-diffusion.cpp, then Pollinations |
| AI clips | Hugging Face Spaces (Wan 2.2, LTX-Video) | local depth parallax, then Ken Burns |
| Talking head | Hugging Face Spaces (MoDA, EchoMimic) | built-in animated mascot |
| Stock footage | Pexels or Pixabay (free keys, optional) | branded motion cards |
| Music | your royalty-free library in `assets/music/` | built-in synth bed |
| Captions | edge-tts word timings | faster-whisper |

## Requirements

- Linux (built on Ubuntu)
- Python 3.11+, Node.js 20+, ffmpeg and ffprobe on `PATH`
- Claude Code, logged in
- About 3 GB of disk for local models and about 1 GB for `studio/node_modules`
- Optional: a Vulkan GPU for upscaling and local images

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cd studio && npm install && cd ..

python tools/setup_local_models.py    # local models, Piper voices, fonts, SFX (~2.5 GB)

cp .env.example .env                  # optional: every key is optional
```

## Run

In Claude Code, from this folder:

```
/video demo "Plan your week in five minutes"
/post demo "One notebook, not five"
/series demo topics: 1) ... 2) ... 3) ...
/onboard-brand
/content-calendar demo 2 weeks
```

Or run the tools by hand:

```bash
RUN=$(python tools/new_project.py --brand demo --title "Weekly plan" --lang en)
# write $RUN/storyboard.json, or let the video-scriptwriter agent do it
python tools/validate_storyboard.py $RUN/storyboard.json
python tools/run_video.py $RUN                        # voice, assets, props, preview, QA
python tools/run_video.py $RUN --from props --final   # full render of every aspect + delivery
```

Or start the web app:

```bash
./factory.sh        # http://127.0.0.1:8787
./factory.sh stop
```

Or run it in Docker:

```bash
make up            # private, http://127.0.0.1:8787
make up-public     # invite-only, behind HTTPS and a login (see Security)
```

After changing a tool or scene, run `python tools/smoke_test.py --quick`. It renders a short test video offline and checks that QA passes.

## Cost

- **External APIs:** none are paid. Edge-tts, the Hugging Face Spaces and Pollinations are used anonymously and free. The Pexels, Pixabay and Hugging Face keys in `.env.example` are free accounts, and all three are optional.
- **Claude:** the agents run inside Claude Code, so each video uses your Claude Code plan's usage. If Claude Code is logged in with an API key, that usage is billed per token. The web app records the tokens used by each job. No per-video figure has been measured yet.
- **Compute:** everything else runs on your machine. The project notes record one laptop (i5-10210U, 7.5 GB RAM, MX350) taking about 50 s for a 26 s half-scale preview render and about 9 minutes per local AI image on CPU.
- **Licences:** Remotion is free for individuals and companies of up to 3 people. MusicGen has a non-commercial licence, so it is off by default (`--allow-ai-music` turns it on).

## Security

The app runs an AI agent on a server, so it is locked down by default:

- **The agent can only use listed tools.** Headless Claude jobs get an allowlist: the project's own Python tools, ffmpeg and a few read-only shell commands. MCP servers are blocked (`app/server/settings.py`).
- **Uploads can't reach other files.** Every uploaded path must resolve inside the uploads folder. Tests try `/etc/passwd`, `../../etc/passwd` and `.env` and expect a refusal (`app/server/tests/test_posts.py`).
- **The public mode sits behind HTTPS and a login.** Caddy gets a Let's Encrypt certificate, asks each invitee for a password (bcrypt hashes), sets security headers and caps upload size (`deploy/Caddyfile`).
- **The container doesn't run as root.** It runs as its own `factory` user (`Dockerfile`).
- **Secrets stay out of git.** Keys live in `.env`, which is gitignored. `.env.example` lists them with empty values.

## Brands

A brand kit lives in `brands/<slug>/`:

- `brand.json`: colours, fonts, logo, voices, image style, do and don't rules
- `profile.md`: the only facts a video may state

`brands/demo/` is a made-up brand ("Margin Notes") used for examples and the smoke test. `brands/_template/` is a blank kit. Real brand kits are gitignored.

## Layout

```
CLAUDE.md          agent instructions and the factory's hard rules
workflows/         SOPs: make_video, make_post, video_series, content_calendar, onboard_brand, review_performance, app
.claude/agents/    strategist, scriptwriter, QA reviewer, motion designer, content planner, post copywriter and designer
.claude/skills/    slash commands and the official Remotion skills (remotion-dev/skills)
tools/             Python execution layer
studio/            Remotion project: scenes, components, render script
app/               web app: FastAPI server and React UI
hyperframes/       post renderer (HyperFrames CLI, CSS template, vendored GSAP)
config/            factory.json: voices, pacing, providers, loudness, local model settings
schemas/           storyboard and post JSON contracts
assets/            offline fonts (Inter, Cairo), music and SFX manifests
brands/            brand kits (_template and demo only)
```
