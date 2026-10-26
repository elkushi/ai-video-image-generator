# syntax=docker/dockerfile:1.7
# Video & post factory: FastAPI app + web UI + Python tools + Remotion (videos) + HyperFrames (posts)
# + the Claude Code CLI that runs the headless jobs.
#
#   docker build -t video-factory .
#   docker compose up -d            # see docker-compose.yml (localhost only by default)
#
# Claude auth (no API key needed): each deployment uses its own Claude subscription, either
#   CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token` (in .env), or
#   `docker compose exec -it factory claude auth login` once (stored in CLAUDE_CONFIG_DIR, a volume).
# ANTHROPIC_API_KEY is an optional, billed alternative.

ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=24

# ---------- node toolchain (copied into the runtime image) ----------
FROM node:${NODE_VERSION}-bookworm-slim AS node

# ---------- web UI ----------
FROM node AS web
WORKDIR /src/app/web
COPY app/web/package.json app/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/web/ ./
RUN npm run build

# ---------- JS dependencies for the renderers ----------
FROM node AS jsdeps
WORKDIR /src
COPY studio/package.json studio/package-lock.json studio/
RUN cd studio && npm ci --no-audit --no-fund
COPY hyperframes/package.json hyperframes/package-lock.json hyperframes/
RUN cd hyperframes && npm ci --no-audit --no-fund

# ---------- Python virtualenv (same path as at runtime: tools are called as .venv/bin/python) ----------
FROM python:${PYTHON_VERSION}-slim AS pydeps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- runtime ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG WITH_PLAYWRIGHT=1
# Match your host user in local-laptop mode so bind-mounted folders stay writable (see docker-compose.local.yml)
ARG APP_UID=10001
ARG APP_GID=10001
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    FACTORY_HOST=0.0.0.0 \
    FACTORY_PORT=8787 \
    HOME=/home/factory \
    CLAUDE_CONFIG_DIR=/home/factory/.claude \
    PATH=/app/.venv/bin:/usr/local/bin:/usr/bin:/bin \
    DO_NOT_TRACK=1 \
    HYPERFRAMES_SKIP_SKILLS=1 \
    HYPERFRAMES_NO_TELEMETRY=1 \
    HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    PUPPETEER_SKIP_DOWNLOAD=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HF_HOME=/app/.tmp/cache/huggingface \
    U2NET_HOME=/app/.tmp/cache/u2net

# ffmpeg (render/QA), chromium (HyperFrames + Remotion deps), fonts with Arabic/Cyrillic coverage,
# Vulkan CPU driver (lavapipe) for the local sd.cpp/Real-ESRGAN builds, pdftotext/identify (allow-listed
# for headless Claude), git (Claude Code), curl (healthcheck), psmisc (fuser).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg chromium \
        fonts-noto-core fonts-dejavu-core fonts-liberation fonts-noto-color-emoji \
        libvulkan1 mesa-vulkan-drivers \
        poppler-utils imagemagick git curl ca-certificates psmisc tini \
    && rm -rf /var/lib/apt/lists/*

# Node runtime from the official image
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm i -g --no-audit --no-fund @anthropic-ai/claude-code \
    && npm cache clean --force

RUN /usr/sbin/groupadd --gid ${APP_GID} factory \
    && /usr/sbin/useradd --uid ${APP_UID} --gid factory --create-home --home-dir /home/factory --shell /bin/bash factory

WORKDIR /app
COPY --from=pydeps --chown=factory:factory /app/.venv /app/.venv

# Playwright's own Chromium for tools/capture_screens.py and tools/extract_brand.py (optional, ~300 MB)
RUN if [ "$WITH_PLAYWRIGHT" = "1" ]; then \
        /app/.venv/bin/python -m playwright install --with-deps chromium \
        && chown -R factory:factory /ms-playwright; \
    fi

COPY --chown=factory:factory . /app
COPY --from=jsdeps --chown=factory:factory /src/studio/node_modules /app/studio/node_modules
COPY --from=jsdeps --chown=factory:factory /src/hyperframes/node_modules /app/hyperframes/node_modules
COPY --from=web --chown=factory:factory /src/app/web/dist /app/app/web/dist

RUN mkdir -p /app/.tmp /app/output /app/assets/music /home/factory/.claude \
    && chown -R factory:factory /app/.tmp /app/output /app/assets/music /app/brands /home/factory \
    && chmod +x /app/deploy/entrypoint.sh

USER factory

# Remotion's headless Chrome is fetched at build time so the first render needs no network;
# HyperFrames uses the system chromium (HYPERFRAMES_BROWSER_PATH) and its telemetry is switched off.
RUN cd /app/studio && npx remotion browser ensure
RUN /app/hyperframes/node_modules/.bin/hyperframes telemetry disable || true

VOLUME ["/app/brands", "/app/output", "/app/.tmp", "/app/assets/music", "/home/factory/.claude"]
EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=20s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8787/api/system >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/deploy/entrypoint.sh"]
