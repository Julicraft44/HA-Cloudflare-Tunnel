# HA Cloudflare Tunnel — Home Assistant Add-on Repository

Expose your Home Assistant instance to the internet securely using a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/). No port forwarding or public IP required.

## Add-ons in this repository

### HA Cloudflare Tunnel

Runs `cloudflared` in token mode, automatically creates Home Assistant sensor entities for tunnel health monitoring, and restarts the tunnel if it drops.

**Supported architectures:** `amd64` · `aarch64` · `armv7` · `armhf` · `i386`

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Click the **⋮** menu (top right) and select **Repositories**.
3. Paste the URL of this repository and click **Add**.
4. Find **HA Cloudflare Tunnel** in the store and click **Install**.
5. Follow the [documentation](cloudflare_tunnel/DOCS.md) to configure and start the add-on.

## Quick-start checklist

- [ ] Create a tunnel in the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com) and copy the token
- [ ] Paste the token into the add-on configuration and start it
- [ ] In the tunnel's **Public Hostnames**, add a hostname pointing to `http://192.168.x.x:8123` (your HA host's LAN IP — not `homeassistant.local`)
- [ ] Add `trusted_proxies` to your `configuration.yaml` so HA accepts proxied requests:

  ```yaml
  http:
    use_x_forwarded_for: true
    trusted_proxies:
      - 127.0.0.1
      - ::1
      - 172.30.0.0/16
  ```

See the [full documentation](cloudflare_tunnel/DOCS.md) for all options and troubleshooting.

## Support

- Open an issue on this repository for bugs or feature requests.
- For Cloudflare-specific issues, refer to the [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).
