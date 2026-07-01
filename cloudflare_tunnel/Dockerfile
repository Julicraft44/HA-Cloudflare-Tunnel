# BUILD_FROM is passed by the HA supervisor at build time and points to the
# correct HA base image for the target architecture.
# The default below is only used when building locally (without the supervisor).
# Updated automatically by .github/workflows/update-base-image.yml
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.21
FROM ${BUILD_FROM}

# ── Cloudflared version ──────────────────────────────────────────────────────
# Updated automatically by .github/workflows/update-cloudflared.yml
ARG CLOUDFLARED_VERSION="2026.6.1"
# ────────────────────────────────────────────────────────────────────────────

ARG BUILD_ARCH
ARG BUILD_VERSION

# The HA base image already includes bash, curl, jq, and s6-overlay.
# We only need Python for the metrics monitor (monitor.py).
RUN apk add --no-cache python3 py3-requests

# ── Install cloudflared ──────────────────────────────────────────────────────
# Download the binary for the right CPU architecture and verify its checksum.
# checksum.py fetches the expected SHA256 hash from the GitHub release notes.
COPY checksum.py /tmp/checksum.py
RUN set -eux; \
    # Map HA architecture names to the ones used by cloudflared release assets
    case "${BUILD_ARCH}" in \
        amd64)   CF_ARCH="amd64" ;; \
        aarch64) CF_ARCH="arm64" ;; \
        armv7)   CF_ARCH="armhf" ;; \
        armhf)   CF_ARCH="arm"   ;; \
        i386)    CF_ARCH="386"   ;; \
        *) echo "Unsupported architecture: ${BUILD_ARCH}" && exit 1 ;; \
    esac; \
    curl -fsSL \
        "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${CF_ARCH}" \
        -o /tmp/cloudflared; \
    EXPECTED=$(CF_ARCH="${CF_ARCH}" CF_VER="${CLOUDFLARED_VERSION}" python3 /tmp/checksum.py); \
    ACTUAL=$(sha256sum /tmp/cloudflared | awk '{print $1}'); \
    if [ "${EXPECTED}" != "${ACTUAL}" ]; then \
        echo "SHA256 mismatch — download may be corrupted or tampered with." >&2; \
        echo "  expected: ${EXPECTED}" >&2; \
        echo "  got:      ${ACTUAL}" >&2; \
        exit 1; \
    fi; \
    install -m 0755 /tmp/cloudflared /usr/local/bin/cloudflared; \
    rm /tmp/cloudflared /tmp/checksum.py; \
    cloudflared --version
# ────────────────────────────────────────────────────────────────────────────

# Copy everything into place:
#   rootfs/       →  /  (s6 service scripts live in /etc/services.d/)
#   monitor.py       (polls cloudflared metrics and updates HA entities)
#   healthcheck.sh   (used by Docker HEALTHCHECK to verify the tunnel is up)
COPY rootfs /
COPY monitor.py /monitor.py
COPY healthcheck.sh /healthcheck.sh
RUN chmod a+x \
    /etc/services.d/cloudflare_tunnel/run \
    /etc/services.d/cloudflare_tunnel_monitor/run \
    /healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /healthcheck.sh

LABEL \
    io.hass.name="HA Cloudflare Tunnel" \
    io.hass.description="Expose your Home Assistant instance via a Cloudflare Tunnel" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}"
