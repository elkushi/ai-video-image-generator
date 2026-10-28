"""PreToolUse hook for headless jobs: the last word on every Bash command and file access the agent makes.

Two live injection tests shaped this. Permission rules match a command as text and the shell expands it
afterwards, so `grep -r KEY .e??` read .env (the glob became .env after the check, and grep is a
read-only command Claude Code allows on its own). And the Read tool happily read a file in the user's
home folder, outside the project. So this hook decides on parsed commands and resolved paths:

Bash
- must start with one of the allow-listed programs (settings.BASH_PREFIXES), so grep, find, cat and
  the other auto-allowed read-only commands are refused;
- must not contain shell syntax (globs, $, backticks, pipes, ;, &&, redirects, ~);
- no argument may contain .. (else "python3 tools/../.tmp/x.py" runs a script the agent just wrote),
  name a secret, or be an absolute path outside the places below.
Read, Grep, Glob, Edit, Write
- the path must be inside the project (or a global Claude skill, read-only), and not a secret.

Exit code 2 blocks the call and shows the reason to the agent. Wired in by jobs.py via --settings.
"""
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import BASH_PREFIXES, ROOT  # noqa: E402

SHELL_CHARS = set("*?[]$`;|&<>(){}~\\\n\r")  # special to the shell outside quotes
STUDIO_TSC = "cd studio && npx tsc"
SECRET_NAMES = {".env", "credentials.json", "token.json"}
SKILLS = Path.home() / ".claude" / "skills"
READ_ONLY_ROOTS = [SKILLS, Path("/usr/share")]  # global skills, system fonts
FILE_TOOLS = {"Read": "file_path", "Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
              "NotebookEdit": "notebook_path", "Grep": "path", "Glob": "path"}


def resolve(path: str) -> Path | None:
    try:
        p = Path(path).expanduser()
        return (p if p.is_absolute() else ROOT / p).resolve()
    except (OSError, RuntimeError):
        return None


def is_secret(r: Path) -> bool:
    return r.name in SECRET_NAMES or r.name.startswith(".env.")


def inside(r: Path, write: bool) -> bool:
    roots = [ROOT] if write else [ROOT, *READ_ONLY_ROOTS]
    return any(r.is_relative_to(root) for root in roots)


def check_path(path: str, write: bool = False) -> str | None:
    r = resolve(path)
    if r is None:
        return "the path could not be resolved"
    if is_secret(r) or is_secret(Path(path)):
        return "secrets are off limits"
    if not inside(r, write):
        return "only files inside the project may be used"
    return None


def has_shell_syntax(cmd: str) -> bool:
    """True if the shell would do more than split cmd into words. Inside single quotes nothing is
    special; inside double quotes $, ` and \\ still are. So an ffmpeg filter in quotes is fine."""
    quote = None
    for c in cmd:
        if quote == "'":
            quote = None if c == "'" else quote
        elif quote == '"':
            if c == '"':
                quote = None
            elif c in "$`\\":
                return True
        elif c in "'\"":
            quote = c
        elif c in SHELL_CHARS:
            return True
    return quote is not None


def check(command: str) -> str | None:
    """None if the Bash command may run, otherwise the reason it may not."""
    cmd = command.strip()
    if not cmd:
        return "empty command"
    if cmd.startswith(STUDIO_TSC):  # the one compound command: type-check the Remotion studio
        cmd = cmd[len("cd studio && "):]
    if has_shell_syntax(cmd):
        return "shell syntax (globs, $, pipes, ;, &&, redirects) is not allowed; run one plain command"
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return "the command could not be parsed"
    if not any(cmd == p.rstrip() or cmd.startswith(p) for p in BASH_PREFIXES):
        return "only the allow-listed commands may run (see workflows/app.md)"
    for arg in argv:
        for part in arg.split("="):  # --input=.env
            if not part:
                continue
            if ".." in Path(part).parts:
                return "paths with .. are not allowed"
            if is_secret(Path(part)):
                return "secrets are off limits"
            if part.startswith("/") and (reason := check_path(part)):
                return reason
    return None


def check_tool(tool: str, tool_input: dict) -> str | None:
    if tool == "Bash":
        return check(tool_input.get("command", ""))
    key = FILE_TOOLS.get(tool)
    if key and tool_input.get(key):
        return check_path(tool_input[key], write=tool not in ("Read", "Grep", "Glob"))
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        reason = check_tool(event.get("tool_name", ""), event.get("tool_input") or {})
    except (ValueError, AttributeError):
        reason = "unreadable hook input"
    if reason:
        print(f"blocked: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
