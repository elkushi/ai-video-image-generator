"""Factory app backend: FastAPI on 127.0.0.1:8787. Drives headless Claude Code and serves the web UI.

Run:  .venv/bin/python app/server/main.py        (or ./factory.sh)
"""
import asyncio
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

import library
from jobs import ACTIVE, FINISHED, manager
from settings import (BRANDS, CLAUDE_BIN, CLAUDE_MODEL, HOST, OUTPUT, PORT, POSTS, PROMPTS, ROOT, SCHEMAS,
                      UPLOADS, WEB_DIST)

app = FastAPI(title="Factory", docs_url="/api/docs", openapi_url="/api/openapi.json")
SERVE_ROOTS = [OUTPUT, BRANDS, ROOT / ".tmp/videos", POSTS, UPLOADS, ROOT / "assets"]
NAME_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")


CYRILLIC = {k: v.strip("_") for k, v in zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїєґ",
              "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch _ y _ e yu ya i yi ye g".split())}
COPY_KEYS = {"linkedin", "instagram", "facebook", "x", "tiktok", "alt", "hashtags"}


def slugify(text: str) -> str:
    """ASCII slug; Cyrillic is transliterated, other scripts (Arabic...) get a stable hash suffix."""
    t = "".join(CYRILLIC.get(ch, ch) for ch in (text or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:30].strip("-")
    return s or "brand-" + hashlib.sha1((text or "brand").encode("utf-8")).hexdigest()[:6]


def check_uploads(paths: list[str]) -> None:
    """Uploads must be files the app received (inside .tmp/app/uploads), never arbitrary paths."""
    root = UPLOADS.resolve()
    for u in paths:
        p = (ROOT / u).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise HTTPException(400, f"not an uploaded file: {u}")


def check_brand(slug: str) -> None:
    if slug and (not NAME_RE.match(slug) or not (BRANDS / slug / "brand.json").is_file()):
        raise HTTPException(404, f"no brand kit '{slug}': create it on the Brands page first")


def run_busy(name: str) -> bool:
    return any(j.status in ACTIVE and (j.run == name or (j.meta or {}).get("run") == name)
               for j in manager().jobs.values())


# ---- models ---------------------------------------------------------------------------------
class Brief(BaseModel):
    brand: str = ""                 # existing slug, or "" for a new brand
    new_brand: dict | None = None   # {"name", "website", "notes"}
    topic: str = ""
    topics: list[str] = []          # series mode: one entry per episode (workflows/video_series.md)
    goal: str = ""
    platforms: list[str] = []
    language: str = ""
    length_s: int | None = None
    style: str = ""
    must_say: str = ""
    cta: str = ""
    event: str = ""
    uploads: list[str] = []         # repo-relative paths from /api/uploads
    answers: list[dict] = []        # [{"question", "answer"}] from the intake cards
    understood: str = ""
    calendar_item: dict | None = None
    kind: Literal["video", "series", "post"] = "video"
    post_format: Literal["auto", "single", "carousel"] = "auto"
    aspect: Literal["4x5", "1x1", "9x16", "16x9"] = "4x5"
    motion: bool = False            # posts: also render an animated MP4 of each variant


class Answer(BaseModel):
    text: str


class Revise(BaseModel):
    feedback: str


class Pick(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    variant: str
    copy_edits: dict = Field(default={}, alias="copy")


class PostRevise(BaseModel):
    feedback: str
    variants: list[str] = []


class NewBrand(BaseModel):
    name: str
    website: str = ""
    notes: str = ""
    uploads: list[str] = []
    language: str = ""


class Guide(BaseModel):
    uploads: list[str] = []
    notes: str = ""


class PlanRequest(BaseModel):
    period: str = "2 weeks"
    per_week: int = 3
    platforms: list[str] = []
    languages: list[str] = []
    themes: str = ""


class Approve(BaseModel):
    items: list[dict]


class Stats(BaseModel):
    platform: str
    posted_at: str = ""
    age_h: float | None = None
    views: int | None = None
    avg_watch_s: float | None = None
    retention: float | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None
    follows: int | None = None
    clicks: int | None = None
    notes: str = ""


# ---- prompts --------------------------------------------------------------------------------
def brief_lines(b: Brief) -> str:
    rows = [("Goal", b.goal), ("Where", ", ".join(b.platforms)), ("Language", b.language),
            ("Length", f"~{b.length_s} s" if b.length_s else ""), ("Style", b.style), ("Must say", b.must_say),
            ("CTA / link", b.cta), ("Event", b.event)]
    out = [f"Topic: {b.topic}"] if b.topic else []
    if b.topics:
        out.append("Series episodes (in this order):")
        out += [f"{i}. {t}" for i, t in enumerate(b.topics, 1)]
    out += [f"{k}: {v}" for k, v in rows if v]
    if b.understood:
        out.append(f"Strategist's reading of the request (confirmed by the user): {b.understood}")
    if b.answers:
        out.append("Answers to the intake questions:")
        out += [f"- {a.get('question')}: {a.get('answer')}" for a in b.answers]
    if b.uploads:
        out.append("Uploaded files (read them):")
        out += [f"- {u}" for u in b.uploads]
    return "\n".join(out)


def video_prompt(b: Brief) -> tuple[str, str]:
    lines = brief_lines(b)
    finish = ("Run the whole workflow to the end: final render of every aspect, QA by video-qa-reviewer, "
              "delivery to output/ and post.md. Then give the summary.")
    cmd = "/video"
    if b.topics:
        cmd = "/series"
        finish = ("The app already asked the series questions (answers above), so skip step 1 unless something "
                  "blocking is still missing. If the user chose to review scripts, stop after the scripts with a "
                  "@@QUESTION card showing the episode table and options 'Go: produce all' / 'I have edits'. "
                  "Otherwise produce every episode to the end and give the summary.")
    if b.calendar_item:
        it = b.calendar_item
        finish += (f"\nThis is calendar item {it.get('id')} of brands/{b.brand}/calendar.json: when it is delivered, "
                   "set its status to \"made\" and append the run name to its \"runs\".")
    if not b.brand:
        nb = b.new_brand or {}
        slug = slugify(nb.get("name") or b.topic)
        return slug, (f"/onboard-brand {nb.get('name', '')} {nb.get('website', '')}\n"
                      f"Use the slug \"{slug}\". Notes from the user: {nb.get('notes', '')}\n"
                      f"Build the kit from the uploaded files listed below, then continue in the same session with:\n\n"
                      f"{cmd} {slug} {b.topic}\n{lines}\n\n{finish}")
    return b.brand, f"{cmd} {b.brand} {b.topic}\n{lines}\n\n{finish}"


def post_prompt(b: Brief) -> tuple[str, str]:
    fmt = {"single": "single image (1 slide per variant)", "carousel": "carousel (3-8 slides per variant)"}.get(
        b.post_format, "auto: pick single or carousel per variant to fit each angle")
    lines = brief_lines(b) + f"\nPost format: {fmt}\nAspect: {b.aspect}\nAnimated MP4 version: {'yes (render_post.py --motion)' if b.motion else 'no'}"
    finish = ("Follow workflows/make_post.md up to step 7: write 3 variants, render the previews, run QA, then STOP "
              "without delivering (the user picks a variant in the app, and the app delivers it). "
              "Return the structured result: the run folder (.tmp/posts/<name>), a 1-2 sentence summary, and each "
              "variant's id, angle and why.")
    if not b.brand:
        nb = b.new_brand or {}
        slug = slugify(nb.get("name") or b.topic)
        return slug, (f"/onboard-brand {nb.get('name', '')} {nb.get('website', '')}\n"
                      f"Use the slug \"{slug}\". Notes from the user: {nb.get('notes', '')}\n"
                      f"Build the kit from the uploaded files listed below, then continue in the same session with:\n\n"
                      f"/post {slug} {b.topic}\n{lines}\n\n{finish}")
    return b.brand, f"/post {b.brand} {b.topic}\n{lines}\n\n{finish}"


# ---- intake (structured questions) -------------------------------------------------------------
async def claude_json(prompt: str, schema: Path, tools: str = "Read Glob Grep", timeout: int = 300) -> dict:
    cmd = [CLAUDE_BIN, "-p", prompt, "--output-format", "json", "--strict-mcp-config",
           "--allowedTools", *tools.split(), "--disallowedTools", "AskUserQuestion", "mcp__*",
           "--json-schema", schema.read_text(encoding="utf-8")]
    if CLAUDE_MODEL:
        cmd += ["--model", CLAUDE_MODEL]
    proc = await asyncio.create_subprocess_exec(*cmd, cwd=ROOT, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.DEVNULL)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(504, "Claude took too long to answer")
    try:
        res = json.loads(out)
    except ValueError:
        raise HTTPException(502, f"Claude returned no JSON: {err.decode()[-400:]}")
    if res.get("is_error") or res.get("structured_output") is None:
        raise HTTPException(502, f"Claude error: {str(res.get('result'))[:400]}")
    return {"data": res["structured_output"], "seconds": round(res.get("duration_ms", 0) / 1000, 1),
            "turns": res.get("num_turns")}


@app.post("/api/intake/questions")
async def intake(b: Brief):
    check_uploads(b.uploads)
    if b.brand:
        check_brand(b.brand)
    exists = bool(b.brand) and (BRANDS / b.brand / "brand.json").exists()
    brand = b.brand or slugify((b.new_brand or {}).get("name", "new"))
    template = "intake_post.md" if b.kind == "post" else "intake.md"
    prompt = (PROMPTS / template).read_text(encoding="utf-8").format(
        brand=brand, brand_status="existing kit" if exists else "NEW brand: no kit yet, ask what's missing",
        uploads=", ".join(b.uploads) or "none", brief=brief_lines(b)
        + (f"\nNew brand: {json.dumps(b.new_brand, ensure_ascii=False)}" if not exists and b.new_brand else ""))
    return await claude_json(prompt, SCHEMAS / "intake.json")


# ---- jobs -----------------------------------------------------------------------------------
@app.post("/api/jobs/video")
def make_video(b: Brief):
    check_uploads(b.uploads)
    check_brand(b.brand)
    brand, prompt = video_prompt(b)
    title = b.topic or (f"Series: {len(b.topics)} episodes · " + " / ".join(b.topics))
    kind = "series" if b.topics else "video" if b.brand else "onboard"
    j = manager().submit(kind=kind, title=title[:140], brand=brand, prompt=prompt,
                         flow="onboard-video" if kind == "onboard" else kind, meta=b.model_dump())
    return j.to_dict()


@app.post("/api/jobs/post")
def make_post(b: Brief):
    check_uploads(b.uploads)
    check_brand(b.brand)
    if not b.brand and not (b.new_brand or {}).get("name"):
        raise HTTPException(400, "pick a brand or describe the new one")
    brand, prompt = post_prompt(b)
    title = f"Post: {b.topic}" if b.topic else "Post"
    j = manager().submit(kind="post", title=title[:140], brand=brand, prompt=prompt, flow="post",
                         meta={**b.model_dump(), "schema": "post_result.json"})
    return j.to_dict()


@app.get("/api/jobs")
def list_jobs():
    m = manager()
    return [{**j, "queue_position": m.queue_position(m.jobs[j["id"]])} for j in m.list()]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    m = manager()
    if job_id not in m.jobs:
        raise HTTPException(404, "no such job")
    return {**m.jobs[job_id].to_dict(), "queue_position": m.queue_position(m.jobs[job_id])}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    return manager().cancel(job_id).to_dict()


@app.post("/api/jobs/{job_id}/answer")
def answer_job(job_id: str, a: Answer):
    try:
        return manager().answer(job_id, a.text).to_dict()
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request, since: int = Query(0)):
    m = manager()
    if job_id not in m.jobs:
        raise HTTPException(404, "no such job")
    path = m.jobs[job_id].dir / "events.jsonl"

    async def stream():
        n, pos, idle, beat = 0, 0, 0, time.time()
        while True:
            if await request.is_disconnected():
                return
            new = False
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    f.seek(pos)
                    while True:
                        line = f.readline()
                        if not line or not line.endswith("\n"):
                            break
                        pos = f.tell()
                        if n >= since:
                            yield f"id: {n}\ndata: {line.strip()}\n\n"
                        n += 1
                        new = True
            j = m.jobs[job_id]
            if not new and j.status in FINISHED | {"waiting"}:
                idle += 1
                if idle > 3:
                    yield f"event: end\ndata: {json.dumps({'status': j.status})}\n\n"
                    return
            else:
                idle = 0
            if time.time() - beat > 15:
                beat = time.time()
                yield ": ping\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- uploads + files ------------------------------------------------------------------------------
@app.post("/api/uploads")
async def upload(files: list[UploadFile] = File(...), draft: str = Query("")):
    draft = re.sub(r"[^a-zA-Z0-9-]", "", draft) or uuid.uuid4().hex[:8]
    d = UPLOADS / draft
    d.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        name = re.sub(r"[^\w.\- ]", "_", Path(f.filename or "file").name).strip() or "file"
        dst = d / name
        size = 0
        with open(dst, "wb") as out:
            while chunk := await f.read(1 << 20):
                size += len(chunk)
                if size > 300 * 1024 * 1024:
                    raise HTTPException(413, f"{name} is over 300 MB")
                out.write(chunk)
        saved.append({"name": name, "path": library.rel(dst), "size": size, "type": f.content_type})
    return {"draft": draft, "files": saved}


@app.api_route("/files/{path:path}", methods=["GET", "HEAD"])
def serve_file(path: str):
    p = (ROOT / path).resolve()
    if not any(p.is_relative_to(r.resolve()) for r in SERVE_ROOTS) or not p.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(p)


# ---- posts (3 variants -> pick -> deliver) ---------------------------------------------------------
def post_run(name: str) -> Path:
    if not NAME_RE.match(name) or ".." in name:
        raise HTTPException(400, "bad post name")
    run = POSTS / name
    if not run.resolve().is_relative_to(POSTS.resolve()) or not (run / "post.json").is_file():
        raise HTTPException(404, "no such post")
    return run


@app.get("/api/posts/{name}")
def get_post(name: str):
    run = post_run(name)
    spec = library.jload(run / "post.json", {})
    return {"name": name, "run": library.rel(run), "spec": spec,
            "previews": library.jload(run / "previews/index.json", {}), "picked": spec.get("picked"),
            "output": name if (OUTPUT / name / "post.json").is_file() else None}


@app.post("/api/posts/{name}/pick")
def pick_post(name: str, p: Pick):
    run = post_run(name)
    if not re.fullmatch(r"[A-Z]", p.variant or ""):
        raise HTTPException(400, "variant must be a letter like A")
    spec = library.jload(run / "post.json", {})
    if p.variant not in {v.get("id") for v in spec.get("variants", [])}:
        raise HTTPException(400, f"variant {p.variant} is not in this post")
    if not library.jload(run / "previews/index.json", {}).get(p.variant):
        raise HTTPException(409, "this variant has no rendered previews yet")
    if run_busy(name):
        raise HTTPException(409, "a job is still working on this post; wait for it to finish")
    cmd = [str(ROOT / ".venv/bin/python"), "tools/deliver_post.py", library.rel(run), "--pick", p.variant]
    edits = {k: v for k, v in (p.copy_edits or {}).items() if k in COPY_KEYS and (
        isinstance(v, str) or (k == "hashtags" and isinstance(v, list) and all(isinstance(h, str) for h in v)))}
    if edits:
        f = run / "copy_edits.json"
        f.write_text(json.dumps(edits, ensure_ascii=False, indent=1), encoding="utf-8")
        cmd += ["--copy-edits", library.rel(f)]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise HTTPException(400, "delivery took over 180 s")
    if r.returncode != 0:
        raise HTTPException(400, (r.stderr or r.stdout)[-1200:])
    out = OUTPUT / name
    return {"output": name, "files": sorted(f.name for f in out.iterdir()) if out.is_dir() else []}


@app.post("/api/posts/{name}/revise")
def revise_post(name: str, r: PostRevise):
    run = post_run(name)
    spec = library.jload(run / "post.json", {})
    if not r.feedback.strip():
        raise HTTPException(400, "tell the team what to change")
    ids = {v.get("id") for v in spec.get("variants", [])}
    if any(v not in ids for v in r.variants):
        raise HTTPException(400, f"unknown variant(s); this post has {sorted(ids)}")
    if run_busy(name):
        raise HTTPException(409, "a job is already working on this post")
    which = ", ".join(r.variants) if r.variants else "all variants"
    prompt = (f"The user reviewed the 3 post variants in .tmp/posts/{name} (brand {spec.get('brand', '')}) and asks for "
              f"changes to {which}:\n\n{r.feedback}\n\nFollow the \"Revise\" section of workflows/make_post.md on this "
              "run folder: edit post.json for those variants only (keep the others as they are), re-validate with "
              "tools/validate_post.py, re-render with tools/render_post.py, run QA, and do NOT deliver. "
              "Return the structured result (run folder, summary, every variant's id, angle and why).")
    return manager().submit(kind="post", title=f"Revise post: {spec.get('topic', name)}"[:140], brand=spec.get("brand", ""),
                            prompt=prompt, flow="post-revise", meta={"schema": "post_result.json", "run": name, "feedback": r.feedback,
                                                 "variants": r.variants}).to_dict()


# ---- brand onboarding (any company: from a brand guide, logo, site) -------------------------------
def uploads_list(paths: list[str]) -> str:
    return "\n".join(f"- {u}" for u in paths) or "- none"


@app.post("/api/brands")
def new_brand(nb: NewBrand):
    if not nb.name.strip():
        raise HTTPException(400, "the brand needs a name")
    check_uploads(nb.uploads)
    slug = slugify(nb.name)
    if (BRANDS / slug / "brand.json").exists():
        raise HTTPException(409, f"brand {slug} already exists; use 'Update from brand guide'")
    prompt = (f"/onboard-brand {nb.name} {nb.website}\nUse the slug \"{slug}\". Follow workflows/onboard_brand.md.\n"
              f"Main language(s): {nb.language or 'infer from the guide/site'}\nNotes from the user: {nb.notes or 'none'}\n"
              f"Uploaded files (brand guide PDFs, logos, fonts, photos; read them all):\n{uploads_list(nb.uploads)}\n\n"
              "Build the full kit (brand.json, profile.md, logos, fonts, assets). Facts only from the user's files and "
              "website. Don't make a video. Finish by checking the look with one quick single-variant test post "
              "(tools/new_post.py + post.json + tools/render_post.py, no delivery), then summarise the kit and list "
              "anything still missing.")
    return manager().submit(kind="onboard", title=f"New brand: {nb.name}"[:140], brand=slug, prompt=prompt,
                            flow="brand-new", meta=nb.model_dump()).to_dict()


@app.post("/api/brands/{slug}/guide")
def update_brand_from_guide(slug: str, g: Guide):
    if not NAME_RE.match(slug) or not (BRANDS / slug / "brand.json").exists():
        raise HTTPException(404, "no such brand")
    check_uploads(g.uploads)
    if not g.uploads and not g.notes.strip():
        raise HTTPException(400, "upload the brand guide (or describe the changes in notes)")
    prompt = (f"Update the existing brand kit brands/{slug}/ from a new brand guide. Follow workflows/onboard_brand.md "
              f"(steps 2-5) as an update, not a fresh kit.\nUploaded files (read them all):\n{uploads_list(g.uploads)}\n"
              f"Notes from the user: {g.notes or 'none'}\n\n"
              "Update brand.json from what the guide states: colours (keep dark readable under white text), fonts "
              "(copy licensed font files the user supplied into fonts/ and list them; otherwise the closest Google Font), "
              "logos on_light/on_dark, icons into assets/icons/, radius/motif, image_style, rules.do/dont. Put tone and "
              "facts into profile.md only when the guide states them; keep the existing approved facts. Then check the "
              "look with one quick single-variant test post (no delivery) and summarise exactly what changed.")
    return manager().submit(kind="onboard", title=f"Update brand from guide: {slug}", brand=slug, prompt=prompt,
                            flow="brand-guide", meta=g.model_dump()).to_dict()


# ---- library ----------------------------------------------------------------------------------
@app.get("/api/brands")
def get_brands():
    return library.brands()


@app.get("/api/brands/{slug}")
def get_brand(slug: str):
    try:
        return library.brand_detail(slug)
    except FileNotFoundError:
        raise HTTPException(404, "no such brand")


@app.get("/api/outputs")
def get_outputs():
    return library.outputs()


@app.get("/api/outputs/{name}")
def get_output(name: str):
    try:
        return library.output_detail(name)
    except FileNotFoundError:
        raise HTTPException(404, "no such output")


@app.post("/api/outputs/{name}/revise")
def revise(name: str, r: Revise):
    if not (OUTPUT / name).is_dir():
        raise HTTPException(404, "no such output")
    brand = name.split("_")[1] if "_" in name else ""
    prompt = (f"The user reviewed the delivered video output/{name} (run folder .tmp/videos/{name}) and asks for "
              f"changes:\n\n{r.feedback}\n\nFollow workflows/make_video.md step 8: apply the change in storyboard.json "
              "(go back to step 3 or 5 as needed), re-render the final aspects, run QA, re-deliver to the same "
              "output folder, and update post.md if the copy changed. Then give the summary.")
    return manager().submit(kind="revise", title=f"Revise: {name}", brand=brand, prompt=prompt,
                            meta={"output": name, "feedback": r.feedback}).to_dict()


@app.post("/api/outputs/{name}/stats")
def add_stats(name: str, s: Stats):
    d = OUTPUT / name
    if not d.is_dir():
        raise HTTPException(404, "no such output")
    stats = library.jload(d / "stats.json", [])
    stats.append({**s.model_dump(), "measured_at": time.strftime("%Y-%m-%dT%H:%M")})
    (d / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


@app.post("/api/brands/{slug}/performance")
def review_performance(slug: str):
    prompt = (f"Follow workflows/review_performance.md for brand {slug}. The stats are already recorded in "
              f"output/*_{slug}_*/stats.json. Update brands/{slug}/performance.md (log + 'What works for this brand'), "
              "add playbook learnings only if the evidence is strong, then summarise the 2-3 takeaways.")
    return manager().submit(kind="performance", title=f"Learn from stats: {slug}", brand=slug, prompt=prompt).to_dict()


@app.post("/api/brands/{slug}/calendar/plan")
def plan_calendar(slug: str, r: PlanRequest):
    prompt = (f"Follow workflows/content_calendar.md step 1 only, for brand {slug}: spawn the content-planner agent with "
              f"period {r.period}, {r.per_week} posts per week, platforms {r.platforms or 'brand default'}, "
              f"languages {r.languages or 'brand default'}, themes/events: {r.themes or 'none'}. "
              "Don't save or make anything. The user approves it in the app. Return the plan as the structured output.")
    j = manager().submit(kind="calendar", title=f"Plan {r.period}: {slug}", brand=slug, prompt=prompt,
                         meta={**r.model_dump(), "schema": "calendar_plan.json"})
    return j.to_dict()


@app.post("/api/brands/{slug}/calendar/approve")
def approve_calendar(slug: str, a: Approve):
    p = BRANDS / slug / "calendar.json"
    if not (BRANDS / slug).is_dir():
        raise HTTPException(404, "no such brand")
    cal = library.jload(p, {"brand": slug, "items": []})
    keep = {it["id"]: it for it in cal.get("items", [])}
    for it in a.items:
        old = keep.get(it["id"], {})
        keep[it["id"]] = {**it, "status": old.get("status", "todo"), "runs": old.get("runs", [])}
    cal.update(brand=slug, updated=time.strftime("%Y-%m-%d"),
               items=sorted(keep.values(), key=lambda x: (x.get("date", ""), x["id"])))
    p.write_text(json.dumps(cal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return cal


@app.get("/api/timings")
def get_timings():
    return library.timings()


@app.get("/api/system")
def get_system():
    m = manager()
    return {**library.system(), "running": m.current.id if m.current else None,
            "queued": sum(1 for j in m.jobs.values() if j.status == "queued")}


# ---- web UI -----------------------------------------------------------------------------------
@app.get("/{path:path}")
def spa(path: str):
    f = (WEB_DIST / path).resolve()
    if path and f.is_file() and f.is_relative_to(WEB_DIST.resolve()):
        return FileResponse(f)
    index = WEB_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"error": "web UI not built: cd app/web && npm install && npm run build "
                                  "(or run ./factory.sh dev)"}, status_code=503)


if __name__ == "__main__":
    manager()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
