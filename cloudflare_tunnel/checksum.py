"""
Fetch the SHA256 checksum for a cloudflared binary from the GitHub release notes.

Cloudflare embeds checksums in the release body text (not a separate file).
This script queries the GitHub API, finds the line for the requested binary,
and prints the 64-character hex hash so the Dockerfile can verify the download.

Usage (called by the Dockerfile RUN step):
    CF_ARCH=amd64 CF_VER=2026.6.1 python3 checksum.py
"""

import json
import os
import re
import sys
import urllib.request

arch = os.environ["CF_ARCH"]  # e.g. "amd64", "arm64", "armhf", "arm", "386"
ver  = os.environ["CF_VER"]   # e.g. "2026.6.1"

url = f"https://api.github.com/repos/cloudflare/cloudflared/releases/tags/{ver}"
req = urllib.request.Request(url, headers={"User-Agent": "ha-cloudflare-tunnel-builder"})

with urllib.request.urlopen(req) as resp:
    body = json.loads(resp.read().decode())["body"]

filename = f"cloudflared-linux-{arch}"
match = re.search(re.escape(filename) + r":\s*([a-f0-9]{64})", body)

if not match:
    sys.exit(f"No checksum found for '{filename}' in the release notes for {ver}")

print(match.group(1))
