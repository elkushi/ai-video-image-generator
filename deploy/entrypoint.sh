#!/usr/bin/env bash
# Container entrypoint: make sure the mounted volumes have the folders the factory expects, report
# how Claude is authenticated, then start the app (or run the command passed, e.g. a smoke test).
set -euo pipefail
cd /app

mkdir -p .tmp/app/jobs .tmp/app/uploads .tmp/posts .tmp/videos .tmp/cache output assets/music
[ -f output/.gitkeep ] || touch output/.gitkeep

# A fresh named volume over /app/brands is seeded from the image; a bind mount may be empty.
if [ ! -d brands/_template ]; then
  echo "warning: brands/_template is missing (empty bind mount?). New brands need it: copy it from the repo." >&2
fi

# Claude auth, in the order Claude Code itself prefers: an API key wins over the subscription.
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "claude auth: ANTHROPIC_API_KEY (billed per use)." >&2
  if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || [ -s "$cfg/.credentials.json" ]; then
    echo "warning: a subscription login is also present, but the API key takes precedence. Unset ANTHROPIC_API_KEY to use the subscription." >&2
  fi
elif [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "claude auth: subscription token (CLAUDE_CODE_OAUTH_TOKEN)." >&2
elif [ -s "$cfg/.credentials.json" ]; then
  echo "claude auth: subscription login stored in $cfg." >&2
else
  echo "claude auth: NOT LOGGED IN. Jobs will fail until you either" >&2
  echo "  - run 'claude setup-token' on a machine with a browser and put CLAUDE_CODE_OAUTH_TOKEN=... in .env, or" >&2
  echo "  - run once: docker compose exec -it factory claude auth login" >&2
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec /app/.venv/bin/python app/server/main.py
