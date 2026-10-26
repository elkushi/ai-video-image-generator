#!/usr/bin/env bash
# Factory app launcher.
#   ./factory.sh          build the web UI if needed, then serve everything on http://127.0.0.1:8787
#   ./factory.sh dev      backend on :8787 + Vite dev server with hot reload on http://127.0.0.1:5173
#   ./factory.sh stop     stop a backend started by this script
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
PIDFILE=.tmp/app/server.pid
mkdir -p .tmp/app

stop() { [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null || true; rm -f "$PIDFILE"; fuser -k 8787/tcp >/dev/null 2>&1 || true; }
start_backend() {
  stop
  nohup "$PY" app/server/main.py >> .tmp/app/server.log 2>&1 &
  echo $! > "$PIDFILE"
  for _ in $(seq 1 30); do curl -sf http://127.0.0.1:8787/api/system >/dev/null && return 0; sleep 0.5; done
  echo "backend did not start; see .tmp/app/server.log"; exit 1
}

case "${1:-}" in
  stop) stop; echo "stopped" ;;
  dev)
    start_backend
    trap stop EXIT
    [ -d app/web/node_modules ] || (cd app/web && npm install)
    cd app/web && npx vite --host 127.0.0.1 --port 5173
    ;;
  *)
    [ -d app/web/node_modules ] || (cd app/web && npm install)
    [ -f app/web/dist/index.html ] && [ -z "$(find app/web/src -newer app/web/dist/index.html -print -quit)" ] || (cd app/web && npm run build)
    start_backend
    echo "Factory running at http://127.0.0.1:8787  (logs: .tmp/app/server.log, stop: ./factory.sh stop)"
    ;;
esac
