#!/usr/bin/env python3
"""Poll cloudflared metrics and keep Home Assistant entities up to date."""

import logging
import os
import re
import sys
import time
from typing import Any, Dict, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [monitor] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config from CLI args ───────────────────────────────────────────────────────
METRICS_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
UPDATE_INTERVAL = int(sys.argv[2]) if len(sys.argv) > 2 else 30

METRICS_URL = f"http://localhost:{METRICS_PORT}/metrics"
READY_URL = f"http://localhost:{METRICS_PORT}/ready"

# ── Home Assistant API ─────────────────────────────────────────────────────────
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_API = "http://supervisor/core/api"

ENTITY_CONNECTED = "binary_sensor.cloudflare_tunnel_connected"
ENTITY_CONNECTIONS = "sensor.cloudflare_tunnel_active_connections"
ENTITY_PROTOCOL = "sensor.cloudflare_tunnel_protocol"
ENTITY_LATENCY = "sensor.cloudflare_tunnel_latency"
ENTITY_BYTES_SENT = "sensor.cloudflare_tunnel_bytes_sent"
ENTITY_BYTES_RECEIVED = "sensor.cloudflare_tunnel_bytes_received"

_HA_HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

_REQUEST_TIMEOUT = 8


# ── Home Assistant helpers ─────────────────────────────────────────────────────

def _set_state(entity_id: str, state: str, attributes: Dict[str, Any]) -> None:
    try:
        r = requests.post(
            f"{HA_API}/states/{entity_id}",
            headers=_HA_HEADERS,
            json={"state": state, "attributes": attributes},
            timeout=_REQUEST_TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Could not update %s: %s", entity_id, exc)


def _mark_unavailable(entity_id: str, friendly_name: str, extra: Optional[Dict[str, Any]] = None) -> None:
    attrs = {"friendly_name": friendly_name}
    if extra:
        attrs.update(extra)
    _set_state(entity_id, "unavailable", attrs)


# ── Prometheus parser ──────────────────────────────────────────────────────────

def _parse_prometheus(text: str) -> Dict[str, float]:
    """Parse Prometheus text exposition format into {metric_key: value}."""
    result: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # metric_name{labels} value  OR  metric_name value
        m = re.match(
            r'^([a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]*\})?)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|NaN|[+-]?Inf)',
            line,
        )
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2)
        try:
            result[key] = float(raw_val)
        except ValueError:
            pass
    return result


# ── cloudflared helpers ────────────────────────────────────────────────────────

def _is_ready() -> bool:
    try:
        r = requests.get(READY_URL, timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _fetch_metrics() -> Optional[Dict[str, float]]:
    try:
        r = requests.get(METRICS_URL, timeout=5)
        r.raise_for_status()
        return _parse_prometheus(r.text)
    except requests.RequestException:
        return None


def _active_connections(metrics: Dict[str, float]) -> int:
    for key, val in metrics.items():
        if key.split("{")[0] == "cloudflared_tunnel_ha_connections":
            return max(0, int(val))
    return 0


def _protocol(metrics: Dict[str, float]) -> str:
    """Best-effort protocol detection from metric names."""
    for key in metrics:
        lk = key.lower()
        if "quic" in lk:
            return "QUIC"
        if "http2" in lk or "_h2_" in lk:
            return "HTTP/2"
    return "unknown"


def _find_metric(metrics: Dict[str, float], *candidates: str) -> Optional[float]:
    for candidate in candidates:
        for key, val in metrics.items():
            if candidate in key.lower():
                return val
    return None


# ── Entity update ──────────────────────────────────────────────────────────────

def update_entities() -> None:
    ready = _is_ready()

    _set_state(
        ENTITY_CONNECTED,
        "on" if ready else "off",
        {
            "friendly_name": "Cloudflare Tunnel Connected",
            "device_class": "connectivity",
            "icon": "mdi:cloud-check" if ready else "mdi:cloud-off",
        },
    )

    if not ready:
        _mark_unavailable(ENTITY_CONNECTIONS, "Cloudflare Tunnel Active Connections",
                          {"icon": "mdi:connection"})
        _mark_unavailable(ENTITY_PROTOCOL, "Cloudflare Tunnel Protocol",
                          {"icon": "mdi:protocol"})
        _mark_unavailable(ENTITY_LATENCY, "Cloudflare Tunnel Latency",
                          {"unit_of_measurement": "ms", "icon": "mdi:timer-outline"})
        _mark_unavailable(ENTITY_BYTES_SENT, "Cloudflare Tunnel Bytes Sent",
                          {"unit_of_measurement": "B", "icon": "mdi:upload"})
        _mark_unavailable(ENTITY_BYTES_RECEIVED, "Cloudflare Tunnel Bytes Received",
                          {"unit_of_measurement": "B", "icon": "mdi:download"})
        return

    metrics = _fetch_metrics()
    if metrics is None:
        log.warning("Tunnel is ready but metrics endpoint is unreachable.")
        return

    # Active connections
    connections = _active_connections(metrics)
    _set_state(
        ENTITY_CONNECTIONS,
        str(connections),
        {
            "friendly_name": "Cloudflare Tunnel Active Connections",
            "unit_of_measurement": "connections",
            "state_class": "measurement",
            "icon": "mdi:connection",
        },
    )

    # Protocol
    proto = _protocol(metrics)
    _set_state(
        ENTITY_PROTOCOL,
        proto,
        {
            "friendly_name": "Cloudflare Tunnel Protocol",
            "icon": "mdi:protocol",
        },
    )

    # Latency — quic_client_smoothed_rtt, latest_rtt, min_rtt are already in milliseconds
    raw_latency = _find_metric(metrics, "smoothed_rtt", "latest_rtt", "min_rtt")
    if raw_latency is not None:
        latency_ms = round(raw_latency, 1)
        _set_state(
            ENTITY_LATENCY,
            str(latency_ms),
            {
                "friendly_name": "Cloudflare Tunnel Latency",
                "unit_of_measurement": "ms",
                "device_class": "duration",
                "state_class": "measurement",
                "icon": "mdi:timer-outline",
            },
        )
    else:
        _mark_unavailable(ENTITY_LATENCY, "Cloudflare Tunnel Latency",
                          {"unit_of_measurement": "ms", "icon": "mdi:timer-outline"})

    # Bytes sent / received — cloudflared exposes quic_client_sent_bytes and quic_client_receive_bytes
    bytes_sent = _find_metric(metrics, "sent_bytes")
    bytes_recv = _find_metric(metrics, "receive_bytes")

    if bytes_sent is not None:
        _set_state(
            ENTITY_BYTES_SENT,
            str(int(bytes_sent)),
            {
                "friendly_name": "Cloudflare Tunnel Bytes Sent",
                "unit_of_measurement": "B",
                "device_class": "data_size",
                "state_class": "total_increasing",
                "icon": "mdi:upload",
            },
        )
    else:
        _mark_unavailable(ENTITY_BYTES_SENT, "Cloudflare Tunnel Bytes Sent",
                          {"unit_of_measurement": "B", "icon": "mdi:upload"})

    if bytes_recv is not None:
        _set_state(
            ENTITY_BYTES_RECEIVED,
            str(int(bytes_recv)),
            {
                "friendly_name": "Cloudflare Tunnel Bytes Received",
                "unit_of_measurement": "B",
                "device_class": "data_size",
                "state_class": "total_increasing",
                "icon": "mdi:download",
            },
        )
    else:
        _mark_unavailable(ENTITY_BYTES_RECEIVED, "Cloudflare Tunnel Bytes Received",
                          {"unit_of_measurement": "B", "icon": "mdi:download"})

    log.info(
        "Updated — connected=%s connections=%d protocol=%s latency=%s bytes_sent=%s bytes_recv=%s",
        ready, connections, proto,
        f"{latency_ms}ms" if raw_latency is not None else "N/A",
        bytes_sent, bytes_recv,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    if not SUPERVISOR_TOKEN:
        log.error("SUPERVISOR_TOKEN is not set. Entities will not be updated.")
        log.error("Ensure homeassistant_api is enabled in the add-on configuration.")

    log.info("Monitor started — metrics port %d, update interval %ds", METRICS_PORT, UPDATE_INTERVAL)

    # Give cloudflared a moment to initialise before the first poll
    time.sleep(12)

    while True:
        try:
            update_entities()
        except Exception as exc:
            log.error("Unexpected error during entity update: %s", exc)
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
