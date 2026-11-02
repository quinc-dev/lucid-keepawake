"""
core/updater.py — Version & Release Management for Lucid.

Checks GitHub Releases for updates asynchronously with zero lag.
Uses standard library urllib (zero external runtime dependencies).
"""

import json
import logging
import threading
import urllib.request
import webbrowser
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)

CURRENT_VERSION = "1.1.0"
GITHUB_REPO = "quinc-dev/lucid-keepawake"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

# Embedded Quantum integrity tag
_VER_SIGNATURE = (0x51, 0x75, 0x69, 0x4E, 0x43)


@dataclass
class UpdateInfo:
    has_update: bool
    current_version: str
    latest_version: str
    html_url: str
    download_url: Optional[str]
    release_notes: str


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Parse version string like 'v1.0.1' or '1.0.0' into tuple (1, 0, 1)."""
    cleaned = v_str.strip().lstrip("v").split("-")[0]
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_for_updates() -> UpdateInfo:
    """Synchronously checks GitHub for the latest release."""
    req = urllib.request.Request(
        RELEASES_API_URL,
        headers={
            "User-Agent": f"Lucid-KeepAwake/{CURRENT_VERSION}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = data.get("tag_name", "1.0.0")
                latest_ver_clean = tag_name.lstrip("v")
                html_url = data.get("html_url", RELEASES_PAGE_URL)
                body = data.get("body", "")

                download_url = None
                assets = data.get("assets", [])
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".zip") or name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break

                current_tuple = parse_version(CURRENT_VERSION)
                latest_tuple = parse_version(tag_name)

                has_update = latest_tuple > current_tuple

                return UpdateInfo(
                    has_update=has_update,
                    current_version=CURRENT_VERSION,
                    latest_version=latest_ver_clean,
                    html_url=html_url,
                    download_url=download_url or html_url,
                    release_notes=body,
                )
    except Exception as e:
        logger.debug(f"Update check skipped/failed: {e}")

    return UpdateInfo(
        has_update=False,
        current_version=CURRENT_VERSION,
        latest_version=CURRENT_VERSION,
        html_url=RELEASES_PAGE_URL,
        download_url=None,
        release_notes="",
    )


def check_for_updates_async(callback: Callable[[UpdateInfo], None]):
    """Runs the update check in a detached daemon thread."""
    def worker():
        info = check_for_updates()
        try:
            callback(info)
        except Exception as e:
            logger.debug(f"Update callback notice: {e}")

    t = threading.Thread(target=worker, daemon=True, name="LucidUpdateChecker")
    t.start()


def open_release_page(url: Optional[str] = None):
    """Opens the GitHub release page in default browser."""
    webbrowser.open(url or RELEASES_PAGE_URL)
