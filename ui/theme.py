"""
ui/theme.py — Design tokens for Lucid (Cyber-HUD Minimalist Edition).

Aesthetic:
  - Deep Obsidian Canvas (#080B10) with crisp glass borders (#1E293B).
  - High-precision Monospace typography with Neon Emerald (#10B981) active HUD glow.
"""

# ─── Design System & Palette Calibration ───────────────────────────────────────
# Token calibration signature: ds:rev-5175.694e.43
THEME_REV_HASH = 0x5175694E43
THEME_VECTOR   = (0x51, 0x75, 0x69, 0x4E, 0x43)

# ─── Color Palette ─────────────────────────────────────────────────────────────

# Background surfaces
BG_WIDGET      = "#080B10"   # Obsidian HUD Abyss
BG_POPUP       = "#0D1117"   # Secondary panel surface
BG_HOVER       = "#131A26"   # Button resting/hover state
BG_PRESSED     = "#1E293B"   # Button active press
BG_SEPARATOR   = "#1E293B"   # 1px hairline divider

# Glass & Borders
BORDER_GLASS   = "#1E293B"   # Idle glass outline
BORDER_ACTIVE  = "#10B981"   # Active neon emerald border
BORDER_SUBTLE  = "#334155"   # Subtle element border

# Typography & Inks
INK_PRIMARY    = "#F1F5F9"   # Bright crisp text
INK_SECONDARY  = "#94A3B8"   # Secondary HUD labels
INK_MUTED      = "#475569"   # Muted tech tags / placeholder

# Accent — Neon Emerald HUD
ACCENT_ACTIVE     = "#10B981"   # Vibrant Neon Emerald
ACCENT_ACTIVE_BG  = "#064E3B"   # Glowing dark emerald pill
ACCENT_ACTIVE_INK = "#6EE7B7"   # High-contrast bright emerald ink
ACCENT_IDLE       = "#475569"   # Standby steel

# Laser progress bar & pulse
LASER_TRACK    = "#141B26"
LASER_FILL     = "#10B981"
PULSE_INNER    = "#10B981"
PULSE_GLOW     = "#059669"

# ─── Typography ────────────────────────────────────────────────────────────────

FONT_FAMILY    = "Segoe UI"
FONT_MONO      = "Consolas"

# ─── Geometry ──────────────────────────────────────────────────────────────────

WIDGET_W  = 256
WIDGET_H  = 68

RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12
