"""Finish and deliver: loudness-normalise the final renders and copy the deliverables to output/.

For every final render (not .preview) in <run>/renders/: normalise audio to config loudness_lufs
(-14 LUFS, true peak -1.5 dB), keep the video stream untouched, add +faststart for social upload.
Delivery folder output/<run-name>/ gets:
  <slug>_<lang>_<aspect>.mp4, <slug>_<lang>_<aspect>_cover.jpg, storyboard.json, strategy.md,
  post.md (if written), credits.txt (stock/music/AI attribution).

Usage:
  python tools/postprocess.py .tmp/videos/<run>
Prints the delivery folder.
"""
import argparse
import shutil
from pathlib import Path

from common import ROOT, config, ff, load_json, run_paths, slugify
from events import emit, rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    args = ap.parse_args()

    cfg = config()
    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    out = ROOT / "output" / args.run.name
    out.mkdir(parents=True, exist_ok=True)
    # non-Latin titles (ar/ru) slugify to almost nothing; use the run folder slug instead
    slug = slugify(sb["title"]) if sb["title"].isascii() else args.run.name.split("_")[2]
    comp_to_aspect = {v["composition"]: k for k, v in cfg["aspects"].items()}
    lufs = cfg["loudness_lufs"]
    made = []
    for video in sorted(p["renders"].glob("Video-*.mp4")):
        if ".preview" in video.name:
            continue
        aspect = comp_to_aspect.get(video.stem, video.stem)
        dst = out / f"{slug}_{sb['language']}_{aspect}.mp4"
        ff("-i", video, "-c:v", "copy", "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-ar", "48000",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst)
        cover = video.with_name(f"{video.stem}.cover.jpg")
        if cover.exists():
            shutil.copy(cover, out / f"{slug}_{sb['language']}_{aspect}_cover.jpg")
        made.append(dst.name)
        emit(args.run, "asset", "deliver", type="video", aspect=aspect, path=rel(dst, args.run))

    for name in ("storyboard.json", "strategy.md", "post.md", "brief.md"):
        if (args.run / name).exists():
            shutil.copy(args.run / name, out / name)
    # QA reports + contact sheets travel with the delivery, so the app's gallery works after .tmp is cleaned
    if p["qa"].exists():
        (out / "qa").mkdir(exist_ok=True)
        for f in list(p["qa"].glob("qa_*.json")) + list(p["qa"].glob("contact_*.jpg")):
            if ".preview" not in f.name:
                shutil.copy(f, out / "qa" / f.name)
    credits = load_json(p["credits"]) if p["credits"].exists() else []
    music = args.run / "music.json"
    lines = [f"Credits for: {sb['title']}", ""]
    lines += [f"- [{c.get('type')}] {c.get('scene', '')} {c['credit']} {c.get('source', '')}".replace("  ", " ") for c in credits]
    if music.exists() and load_json(music).get("source") == "synth":
        lines.append("- [music] Original synth bed generated locally (no licence needed)")
    lines += ["", "Voice: AI text-to-speech (Microsoft Edge neural voices via edge-tts, or Piper).",
              "Disclose AI-generated audio/visuals where the platform asks (Instagram/TikTok 'AI info' label)."]
    (out / "credits.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit(args.run, "log", "deliver", folder=rel(out, args.run), videos=made)
    print(f"delivered {len(made)} video(s): {', '.join(made)}")
    print(out)


if __name__ == "__main__":
    main()
