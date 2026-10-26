"""Read-only views of the factory's files: brands, delivered videos, QA, timings, system status.

The file system is the database: brands/<slug>/, output/<run>/, .tmp/videos/<run>/.
"""
import json
import re
import shutil
import statistics
import subprocess
from pathlib import Path

from settings import BRANDS, OUTPUT, POSTS, ROOT, RUNS


def jload(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


# ---- brands -------------------------------------------------------------------------------
def brand_logo(slug: str, kit: dict) -> str | None:
    for key in ("on_dark", "on_light"):
        f = (kit.get("logo") or {}).get(key)
        if f and (BRANDS / slug / f).exists():
            return rel(BRANDS / slug / f)
    return None


def brands() -> list[dict]:
    out = []
    for d in sorted(BRANDS.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or not (d / "brand.json").exists():
            continue
        kit = jload(d / "brand.json", {})
        out.append({"slug": d.name, "name": kit.get("name", d.name), "tagline": kit.get("tagline", ""),
                    "colors": kit.get("colors", {}), "fonts": {k: v.get("family") for k, v in (kit.get("fonts") or {}).items() if isinstance(v, dict)},
                    "logo": brand_logo(d.name, kit), "logo_dark": rel(BRANDS / d.name / kit["logo"]["on_light"])
                    if (kit.get("logo") or {}).get("on_light") and (BRANDS / d.name / kit["logo"]["on_light"]).exists() else None,
                    "voices": kit.get("voices", {}), "website": kit.get("website", ""),
                    "videos": sum(1 for o in OUTPUT.glob(f"*_{d.name}_*") if o.is_dir() and not (o / "post.json").is_file()),
                    "posts": sum(1 for o in OUTPUT.glob(f"*_{d.name}_*") if (o / "post.json").is_file()),
                    "assets": sum(1 for f in (d / "assets").rglob("*") if f.is_file() and f.name != ".gitkeep") if (d / "assets").exists() else 0})
    return out


def brand_detail(slug: str) -> dict:
    d = BRANDS / slug
    if not (d / "brand.json").exists():
        raise FileNotFoundError(slug)
    kit = jload(d / "brand.json", {})
    read = lambda n: (d / n).read_text(encoding="utf-8") if (d / n).exists() else ""
    assets = [rel(f) for f in sorted((d / "assets").rglob("*")) if f.is_file() and f.suffix.lower() in
              (".png", ".jpg", ".jpeg", ".webp", ".svg")][:60] if (d / "assets").exists() else []
    return {"slug": slug, "kit": kit, "logo": brand_logo(slug, kit), "profile": read("profile.md"),
            "performance": read("performance.md"), "calendar": jload(d / "calendar.json"), "assets": assets}


# ---- outputs / gallery ----------------------------------------------------------------------
ASPECT_RE = re.compile(r"_(9x16|1x1|4x5|16x9)\.mp4$")


def qa_reports(name: str) -> list[dict]:
    for qa_dir in (OUTPUT / name / "qa", RUNS / name / "qa"):
        files = [f for f in sorted(qa_dir.glob("qa_*.json")) if ".preview" not in f.name] if qa_dir.exists() else []
        if files:
            out = []
            for f in files:
                r = jload(f, {})
                sheet = qa_dir / f"contact_{f.stem[3:]}.jpg"
                r["contact_sheet"] = rel(sheet) if sheet.exists() else None
                out.append(r)
            return out
    return []


def split_post(md: str) -> list[dict]:
    parts, cur = [], None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "text": ""}
            parts.append(cur)
        elif cur is not None:
            cur["text"] += line + "\n"
    for p in parts:
        p["text"] = p["text"].strip()
    return parts


def post_item(d: Path) -> dict:
    spec = jload(d / "post.json", {})
    v = (spec.get("variants") or [{}])[0]
    parts = d.name.split("_")
    motion = d / "motion.mp4"
    cover = d / "cover.jpg"
    return {
        "kind": "post", "name": d.name, "date": parts[0], "brand": spec.get("brand") or (parts[1] if len(parts) > 1 else ""),
        "title": spec.get("topic") or d.name, "language": spec.get("language"), "goal": spec.get("goal"),
        "format": v.get("format"), "aspect": spec.get("aspect"), "angle": v.get("angle"), "platforms": spec.get("platforms", []),
        "images": [rel(f) for f in sorted(d.glob("slide_*.png"))],
        "cover": rel(cover) if cover.exists() else None,
        "pdf": rel(d / "carousel.pdf") if (d / "carousel.pdf").exists() else None,
        "videos": [{"aspect": spec.get("aspect", "4x5"), "path": rel(motion), "cover": rel(cover) if cover.exists() else None}]
        if motion.exists() else [],
        "duration": None, "qa": {"pass": 0, "total": 0},
        "has_post": (d / "post.md").exists(), "has_stats": (d / "stats.json").exists(), "smoke": "smoke-test" in d.name,
    }


def outputs() -> list[dict]:
    items = []
    for d in sorted(OUTPUT.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        if (d / "post.json").is_file():
            items.append(post_item(d))
            continue
        vids = sorted(d.glob("*.mp4"))
        if not vids:
            continue
        sb = jload(d / "storyboard.json", {})
        parts = d.name.split("_")
        reports = qa_reports(d.name)
        checks = [c for r in reports for c in r.get("checks", [])]
        items.append({
            "kind": "video", "name": d.name, "date": parts[0], "brand": sb.get("brand") or (parts[1] if len(parts) > 1 else ""),
            "title": sb.get("title") or d.name, "language": sb.get("language"), "goal": sb.get("goal"),
            "format": sb.get("format"),
            "videos": [{"aspect": (ASPECT_RE.search(v.name) or [None, "?"])[1], "path": rel(v),
                        "cover": rel(v.with_name(v.stem + "_cover.jpg")) if v.with_name(v.stem + "_cover.jpg").exists() else None}
                       for v in vids],
            "duration": round(reports[0]["duration"], 1) if reports and reports[0].get("duration") else None,
            "qa": {"pass": sum(c["ok"] for c in checks), "total": len(checks)},
            "has_post": (d / "post.md").exists(), "has_stats": (d / "stats.json").exists(),
            "smoke": "smoke-test" in d.name,
        })
    return items


def output_detail(name: str) -> dict:
    d = OUTPUT / name
    if not d.is_dir():
        raise FileNotFoundError(name)
    base = next((o for o in outputs() if o["name"] == name), {})
    read = lambda n: (d / n).read_text(encoding="utf-8") if (d / n).exists() else ""
    run = RUNS / name
    strategy = read("strategy.md") or ((run / "strategy.md").read_text(encoding="utf-8") if (run / "strategy.md").exists() else "")
    return {**base, "qa_reports": qa_reports(name), "post": split_post(read("post.md")), "post_md": read("post.md"),
            "credits": read("credits.txt"), "strategy": strategy, "brief": read("brief.md"),
            "storyboard": jload(d / "storyboard.json"), "stats": jload(d / "stats.json", []),
            "events": rel(run / "events.jsonl") if (run / "events.jsonl").exists() else None,
            **({"post_spec": jload(d / "post.json"), "events": rel(POSTS / name / "events.jsonl")
                if (POSTS / name / "events.jsonl").exists() else None} if (d / "post.json").is_file() else {})}


# ---- timings (for ETAs before a stage starts) ----------------------------------------------------
def timings() -> dict:
    """Median seconds per stage/tool node from past video runs, plus seconds per video-second for scaling.
    Post runs (.tmp/posts) are reported separately under post_median_s / post_samples."""
    per_node: dict[str, list[float]] = {}
    per_vsec: dict[str, list[float]] = {}
    per_post: dict[str, list[float]] = {}  # post runs (HyperFrames stills) kept apart from video renders
    for ev_file in POSTS.glob("*/events.jsonl"):
        for line in ev_file.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") in ("tool_end", "stage_end") and e.get("data", {}).get("seconds") and e["data"].get("ok", True):
                per_post.setdefault(e["node"], []).append(e["data"]["seconds"])
    for ev_file in RUNS.glob("*/events.jsonl"):
        total = None
        props = jload(ev_file.parent / "props.json", {})
        if props.get("totalFrames"):
            total = props["totalFrames"] / 30
        for line in ev_file.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") in ("tool_end", "stage_end") and e.get("data", {}).get("seconds") and e["data"].get("ok", True):
                node = e["node"]
                per_node.setdefault(node, []).append(e["data"]["seconds"])
                if total:
                    per_vsec.setdefault(node, []).append(e["data"]["seconds"] / total)
    return {"median_s": {k: round(statistics.median(v), 1) for k, v in per_node.items()},
            "per_video_second": {k: round(statistics.median(v), 2) for k, v in per_vsec.items()},
            "samples": {k: len(v) for k, v in per_node.items()},
            "post_median_s": {k: round(statistics.median(v), 1) for k, v in per_post.items()},
            "post_samples": {k: len(v) for k, v in per_post.items()}}


# ---- system --------------------------------------------------------------------------------
def system() -> dict:
    def cmd(*a):
        try:
            return subprocess.run(a, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    mem = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":")
            mem[k] = int(v.split()[0]) // 1024
    except Exception:
        pass
    disk = shutil.disk_usage(ROOT)
    models = ROOT / ".tmp/models"
    return {"claude": cmd("claude", "--version"), "node": cmd("node", "--version"),
            "ram_total_mb": mem.get("MemTotal"), "ram_free_mb": mem.get("MemAvailable"),
            "disk_free_gb": round(disk.free / 1e9, 1),
            "local_models": {"sd": (models / "sd/DreamShaper8_LCM_q8_0.gguf").exists(),
                             "realesrgan": (models / "realesrgan").exists(), "depth": (models / "depth").exists(),
                             "piper": (models / "piper").exists()}}
