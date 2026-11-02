"""
ui/widget.py — Cyber-HUD Minimalist Edition for Lucid.

Features:
  - 256×68px Obsidian HUD capsule with 4 flush Cyber-HUD Corner Brackets.
  - TOP HUD ROW: Radar pulse blip + Tech tag (LUCID // SYS) + Monospace State/Timer + Action toggle.
  - LASER LINE: 2px real-time neon laser countdown bar.
  - CYBER STRIP: High-tech segmented controls [15m] [30m] [1h] [2h] [min] [∞].
  - CYBER CONTEXT CARD: Custom dark glass right-click menu with hover animations.
  - APP FAVICON: Auto-loads crisp multi-res icon.ico.
"""

import tkinter as tk
import customtkinter as ctk
import math
import logging
from typing import Callable, Optional
from pathlib import Path
from PIL import Image, ImageTk

from ui import theme
from core.timer import AppState
from core.updater import (
    UpdateInfo,
    open_release_page,
    check_for_updates_async,
    CURRENT_VERSION,
)
from core.icon import (
    ICON_ICO_PATH,
    ICON_PNG_PATH,
    ICON_ACTIVE_ICO_PATH,
    ICON_ACTIVE_PNG_PATH,
    ICON_IDLE_ICO_PATH,
    ICON_IDLE_PNG_PATH,
    ensure_icon_files,
)

logger = logging.getLogger(__name__)

# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Duration Parser
# ─────────────────────────────────────────────────────────────────────────────

def _force_window_foreground(hwnd: int) -> bool:
    """
    Robust Win32 foreground activation for borderless / system tray windows.
    Bypasses Windows foreground lock timeout via thread attachment / Alt key toggle.
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if user32.SetForegroundWindow(hwnd):
            user32.SetFocus(hwnd)
            return True

        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd:
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            cur_tid = kernel32.GetCurrentThreadId()
            if fg_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, fg_tid, True)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                user32.AttachThreadInput(cur_tid, fg_tid, False)
                return True

        # Fallback: Alt key toggle to bypass foreground lock timeout
        user32.keybd_event(0x12, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        user32.keybd_event(0x12, 0, 2, 0)
        return True
    except Exception:
        return False


def parse_duration(text: str) -> Optional[int]:
    """
    Parse user time input (e.g. '45', '45m', '1.5h', '90s', '01:30') into seconds.
    Defaults to minutes if no unit is given.
    """
    text = text.strip().lower()
    if not text:
        return None
    try:
        if ":" in text:
            parts = [int(p) for p in text.split(":")]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]

        if text.endswith("h") or text.endswith("hr") or text.endswith("hrs"):
            num_str = text.rstrip("hrs").rstrip("hr").rstrip("h").strip()
            return int(float(num_str) * 3600)
        elif text.endswith("min") or text.endswith("m"):
            num_str = text.rstrip("min").rstrip("m").strip()
            return int(float(num_str) * 60)
        elif text.endswith("s") or text.endswith("sec"):
            num_str = text.rstrip("sec").rstrip("s").strip()
            return int(float(num_str))

        val = float(text)
        return int(val * 60) if val > 0 else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# RadarBlip (Multi-Wave Holographic Cyber Pulse)
# ─────────────────────────────────────────────────────────────────────────────

# HUD matrix geometry vector & Quantum animation salt
_HUD_MATRIX_SEED = (0x51, 0x75, 0x69, 0x4E, 0x43)
_HUD_TICK_OFFSET = (_HUD_MATRIX_SEED[0] ^ _HUD_MATRIX_SEED[-1]) & 0x07  # 2


class RadarBlip(tk.Canvas):
    """
    Cyber-HUD radar pulse with dual-wave expanding holographic rings and hot core.
    """

    DOT_R = 3.5
    RING_MAX = 8.5

    def __init__(self, parent, size: int = 18, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=theme.BG_WIDGET,
            highlightthickness=0,
            **kwargs,
        )
        self._size = size
        self._cx = size // 2
        self._cy = size // 2
        self._active = False
        self._phase = 0.0
        self._animating = False
        self._after_id: Optional[str] = None
        self._draw_idle()

    def set_active(self, active: bool):
        was = self._active
        self._active = active
        if active and not was:
            self._phase = 0.0
            self._start_animation()
        elif not active and was:
            self._stop_animation()
            self._draw_idle()

    def stop(self):
        self._stop_animation()

    def _start_animation(self):
        if self._animating:
            return
        self._animating = True
        self._tick()

    def _stop_animation(self):
        self._animating = False
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        if not self._animating:
            return
        self._phase = (self._phase + 0.045) % 1.0
        self._draw_active()
        if self._animating:
            self._after_id = self.after(33, self._tick)

    def _draw_idle(self):
        self.delete("all")
        cx, cy, r = self._cx, self._cy, self.DOT_R
        # Outer subtle ring
        self.create_oval(cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
                         outline="#1E293B", width=1)
        # Standby steel dot
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=theme.ACCENT_IDLE, outline="")

    def _draw_active(self):
        self.delete("all")
        cx, cy = self._cx, self._cy
        p = self._phase

        # Wave 1: Primary expanding sonar ring
        r1 = self.DOT_R + p * (self.RING_MAX - self.DOT_R)
        a1 = int(240 * (1.0 - p) ** 1.5 * 0.45)
        col1 = self._blend(16, 185, 129, a1)
        if col1:
            self.create_oval(cx - r1, cy - r1, cx + r1, cy + r1,
                             fill=col1, outline="")

        # Wave 2: Secondary offset echoing sonar ring
        p2 = (p + 0.5) % 1.0
        r2 = self.DOT_R + p2 * (self.RING_MAX - self.DOT_R)
        a2 = int(200 * (1.0 - p2) ** 1.5 * 0.30)
        col2 = self._blend(16, 185, 129, a2)
        if col2:
            self.create_oval(cx - r2, cy - r2, cx + r2, cy + r2,
                             fill=col2, outline="")

        # Core outer halo
        r = self.DOT_R
        self.create_oval(cx - r - 0.5, cy - r - 0.5, cx + r + 0.5, cy + r + 0.5,
                         fill=theme.ACCENT_ACTIVE, outline="")

        # Core inner hot photon spark
        r_hot = 1.8
        self.create_oval(cx - r_hot, cy - r_hot, cx + r_hot, cy + r_hot,
                         fill=theme.ACCENT_ACTIVE_INK, outline="")

    @staticmethod
    def _blend(r: int, g: int, b: int, a: int) -> Optional[str]:
        if a <= 0:
            return None
        bg = 8
        t = a / 255
        return "#{:02x}{:02x}{:02x}".format(
            int(bg + t * (r - bg)),
            int(bg + t * (g - bg)),
            int(bg + t * (b - bg)),
        )


# ─────────────────────────────────────────────────────────────────────────────
# LaserBar (Fluid 60fps Laser Beam with Smooth Lerp Animation)
# ─────────────────────────────────────────────────────────────────────────────

class LaserBar(tk.Canvas):
    """
    Fluid 60fps Laser Beam with smooth exponential lerp interpolation,
    laser ignition shoot-out, and glowing optical photon tip.
    """

    def __init__(self, parent, height: int = 4, **kwargs):
        super().__init__(
            parent,
            height=height,
            bg=theme.BG_WIDGET,
            highlightthickness=0,
            **kwargs,
        )
        self._mode: AppState = AppState.IDLE
        self._target_fraction: float = 0.0
        self._current_fraction: float = 0.0
        self._scan_phase: float = 0.0
        self._glow_phase: float = 0.0
        self._animating: bool = False
        self._after_id: Optional[str] = None
        self.bind("<Configure>", lambda e: self._draw())

    def set_state(self, state: AppState, progress: float = 0.0):
        prev_mode = self._mode
        self._mode = state

        if state == AppState.IDLE:
            self._target_fraction = 0.0
        elif state == AppState.ACTIVE_INFINITE:
            self._target_fraction = 1.0
            if prev_mode == AppState.IDLE:
                self._current_fraction = 0.0  # Smooth beam shot from 0 to full
        elif state == AppState.ACTIVE_TIMER:
            rem = max(0.0, min(1.0, 1.0 - progress))
            self._target_fraction = rem
            if prev_mode == AppState.IDLE:
                self._current_fraction = 0.0  # Smooth laser shoot out!

        if not self._animating:
            self._animating = True
            self._tick()

    def _tick(self):
        if not self._animating:
            return

        # Smooth exponential lerp interpolation (ease-out physics)
        diff = self._target_fraction - self._current_fraction
        if abs(diff) > 0.001:
            self._current_fraction += diff * 0.18
        else:
            self._current_fraction = self._target_fraction

        self._scan_phase = (self._scan_phase + 0.035) % 1.0
        self._glow_phase = (self._glow_phase + 0.06) % 1.0
        self._draw()

        # Stop animation only when IDLE and fully collapsed to 0
        if self._mode == AppState.IDLE and self._current_fraction <= 0.002:
            self._current_fraction = 0.0
            self._animating = False
            self._draw()
            return

        self._after_id = self.after(20, self._tick)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            return

        mid_y = h // 2

        # 1. Subtle baseline guide rail
        self.create_line(0, mid_y, w, mid_y, fill=theme.LASER_TRACK, width=1)

        # 2. Render interpolated glowing laser beam
        active_w = int(w * self._current_fraction)
        if active_w > 0:
            # Glowing core beam
            self.create_line(0, mid_y, active_w, mid_y, fill=theme.LASER_FILL, width=2)

            if self._mode == AppState.ACTIVE_INFINITE:
                # Sweeping laser photon wave scanning across beam
                scan_x = int(active_w * (0.5 + 0.5 * math.sin(self._scan_phase * 2 * math.pi)))
                self.create_oval(
                    scan_x - 3, mid_y - 1.5,
                    scan_x + 3, mid_y + 1.5,
                    fill=theme.ACCENT_ACTIVE_INK,
                    outline="",
                )
            else:
                # Leading edge optical photon head with pulsating halo
                glow_r = 3.5 + 1.0 * math.sin(self._glow_phase * 2 * math.pi)
                # Outer photon halo
                self.create_oval(
                    active_w - glow_r, mid_y - glow_r / 2,
                    active_w + glow_r, mid_y + glow_r / 2,
                    fill="#065F46",
                    outline="",
                )
                # Center hot photon spark
                self.create_oval(
                    active_w - 2.5, mid_y - 1.5,
                    active_w + 2.5, mid_y + 1.5,
                    fill=theme.ACCENT_ACTIVE_INK,
                    outline="",
                )


# ─────────────────────────────────────────────────────────────────────────────
# CornerBrackets (HUD 4-Corner Viewfinder Accents)
# ─────────────────────────────────────────────────────────────────────────────

class CornerBracket(tk.Canvas):
    """
    Individual HUD corner L-bracket with high-tech viewfinder micro-ticks.
    kind: 'tl', 'tr', 'bl', 'br'
    """
    def __init__(self, parent, kind: str, size: int = 14, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=theme.BG_WIDGET,
            highlightthickness=0,
            **kwargs,
        )
        self._kind = kind
        self._size = size
        self._color = theme.BORDER_SUBTLE
        self._draw()

    def set_color(self, color: str):
        self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        c = self._color
        w = 2

        if self._kind == "tl":
            self.create_line(1, s, 1, 1, s, 1, fill=c, width=w)
            self.create_oval(1, 1, 3, 3, fill=c, outline="")
        elif self._kind == "tr":
            self.create_line(0, 1, s - 2, 1, s - 2, s, fill=c, width=w)
            self.create_oval(s - 4, 1, s - 2, 3, fill=c, outline="")
        elif self._kind == "bl":
            self.create_line(1, 0, 1, s - 2, s, s - 2, fill=c, width=w)
            self.create_oval(1, s - 4, 3, s - 2, fill=c, outline="")
        elif self._kind == "br":
            self.create_line(s - 2, 0, s - 2, s - 2, 0, s - 2, fill=c, width=w)
            self.create_oval(s - 4, s - 4, s - 2, s - 2, fill=c, outline="")


# ─────────────────────────────────────────────────────────────────────────────
# LucidWidget  (Cyber-HUD Minimalist)
# ─────────────────────────────────────────────────────────────────────────────

class CyberContextMenu(tk.Toplevel):
    """
    Ultra-compact Titanium/Zinc Cyber Context Card.
    Pixel-perfect frameless card with zero wasted padding or DPI scaling voids.
    Instant 1st-click response, smooth hover illumination, leak-free teardown.
    """

    def __init__(self, master: ctk.CTk, x: int, y: int, items: list):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=theme.BG_POPUP)
        self._master = master
        self._is_closed = False

        card = tk.Frame(
            self,
            bg=theme.BG_POPUP,
            highlightthickness=1,
            highlightbackground=theme.BORDER_SUBTLE,
        )
        card.pack(fill="both", expand=True)

        for item in items:
            if item == "---":
                sep = tk.Frame(card, height=1, bg=theme.BORDER_GLASS, bd=0)
                sep.pack(fill="x", padx=6, pady=2)
            else:
                label, cmd, color, accel = item
                row = tk.Frame(card, bg=theme.BG_POPUP, cursor="hand2")
                row.pack(fill="x", padx=1, pady=0)

                lbl = tk.Label(
                    row,
                    text=f" {label}",
                    anchor="w",
                    bg=theme.BG_POPUP,
                    fg=color or theme.INK_PRIMARY,
                    font=(theme.FONT_MONO, 9),
                    pady=2,
                    cursor="hand2",
                )
                lbl.pack(side="left", fill="x", expand=True, padx=(2, 6))

                accel_lbl = None
                if accel:
                    accel_lbl = tk.Label(
                        row,
                        text=accel,
                        anchor="e",
                        bg=theme.BG_POPUP,
                        fg=theme.INK_MUTED,
                        font=(theme.FONT_MONO, 8),
                        cursor="hand2",
                    )
                    accel_lbl.pack(side="right", padx=(0, 6))

                # Coordinated hover illumination
                def on_enter(e, r=row, l=lbl, a=accel_lbl):
                    r.configure(bg=theme.BG_HOVER)
                    l.configure(bg=theme.BG_HOVER)
                    if a:
                        a.configure(bg=theme.BG_HOVER)

                def on_leave(e, r=row, l=lbl, a=accel_lbl):
                    r.configure(bg=theme.BG_POPUP)
                    l.configure(bg=theme.BG_POPUP)
                    if a:
                        a.configure(bg=theme.BG_POPUP)

                widgets = [row, lbl, accel_lbl] if accel_lbl else [row, lbl]
                for w in widgets:
                    w.bind("<Enter>", on_enter)
                    w.bind("<Leave>", on_leave)
                    w.bind("<Button-1>", lambda e, c=cmd: self._select(c))

        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Natural cursor-anchored placement (standard OS context menu behavior):
        # Spawns immediately adjacent to the cursor (+2, +2) with automatic smart flip
        target_x = x + 2
        target_y = y + 2

        # If overflowing bottom edge, flip upward right above cursor
        if target_y + h > sh - 6:
            target_y = y - h - 2

        # If overflowing right edge, flip leftward right beside cursor
        if target_x + w > sw - 6:
            target_x = x - w - 2

        # Clamp safely within visible display boundaries
        target_x = max(4, min(target_x, sw - w - 4))
        target_y = max(4, min(target_y, sh - h - 4))
        self.geometry(f"+{target_x}+{target_y}")

        self.focus_force()
        self.bind("<Escape>", lambda e: self._close())
        self.after(50, self._setup_dismiss)

    def _setup_dismiss(self):
        try:
            self.grab_set()
            self.bind("<ButtonPress>", self._on_click_check)
        except Exception:
            pass

    def _on_click_check(self, event):
        x, y = event.x_root, event.y_root
        wx = self.winfo_rootx()
        wy = self.winfo_rooty()
        ww = self.winfo_width()
        wh = self.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            self._close()

    def _close(self):
        if self._is_closed:
            return
        self._is_closed = True
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _select(self, cmd):
        self._close()
        if cmd:
            self._master.after(20, cmd)



class LucidWidget(ctk.CTk):
    """
    Cyber-HUD Minimalist Floating Widget (256×68px) with 4-Corner Accent Brackets.
    """

    _PRESETS = [
        ("15m",  15 * 60),
        ("30m",  30 * 60),
        ("1h",   60 * 60),
        ("2h",  120 * 60),
    ]

    def __init__(
        self,
        on_toggle_infinite: Callable,
        on_start_timer: Callable[[int], None],
        on_stop: Callable,
        on_quit: Callable,
        get_state: Callable[[], AppState],
        get_time_str: Callable[[], str],
        get_progress: Callable[[], float],
        on_toggle_blackout: Optional[Callable] = None,
    ):
        super().__init__()
        self._cb_toggle_infinite = on_toggle_infinite
        self._cb_start_timer = on_start_timer
        self._cb_stop = on_stop
        self._cb_quit = on_quit
        self._get_state = get_state
        self._get_time_str = get_time_str
        self._get_progress = get_progress
        self._cb_toggle_blackout = on_toggle_blackout

        self._drag_x = 0
        self._drag_y = 0
        self._current_state: AppState = AppState.IDLE
        self._active_preset: Optional[str] = None
        self._is_closing = False
        self._ui_after_id: Optional[str] = None
        self._update_info: Optional[UpdateInfo] = None
        self._active_menu: Optional[tk.Menu] = None

        ensure_icon_files()
        self._setup_window()
        self._build_ui()
        self._start_update_loop()

    # ─── Window Setup ────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Lucid HUD")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=theme.BG_WIDGET)

        # Set Window Favicon (High-Res PNG + Multi-Res ICO)
        try:
            if ICON_PNG_PATH.exists():
                img_png = Image.open(ICON_PNG_PATH)
                self._app_icon_photo = ImageTk.PhotoImage(img_png.resize((64, 64), Image.Resampling.LANCZOS))
                self.iconphoto(False, self._app_icon_photo)
            if ICON_ICO_PATH.exists():
                self.iconbitmap(str(ICON_ICO_PATH))
        except Exception as e:
            logger.debug(f"Favicon setting notice: {e}")

        w, h = theme.WIDGET_W, theme.WIDGET_H
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 64}")
        self.resizable(False, False)

        self.bind("<ButtonPress-1>", self._drag_start)
        self.bind("<B1-Motion>", self._drag_move)
        self.bind("<Button-3>", self._show_context_menu)
        self.bind("<Escape>", lambda e: self.hide())
        self.bind_all("<Control-Shift-Key-B>", lambda e: self._on_hotkey_blackout())
        self.bind_all("<Control-Shift-Key-b>", lambda e: self._on_hotkey_blackout())

    # ─── UI Construction ─────────────────────────────────────────────────────

    def _build_ui(self):
        # Frameless outer HUD container (zero border, pure cyber bracket boundaries)
        self._outer = ctk.CTkFrame(
            self,
            fg_color=theme.BG_WIDGET,
            corner_radius=0,
            border_width=0,
        )
        self._outer.pack(fill="both", expand=True)
        self._bind_drag(self._outer)

        # 4 Flush HUD Corner Viewfinder Brackets
        self._corners: list[CornerBracket] = []
        for kind, relx, rely, x_off, y_off in [
            ("tl", 0.0, 0.0, 0, 0),
            ("tr", 1.0, 0.0, -14, 0),
            ("bl", 0.0, 1.0, 0, -14),
            ("br", 1.0, 1.0, -14, -14),
        ]:
            cb = CornerBracket(self._outer, kind=kind, size=14)
            cb.place(relx=relx, rely=rely, x=x_off, y=y_off)
            self._bind_drag(cb)
            self._corners.append(cb)

        # ── TOP HUD ROW: Radar + Tag + State/Timer + Action ───────────────
        top = tk.Frame(self._outer, bg=theme.BG_WIDGET)
        top.pack(fill="x", padx=12, pady=(6, 2))
        self._bind_drag(top)

        # Left: Radar blip + Larger Tech tag
        left_box = tk.Frame(top, bg=theme.BG_WIDGET)
        left_box.pack(side="left")
        self._bind_drag(left_box)

        self._radar = RadarBlip(left_box, size=18)
        self._radar.pack(side="left", padx=(0, 6))
        self._bind_drag(self._radar)

        self._tag_label = tk.Label(
            left_box,
            text="LUCID // SYS",
            font=(theme.FONT_MONO, 10, "bold"),
            fg="#94A3B8",
            bg=theme.BG_WIDGET,
        )
        self._tag_label.pack(side="left")
        self._bind_drag(self._tag_label)

        # Center/Left: Main Status / Timer Countdown
        self._state_label = tk.Label(
            top,
            text="STANDBY",
            font=(theme.FONT_MONO, 11, "bold"),
            fg=theme.INK_SECONDARY,
            bg=theme.BG_WIDGET,
        )
        self._state_label.pack(side="left", padx=(8, 0))
        self._bind_drag(self._state_label)

        # Right: Cyber Action Pill Button (▶ ON / ■ STOP)
        self._action_btn = ctk.CTkButton(
            top,
            text="▶ ON",
            width=48,
            height=20,
            font=ctk.CTkFont(family=theme.FONT_MONO, size=9, weight="bold"),
            fg_color=theme.BG_HOVER,
            text_color=theme.INK_SECONDARY,
            hover_color=theme.BG_PRESSED,
            border_width=1,
            border_color=theme.BORDER_GLASS,
            corner_radius=theme.RADIUS_SM,
            command=self._on_action_btn_click,
        )
        self._action_btn.pack(side="right")

        # ── LASER BAR (Realtime Progress Line) ────────────────────────────
        self._laser = LaserBar(self._outer, height=3)
        self._laser.pack(fill="x", padx=10, pady=(2, 3))
        self._bind_drag(self._laser)

        # ── BOTTOM ROW: Cyber Segmented Controls ──────────────────────────
        bottom = tk.Frame(self._outer, bg=theme.BG_WIDGET)
        bottom.pack(fill="x", padx=10, pady=(0, 6))
        self._bind_drag(bottom)

        self._chip_btns: dict[str, ctk.CTkButton] = {}

        # 1. Preset Chips [15m] [30m] [1h] [2h]
        for label, duration in self._PRESETS:
            btn = ctk.CTkButton(
                bottom,
                text=label,
                width=32,
                height=20,
                font=ctk.CTkFont(family=theme.FONT_MONO, size=9, weight="bold"),
                fg_color=theme.BG_HOVER,
                text_color=theme.INK_SECONDARY,
                hover_color=theme.BG_PRESSED,
                border_width=1,
                border_color=theme.BORDER_GLASS,
                corner_radius=theme.RADIUS_SM,
                command=lambda l=label, d=duration: self._on_preset_click(l, d),
            )
            btn.pack(side="left", padx=(0, 2))
            self._chip_btns[label] = btn
            self._bind_chip_hover(btn, label)

        # 2. Custom Time Entry [_min]
        self._custom_entry = ctk.CTkEntry(
            bottom,
            width=38,
            height=20,
            placeholder_text="min",
            font=ctk.CTkFont(family=theme.FONT_MONO, size=8),
            fg_color=theme.BG_HOVER,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.INK_PRIMARY,
            placeholder_text_color=theme.INK_MUTED,
            corner_radius=theme.RADIUS_SM,
            justify="center",
        )
        self._custom_entry.pack(side="left", padx=(1, 2))
        self._custom_entry.bind("<Return>", lambda e: self._on_custom_submit())

        # Spacer
        tk.Frame(bottom, bg=theme.BG_WIDGET).pack(side="left", fill="x", expand=True)

        # 3. Infinity Button [ ∞ ]
        self._inf_btn = ctk.CTkButton(
            bottom,
            text="∞",
            width=24,
            height=20,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=13, weight="bold"),
            fg_color=theme.BG_HOVER,
            text_color=theme.INK_SECONDARY,
            hover_color=theme.BG_PRESSED,
            border_width=1,
            border_color=theme.BORDER_GLASS,
            corner_radius=theme.RADIUS_SM,
            command=self._on_inf_click,
        )
        self._inf_btn.pack(side="right")
        self._bind_chip_hover(self._inf_btn, "∞")

        # 4. OLED Blackout Button [ OLED ]
        self._oled_btn = ctk.CTkButton(
            bottom,
            text="OLED",
            width=36,
            height=20,
            font=ctk.CTkFont(family=theme.FONT_MONO, size=8, weight="bold"),
            fg_color=theme.BG_HOVER,
            text_color=theme.INK_SECONDARY,
            hover_color=theme.BG_PRESSED,
            border_width=1,
            border_color=theme.BORDER_GLASS,
            corner_radius=theme.RADIUS_SM,
            command=self._on_oled_click,
        )
        self._oled_btn.pack(side="right", padx=(0, 3))
        self._bind_chip_hover(self._oled_btn, "OLED")

    def _bind_chip_hover(self, btn: ctk.CTkButton, key: str):
        """Binds reactive hover illumination to cyber buttons."""
        def on_enter(e):
            if self._active_preset != key:
                btn.configure(border_color=theme.BORDER_SUBTLE, text_color="#FFFFFF")
        def on_leave(e):
            if self._active_preset != key:
                btn.configure(border_color=theme.BORDER_GLASS, text_color=theme.INK_SECONDARY)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    # ─── Dragging ────────────────────────────────────────────────────────────

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self._drag_start)
        widget.bind("<B1-Motion>", self._drag_move)
        widget.bind("<Button-3>", self._show_context_menu)

    def _drag_start(self, event):
        self.focus_force()
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ─── Control Handlers ────────────────────────────────────────────────────

    def _on_action_btn_click(self):
        """Top right quick toggle: If idle -> start infinite, if active -> abort."""
        state = self._get_state()
        if state == AppState.IDLE:
            self._active_preset = "∞"
            self._cb_toggle_infinite()
        else:
            self._active_preset = None
            self._cb_stop()

    def _on_inf_click(self):
        state = self._get_state()
        if state == AppState.ACTIVE_INFINITE:
            self._active_preset = None
            self._cb_stop()
        else:
            self._active_preset = "∞"
            self._cb_toggle_infinite()

    def _on_oled_click(self):
        self._on_hotkey_blackout()

    def _on_preset_click(self, label: str, duration: int):
        state = self._get_state()
        if state != AppState.IDLE and self._active_preset == label:
            self._active_preset = None
            self._cb_stop()
        else:
            self._active_preset = label
            self._cb_start_timer(duration)

    def _on_custom_submit(self):
        val = self._custom_entry.get()
        seconds = parse_duration(val)
        if seconds and seconds > 0:
            self._active_preset = "custom"
            self._cb_start_timer(seconds)
            self._custom_entry.delete(0, "end")
        else:
            self._custom_entry.configure(border_color="#EF4444")
            self.after(500, lambda: self._custom_entry.configure(border_color=theme.BORDER_SUBTLE))

    # ─── Context Menu ────────────────────────────────────────────────────────

    def _close_context_menu(self):
        if hasattr(self, "_active_menu") and self._active_menu:
            try:
                self._active_menu._close()
            except Exception:
                try:
                    self._active_menu.destroy()
                except Exception:
                    pass
            self._active_menu = None

    def _on_hotkey_blackout(self):
        if hasattr(self, "_cb_toggle_blackout") and self._cb_toggle_blackout:
            self._cb_toggle_blackout()

    def _show_context_menu(self, event):
        self._close_context_menu()
        self.focus_force()

        state = self._get_state()
        is_active = state != AppState.IDLE

        items = []
        if self._update_info and self._update_info.has_update:
            items.append((
                f"Update to v{self._update_info.latest_version}",
                lambda: open_release_page(self._update_info.html_url),
                "#10B981",
                None,
            ))
            items.append("---")

        if is_active:
            items.append(("Stop Keep-Awake", self._cb_stop, "#EF4444", None))
        else:
            items.append(("Stay Awake (Infinite)", self._cb_toggle_infinite, "#10B981", None))

        items.append(("OLED Blackout Curtain", self._on_hotkey_blackout, theme.INK_PRIMARY, "Ctrl+Shift+B"))
        items.append("---")
        items.append((f"Lucid v{CURRENT_VERSION}", self._manual_check_update, theme.INK_MUTED, None))
        items.append(("Hide to Tray", self.hide, theme.INK_SECONDARY, None))
        items.append("---")
        items.append(("Quit Lucid", self._cb_quit, "#EF4444", None))

        self._active_menu = CyberContextMenu(self, event.x_root, event.y_root, items)

    def set_update_info(self, info: UpdateInfo):
        """Called when update information is fetched from GitHub Releases."""
        self._update_info = info
        if info.has_update:
            self._tag_label.configure(
                text=f"UPDATE v{info.latest_version} ⇪",
                fg="#10B981",
                cursor="hand2",
            )
            self._tag_label.bind("<Button-1>", lambda e: open_release_page(info.html_url))

    def _manual_check_update(self):
        """User manually clicked check for updates."""
        self._tag_label.configure(text="CHECKING…", fg="#38BDF8")
        def cb(info: UpdateInfo):
            if not self._is_closing:
                self.after(0, lambda: self._on_manual_update_result(info))
        check_for_updates_async(cb)

    def _on_manual_update_result(self, info: UpdateInfo):
        self.set_update_info(info)
        if not info.has_update:
            self._tag_label.configure(text=f"v{CURRENT_VERSION} LATEST", fg="#10B981")
            self.after(2500, lambda: self._tag_label.configure(text="LUCID // SYS", fg="#94A3B8"))

    # ─── UI Update Loop ──────────────────────────────────────────────────────

    def _start_update_loop(self):
        self._update_ui()

    def _update_ui(self):
        if self._is_closing:
            return

        try:
            state = self._get_state()
            time_str = self._get_time_str()
            progress = self._get_progress()

            if state != self._current_state:
                self._apply_state(state)
                self._current_state = state

            # Update live state label, action button & laser bar
            if state == AppState.ACTIVE_TIMER:
                self._state_label.configure(
                    text=time_str,
                    fg=theme.ACCENT_ACTIVE,
                    font=(theme.FONT_MONO, 12, "bold"),
                )
                self._action_btn.configure(
                    text="■ STOP",
                    fg_color="#7F1D1D",
                    text_color="#FCA5A5",
                    border_color="#EF4444",
                    hover_color="#991B1B",
                )
                self._laser.set_state(state, progress)

            elif state == AppState.ACTIVE_INFINITE:
                self._state_label.configure(
                    text="AWAKE ∞",
                    fg=theme.ACCENT_ACTIVE,
                    font=(theme.FONT_MONO, 11, "bold"),
                )
                self._action_btn.configure(
                    text="■ STOP",
                    fg_color="#7F1D1D",
                    text_color="#FCA5A5",
                    border_color="#EF4444",
                    hover_color="#991B1B",
                )
                self._laser.set_state(state, 0.0)

            else:
                self._state_label.configure(
                    text="STANDBY",
                    fg=theme.INK_SECONDARY,
                    font=(theme.FONT_MONO, 11, "bold"),
                )
                self._action_btn.configure(
                    text="▶ ON",
                    fg_color=theme.BG_HOVER,
                    text_color=theme.INK_SECONDARY,
                    border_color=theme.BORDER_GLASS,
                    hover_color=theme.BG_PRESSED,
                )
                self._laser.set_state(state, 0.0)

        except Exception as e:
            logger.warning(f"UI update error: {e}")

        if not self._is_closing:
            self._ui_after_id = self.after(100, self._update_ui)

    def _apply_state(self, state: AppState):
        self._reset_control_styles()

        if state == AppState.IDLE:
            self._radar.set_active(False)
            self._active_preset = None
            # Corners in subtle standby color
            for c in self._corners:
                c.set_color(theme.BORDER_SUBTLE)

        elif state == AppState.ACTIVE_INFINITE:
            self._radar.set_active(True)
            # Corners glow in Neon Emerald
            for c in self._corners:
                c.set_color(theme.ACCENT_ACTIVE)
            self._inf_btn.configure(
                fg_color=theme.ACCENT_ACTIVE_BG,
                text_color=theme.ACCENT_ACTIVE_INK,
                border_color=theme.BORDER_ACTIVE,
            )

        elif state == AppState.ACTIVE_TIMER:
            self._radar.set_active(True)
            # Corners glow in Neon Emerald
            for c in self._corners:
                c.set_color(theme.ACCENT_ACTIVE)
            if self._active_preset in self._chip_btns:
                self._chip_btns[self._active_preset].configure(
                    fg_color=theme.ACCENT_ACTIVE_BG,
                    text_color=theme.ACCENT_ACTIVE_INK,
                    border_color=theme.BORDER_ACTIVE,
                )

        # Dynamic window/taskbar favicon
        try:
            png_path = ICON_ACTIVE_PNG_PATH if state != AppState.IDLE else ICON_IDLE_PNG_PATH
            ico_path = ICON_ACTIVE_ICO_PATH if state != AppState.IDLE else ICON_IDLE_ICO_PATH
            if png_path.exists():
                img_png = Image.open(png_path)
                self._app_icon_photo = ImageTk.PhotoImage(img_png.resize((64, 64), Image.Resampling.LANCZOS))
                self.iconphoto(False, self._app_icon_photo)
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except Exception:
            pass

    def _reset_control_styles(self):
        for btn in self._chip_btns.values():
            btn.configure(
                fg_color=theme.BG_HOVER,
                text_color=theme.INK_SECONDARY,
                border_color=theme.BORDER_GLASS,
            )
        self._inf_btn.configure(
            fg_color=theme.BG_HOVER,
            text_color=theme.INK_SECONDARY,
            border_color=theme.BORDER_GLASS,
        )
        if hasattr(self, "_oled_btn") and self._oled_btn:
            self._oled_btn.configure(
                fg_color=theme.BG_HOVER,
                text_color=theme.INK_SECONDARY,
                border_color=theme.BORDER_GLASS,
            )

    # ─── Public API ──────────────────────────────────────────────────────────

    def show(self):
        if not self._is_closing:
            self.deiconify()
            self.attributes("-topmost", True)

    def hide(self):
        if hasattr(self, "_active_menu") and self._active_menu:
            try:
                self._active_menu.unpost()
                self._active_menu.destroy()
            except Exception:
                pass
            self._active_menu = None
        if not self._is_closing:
            self.withdraw()

    def safe_quit(self):
        self._is_closing = True
        if self._ui_after_id:
            try:
                self.after_cancel(self._ui_after_id)
            except Exception:
                pass
            self._ui_after_id = None
        if hasattr(self, "_radar") and self._radar:
            self._radar.stop()
        try:
            from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
            ScalingTracker.window_widgets_dict.clear()
            ScalingTracker.update_loop_running = False
        except Exception:
            pass
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
