"""Build a HyperFrames project from post variants (post.json -> <proj>/index.html + assets/).

Each slide is a 1 s clip on the root timeline (stills), so `hyperframes snapshot --at i+0.5` gives
one PNG per slide. With motion=True each slide lasts SLIDE_MOTION_S and its elements animate in,
so `hyperframes render` gives an animated MP4 version of the same post.
Layouts: title, stat, quote, list, compare, icons, photo, screen, cta, custom (designer-written HTML).
Text markup: **word** -> brand highlight colour, a newline -> line break.
Works for any brand kit: missing colours, fonts, logo, icons or motif fall back to sensible defaults
(text wordmark from the brand name, numbered badges instead of icons).
"""
import html
import json
import re
import shutil
from pathlib import Path

from common import BRANDS, ROOT

HF = ROOT / "hyperframes"
SIZES = {"4x5": (1080, 1350), "1x1": (1080, 1080), "9x16": (1080, 1920), "16x9": (1920, 1080)}
SLIDE_MOTION_S = 3.0
SWIPE = {"en": "Swipe", "ru": "Листайте", "ar": "اسحب"}
MOTIFS = {"tilted_squares", "circles", "grid", "none"}
# Layouts whose copy is short: anchor it low and give the top to the brand motif.
BOTTOM = {"title", "stat", "quote", "cta", "photo"}


def md(text) -> str:
    t = html.escape(str(text or ""))
    t = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', t)
    return t.replace("\n", "<br>")


def size_class(text: str, steps: list[tuple[int, str]]) -> str:
    n = len(re.sub(r"\*\*", "", str(text or "")))
    for limit, cls in steps:
        if n <= limit:
            return cls
    return steps[-1][1]


def brand_file(slug: str, rel: str) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    for cand in ([p] if p.is_absolute() else [BRANDS / slug / rel, ROOT / rel]):
        if cand.is_file():
            return cand
    return None


def load_kit(slug: str) -> dict:
    """brand.json with defaults for every key the post design reads."""
    kit = json.loads((BRANDS / slug / "brand.json").read_text(encoding="utf-8"))
    c = kit.setdefault("colors", {})
    c.setdefault("primary", "#3355FF")
    c.setdefault("secondary", c["primary"])
    c.setdefault("dark", "#111827")
    c.setdefault("light", "#F5F5F7")
    c.setdefault("accent", c["primary"])
    c.setdefault("text_on_dark", "#FFFFFF")
    c.setdefault("text_on_light", c["dark"])
    f = kit.setdefault("fonts", {})
    f.setdefault("heading", {"family": "Inter"})
    f.setdefault("body", {"family": f["heading"].get("family", "Inter")})
    kit.setdefault("logo", {})
    kit.setdefault("name", slug)
    if kit.get("motif") not in MOTIFS:
        kit["motif"] = "tilted_squares" if kit.get("motif") else "none"
    if kit.get("theme_default") not in ("dark", "light", "brand"):
        kit["theme_default"] = "dark"
    return kit


class Assets:
    """Copies files into <project>/assets/ once and returns root-relative paths."""

    def __init__(self, proj: Path):
        self.dir = proj / "assets"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.map: dict[Path, str] = {}

    def add(self, src: Path | None, sub: str = "") -> str:
        if not src or not src.exists():
            return ""
        src = src.resolve()
        if src not in self.map:
            d = self.dir / sub if sub else self.dir
            d.mkdir(parents=True, exist_ok=True)
            name = src.name
            i = 1
            while (d / name).exists() and (d / name).resolve() != src:
                name = f"{src.stem}_{i}{src.suffix}"
                i += 1
            shutil.copy(src, d / name)
            self.map[src] = f"assets/{sub + '/' if sub else ''}{name}"
        return self.map[src]


def font_faces(kit: dict, slug: str, assets: Assets) -> tuple[str, str, str]:
    css, seen = [], set()
    for role in ("heading", "body"):
        f = kit["fonts"].get(role, {})
        fam = f.get("family", "Inter")
        for weight, rel in (f.get("files") or {}).items():
            path = assets.add(brand_file(slug, rel), "fonts")
            if path and (fam, weight) not in seen:
                seen.add((fam, weight))
                css.append(f'@font-face{{font-family:"{fam}";src:url("{path}");font-weight:{weight};font-display:block}}')
    for fam in ("Inter", "Cairo"):
        for w in (400, 500, 600, 700, 800):
            if (fam, str(w)) in seen:
                continue
            path = assets.add(ROOT / f"assets/fonts/{fam}-{w}.ttf", "fonts")
            if path:
                css.append(f'@font-face{{font-family:"{fam}";src:url("{path}");font-weight:{w};font-display:block}}')
    head = kit["fonts"]["heading"].get("family", "Inter")
    body = kit["fonts"]["body"].get("family", head)
    return "\n".join(css), head, body


def stack(family: str, lang: str) -> str:
    return f'Cairo, "{family}", Inter, sans-serif' if lang == "ar" else f'"{family}", Inter, Cairo, sans-serif'


def group(cls: str, parts: list[str]) -> str:
    inner = "".join(p for p in parts if p)
    return f'<div class="{cls}">{inner}</div>' if inner else ""


def kicker(p) -> str:
    return f'<div class="kicker a">{md(p["kicker"])}</div>' if p.get("kicker") else ""


# ---------- layouts: each returns (slide classes, body html, background html) ----------
# Body html is a .ca (copy) group and optionally a .cb (visual) group; 16x9 puts them side by side.

def L_title(p, ctx):
    t = p.get("title", "")
    cls = size_class(t, [(26, "xl"), (56, ""), (90, "l"), (999, "s")])
    ca = group("ca", [kicker(p), f'<h1 class="h1 {cls} a">{md(t)}</h1>',
                      f'<p class="lead a">{md(p["subtitle"])}</p>' if p.get("subtitle") else ""])
    return "", ca, ""


def L_stat(p, ctx):
    v = str(p.get("value", ""))
    cls = size_class(v, [(5, ""), (7, "l"), (9, "m"), (99, "s")])
    label = p.get("label", "")
    lcls = "s" if len(label) > 50 else ""
    cb = group("cb", [f'<div class="stat-value {cls} a">{md(v)}</div>', '<div class="rule a"></div>'])
    ca = group("ca", [kicker(p), f'<div class="stat-label {lcls} a">{md(label)}</div>',
                      f'<p class="lead a">{md(p["sub"])}</p>' if p.get("sub") else "",
                      f'<div class="source a">{md(p["source"])}</div>' if p.get("source") else ""])
    if ctx["aspect"] == "16x9":
        return "", cb + ca, ""
    return "", group("ca", [kicker(p)]) + cb + group("ca", [f'<div class="stat-label {lcls} a">{md(label)}</div>',
                                                            f'<p class="lead a">{md(p["sub"])}</p>' if p.get("sub") else "",
                                                            f'<div class="source a">{md(p["source"])}</div>' if p.get("source") else ""]), ""


def L_quote(p, ctx):
    q = p.get("quote", "")
    cls = "s" if len(q) > 110 else ("l" if len(q) <= 60 else "")
    who = ""
    if p.get("author"):
        role = f"<small>{md(p['role'])}</small>" if p.get("role") else ""
        who = f'<div class="who a"><div>{md(p["author"])}{role}</div></div>'
    return "", group("ca", ['<div class="quote-mark a"><svg viewBox="0 0 120 96" aria-hidden="true"><path d="M0 96V58C0 26 14 6 46 0l6 14C34 20 26 32 25 48h23v48H0zm68 0V58C68 26 82 6 114 0l6 14c-18 6-26 18-27 34h23v48H68z"/></svg></div>', f'<blockquote class="quote {cls} a">{md(q)}</blockquote>', who]), ""


def icon_img(ctx, name: str) -> str:
    if not name:
        return ""
    base = BRANDS / ctx["slug"] / "assets/icons"
    for ext in (".svg", ".png", ".webp"):
        path = ctx["assets"].add(base / f"{name}{ext}", "icons")
        if path:
            return f'<img src="{path}" alt="">'
    return ""


def L_list(p, ctx):
    items = p.get("items", [])
    total = sum(len(str(i if isinstance(i, str) else i.get("text", ""))) for i in items)
    tight = " tight" if len(items) > 4 or total > 140 else ""
    lis = []
    for n, it in enumerate(items, 1):
        text, icon = (it, "") if isinstance(it, str) else (it.get("text", ""), it.get("icon", ""))
        badge = icon_img(ctx, icon) or str(n)
        lis.append(f'<li class="a"><span class="n">{badge}</span><span>{md(text)}</span></li>')
    tcls = " s" if len(p.get("title", "")) > 34 else ""
    ca = group("ca", [kicker(p), f'<h2 class="h2{tcls} a">{md(p["title"])}</h2>' if p.get("title") else ""])
    return "", ca + f'<div class="cb"><ul class="list{tight}">{"".join(lis)}</ul></div>', ""


def L_compare(p, ctx):
    def col(side, cls):
        d = p.get(side, {})
        items = d.get("items", []) if isinstance(d, dict) else [d]
        label = d.get("label", "Before" if side == "before" else "After") if isinstance(d, dict) else side.title()
        return f'<div class="col {cls} a"><h3>{md(label)}</h3><ul>{"".join(f"<li><span>{md(i)}</span></li>" for i in items)}</ul></div>'
    tcls = " s" if len(p.get("title", "")) > 34 else ""
    ca = group("ca", [kicker(p), f'<h2 class="h2{tcls} a">{md(p["title"])}</h2>' if p.get("title") else ""])
    return "", ca + f'<div class="cb"><div class="compare">{col("before", "before")}{col("after", "after")}</div></div>', ""


def L_icons(p, ctx):
    tiles = []
    items = p.get("items", [])
    for n, it in enumerate(items, 1):
        name, label = (it, it) if isinstance(it, str) else (it.get("icon", ""), it.get("label", ""))
        ic = icon_img(ctx, name) or md(str(label or name)[:1].upper() or str(n))
        tiles.append(f'<div class="tile a"><div class="ic">{ic}</div><span>{md(label)}</span></div>')
    c3 = " c3" if len(items) in (3, 5, 6) and ctx["aspect"] != "16x9" else ""
    tcls = " s" if len(p.get("title", "")) > 34 else ""
    ca = group("ca", [kicker(p), f'<h2 class="h2{tcls} a">{md(p["title"])}</h2>' if p.get("title") else "",
                      f'<p class="lead a">{md(p["caption"])}</p>' if p.get("caption") else ""])
    return "", ca + f'<div class="cb"><div class="tiles{c3}">{"".join(tiles)}</div></div>', ""


def L_photo(p, ctx):
    img = ctx["assets"].add(brand_file(ctx["slug"], p.get("image", "")), "images")
    t = p.get("headline", p.get("title", ""))
    if not img:  # no image resolved: degrade to a title card with the same words
        return L_title({"kicker": p.get("kicker"), "title": t, "subtitle": p.get("sub", p.get("subtitle"))}, ctx)
    ca = group("ca", [kicker(p), f'<h1 class="h1 {size_class(t, [(40, ""), (80, "l"), (999, "s")])} a">{md(t)}</h1>',
                      f'<p class="lead a">{md(p["sub"])}</p>' if p.get("sub") else ""])
    return "photo", ca, f'<div class="photo-bg"><img src="{img}" alt=""></div>'


def L_screen(p, ctx):
    img = ctx["assets"].add(brand_file(ctx["slug"], p.get("image", "")), "images")
    device = p.get("device", "desktop")
    hcls = " s" if len(p.get("headline", "")) > 34 else ""
    ca = group("ca", [kicker(p), f'<h2 class="h2{hcls} a">{md(p["headline"])}</h2>' if p.get("headline") else "",
                      f'<p class="lead a">{md(p["caption"])}</p>' if p.get("caption") else ""])
    cb = f'<div class="cb"><div class="device {device} a"><img src="{img}" alt=""></div></div>' if img else ""
    return "", ca + cb, ""


def L_cta(p, ctx):
    t = p.get("headline", "")
    logo = ""
    if p.get("show_logo", True):
        logo = (f'<img class="cta-logo a" src="{ctx["logo_big"]}" alt="">' if ctx["logo_big"]
                else f'<div class="wordmark cta-word a">{html.escape(ctx["name"])}</div>')
    ca = group("ca", [logo if ctx["aspect"] != "16x9" else "",
                      f'<h1 class="h1 {size_class(t, [(30, ""), (70, "l"), (999, "s")])} a">{md(t)}</h1>',
                      f'<p class="lead a">{md(p["sub"])}</p>' if p.get("sub") else "",
                      f'<div class="cta-btn a">{md(p["button"])} <span>{"←" if ctx["lang"] == "ar" else "→"}</span></div>' if p.get("button") else "",
                      f'<div class="url a">{md(p["url"])}</div>' if p.get("url") else ""])
    cb = group("cb", [logo]) if ctx["aspect"] == "16x9" else ""
    return "", ca + cb, ""


def L_custom(p, ctx):
    css = p.get("css", "")
    style = f"<style>{css}</style>" if css else ""
    return "", style + str(p.get("html", "")), ""


LAYOUTS = {"title": L_title, "stat": L_stat, "quote": L_quote, "list": L_list, "compare": L_compare,
           "icons": L_icons, "photo": L_photo, "screen": L_screen, "cta": L_cta, "custom": L_custom}


def build(spec: dict, variants: list[dict], proj: Path, motion: bool = False) -> dict:
    """Write one HyperFrames project holding the slides of the given variants back to back.
    Returns {"dir", "times": {variant_id: [snapshot seconds]}, "duration", "size"}."""
    slug, lang, aspect = spec["brand"], spec.get("language", "en"), spec.get("aspect", "4x5")
    kit = load_kit(slug)
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    assets = Assets(proj)
    faces, head, body = font_faces(kit, slug, assets)
    shutil.copy(HF / "vendor/gsap.min.js", proj / "assets/gsap.min.js")
    w, h = SIZES[aspect]
    c = kit["colors"]
    logos = {k: assets.add(brand_file(slug, v), "logo") for k, v in kit["logo"].items() if isinstance(v, str) and k != "icon"}
    motif = kit["motif"]
    handle = html.escape(kit.get("handle") or kit.get("website") or "")
    d = SLIDE_MOTION_S if motion else 1.0
    secs, times, k = [], {}, 0
    for variant in variants:
        slides = variant["slides"]
        n = len(slides)
        carousel = variant.get("format") == "carousel" and n > 1
        vtheme = variant.get("theme", kit["theme_default"])
        times[variant["id"]] = []
        for i, s in enumerate(slides):
            theme = s.get("theme", vtheme)
            logo = logos.get("on_light" if theme == "light" else "on_dark") or logos.get("on_dark") or logos.get("on_light") or ""
            ctx = {"slug": slug, "assets": assets, "lang": lang, "logo_big": logo, "aspect": aspect, "name": kit["name"]}
            props = s.get("props", {})
            extra, inner, bg = LAYOUTS[s["layout"]](props, ctx)
            classes = ["slide", "clip", f"theme-{theme}", extra]
            if s["layout"] in BOTTOM:
                classes.append("bottom")
            if props.get("align") == "center":
                classes.append("center")
            split = " split" if 'class="cb"' in inner and 'class="ca"' in inner else ""
            if s["layout"] == "cta":
                top = "<span></span>"
            elif logo:
                top = f'<img class="logo" src="{logo}" alt="">'
            else:
                top = f'<span class="wordmark">{html.escape(kit["name"])}</span>'
            count = f'<span class="count">{i + 1:02d}/{n:02d}</span>' if carousel else ""
            arrow = "←" if lang == "ar" else "→"
            foot_r = (f'<span class="swipe">{SWIPE.get(lang, "Swipe")} <b>{arrow}</b></span>' if carousel and i == 0 else
                      f'<span>{html.escape(kit.get("website", ""))}</span>' if carousel and i == n - 1 and kit.get("handle") and kit.get("website") else "")
            deco = "" if extra == "photo" else f'<div class="glow"></div><div class="motif motif-{motif}"><i></i><i></i><i></i></div>'
            k += 1
            secs.append(
                f'<section id="s{k}" class="{" ".join(x for x in classes if x)}" data-start="{(k - 1) * d:g}" data-duration="{d:g}">'
                f'{bg}{deco}<header class="chrome">{top}{count}</header>'
                f'<main class="body L-{s["layout"]}{split}">{inner}</main>'
                f'<footer class="foot"><span class="handle">{handle}</span>{foot_r}</footer></section>')
            times[variant["id"]].append(round((k - 1) * d + d * (0.85 if motion else 0.5), 3))
    n = k
    root_vars = (f"--w:{w}px;--h:{h}px;--radius:{kit.get('radius', 24)}px;"
                 f"--font-head:{stack(head, lang)};--font-body:{stack(body, lang)};"
                 f"--c-primary:{c['primary']};--c-secondary:{c['secondary']};"
                 f"--c-dark:{c['dark']};--c-light:{c['light']};"
                 f"--c-accent:{c['accent']};--c-on-dark:{c['text_on_dark']};"
                 f"--c-on-light:{c['text_on_light']};--bg-dark:{c['dark']};")
    tl = ["const tl = gsap.timeline({ paused: true });"]
    if motion:
        for i in range(n):
            tl.append(f'tl.from("#s{i + 1} .a", {{ opacity: 0, y: 46, duration: 0.6, ease: "power3.out", stagger: 0.09 }}, {i * d + 0.15:g});')
    tl.append('window.__timelines = window.__timelines || {};\nwindow.__timelines["post"] = tl;\ntl.seek(0);')
    css = (HF / "templates/post.css").read_text(encoding="utf-8")
    doc = f"""<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={w}, height={h}" />
<script src="assets/gsap.min.js"></script>
<style>
{faces}
:root {{ {root_vars} }}
{css}
</style>
</head>
<body>
<div id="root" class="a{aspect}" data-composition-id="post" data-start="0" data-duration="{n * d:g}" data-width="{w}" data-height="{h}">
{chr(10).join(secs)}
</div>
<script>
{chr(10).join(tl)}
</script>
</body>
</html>
"""
    (proj / "index.html").write_text(doc, encoding="utf-8")
    (proj / "meta.json").write_text(json.dumps({"id": "post-" + "".join(v["id"] for v in variants), "name": spec.get("topic", "post")[:60]}), encoding="utf-8")
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}), encoding="utf-8")
    return {"dir": proj, "times": times, "duration": n * d, "size": (w, h)}
