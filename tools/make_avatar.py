"""Make a free talking-head presenter clip for scenes with visual.source avatar.

Needs: the portrait (visual.path = your own photo, or visual.still from gen_image.py) and the
voiceover (make_voiceover.py). The scene's slice of voice.wav drives a free ZeroGPU Space
(config avatar.hf_spaces, e.g. MoDA fast talking head). Only use real people's photos with consent.
Fallback when the quota is used up or the Space is down: the scene renders the built-in
animated mascot presenter (visual.fallback_used = "mascot"), which is always free and local.

Usage:
  python tools/make_avatar.py .tmp/videos/<run> [--only scene_id]
Updates storyboard.json visual.resolved/kind for avatar scenes.
"""
import argparse
import os
import sys
from pathlib import Path

import hf_space
from common import BRANDS, add_credit, config, ff, load_json, run_paths, save_json


def moda(space: str, img: Path, wav: Path):
    return hf_space.call(space, "/generate_motion", source_image_path=hf_space.file_arg(img),
                         driving_audio_path=hf_space.file_arg(wav), cfg_scale=1.2)


def echomimic(space: str, img: Path, wav: Path):
    return hf_space.call(space, "/generate_video", uploaded_img=hf_space.file_arg(img),
                         uploaded_audio=hf_space.file_arg(wav), width=512, height=512, length=1200, seed=420,
                         facemask_dilation_ratio=0.1, facecrop_dilation_ratio=0.5, context_frames=12,
                         context_overlap=3, cfg=2.5, steps=30, sample_rate=16000, fps=24, device="cuda")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    timeline = {t["id"]: t for t in load_json(p["timeline"])["scenes"]}
    ok = total = 0
    for s in sb["scenes"]:
        v = s.get("visual", {})
        if v.get("source") != "avatar" or (args.only and s["id"] != args.only):
            continue
        total += 1
        v.update(resolved=None, kind="none", fallback_used="mascot")
        img = (Path(v["path"]) if Path(v["path"]).is_absolute() else BRANDS / sb["brand"] / v["path"]) \
            if v.get("path") else (p["public"] / v["still"] if v.get("still") else None)
        tl = timeline.get(s["id"])
        if not img or not img.exists() or not tl or not tl["speech"]:
            print(f"  ! {s['id']}: needs a portrait and spoken vo -> mascot", file=sys.stderr)
            continue
        wav = args.run / "voice_parts" / f"avatar_{s['id']}.wav"
        ff("-ss", tl["start"], "-t", tl["speech"] + 0.1, "-i", p["public"] / "voice.wav", "-ac", "1", "-ar", "16000", wav)
        out = p["public"] / "visuals" / f"{s['id']}_avatar.mp4"
        for space in ([] if os.getenv("FACTORY_OFFLINE") else config()["avatar"]["hf_spaces"]):
            fn = echomimic if "echomimic" in space.lower() else moda
            try:
                hf_space.keep(fn(space, img, wav), out)
            except Exception as e:
                print(f"  ! {str(e)[:200]}", file=sys.stderr)
                continue
            v.update(resolved=f"visuals/{out.name}", kind="video", fallback_used="")
            add_credit(args.run, {"scene": s["id"], "type": "avatar", "credit": f"AI talking head ({space})",
                                  "source": space})
            ok += 1
            print(f"  avatar {s['id']} via {space}", flush=True)
            break
    save_json(p["storyboard"], sb)
    print(f"avatars: {ok}/{total} (rest use the mascot presenter)")


if __name__ == "__main__":
    main()
