"""Fetch free stock video/photos for storyboard scenes with visual.source stock_video|stock_photo.

Providers (free keys, see .env.example): Pexels first, Pixabay second. Search results are
cached in .tmp/stock/ by provider+query (Pixabay requires 24h caching), files are copied into
<run>/public/visuals/ and logged in credits.json (Pixabay requires showing the source).
No key / no match -> visual.resolved stays null and the scene renders as a branded motion card.

Usage:
  python tools/fetch_stock.py .tmp/videos/<run>
Updates storyboard.json (visual.resolved, visual.kind, visual.fallback_used).
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from common import ROOT, add_credit, load_json, run_paths, save_json

CACHE = ROOT / ".tmp/stock"
ORIENT = {"9x16": "portrait", "4x5": "portrait", "1x1": "square", "16x9": "landscape"}


def cached(name: str, fetch):
    import json
    path = CACHE / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = fetch()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def qkey(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", q.lower())


def pexels(query: str, kind: str, orient: str, key: str) -> list[dict]:
    def fetch():
        url = "https://api.pexels.com/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
        r = requests.get(url, params={"query": query, "orientation": orient, "per_page": 10},
                         headers={"Authorization": key}, timeout=20)
        r.raise_for_status()
        out = []
        if kind == "video":
            for v in r.json().get("videos", []):
                files = [f for f in v["video_files"] if f.get("file_type") == "video/mp4" and f.get("height")]
                files = [f for f in files if max(f["width"], f["height"]) <= 2160] or files
                if not files or v.get("duration", 0) < 4:
                    continue
                best = max(files, key=lambda f: min(f["width"], f["height"]))
                out.append({"id": f"pexels_{v['id']}", "url": best["link"], "ext": "mp4",
                            "credit": f"Video by {v['user']['name']} on Pexels", "page": v["url"]})
        else:
            for ph in r.json().get("photos", []):
                out.append({"id": f"pexels_{ph['id']}", "url": ph["src"]["large2x"], "ext": "jpg",
                            "credit": f"Photo by {ph['photographer']} on Pexels", "page": ph["url"]})
        return out
    return cached(f"pexels_{kind}_{orient}_{qkey(query)}", fetch)


def pixabay(query: str, kind: str, orient: str, key: str) -> list[dict]:
    def fetch():
        url = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
        params = {"key": key, "q": query, "per_page": 10, "safesearch": "true"}
        if kind == "photo":
            params["orientation"] = "vertical" if orient == "portrait" else "horizontal"
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        out = []
        for h in r.json().get("hits", []):
            if kind == "video":
                f = h["videos"].get("large") or h["videos"].get("medium")
                if not f or not f.get("url"):
                    continue
                out.append({"id": f"pixabay_{h['id']}", "url": f["url"], "ext": "mp4",
                            "credit": f"Video by {h['user']} on Pixabay", "page": h["pageURL"]})
            else:
                out.append({"id": f"pixabay_{h['id']}", "url": h["largeImageURL"], "ext": "jpg",
                            "credit": f"Image by {h['user']} on Pixabay", "page": h["pageURL"]})
        return out
    return cached(f"pixabay_{kind}_{orient}_{qkey(query)}", fetch)


def download(item: dict) -> Path:
    path = CACHE / f"{item['id']}.{item['ext']}"
    if not path.exists():
        with requests.get(item["url"], stream=True, timeout=90) as r:
            r.raise_for_status()
            tmp = path.with_suffix(".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
            tmp.rename(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    keys = {"pexels": os.getenv("PEXELS_API_KEY"), "pixabay": os.getenv("PIXABAY_API_KEY")}
    providers = [(n, f) for n, f in (("pexels", pexels), ("pixabay", pixabay)) if keys[n]]

    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    orient = ORIENT[sb["aspects"][0]]
    vis_dir = p["public"] / "visuals"
    vis_dir.mkdir(exist_ok=True)
    used, got, want = set(), 0, 0
    for s in sb["scenes"]:
        v = s.get("visual", {})
        if v.get("source") not in ("stock_video", "stock_photo"):
            continue
        want += 1
        kind = "video" if v["source"] == "stock_video" else "photo"
        v.update(resolved=None, kind="none", fallback_used="motion_card")
        queries = [v["query"], " ".join(v["query"].split()[:2])]
        for name, fn in providers:
            try:
                hits = [h for q in queries for h in fn(q, kind, orient, keys[name])]
            except requests.RequestException as e:
                print(f"  ! {name} '{v['query']}': {e}", file=sys.stderr)
                continue
            hit = next((h for h in hits if h["id"] not in used), None)
            if hit:
                src = download(hit)
                dst = vis_dir / f"{s['id']}_{src.name}"
                shutil.copy(src, dst)
                used.add(hit["id"])
                v.update(resolved=f"visuals/{dst.name}", kind="image" if kind == "photo" else "video",
                         fallback_used="")
                add_credit(args.run, {"scene": s["id"], "type": "stock", "credit": hit["credit"], "source": hit["page"]})
                got += 1
                break
    save_json(p["storyboard"], sb)
    note = "" if providers else " (no PEXELS_API_KEY/PIXABAY_API_KEY in .env -> motion cards)"
    print(f"stock: {got}/{want} scenes{note}")


if __name__ == "__main__":
    main()
