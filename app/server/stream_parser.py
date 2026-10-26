"""Turn Claude Code `--output-format stream-json` lines into Factory events.

Claude events we use:
  system/init                    -> session id, model
  assistant tool_use "Agent"     -> agent_start (node from subagent_type)
  system/task_started            -> agent_start (background agents)
  system/task_notification       -> agent_end
  user tool_result for an Agent  -> agent_end (foreground agents)
  assistant tool_use "Bash"      -> tool_start when it runs tools/<x>.py, else activity
  other tool_use (Read, Write..) -> activity (small ticker in the UI)
  assistant text                 -> thought (node = the agent that said it, via parent_tool_use_id)
  result                         -> usage (turns, tokens, time)
Text containing "@@QUESTION {json}" -> question (the app shows a card; the answer resumes the session).
"""
import json
import re

from settings import AGENT_NODES, TOOL_NODES

TOOL_RE = re.compile(r"tools/([a-z_]+)\.py")
QUESTION_RE = re.compile(r"@@QUESTION\s*(\{.*\})", re.S)


def short(v, n=140) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def parse_question(text: str):
    m = QUESTION_RE.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    for end in range(len(raw), 0, -1):  # tolerate trailing prose after the JSON
        if raw[end - 1] != "}":
            continue
        try:
            q = json.loads(raw[:end])
            return q if isinstance(q, dict) else None
        except ValueError:
            continue
    return None


class StreamParser:
    def __init__(self):
        self.tool_uses: dict[str, dict] = {}   # tool_use_id -> {name, node, kind}
        self.agent_of: dict[str, str] = {}     # Agent tool_use_id -> node
        self.ended: set[str] = set()
        self.session_id = None
        self.last_text = ""

    def node_for_parent(self, parent):
        return self.agent_of.get(parent, "claude") if parent else "claude"

    def feed(self, line: str) -> list[dict]:
        try:
            e = json.loads(line)
        except ValueError:
            return []
        t, st = e.get("type"), e.get("subtype")
        out = []
        if t == "system" and st == "init":
            self.session_id = e.get("session_id")
            out.append(ev("log", "claude", session_id=self.session_id, model=e.get("model"),
                          auth=e.get("apiKeySource"), mcp=len(e.get("mcp_servers") or [])))
        elif t == "system" and st == "task_started":
            tid = e.get("tool_use_id")
            node = AGENT_NODES.get(e.get("subagent_type"), "agent")
            if tid and tid not in self.agent_of:
                self.agent_of[tid] = node
                out.append(ev("agent_start", node, agent=e.get("subagent_type"), task=short(e.get("description", ""))))
        elif t == "system" and st == "task_progress":
            node = self.agent_of.get(e.get("tool_use_id"), "agent")
            if e.get("last_tool_name"):
                out.append(ev("activity", node, tool=e.get("last_tool_name")))
        elif t == "system" and st == "task_notification":
            tid = e.get("tool_use_id")
            if tid and tid not in self.ended:
                self.ended.add(tid)
                out.append(ev("agent_end", self.agent_of.get(tid, "agent"), status=e.get("status"),
                              summary=short(e.get("summary", ""), 240)))
        elif t == "assistant":
            parent = e.get("parent_tool_use_id")
            who = self.node_for_parent(parent)
            for c in e.get("message", {}).get("content", []):
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text", "").strip():
                    text = c["text"].strip()
                    if not parent:
                        self.last_text = text
                    q = parse_question(text)
                    if q and not parent:
                        out.append(ev("question", "claude", **q))
                    out.append(ev("thought", who, text=short(QUESTION_RE.sub("", text), 600)))
                elif c.get("type") == "tool_use":
                    out += self.tool_use(c, who)
        elif t == "user":
            for c in e.get("message", {}).get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    out += self.tool_result(c)
        elif t == "result":
            u = e.get("usage") or {}
            out.append(ev("usage", "claude", turns=e.get("num_turns"), seconds=round((e.get("duration_ms") or 0) / 1000, 1),
                          output_tokens=u.get("output_tokens"), input_tokens=(u.get("input_tokens") or 0)
                          + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0),
                          denials=[short(d, 120) for d in e.get("permission_denials") or []],
                          is_error=e.get("is_error"), structured=e.get("structured_output")))
        return out

    def tool_use(self, c: dict, who: str) -> list[dict]:
        name, inp, tid = c.get("name"), c.get("input") or {}, c.get("id")
        if name in ("Agent", "Task"):
            node = AGENT_NODES.get(inp.get("subagent_type"), "agent")
            self.agent_of[tid] = node
            self.tool_uses[tid] = {"name": name, "node": node, "kind": "agent"}
            return [ev("agent_start", node, agent=inp.get("subagent_type"), task=short(inp.get("description", "")),
                       by=who)]
        if name == "Bash":
            cmd = inp.get("command", "")
            m = TOOL_RE.search(cmd)
            if m and m.group(1) in TOOL_NODES:
                node = TOOL_NODES[m.group(1)]
                self.tool_uses[tid] = {"name": m.group(1), "node": node, "kind": "tool"}
                return [ev("tool_start", node, tool=m.group(1) + ".py", command=short(cmd, 200), by=who)]
            self.tool_uses[tid] = {"name": "Bash", "node": who, "kind": "activity"}
            return [ev("activity", who, tool="Bash", detail=short(inp.get("description") or cmd))]
        detail = inp.get("file_path") or inp.get("pattern") or inp.get("skill") or inp.get("query") or inp.get("url") or ""
        self.tool_uses[tid] = {"name": name, "node": who, "kind": "activity"}
        return [ev("activity", who, tool=name, detail=short(str(detail).replace(str(_root()), "").lstrip("/")))]

    def tool_result(self, c: dict) -> list[dict]:
        tid = c.get("tool_use_id")
        info = self.tool_uses.get(tid)
        if not info:
            return []
        content = c.get("content")
        text = content if isinstance(content, str) else " ".join(
            x.get("text", "") for x in content or [] if isinstance(x, dict))
        err = bool(c.get("is_error"))
        if info["kind"] == "agent":
            if "Async agent launched" in text or tid in self.ended:
                return []
            self.ended.add(tid)
            return [ev("agent_end", info["node"], status="error" if err else "completed", summary=short(text, 240))]
        if info["kind"] == "tool":
            return [ev("tool_end", info["node"], tool=info["name"] + ".py", ok=not err, tail=short(text[-400:], 400))]
        if err:
            return [ev("activity", info["node"], tool=info["name"], error=short(text, 200))]
        return []


def _root():
    from settings import ROOT
    return ROOT


def ev(kind: str, node: str, **data) -> dict:
    return {"source": "claude", "kind": kind, "node": node, "data": data}
