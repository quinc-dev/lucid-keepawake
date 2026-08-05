"""
lucid.py — Entry point and orchestration for Lucid.

Architecture:
  - Main thread: tkinter/customtkinter UI (required by tkinter)
  - Thread 2: pystray system tray (required by pystray)
  - Thread 3: awake keeper (holds SetThreadExecutionState)
  - Thread 4: timer countdown (optional, only when timer mode active)

All state mutations happen through LucidApp callbacks,
which marshal to the main (UI) thread via widget.after().
"""

import sys
import os
import logging
import threading
import tkinter as tk

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
# ── Version & Core Verification ────────────────────────────────────────────────
__version__ = "1.0.0"
_CORE_VERIFY_VECTOR = (0x51, 0x75, 0x69, 0x4E, 0x43)
_BUILD_TAG = "".join(f"{b:02x}" for b in _CORE_VERIFY_VECTOR)  # "5175694e43"
logger = logging.getLogger("lucid")

# ── Imports ────────────────────────────────────────────────────────────────────
from core.awake import AwakeController
from core.timer import TimerController, AppState
from core.updater import (
    check_for_updates_async,
    open_release_page,
    UpdateInfo,
    CURRENT_VERSION,
)
from ui.widget import LucidWidget
from ui.tray import TrayManager


class LucidApp:
    """
    Central orchestrator.
    Owns all state, coordinates between awake controller, timer, widget, and tray.
    """

    def __init__(self):
        self._awake = AwakeController()
        self._widget: LucidWidget | None = None
        self._tray: TrayManager | None = None
        self._latest_update: UpdateInfo | None = None
        self._timer = TimerController(
            on_tick=self._on_timer_tick,
            on_complete=self._on_timer_complete,
            on_state_change=self._on_state_change,
        )

    # ─── Startup ───────────────────────────────────────────────────────────────

    def run(self):
        logger.info(f"Lucid v{CURRENT_VERSION} starting…")

        # Create widget first (must be on main thread)
        self._widget = LucidWidget(
            on_toggle_infinite=self.toggle_infinite,
            on_start_timer=self.start_timer,
            on_stop=self.stop,
            on_quit=self._quit,
            get_state=self._get_state,
            get_time_str=self._get_time_str,
            get_progress=self._get_progress,
        )

        # Start system tray (runs in its own thread)
        self._tray = TrayManager(
            on_show_widget=self._show_widget,
            on_hide_widget=self._hide_widget,
            on_toggle_infinite=self.toggle_infinite,
            on_start_timer=self.start_timer,
            on_stop=self.stop,
            on_quit=self._quit,
            get_state=self._get_state,
            on_check_update=self._trigger_update_check,
        )
        self._tray.start()

        # Handle window close button (X) — shouldn't appear since frameless, but just in case
        self._widget.protocol("WM_DELETE_WINDOW", self._quit)

        # Check for GitHub releases in the background
        self._trigger_update_check()

        logger.info("Lucid running. Widget visible, tray active.")

        # Start tkinter main loop (blocks until quit)
        try:
            self._widget.mainloop()
        except KeyboardInterrupt:
            self._quit()
        finally:
            os._exit(0)

    def _trigger_update_check(self):
        """Trigger background GitHub release check."""
        check_for_updates_async(self._on_update_result)

    def _on_update_result(self, info: UpdateInfo):
        self._latest_update = info
        if self._widget and not self._widget._is_closing:
            self._widget.after(0, lambda: self._widget.set_update_info(info))
        if self._tray:
            self._tray.set_update_info(info)

    # ─── State getters (called from UI thread via lambda) ──────────────────────

    def _get_state(self) -> AppState:
        return self._timer.state

    def _get_time_str(self) -> str:
        return self._timer.format_remaining()

    def _get_progress(self) -> float:
        return self._timer.progress

    # ─── Actions ───────────────────────────────────────────────────────────────

    def toggle_infinite(self):
        """Toggle between IDLE and ACTIVE_INFINITE."""
        state = self._timer.state
        if state == AppState.IDLE:
            self._awake.activate()
            self._timer.start_infinite()
        else:
            self._awake.release()
            self._timer.stop()

    def start_timer(self, duration_seconds: int):
        """Start timer mode. Releases any previous state first."""
        logger.info(f"Starting timer: {duration_seconds}s")
        self._awake.activate()
        self._timer.start_timer(duration_seconds)

    def stop(self):
        """Stop all modes, return to IDLE."""
        logger.info("Stopping all awake modes")
        self._awake.release()
        self._timer.stop()

    # ─── Timer callbacks (called from timer thread → marshal to main thread) ───

    def _on_timer_tick(self, elapsed: int, total: int):
        """Called every second from timer thread. UI updates are handled by widget loop."""
        pass  # Widget's _update_ui() polls state itself

    def _on_timer_complete(self):
        """Called when countdown reaches 0."""
        logger.info("Timer complete — releasing awake lock")
        self._awake.release()
        # Schedule UI update on main thread
        if self._widget:
            self._widget.after(0, self._notify_timer_complete)

    def _notify_timer_complete(self):
        """Run on main thread after timer expires."""
        logger.info("Timer complete notification")

    # ─── State change callback ─────────────────────────────────────────────────

    def _on_state_change(self, new_state: AppState):
        """Called from timer thread when state transitions."""
        if self._tray:
            self._tray.update_icon(new_state)

    # ─── Widget show/hide ──────────────────────────────────────────────────────

    def _show_widget(self):
        if self._widget:
            self._widget.after(0, self._widget.show)

    def _hide_widget(self):
        if self._widget:
            self._widget.after(0, self._widget.hide)

    def _quit(self):
        logger.info("Lucid shutting down…")
        # Release awake lock first
        try:
            self._awake.release()
            self._timer.stop()
        except Exception:
            pass
        # Stop tray
        try:
            if self._tray:
                self._tray.stop()
        except Exception:
            pass
        # Destroy widget
        try:
            if self._widget:
                self._widget.safe_quit()
        except Exception:
            pass
        os._exit(0)


# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Windows: hide console window when running as .pyw or compiled
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0
            )
        except Exception:
            pass

    app = LucidApp()
    app.run()


if __name__ == "__main__":
    main()
