"""Paths, Claude CLI flags and the node vocabulary shared by the Factory app backend."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_DATA = ROOT / ".tmp/app"
JOBS_DIR = APP_DATA / "jobs"
UPLOADS = APP_DATA / "uploads"
OUTPUT = ROOT / "output"
BRANDS = ROOT / "brands"
RUNS = ROOT / ".tmp/videos"
POSTS = ROOT / ".tmp/posts"
WEB_DIST = ROOT / "app/web/dist"
PROMPTS = Path(__file__).resolve().parent / "prompts"
SCHEMAS = Path(__file__).resolve().parent / "schemas"

HOST = os.environ.get("FACTORY_HOST", "127.0.0.1")
PORT = int(os.environ.get("FACTORY_PORT", "8787"))
CLAUDE_BIN = os.environ.get("FACTORY_CLAUDE", "claude")
CLAUDE_MODEL = os.environ.get("FACTORY_MODEL", "")  # empty = the user's default model

# Headless Claude may only use these. No MCP servers at all (--strict-mcp-config), so the paid
# Higgsfield/Freepik connectors can never be called: the free-only rule is enforced, not just asked for.
ALLOWED_TOOLS = [
    "Read", "Write", "Edit", "Glob", "Grep", "Agent", "Skill", "WebSearch", "WebFetch", "TodoWrite",
    "Bash(.venv/bin/python tools/*)", "Bash(python tools/*)", "Bash(python3 tools/*)",
    "Bash(ffmpeg *)", "Bash(ffprobe *)", "Bash(edge-tts *)", "Bash(.venv/bin/edge-tts *)",
    "Bash(ls *)", "Bash(wc *)", "Bash(file *)", "Bash(mkdir *)", "Bash(pdftotext *)", "Bash(identify *)",
    "Bash(npx tsc *)", "Bash(cd studio && npx tsc *)",
]
BASH_PREFIXES = [t[5:-2] for t in ALLOWED_TOOLS if t.startswith("Bash(") and t.endswith("*)")]
GUARD = Path(__file__).resolve().parent / "guard.py"
# The agent reads web pages and uploads, so a prompt injection could ask it to read a key and send it
# out with WebFetch. Deny wins over allow, so these hold even in acceptEdits mode, which otherwise
# auto-approves cp and mv. Each line closes a route found by a live injection test:
SECRET_RULES = [
    # read the secret directly (paths are resolved, so "brands/../.env" is caught too)
    "Read(**/.env)", "Read(**/.env.*)", "Read(**/credentials.json)", "Read(**/token.json)",
    "Read(~/.claude/.credentials.json)", "Read(~/.ssh/**)", "Read(~/.config/**)",
    "Edit(**/.env)", "Edit(**/.env.*)", "Write(**/.env)", "Write(**/.env.*)",
    # copy it somewhere readable first (uploads go into a kit with tools/keep_upload.py instead)
    "Bash(cp *)", "Bash(mv *)", "Bash(ln *)", "Bash(rsync *)",
    # name it in a shell command, e.g. "python3 tools/../.env" prints a line in the traceback
    "Bash(*.env*)", "Bash(*credentials*)", "Bash(*..*)",
    # write a new tool that reads it, then run the tool
    "Write(tools/**)", "Edit(tools/**)", "Write(app/**)", "Edit(app/**)",
]
DISALLOWED_TOOLS = ["AskUserQuestion", "mcp__*", *SECRET_RULES]

# Agent subagent_type -> station on the factory floor / node in the graph
AGENT_NODES = {
    "content-planner": "planner",
    "video-strategist": "strategist",
    "video-scriptwriter": "scriptwriter",
    "video-qa-reviewer": "qa-reviewer",
    "remotion-motion-designer": "designer",
    "post-copywriter": "post-copywriter",
    "post-designer": "post-designer",
}
# tools/<script>.py -> node
TOOL_NODES = {
    "new_project": "intake", "validate_storyboard": "validate", "make_voiceover": "voice",
    "fetch_stock": "stock", "gen_image": "images", "local_image": "images", "upscale": "images",
    "animate_image": "clips", "depth_parallax": "clips", "make_avatar": "avatar", "cutout": "images",
    "pick_music": "music", "make_sfx": "sfx", "build_props": "props", "render": "render",
    "qa_frames": "qa", "postprocess": "deliver", "run_video": "pipeline", "extract_brand": "brand",
    "capture_screens": "brand", "smoke_test": "test", "setup_local_models": "setup",
    "new_post": "intake", "validate_post": "validate", "render_post": "render", "deliver_post": "deliver",
}
# run_video.py stage names -> node
STAGE_NODES = {"validate": "validate", "voice": "voice", "assets": "assets", "props": "props",
               "preview": "render", "final": "render"}

for d in (JOBS_DIR, UPLOADS, POSTS):
    d.mkdir(parents=True, exist_ok=True)
