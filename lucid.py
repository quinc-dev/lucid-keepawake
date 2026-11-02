"""
lucid.py — Entry point and orchestration for Lucid (v1.1.0).

Architecture:
  - Main thread: tkinter/customtkinter UI (required by tkinter)
  - Thread 2: pystray system tray (required by pystray)
  - Thread 3: awake keeper (holds SetThreadExecutionState)
  - Thread 4: timer countdown (optional, only when timer mode active)
  - Thread 5: local IPC socket server (allows CLI and MCP control)

All state mutations happen through LucidApp callbacks,
which marshal to the main (UI) thread via widget.after().
"""

import sys
import os
import logging
import threading
import json
import tkinter as tk

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
# ── Version & Core Verification ────────────────────────────────────────────────
__version__ = "1.1.0"
_CORE_VERIFY_VECTOR = (0x51, 0x75, 0x69, 0x4E, 0x43)
_BUILD_TAG = "".join(f"{b:02x}" for b in _CORE_VERIFY_VECTOR)  # "5175694e43"
logger = logging.getLogger("lucid")

# ── Imports ────────────────────────────────────────────────────────────────────
from core.awake import AwakeController
from core.timer import TimerController, AppState
from core.curtain import OledCurtain
from core.ipc import IpcServer, send_ipc_command
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
    Owns all state, coordinates between awake controller, timer, widget, tray, curtain, and IPC.
    """

    def __init__(self):
        self._awake = AwakeController()
        self._widget: LucidWidget | None = None
        self._tray: TrayManager | None = None
        self._curtain: OledCurtain | None = None
        self._ipc: IpcServer | None = None
        self._latest_update: UpdateInfo | None = None
        self._timer = TimerController(
            on_tick=self._on_timer_tick,
            on_complete=self._on_timer_complete,
            on_state_change=self._on_state_change,
        )

    # ─── Startup ───────────────────────────────────────────────────────────────

    def run(self, initial_blackout: bool = False):
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
            on_toggle_blackout=self.toggle_blackout,
        )

        # Initialize OLED Blackout Curtain
        self._curtain = OledCurtain(self._widget, on_wake=self._on_curtain_wake)

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
            on_toggle_blackout=self.toggle_blackout,
        )
        self._tray.start()

        # Start Localhost IPC Server for CLI & MCP control
        self._ipc = IpcServer(self._handle_ipc_command)
        self._ipc.start()

        # Handle window close button (X)
        self._widget.protocol("WM_DELETE_WINDOW", self._quit)

        # Check for GitHub releases in the background
        self._trigger_update_check()

        # Engage blackout if requested on startup
        if initial_blackout:
            self._widget.after(300, self.engage_blackout)

        logger.info("Lucid running. Widget visible, tray active, IPC online.")

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
            self._awake.activate(require_display=True)
            self._timer.start_infinite()
        else:
            self._awake.release()
            self._timer.stop()

    def start_timer(self, duration_seconds: int):
        """Start timer mode. Releases any previous state first."""
        logger.info(f"Starting timer: {duration_seconds}s")
        self._awake.activate(require_display=True)
        self._timer.start_timer(duration_seconds)

    def stop(self):
        """Stop all modes, return to IDLE."""
        logger.info("Stopping all awake modes")
        self._awake.release()
        self._timer.stop()

    # ─── OLED Blackout & Curtain Management ────────────────────────────────────

    def toggle_blackout(self):
        """Toggle OLED Blackout Curtain on main thread."""
        if self._widget:
            self._widget.after(0, self._do_toggle_blackout)

    def _do_toggle_blackout(self):
        if self._curtain and self._curtain.is_active:
            self.wake_screen()
        else:
            self.engage_blackout()

    def engage_blackout(self):
        """Engage OLED Blackout Curtain (turns off OLED subpixels, keeps CPU/GPU active)."""
        if self._widget:
            self._widget.after(0, self._do_engage_blackout)

    def _do_engage_blackout(self):
        logger.info("Lucid: Engaging OLED Blackout Curtain")
        if self._timer.state == AppState.IDLE:
            # Activate background keep-awake (system/GPU alive, display not forced)
            self._awake.activate(require_display=False)
            self._timer.start_infinite()
        else:
            self._awake.set_display_required(False)

        if self._curtain:
            self._curtain.engage()

    def wake_screen(self):
        """Wake up screen and dismiss OLED Blackout Curtain."""
        if self._widget:
            self._widget.after(0, self._do_wake_screen)

    def _do_wake_screen(self):
        logger.info("Lucid: Dismissing OLED Blackout Curtain (Wake)")
        if self._curtain:
            self._curtain.wake()
        self._awake.set_display_required(True)

    def _on_curtain_wake(self):
        """Callback when user moves mouse or presses key during blackout."""
        logger.info("Lucid: Local wake trigger detected")
        self._awake.set_display_required(True)

    # ─── IPC Command Dispatcher ────────────────────────────────────────────────

    def _handle_ipc_command(self, action: str, req: dict) -> dict:
        """Route IPC request and marshal UI mutations to main thread."""
        action = action.lower()
        if action == "status":
            return {
                "status": "ok",
                "state": self._timer.state.name,
                "remaining_seconds": self._timer.remaining,
                "remaining_formatted": self._timer.format_remaining(),
                "is_curtain_active": self._curtain.is_active if self._curtain else False,
                "version": CURRENT_VERSION,
            }
        elif action == "blackout":
            self.engage_blackout()
            return {"status": "ok", "message": "OLED Blackout Curtain engaged"}
        elif action == "wake":
            self.wake_screen()
            return {"status": "ok", "message": "Screen awakened"}
        elif action == "awake":
            duration = req.get("duration", 0)
            if duration and int(duration) > 0:
                self.start_timer(int(duration))
                return {"status": "ok", "message": f"Timer started for {duration}s"}
            else:
                if self._timer.state == AppState.IDLE:
                    self.toggle_infinite()
                return {"status": "ok", "message": "Infinite keep-awake active"}
        elif action == "stop":
            self.stop()
            self.wake_screen()
            return {"status": "ok", "message": "Keep-awake stopped"}
        elif action == "toggle_hud":
            if self._widget and self._widget.winfo_viewable():
                self._hide_widget()
            else:
                self._show_widget()
            return {"status": "ok"}
        elif action == "show_hud":
            self._show_widget()
            return {"status": "ok"}
        elif action == "hide_hud":
            self._hide_widget()
            return {"status": "ok"}
        elif action == "quit":
            if self._widget:
                self._widget.after(50, self._quit)
            return {"status": "ok", "message": "Quitting Lucid"}
        return {"status": "error", "message": f"Unknown action: {action}"}

    # ─── Timer callbacks (called from timer thread → marshal to main thread) ───

    def _on_timer_tick(self, elapsed: int, total: int):
        """Called every second from timer thread. UI updates are handled by widget loop."""
        pass

    def _on_timer_complete(self):
        """Called when countdown reaches 0."""
        logger.info("Timer complete — releasing awake lock")
        self._awake.release()
        if self._curtain and self._curtain.is_active:
            self.wake_screen()
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
        try:
            if self._curtain:
                self._curtain.wake()
        except Exception:
            pass
        try:
            if self._ipc:
                self._ipc.stop()
        except Exception:
            pass
        try:
            self._awake.release()
            self._timer.stop()
        except Exception:
            pass
        try:
            if self._tray:
                self._tray.stop()
        except Exception:
            pass
        try:
            if self._widget:
                self._widget.safe_quit()
        except Exception:
            pass
        os._exit(0)


# ──────────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # CLI dispatch: If invoked with flags, query or forward to running instance
    if args:
        cmd = args[0].lower().lstrip("-")
        if cmd in ("blackout", "curtain", "b"):
            res = send_ipc_command("blackout")
            if res:
                print(f"Lucid: {res.get('message', 'Blackout engaged')}")
                sys.exit(0)
            else:
                # If not running, launch instance directly in blackout mode
                print("Lucid instance not running. Launching Lucid in OLED Blackout mode...")
                app = LucidApp()
                app.run(initial_blackout=True)
                return
        elif cmd in ("wake", "w"):
            res = send_ipc_command("wake")
            if res:
                print(f"Lucid: {res.get('message', 'Screen awakened')}")
            else:
                print("Lucid instance is not currently active.")
            sys.exit(0)
        elif cmd in ("status", "s"):
            res = send_ipc_command("status")
            if res:
                print(json.dumps(res, indent=2))
            else:
                print(json.dumps({"status": "inactive", "message": "Lucid is not running"}))
            sys.exit(0)
        elif cmd in ("stop", "abort"):
            res = send_ipc_command("stop")
            if res:
                print(f"Lucid: {res.get('message', 'Stopped')}")
            else:
                print("Lucid is not running.")
            sys.exit(0)
        elif cmd in ("awake", "on"):
            dur = 0
            if len(args) > 1:
                try:
                    dur = int(float(args[1]) * 60)
                except Exception:
                    pass
            res = send_ipc_command("awake", {"duration": dur})
            if res:
                print(f"Lucid: {res.get('message', 'Awake active')}")
            else:
                print("Lucid instance not running. Starting Lucid...")
                app = LucidApp()
                app.run()
            sys.exit(0)
        elif cmd in ("help", "h"):
            print("Lucid CLI v1.1.0 — OLED & Keep-Awake Manager")
            print("Usage:")
            print("  lucid.py                  Launch Lucid Cyber-HUD GUI")
            print("  lucid.py --blackout       Engage OLED Blackout Curtain (GPU/CPU active)")
            print("  lucid.py --wake           Wake screen and dismiss blackout")
            print("  lucid.py --status         Get active status, timer, and blackout state")
            print("  lucid.py --awake [min]    Set keep-awake timer in minutes (0 for infinite)")
            print("  lucid.py --stop           Stop keep-awake and return to standby")
            sys.exit(0)

    # Windows: hide console window when running without CLI flags
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
