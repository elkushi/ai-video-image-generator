"""Backend tests for posts, brand onboarding, files and the stream parser. No Claude jobs are started:
the job manager is replaced by a fake before the app touches it (the real one would also pick up queued jobs).

Run:  .venv/bin/python app/server/tests/test_posts.py      (or with pytest, if installed)
Self-contained (CI too): builds a 3-variant post run for the public demo brand with placeholder
preview PNGs (no HyperFrames or Chrome needed) and removes it afterwards.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jobs  # noqa: E402
from PIL import Image  # noqa: E402


class FakeManager:
    def __init__(self):
        self.jobs: dict[str, jobs.Job] = {}
        self.submitted: list[jobs.Job] = []
        self.current = None

    def submit(self, **kw):
        j = jobs.Job(**kw)
        self.submitted.append(j)
        return j

    def queue_position(self, j):
        return 0


FAKE = FakeManager()
jobs.MANAGER = FAKE

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from settings import OUTPUT, POSTS, ROOT, UPLOADS  # noqa: E402
from stream_parser import StreamParser  # noqa: E402

FIXTURE = "2000-01-01_demo_backend-test-post"
TEMP = "2000-01-01_demo_backend-test-pick"
client = TestClient(main.app)


def make_fixture():
    """A post run as render_post.py leaves it: post.json, previews/<V>/slide_NN.png, index.json, events."""
    run = POSTS / FIXTURE
    if run.exists():
        shutil.rmtree(run)
    variants = [("A", "Lead with one number", "single", ["stat"]),
                ("B", "Explain it step by step", "carousel", ["title", "list", "cta"]),
                ("C", "One quote", "single", ["quote"])]
    spec = {"brand": "demo", "topic": "Backend test", "language": "en", "aspect": "4x5",
            "platforms": ["linkedin", "instagram"], "variants": []}
    index = {}
    for vid, angle, fmt, layouts in variants:
        spec["variants"].append({"id": vid, "angle": angle, "format": fmt, "theme": "dark",
                                 "copy": {"linkedin": f"Post {vid}.", "instagram": f"Post {vid}.", "alt": f"Slides of {vid}."},
                                 "slides": [{"layout": lay, "props": {"title": lay}} for lay in layouts]})
        (run / "previews" / vid).mkdir(parents=True)
        slides = []
        for i, _ in enumerate(layouts, 1):
            f = run / "previews" / vid / f"slide_{i:02d}.png"
            Image.new("RGB", (1080, 1350), (30, 30, 60)).save(f)
            slides.append(f".tmp/posts/{FIXTURE}/previews/{vid}/slide_{i:02d}.png")
        index[vid] = {"angle": angle, "format": fmt, "slides": slides}
    Image.new("RGB", (540, 675), (30, 30, 60)).save(run / "previews/contact.jpg")
    index["contact"] = f".tmp/posts/{FIXTURE}/previews/contact.jpg"
    (run / "post.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    (run / "previews/index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    (run / "events.jsonl").write_text(json.dumps({"source": "tool", "kind": "stage_end", "node": "render", "run": FIXTURE,
                                                  "data": {"ok": True, "seconds": 20.0}}) + "\n", encoding="utf-8")


def teardown_module():
    teardown_temp()
    if (POSTS / FIXTURE).exists():
        shutil.rmtree(POSTS / FIXTURE)


make_fixture()


def setup_temp():
    teardown_temp()
    shutil.copytree(POSTS / FIXTURE, POSTS / TEMP, ignore=shutil.ignore_patterns("hf"))


def teardown_temp():
    for d in (POSTS / TEMP, OUTPUT / TEMP):
        if d.exists():
            shutil.rmtree(d)


def test_get_post():
    r = client.get(f"/api/posts/{FIXTURE}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["run"] == f".tmp/posts/{FIXTURE}"
    assert {v["id"] for v in d["spec"]["variants"]} == {"A", "B", "C"}
    assert d["previews"]["B"]["slides"], d["previews"]
    for bad in ("..", ".hidden", "nope-post", "a..b", "../output", "x/../../etc"):
        try:
            main.get_post(bad)
            raise AssertionError(f"accepted {bad}")
        except main.HTTPException as e:
            assert e.status_code in (400, 404), bad
    assert client.get("/api/posts/%2e%2e").status_code in (400, 404)


def test_pick_and_busy():
    setup_temp()
    try:
        r = client.post(f"/api/posts/{TEMP}/pick", json={"variant": "B", "copy": {"alt": "Edited alt", "evil": "x",
                                                                                     "hashtags": ["A", "B"]}})
        assert r.status_code == 200, r.text
        files = set(r.json()["files"])
        assert {"carousel.pdf", "cover.jpg", "post.md", "post.json", "slide_01.png"} <= files, files
        md = (OUTPUT / TEMP / "post.md").read_text(encoding="utf-8")
        assert "Edited alt" in md and "#A #B" in md
        edits = json.loads((POSTS / TEMP / "copy_edits.json").read_text(encoding="utf-8"))
        assert "evil" not in edits
        assert client.get(f"/api/posts/{TEMP}").json()["output"] == TEMP
        # pick again: a single-image variant replaces the delivery
        r = client.post(f"/api/posts/{TEMP}/pick", json={"variant": "A"})
        assert r.status_code == 200, r.text
        assert "carousel.pdf" not in r.json()["files"]
        assert client.post(f"/api/posts/{TEMP}/pick", json={"variant": "Z"}).status_code == 400
        assert client.post(f"/api/posts/{TEMP}/pick", json={"variant": "a; rm"}).status_code == 400
        # gallery lists it as a post
        item = next(o for o in client.get("/api/outputs").json() if o["name"] == TEMP)
        assert item["kind"] == "post" and item["images"] and item["cover"], item
        det = client.get(f"/api/outputs/{TEMP}").json()
        assert det["post_spec"]["picked"] == "A" and det["post"], det.keys()
        # a running job on this run blocks pick and revise
        busy = jobs.Job(kind="post", status="running", meta={"run": TEMP})
        FAKE.jobs[busy.id] = busy
        assert client.post(f"/api/posts/{TEMP}/pick", json={"variant": "B"}).status_code == 409
        assert client.post(f"/api/posts/{TEMP}/revise", json={"feedback": "shorter"}).status_code == 409
        del FAKE.jobs[busy.id]
    finally:
        teardown_temp()


def test_revise():
    assert client.post(f"/api/posts/{FIXTURE}/revise", json={"feedback": "  "}).status_code == 400
    assert client.post(f"/api/posts/{FIXTURE}/revise", json={"feedback": "x", "variants": ["Q"]}).status_code == 400
    r = client.post(f"/api/posts/{FIXTURE}/revise", json={"feedback": "Make B punchier", "variants": ["B"]})
    assert r.status_code == 200, r.text
    j = FAKE.submitted[-1]
    assert j.kind == "post" and j.meta["schema"] == "post_result.json" and j.meta["run"] == FIXTURE
    assert "Make B punchier" in j.prompt and "do NOT deliver" in j.prompt


def test_make_post_and_uploads():
    assert client.post("/api/jobs/post", json={"brand": "no-such-brand", "topic": "x"}).status_code == 404
    assert client.post("/api/jobs/post", json={"topic": "x"}).status_code == 400
    for bad in ("/etc/passwd", "../../etc/passwd", ".env", "brands/demo/brand.json"):
        r = client.post("/api/jobs/post", json={"brand": "demo", "topic": "x", "uploads": [bad]})
        assert r.status_code == 400, (bad, r.text)
    assert client.post("/api/jobs/post", json={"brand": "demo", "topic": "x", "aspect": "3x2"}).status_code == 422
    up = UPLOADS / "r1-test"
    up.mkdir(parents=True, exist_ok=True)
    (up / "guide.txt").write_text("brand guide", encoding="utf-8")
    try:
        r = client.post("/api/jobs/post", json={"brand": "demo", "topic": "Uptime", "post_format": "carousel",
                                                "aspect": "1x1", "motion": True,
                                                "uploads": [".tmp/app/uploads/r1-test/guide.txt"]})
        assert r.status_code == 200, r.text
        j = FAKE.submitted[-1]
        assert j.kind == "post" and j.meta["schema"] == "post_result.json"
        assert j.prompt.startswith("/post demo Uptime") and "carousel" in j.prompt and "--motion" in j.prompt
    finally:
        shutil.rmtree(up)


def test_brands():
    r = client.post("/api/brands", json={"name": "شركة النور", "website": "example.com"})
    assert r.status_code == 200, r.text
    assert FAKE.submitted[-1].brand.startswith("brand-") and FAKE.submitted[-1].kind == "onboard"
    r = client.post("/api/brands", json={"name": "Новая Школа"})
    assert FAKE.submitted[-1].brand == "novaya-shkola"
    assert client.post("/api/brands", json={"name": "Demo"}).status_code == 409
    assert client.post("/api/brands", json={"name": "  "}).status_code == 400
    assert client.post("/api/brands", json={"name": "X", "uploads": ["/etc/hosts"]}).status_code == 400
    assert client.post("/api/brands/no-such/guide", json={"notes": "x"}).status_code == 404
    assert client.post("/api/brands/demo/guide", json={}).status_code == 400
    assert client.post("/api/brands/demo/guide", json={"notes": "new blue"}).status_code == 200


def test_files():
    assert client.get(f"/files/.tmp/posts/{FIXTURE}/previews/contact.jpg").status_code == 200
    for bad in (".env", "tools/common.py", "%2e%2e/%2e%2e/%2e%2e/etc/passwd", "output/%2e%2e/.env",
                ".tmp/posts/%2e%2e/app/jobs", "brands/%2e%2e/.env"):
        assert client.get(f"/files/{bad}").status_code == 404, bad
    for bad in ("../../../etc/passwd", "output/../.env"):  # httpx normalises these to other routes; never the file
        assert "root:" not in client.get(f"/files/{bad}").text and "API_KEY" not in client.get(f"/files/{bad}").text


def test_stream_parser():
    p = StreamParser()
    lines = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a1", "name": "Agent", "input": {"subagent_type": "post-copywriter", "description": "3 angles"}},
            {"type": "tool_use", "id": "a2", "name": "Agent", "input": {"subagent_type": "post-designer", "description": "slides"}},
            {"type": "tool_use", "id": "a3", "name": "Agent", "input": {"subagent_type": "video-qa-reviewer", "description": "QA"}},
            {"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": ".venv/bin/python tools/render_post.py .tmp/posts/x"}},
            {"type": "tool_use", "id": "b2", "name": "Bash", "input": {"command": ".venv/bin/python tools/deliver_post.py .tmp/posts/x --pick A"}},
            {"type": "tool_use", "id": "b3", "name": "Bash", "input": {"command": ".venv/bin/python tools/new_post.py --brand x --topic y"}},
            {"type": "tool_use", "id": "b4", "name": "Bash", "input": {"command": ".venv/bin/python tools/validate_post.py .tmp/posts/x/post.json"}},
        ]}},
    ]
    evs = [e for line in lines for e in p.feed(json.dumps(line))]
    nodes = [(e["kind"], e["node"]) for e in evs]
    for want in [("agent_start", "post-copywriter"), ("agent_start", "post-designer"), ("agent_start", "qa-reviewer"),
                 ("tool_start", "render"), ("tool_start", "deliver"), ("tool_start", "intake"), ("tool_start", "validate")]:
        assert want in nodes, (want, nodes)
    end = p.feed(json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "b1", "content": "rendered 6 slide(s)"}]}}))
    assert end and end[0]["kind"] == "tool_end" and end[0]["node"] == "render"


def test_result_normalize_and_timings():
    j = jobs.Job(kind="post", result={"run": str(POSTS / FIXTURE), "summary": "s", "variants": []})
    jobs.JobManager.normalize_post_result(None, j)
    assert j.result["run"] == f".tmp/posts/{FIXTURE}" and j.result["summary"] == "s"
    j = jobs.Job(kind="post", result=None, run=FIXTURE)
    jobs.JobManager.normalize_post_result(None, j)
    assert j.result == {"summary": "", "variants": [], "run": f".tmp/posts/{FIXTURE}"}
    t = client.get("/api/timings").json()
    assert {"median_s", "per_video_second", "samples", "post_median_s", "post_samples"} <= set(t)
    assert "render" in t["post_median_s"], t["post_median_s"]


def test_dotdot_names():
    """%2e%2e arrives as a '..' path param; it must never resolve to the repo root."""
    n = len(FAKE.submitted)
    for method, url, body in [
        ("post", "/api/brands/%2e%2e/calendar/approve", {"items": []}),
        ("post", "/api/brands/%2e%2e/calendar/plan", {}),
        ("post", "/api/brands/%2e%2e/performance", None),
        ("get", "/api/brands/%2e%2e", None),
        ("post", "/api/outputs/%2e%2e/stats", {"platform": "x"}),
        ("post", "/api/outputs/%2e%2e/revise", {"feedback": "x"}),
        ("get", "/api/outputs/%2e%2e", None),
    ]:
        r = client.request(method, url, json=body)
        assert r.status_code == 404, (url, r.status_code, r.text)
    assert len(FAKE.submitted) == n
    assert not (ROOT / "calendar.json").exists() and not (ROOT / "stats.json").exists()


def test_slugify():
    assert main.slugify("Acme Co.") == "acme-co"
    assert main.slugify("Объём") == "obem"
    assert main.slugify("شركة") == main.slugify("شركة") and main.slugify("شركة").startswith("brand-")


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok    {name}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL  {name}: {type(e).__name__}: {e}")
    teardown_module()
    print("PASS" if not failed else f"{failed} failed")
    sys.exit(1 if failed else 0)
