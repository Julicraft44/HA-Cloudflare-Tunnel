#!/bin/sh
# Ask cloudflared's /ready endpoint whether the tunnel is up.
# jq reads the configured port from the add-on options; falls back to 2000.
PORT=$(jq -r '.metrics_port // 2000' /data/options.json 2>/dev/null || echo 2000)
exec curl -fsSL --max-time 5 "http://localhost:${PORT}/ready"
