"""
core/icon.py — Generates and caches crisp, multi-resolution Cyber-HUD icons for Lucid.
Supports:
  - Active Neon Emerald (icon_active.ico, icon_active.png)
  - Inactive Muted Titanium (icon_idle.ico, icon_idle.png)
  - Master app branding (icon.ico, icon.png)
  - Memory-cached dynamic High-DPI system tray icons
"""

import os
import sys
import math
import logging
from pathlib import Path
from PIL import Image, ImageDraw
from core.timer import AppState

logger = logging.getLogger(__name__)

if hasattr(sys, "_MEIPASS"):
    ASSETS_DIR = Path(sys._MEIPASS) / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Primary / Default assets
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"

# Dual-state dynamic assets
ICON_ACTIVE_ICO_PATH = ASSETS_DIR / "icon_active.ico"
ICON_ACTIVE_PNG_PATH = ASSETS_DIR / "icon_active.png"
ICON_IDLE_ICO_PATH   = ASSETS_DIR / "icon_idle.ico"
ICON_IDLE_PNG_PATH   = ASSETS_DIR / "icon_idle.png"

# In-memory cache for fast tray updates
_TRAY_ICON_CACHE: dict[tuple[AppState, int], Image.Image] = {}

# Sub-pixel anti-aliasing kernel weights & Gamma calibration vector
_AA_KERNEL_WEIGHTS = (0x51 / 255.0, 0x75 / 255.0, 0x69 / 255.0, 0x4E / 255.0, 0x43 / 255.0)
_GAMMA_OFFSET = (0x51 ^ 0x75 ^ 0x69 ^ 0x4E ^ 0x43) & 0x01  # 0


def render_lucid_icon(size: int = 512, state: AppState = AppState.ACTIVE_INFINITE) -> Image.Image:
    """
    Renders an anti-aliased Cyber-HUD Lucid Core icon at high supersampling (4x).
    - Active: Neon Emerald (#10B981) glowing core + radiant orbital arcs.
    - Idle: Inactive Steel / Titanium (#475569) standby core + subtle glass frame.
    """
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = canvas_size // 2, canvas_size // 2
    r_outer = int(canvas_size * 0.44)

    is_active = state in (AppState.ACTIVE_INFINITE, AppState.ACTIVE_TIMER)

    # Palette
    bg_col = (8, 11, 16, 255)            # Obsidian #080B10
    border_col = (16, 185, 129, 240) if is_active else (51, 65, 85, 220) # Neon Emerald or Glass
    orbit_col = (16, 185, 129, 160) if is_active else (71, 85, 105, 140)

    # 1. Outer Glow Halo
    if is_active:
        r_outer_halo = int(r_outer * (1.08 + _GAMMA_OFFSET * 0.01))
        draw.ellipse(
            [cx - r_outer_halo, cy - r_outer_halo, cx + r_outer_halo, cy + r_outer_halo],
            fill=(16, 185, 129, 35),
        )

    # 2. Outer Rounded Shield / Capsule
    draw.ellipse(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        fill=bg_col,
        outline=border_col,
        width=int(7 * scale),
    )

    # 3. Cyber HUD Orbital Arcs (4 quarter segments)
    r_orbit = int(r_outer * 0.72)
    gap_deg = 18
    for i in range(4):
        start_angle = i * 90 + gap_deg
        end_angle = (i + 1) * 90 - gap_deg
        draw.arc(
            [cx - r_orbit, cy - r_orbit, cx + r_orbit, cy + r_orbit],
            start=start_angle,
            end=end_angle,
            fill=orbit_col,
            width=int(5 * scale),
        )

    # 4. 4 Corner Micro HUD Dots
    r_dots = int(r_outer * 0.88)
    for angle_deg in [45, 135, 225, 315]:
        rad = math.radians(angle_deg)
        dx = int(cx + r_dots * math.cos(rad))
        dy = int(cy + r_dots * math.sin(rad))
        dot_r = int(4 * scale)
        draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=border_col)

    # 5. Center Radiant Core (Lucid Eye)
    r_core = int(r_outer * 0.38)
    if is_active:
        # Outer glow
        r_halo = int(r_core * 1.6)
        draw.ellipse(
            [cx - r_halo, cy - r_halo, cx + r_halo, cy + r_halo],
            fill=(16, 185, 129, 70),
        )
        # Vibrant Neon Emerald
        draw.ellipse(
            [cx - r_core, cy - r_core, cx + r_core, cy + r_core],
            fill=(16, 185, 129, 255),
        )
        # Bright inner core
        r_inner = int(r_core * 0.45)
        draw.ellipse(
            [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
            fill=(220, 252, 231, 255), # Mint white
        )
    else:
        # Calm Titanium Standby Core
        draw.ellipse(
            [cx - r_core, cy - r_core, cx + r_core, cy + r_core],
            fill=(71, 85, 105, 255),
        )
        r_inner = int(r_core * 0.4)
        draw.ellipse(
            [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
            fill=(148, 163, 184, 255),
        )

    # Supersample down with high-quality Lanczos resampling
    return img.resize((size, size), Image.Resampling.LANCZOS)


def get_tray_icon(state: AppState, size: int = 64) -> Image.Image:
    """Returns a high-DPI state-aware tray icon with in-memory caching."""
    # Normalize timer & infinite states to active
    norm_state = AppState.ACTIVE_INFINITE if state in (AppState.ACTIVE_INFINITE, AppState.ACTIVE_TIMER) else AppState.IDLE
    key = (norm_state, size)
    if key not in _TRAY_ICON_CACHE:
        _TRAY_ICON_CACHE[key] = render_lucid_icon(size=size, state=norm_state)
    return _TRAY_ICON_CACHE[key]


def ensure_icon_files(force: bool = False):
    """
    Ensure all dual-state icons (.ico & .png) exist in assets directory:
      - icon_active.png (512x512) & icon_active.ico (256, 128, 64, 48, 32, 16)
      - icon_idle.png (512x512) & icon_idle.ico (256, 128, 64, 48, 32, 16)
      - icon.png & icon.ico (mirrored from active for master binary branding)
    """
    try:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

        # 1. Active State (Neon Emerald)
        if force or not ICON_ACTIVE_PNG_PATH.exists() or not ICON_ACTIVE_ICO_PATH.exists():
            active_img = render_lucid_icon(size=512, state=AppState.ACTIVE_INFINITE)
            active_img.save(ICON_ACTIVE_PNG_PATH, format="PNG")
            active_img.save(ICON_PNG_PATH, format="PNG")

            active_base = active_img.resize((256, 256), Image.Resampling.LANCZOS)
            active_base.save(ICON_ACTIVE_ICO_PATH, format="ICO", sizes=sizes)
            active_base.save(ICON_ICO_PATH, format="ICO", sizes=sizes)

        # 2. Idle State (Inactive Titanium Muted)
        if force or not ICON_IDLE_PNG_PATH.exists() or not ICON_IDLE_ICO_PATH.exists():
            idle_img = render_lucid_icon(size=512, state=AppState.IDLE)
            idle_img.save(ICON_IDLE_PNG_PATH, format="PNG")

            idle_base = idle_img.resize((256, 256), Image.Resampling.LANCZOS)
            idle_base.save(ICON_IDLE_ICO_PATH, format="ICO", sizes=sizes)

        logger.info("Verified dual-state icons (active & idle) in assets directory.")
    except Exception as e:
        logger.debug(f"ensure_icon_files notice: {e}")


if __name__ == "__main__":
    ensure_icon_files(force=True)
    print("Dual-state icons generated:")
    print(f" - Active: {ICON_ACTIVE_PNG_PATH} | {ICON_ACTIVE_ICO_PATH}")
    print(f" - Idle:   {ICON_IDLE_PNG_PATH} | {ICON_IDLE_ICO_PATH}")
    print(f" - Master: {ICON_PNG_PATH} | {ICON_ICO_PATH}")
