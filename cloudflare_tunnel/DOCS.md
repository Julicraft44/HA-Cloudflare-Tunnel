# HA Cloudflare Tunnel

Expose your Home Assistant instance (and any other services running on the same host) to the internet securely using a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/). No port forwarding, no public IP required.

---

## Prerequisites

- A **Cloudflare account** (free tier is sufficient)
- A **domain name** managed by Cloudflare DNS
- **Cloudflare Zero Trust** activated on your account (free plan available at [one.dash.cloudflare.com](https://one.dash.cloudflare.com))

---

## Step 1 – Create a Tunnel and get your token

1. Log in to the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com).
2. Go to **Networks → Tunnels**.
3. Click **Create a tunnel**.
4. Choose **Cloudflared** as the connector type and give the tunnel a name (e.g. `home-assistant`).
5. On the **Install connector** page, select **Docker** as the environment.
6. From the shown command, copy only the long token string that appears after `--token`. It looks like:

   ```
   eyJhIjoiMTIz...
   ```

7. Paste this token into the add-on's **Tunnel Token** configuration field.

---

## Step 2 – Configure the add-on

Open the add-on configuration tab and set at minimum:

| Option | Required | Description |
|--------|----------|-------------|
| `tunnel_token` | **Yes** | The token copied from the Cloudflare dashboard |
| `log_level` | No | Log verbosity: `trace`, `debug`, `info`, `warn`, `error`, `fatal` (default: `info`) |
| `metrics_port` | No | Internal port for cloudflared's metrics server (default: `2000`) |
| `update_interval` | No | How often (seconds) Home Assistant entities are refreshed (default: `30`) |

---

## Step 3 – Start the add-on

Start the add-on. Check the **Log** tab — you should see cloudflared report four registered tunnel connections and the monitor log a first update within about 40 seconds.

---

## Step 4 – Route traffic in Cloudflare

All routing is configured inside the Cloudflare Zero Trust dashboard, **not** in the add-on.

1. In the dashboard, go to **Networks → Tunnels → your tunnel → Configure → Public Hostnames**.
2. Click **Add a public hostname**.
3. Fill in:

   | Field | Value |
   |-------|-------|
   | Subdomain | `ha` (or whatever you like) |
   | Domain | your Cloudflare domain |
   | Type | `HTTP` |
   | URL | `192.168.x.x:8123` — your HA host's **LAN IP address** |

   Use your Home Assistant host's local IP address (e.g. `192.168.178.24:8123`). The type is `HTTP` — Cloudflare handles external HTTPS automatically, so no SSL certificate is required on the local side.

   > **Why not `homeassistant.local`?** The add-on runs inside a Docker container. mDNS (`.local`) resolution is not reliably available from within the container, so the plain LAN IP is more dependable.

4. Save. Your Home Assistant instance will now be reachable at `https://ha.yourdomain.com`.

### Exposing additional services

To expose other services running on the same host (e.g. Frigate, Node-RED, Portainer):

1. Add another public hostname in the Cloudflare dashboard.
2. Point the **URL** to the service's local address and port (e.g. `192.168.178.24:8080`).
3. No changes to the add-on are required — the tunnel handles all routing automatically.

> **Tip:** Use Cloudflare Access (Zero Trust → Access → Applications) to put authentication in front of any hostname if you want to restrict who can reach it.

---

## Step 5 – Configure Home Assistant to trust the proxy

When requests arrive through the tunnel, Home Assistant sees them coming from an internal Docker IP rather than the original client. Without telling HA to trust that proxy, it will reject the requests with a `400 Bad Request` error.

Add the following to your `configuration.yaml` and restart Home Assistant:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
    - 172.30.0.0/16
```

The `172.30.0.0/16` range covers the internal Docker network that the add-on runs on. `use_x_forwarded_for: true` ensures HA logs and rate-limits based on the real client IP passed through by Cloudflare, not the tunnel's internal IP.

---

## Home Assistant Entities

The add-on creates the following entities automatically. They appear in Home Assistant shortly after the add-on starts and the tunnel connects.

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.cloudflare_tunnel_connected` | Binary Sensor | `on` when the tunnel has at least one active edge connection |
| `sensor.cloudflare_tunnel_active_connections` | Sensor | Number of currently proxied streams |
| `sensor.cloudflare_tunnel_protocol` | Sensor | Transport protocol in use (`QUIC`, `HTTP/2`, or `unknown`) |
| `sensor.cloudflare_tunnel_latency` | Sensor | Round-trip time to the Cloudflare edge in milliseconds |
| `sensor.cloudflare_tunnel_bytes_sent` | Sensor | Total bytes transmitted through the tunnel since last restart |
| `sensor.cloudflare_tunnel_bytes_received` | Sensor | Total bytes received through the tunnel since last restart |

> **Note:** Latency, bytes sent, and bytes received depend on metrics exposed by the specific version of cloudflared pinned in this add-on. If cloudflared does not expose them in its metrics output, those entities will show `unavailable`. This is expected and does not indicate a problem.

Entities are updated every `update_interval` seconds. They will show `unavailable` while the tunnel is not connected.

---

## Troubleshooting

**The add-on starts but no entities appear in Home Assistant**

- Ensure the add-on log does not show `SUPERVISOR_TOKEN is not set`.
- Wait up to one minute after startup; the monitor waits ~12 seconds before the first poll.

**The tunnel token is rejected**

- Make sure you copied the full token (it can be several hundred characters long).
- Re-generate the token in the Cloudflare dashboard if needed (go to your tunnel → Configure → re-run connector setup).

**The tunnel connects but my domain returns an SSL error**

- Cloudflare handles TLS termination automatically. Set the **SSL/TLS encryption mode** on your Cloudflare domain to **Full** or **Full (strict)** under SSL/TLS → Overview.

**The `armhf` or `i386` build fails**

- Cloudflare may drop support for older architectures in future cloudflared releases. If the version pinned in this add-on no longer publishes a binary for your architecture, open an issue on the repository.

---

## Security Notes

- Your tunnel token grants full access to the tunnel. Treat it like a password. Do not share it.
- The add-on does not expose any port to your local network beyond the internal metrics endpoint on `localhost`.
- All traffic between your host and Cloudflare's edge is encrypted by cloudflared.
