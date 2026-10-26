"""Job queue: one headless Claude Code session at a time (the laptop can't render two videos at once).

A job = one prompt run by `claude -p` in the repo root. Its events (from Claude's stream and from the
Python tools via FACTORY_JOB) are merged into .tmp/app/jobs/<id>/events.jsonl, which the SSE endpoint tails.
If Claude ends its turn with @@QUESTION, the job waits; an answer resumes the same session.
"""
import json
import os
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

from settings import (ALLOWED_TOOLS, CLAUDE_BIN, CLAUDE_MODEL, DISALLOWED_TOOLS, JOBS_DIR, POSTS, PROMPTS, ROOT,
                      SCHEMAS)
from stream_parser import StreamParser, parse_question

ACTIVE = {"queued", "running"}
FINISHED = {"done", "error", "cancelled"}


class Job:
    def __init__(self, **kw):
        self.id = kw.get("id") or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.kind = kw.get("kind", "video")          # video | series | post | onboard | calendar | revise | performance
        self.title = kw.get("title", "")
        self.brand = kw.get("brand", "")
        self.prompt = kw.get("prompt", "")
        self.status = kw.get("status", "queued")      # queued | running | waiting | done | error | cancelled
        self.created = kw.get("created", time.time())
        self.started = kw.get("started")
        self.ended = kw.get("ended")
        self.session_id = kw.get("session_id") or str(uuid.uuid4())
        self.resumes = kw.get("resumes", 0)           # how many answer/continue turns so far
        self.pending_prompt = kw.get("pending_prompt")  # next prompt for a resume
        self.question = kw.get("question")
        self.run = kw.get("run")                      # .tmp/videos/<run> or .tmp/posts/<run> name, from tool events
        self.output = kw.get("output")                # output/<name> once delivered
        self.usage = kw.get("usage", {})
        self.result = kw.get("result")                # structured output (calendar plans)
        self.error = kw.get("error")
        self.meta = kw.get("meta", {})                # form fields, for display
        # what the job is for, explicit so the UI never guesses from the title:
        # video | series | onboard-video | post | post-revise | brand-new | brand-guide | revise | performance | calendar
        self.flow = kw.get("flow") or kw.get("kind", "video")

    @property
    def dir(self) -> Path:
        return JOBS_DIR / self.id

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / "job.json.tmp"
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.dir / "job.json")


class JobManager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.proc: subprocess.Popen | None = None
        self.current: Job | None = None
        for f in sorted(JOBS_DIR.glob("*/job.json")):
            try:
                j = Job(**json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
            if j.status == "running":  # the server stopped mid-job
                j.status, j.error = "error", "Factory server restarted while this job was running"
                j.save()
            self.jobs[j.id] = j
        threading.Thread(target=self.worker, daemon=True).start()

    # ---- public API -------------------------------------------------------------------------
    def submit(self, **kw) -> Job:
        j = Job(**kw)
        j.save()
        with self.lock:
            self.jobs[j.id] = j
        self.append(j, {"source": "app", "kind": "log", "node": "app", "data": {"queued": True, "title": j.title}})
        self.wake.set()
        return j

    def answer(self, job_id: str, text: str) -> Job:
        j = self.jobs[job_id]
        if j.status not in ("waiting", "done", "error"):
            raise ValueError(f"job is {j.status}")
        j.status, j.question, j.pending_prompt, j.error = "queued", None, text, None
        j.save()
        self.append(j, {"source": "app", "kind": "answer", "node": "app", "data": {"text": text}})
        self.wake.set()
        return j

    def cancel(self, job_id: str) -> Job:
        j = self.jobs[job_id]
        if j.status == "running" and self.proc and self.current is j:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if j.status not in FINISHED:
            j.status, j.ended = "cancelled", time.time()
            j.save()
            self.append(j, {"source": "app", "kind": "done", "node": "app", "data": {"status": "cancelled"}})
        return j

    def list(self) -> list[dict]:
        return [j.to_dict() for j in sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)]

    def queue_position(self, j: Job) -> int:
        queued = sorted((x for x in self.jobs.values() if x.status == "queued"), key=lambda x: x.created)
        return next((i + 1 for i, x in enumerate(queued) if x is j), 0)

    # ---- events ---------------------------------------------------------------------------
    def append(self, j: Job, e: dict) -> None:
        e = {"ts": round(time.time(), 3), "job": j.id, **e}
        with self.lock:
            with open(j.dir / "events.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")

    # ---- worker ---------------------------------------------------------------------------
    def worker(self) -> None:
        while True:
            self.wake.wait(2)
            self.wake.clear()
            nxt = sorted((j for j in self.jobs.values() if j.status == "queued"), key=lambda j: j.created)
            if nxt:
                self.run(nxt[0])
                self.wake.set()

    def command(self, j: Job) -> list[str]:
        cmd = [CLAUDE_BIN, "-p", "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits", "--strict-mcp-config",
               "--allowedTools", *ALLOWED_TOOLS, "--disallowedTools", *DISALLOWED_TOOLS,
               "--append-system-prompt-file", str(PROMPTS / "headless.md")]
        if CLAUDE_MODEL:
            cmd += ["--model", CLAUDE_MODEL]
        if (j.meta or {}).get("schema"):
            cmd += ["--json-schema", (SCHEMAS / j.meta["schema"]).read_text(encoding="utf-8")]
        if j.resumes or j.pending_prompt:
            cmd += ["--resume", j.session_id]
        else:
            cmd += ["--session-id", j.session_id]
        return cmd

    def run(self, j: Job) -> None:
        prompt = j.pending_prompt or j.prompt
        resumed = bool(j.pending_prompt)
        j.status, j.started = "running", j.started or time.time()
        j.pending_prompt = None
        j.save()
        self.current = j
        self.append(j, {"source": "app", "kind": "log", "node": "app",
                        "data": {"started": True, "resume": resumed, "prompt": prompt[:2000]}})
        env = {**os.environ, "FACTORY_JOB": j.id, "PYTHONUNBUFFERED": "1",
               "PATH": f"{ROOT / '.venv/bin'}:{os.environ.get('PATH', '')}", "VIRTUAL_ENV": str(ROOT / ".venv")}
        stop = threading.Event()
        watcher = threading.Thread(target=self.watch_tools, args=(j, stop), daemon=True)
        watcher.start()
        parser = StreamParser()
        try:
            self.proc = subprocess.Popen(self.command(j) + ["--", prompt], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
                                         start_new_session=True)
            with open(j.dir / "claude_stream.jsonl", "a", encoding="utf-8") as raw:
                for line in self.proc.stdout:
                    raw.write(line)
                    for e in parser.feed(line):
                        if e["kind"] == "usage":
                            self.merge_usage(j, e["data"])
                            if e["data"].get("structured") is not None:
                                j.result = e["data"]["structured"]
                        self.append(j, e)
            code = self.proc.wait()
            err = self.proc.stderr.read()[-2000:]
        except FileNotFoundError:
            code, err = 127, f"'{CLAUDE_BIN}' not found: install Claude Code and log in (claude /login)"
        finally:
            stop.set()
            watcher.join(timeout=3)
            self.proc = None
            self.current = None
        j.resumes += 1
        if j.status == "cancelled":
            return
        q = parse_question(parser.last_text)
        if code == 0 and q:
            j.status, j.question = "waiting", q
            self.append(j, {"source": "app", "kind": "waiting", "node": "app", "data": q})
        elif code == 0:
            j.status, j.ended = "done", time.time()
            if j.kind == "post":
                self.normalize_post_result(j)
            self.append(j, {"source": "app", "kind": "done", "node": "app",
                            "data": {"status": "done", "output": j.output, "summary": parser.last_text[-1500:]}})
        else:
            j.status, j.ended, j.error = "error", time.time(), (err or f"claude exited {code}").strip()
            self.append(j, {"source": "app", "kind": "error", "node": "app", "data": {"error": j.error[-800:]}})
        j.save()

    def normalize_post_result(self, j: Job) -> None:
        """job.result.run must be ".tmp/posts/<name>" of an existing run, whatever form Claude returned."""
        res = j.result if isinstance(j.result, dict) else {}
        cands = [Path(str(res.get("run") or "")).name, (j.meta or {}).get("run"), j.run]
        name = next((c for c in cands if c and (POSTS / c / "post.json").is_file()), None)
        if name:
            j.result = {"summary": "", "variants": [], **res, "run": f".tmp/posts/{name}"}

    def merge_usage(self, j: Job, u: dict) -> None:
        tot = j.usage or {}
        for k in ("turns", "seconds", "output_tokens", "input_tokens"):
            tot[k] = round((tot.get(k) or 0) + (u.get(k) or 0), 1)
        if u.get("denials"):
            tot["denials"] = (tot.get("denials") or []) + u["denials"]
        j.usage = tot
        j.save()

    def watch_tools(self, j: Job, stop: threading.Event) -> None:
        """Tail tool_events.jsonl (written by tools/events.py) into the job's event stream."""
        path = j.dir / "tool_events.jsonl"
        pos = path.stat().st_size if path.exists() else 0
        while True:
            done = stop.is_set()
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    f.seek(pos)
                    for line in f:
                        if not line.endswith("\n"):
                            break
                        pos += len(line.encode("utf-8"))
                        try:
                            e = json.loads(line)
                        except ValueError:
                            continue
                        if e.get("run") and e["run"] != j.run:
                            j.run = e["run"]
                            j.save()
                        if e.get("node") == "deliver" and e.get("data", {}).get("folder"):
                            j.output = Path(e["data"]["folder"]).name
                            j.save()
                        self.append(j, e)
            if done:
                return
            time.sleep(0.4)


MANAGER: JobManager | None = None


def manager() -> JobManager:
    global MANAGER
    if MANAGER is None:
        MANAGER = JobManager()
    return MANAGER
