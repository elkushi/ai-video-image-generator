"""Shared helpers for the video factory tools (paths, config, ffmpeg, JSON IO)."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config/factory.json"
BRANDS = ROOT / "brands"
STUDIO = ROOT / "studio"
RUNS = ROOT / ".tmp/videos"


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def config() -> dict:
    return load_json(CONFIG)


def brand(slug: str) -> dict:
    path = BRANDS / slug / "brand.json"
    if not path.exists():
        raise SystemExit(f"Brand kit not found: {path} (run workflows/onboard_brand.md first)")
    return load_json(path)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "video"


def ff(*args) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    w, h = out.stdout.strip().split(",")[:2]
    return int(w), int(h)


def run_paths(run: Path) -> dict:
    """Standard file layout inside one run folder."""
    run = Path(run)
    return {
        "run": run,
        "public": run / "public",
        "storyboard": run / "storyboard.json",
        "timeline": run / "timeline.json",
        "props": run / "props.json",
        "credits": run / "credits.json",
        "brief": run / "brief.md",
        "renders": run / "renders",
        "qa": run / "qa",
    }


def add_credit(run: Path, entry: dict) -> None:
    """Append an attribution/provenance entry (stock, music, AI) to credits.json."""
    p = run_paths(run)["credits"]
    items = load_json(p) if p.exists() else []
    if entry not in items:
        items.append(entry)
    save_json(p, items)


# ---- mixed-language voiceover ------------------------------------------------------------------
# A Russian voice reading "Hi" sounds Russian ("Фило, хау-райу" in Whisper), and English/Arabic edge voices
# return NO audio for Cyrillic. So every VO line is split into language runs and each run is voiced natively.
# Explicit markup wins: [[en:Hi]] [[ru:privet]]. Otherwise runs are detected by script.
MIX_MARK = re.compile(r"\[\[(en|ar|ru):(.+?)\]\]", re.S)
_SCRIPTS = (("ru", re.compile(r"[Ѐ-ӿ]")), ("ar", re.compile(r"[؀-ۿݐ-ݿ]")),
            ("en", re.compile(r"[A-Za-z]")))


def plain_vo(text: str) -> str:
    """The VO as it is spoken and captioned: markup removed."""
    return MIX_MARK.sub(lambda m: m.group(2), text or "")


def token_lang(tok: str) -> str | None:
    for lang, rx in _SCRIPTS:
        if rx.search(tok):
            return lang
    return None  # digits / punctuation: belongs to its neighbour


def split_langs(text: str, main: str, keep: set[str] | None = None, auto: bool = True) -> list[tuple[str, str]]:
    """[(lang, text)] runs in speaking order. `keep` = Latin words that stay in the main voice inside a
    non-Latin line (brand names, SMS, API...), so "Acme" isn't read by a stranger mid-sentence."""
    keep = {k.lower() for k in (keep or set())}
    runs: list[list] = []

    def add(lang, piece):
        if runs and runs[-1][0] == lang:
            runs[-1][1] += piece
        else:
            runs.append([lang, piece])

    pos = 0
    for m in list(MIX_MARK.finditer(text)) + [None]:
        chunk = text[pos:m.start()] if m else text[pos:]
        for tok in re.split(r"(\s+)", chunk):
            if not tok:
                continue
            lang = token_lang(tok)
            bare = re.sub(r"[^\w-]", "", tok).lower()
            if lang is None or tok.isspace() or not auto:
                lang = runs[-1][0] if runs else main
            elif lang == "en" and main != "en" and (bare in keep or (tok.strip("«»\"'.,!?:;()").isupper() and len(bare) <= 5)):
                lang = main
            add(lang, tok)
        if m:
            add(m.group(1), m.group(2))
            pos = m.end()
    # punctuation-only runs ("— ", ", ") fold into the previous run
    out: list[tuple[str, str]] = []
    for lang, piece in runs:
        if out and (token_lang(piece) is None or lang == out[-1][0]):
            out[-1] = (out[-1][0], out[-1][1] + piece)
        elif piece.strip():
            out.append((lang, piece))
    return [(l, p.strip()) for l, p in out if p.strip()]
