#!/bin/sh
# Run Rabbit Hole on one small Linux box with Docker:
#   openclaw-rh : OpenClaw gateway, private to the docker network
#   rabbithole  : race server on 127.0.0.1:8031 (put Caddy/nginx in front for HTTPS)
# Expects ./rabbithole.env (keys, OPENCLAW_URL=http://openclaw-rh:18789/v1) and ./openclaw-home (copy of ../openclaw).
set -e
cd "$(dirname "$0")"
docker network inspect rabbithole-net >/dev/null 2>&1 || docker network create rabbithole-net >/dev/null
docker rm -f openclaw-rh rabbithole >/dev/null 2>&1 || true
docker run -d --name openclaw-rh --restart unless-stopped --network rabbithole-net --cpus 1.0 --memory 2g \
  --env-file ./rabbithole.env -v "$PWD/openclaw-home:/home/node/.openclaw" \
  ghcr.io/openclaw/openclaw:latest node openclaw.mjs gateway --bind lan --port 18789
docker run -d --name rabbithole --restart unless-stopped --network rabbithole-net --cpus 0.5 --memory 512m \
  --env-file ./rabbithole.env -v "$PWD/runs:/app/backend/runs" -p 127.0.0.1:8031:8000 rabbithole
