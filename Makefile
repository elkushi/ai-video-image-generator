# Shortcuts for the Docker deployment. Local dev without Docker: ./factory.sh (or `vg`).
SHELL := /bin/bash
COMPOSE_LOCAL := docker compose -f docker-compose.yml -f docker-compose.local.yml
.PHONY: build up up-local up-public down logs ps shell login token auth-status models smoke invite reload-proxy

build:
	docker compose build

up:                      ## private: http://127.0.0.1:8787, data in Docker volumes
	docker compose up -d

up-local:                ## laptop: brands/, output/, assets/music/ as repo folders, built with your uid
	APP_UID=$$(id -u) APP_GID=$$(id -g) $(COMPOSE_LOCAL) up -d --build

up-public:               ## invite-only beta behind Caddy (HTTPS + per-invitee basic auth)
	@test -f deploy/users.caddy || { echo "create deploy/users.caddy first: make invite NAME=name"; exit 1; }
	docker compose --profile public up -d

down:
	docker compose --profile public down

logs:
	docker compose logs -f factory

ps:
	docker compose ps

shell:
	docker compose exec -it factory bash

login:                   ## log the container into your Claude subscription (stored in the claude-config volume)
	docker compose exec -it factory claude auth login

token:                   ## long-lived subscription token; put the result in .env as CLAUDE_CODE_OAUTH_TOKEN=...
	@command -v claude >/dev/null && claude setup-token || docker compose exec -it factory claude setup-token

auth-status:
	docker compose exec factory claude auth status

models:
	docker compose exec factory python tools/setup_local_models.py

smoke:
	docker compose exec factory python tools/smoke_test.py --quick

invite:                  ## make invite NAME=alice  -> appends "alice <bcrypt>" to deploy/users.caddy
	@test -n "$(NAME)" || { echo "usage: make invite NAME=name"; exit 1; }
	@read -s -p "Password for $(NAME): " pw; echo; \
	  hash=$$(docker run --rm caddy:2.8.4 caddy hash-password --plaintext "$$pw") && \
	  echo "$(NAME) $$hash" >> deploy/users.caddy && echo "added $(NAME); run: make reload-proxy"

reload-proxy:
	docker compose --profile public exec caddy caddy reload --config /etc/caddy/Caddyfile
