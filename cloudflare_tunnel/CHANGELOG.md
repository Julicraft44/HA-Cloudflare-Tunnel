## 1.0.5

- Update cloudflared to 2026.7.2

## 1.0.4

- Update base image to Alpine 3.24
- Update cloudflared to 2026.7.0

## 1.0.2

- Fix s6-overlay startup: add `init: false` to config.yaml (required for s6-overlay v3)
- Fix latency entity: cloudflared RTT metrics are already in ms, remove incorrect ×1000 conversion
- Fix bytes sent/received: use correct metric names (`quic_client_sent_bytes`, `quic_client_receive_bytes`)
- Switch base image from Alpine to `ghcr.io/home-assistant/base` (includes s6-overlay and bashio)
- Replace monolithic `run.sh` with proper s6 `services.d` service scripts

## 1.0.0

- Initial release
- Token-based Cloudflare Tunnel support
- Home Assistant entities for tunnel status, active connections, protocol, latency, and bytes