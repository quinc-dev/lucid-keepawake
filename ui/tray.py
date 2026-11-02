"""
ui/tray.py — System tray icon and Cyber-HUD menu for Lucid.
Uses pystray + core.icon for crisp, state-reactive system tray icons.
"""

import threading
import logging
from typing import Callable, Optional

try:
    import pystray
    from pystray import MenuItem as TrayItem, Menu as TrayMenu
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

from core.icon import get_tray_icon
from core.timer import AppState, TIMER_PRESETS
from core.updater import UpdateInfo, open_release_page, CURRENT_VERSION

logger = logging.getLogger(__name__)


class TrayManager:
    """
    Manages the system tray icon and contextual actions.
    Runs in its own background thread (pystray requirement).
    """

    def __init__(
        self,
        on_show_widget: Callable,
        on_hide_widget: Callable,
        on_toggle_infinite: Callable,
        on_start_timer: Callable[[int], None],
        on_stop: Callable,
        on_quit: Callable,
        get_state: Callable[[], AppState],
        on_check_update: Optional[Callable] = None,
        on_toggle_blackout: Optional[Callable] = None,
    ):
        self._on_show = on_show_widget
        self._on_hide = on_hide_widget
        self._on_toggle = on_toggle_infinite
        self._on_start_timer = on_start_timer
        self._on_stop = on_stop
        self._on_quit = on_quit
        self._get_state = get_state
        self._on_check_update = on_check_update
        self._on_toggle_blackout = on_toggle_blackout
        self._update_info: Optional[UpdateInfo] = None
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not PYSTRAY_AVAILABLE:
            logger.warning("pystray not available — tray icon disabled")
            return
        self._thread = threading.Thread(
            target=self._run_tray,
            name="lucid-tray",
            daemon=True
        )
        self._thread.start()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def set_update_info(self, info: UpdateInfo):
        """Update release notification in tray menu."""
        self._update_info = info
        if self._icon:
            try:
                self._icon.menu = self._build_menu()
            except Exception as e:
                logger.debug(f"Tray menu refresh notice: {e}")

    def update_icon(self, state: AppState):
        """Refresh tray icon and tooltip to reflect current state."""
        if self._icon:
            try:
                self._icon.icon = get_tray_icon(state, size=64)
                if state == AppState.ACTIVE_INFINITE:
                    self._icon.title = "Lucid // Awake (Infinite)"
                elif state == AppState.ACTIVE_TIMER:
                    self._icon.title = "Lucid // Timer Active"
                else:
                    self._icon.title = "Lucid // Standby"
            except Exception as e:
                logger.warning(f"Tray icon update failed: {e}")

    def _build_menu(self) -> "TrayMenu":
        def _show_handler(icon, item):
            self._on_show()

        def _hide_handler(icon, item):
            self._on_hide()

        def _toggle_handler(icon, item):
            current = self._get_state()
            if current == AppState.IDLE:
                self._on_toggle()
            else:
                self._on_stop()

        def _stop_handler(icon, item):
            self._on_stop()

        def _quit_handler(icon, item):
            self._on_quit()
            icon.stop()

        def _update_click_handler(icon, item):
            if self._update_info:
                open_release_page(self._update_info.html_url)

        def _check_update_handler(icon, item):
            if self._on_check_update:
                self._on_check_update()

        # Build timer preset subitems
        timer_items = []
        for label, duration in TIMER_PRESETS.items():
            def make_timer_handler(dur):
                return lambda icon, item: self._on_start_timer(dur)
            timer_items.append(TrayItem(f"{label}", make_timer_handler(duration)))

        menu_items = []

        # If update is available, place prominent highlight at top
        if self._update_info and self._update_info.has_update:
            menu_items.append(
                TrayItem(
                    f"✦  Update Available (v{self._update_info.latest_version})",
                    _update_click_handler,
                )
            )
            menu_items.append(TrayMenu.SEPARATOR)

        def _blackout_handler(icon, item):
            if self._on_toggle_blackout:
                self._on_toggle_blackout()

        menu_items.extend([
            TrayItem("Show HUD", _show_handler, default=True),
            TrayItem("Hide to Tray", _hide_handler),
            TrayMenu.SEPARATOR,
            TrayItem("Stay Awake (Infinite)", _toggle_handler),
            TrayItem("Set Timer", TrayMenu(*timer_items)),
            TrayItem("OLED Blackout Curtain (Ctrl+Shift+B)", _blackout_handler),
            TrayItem("Stop Keep-Awake", _stop_handler),
            TrayMenu.SEPARATOR,
            TrayItem("Check for Updates", _check_update_handler),
            TrayItem(f"Version {CURRENT_VERSION}", lambda icon, item: None, enabled=False),
            TrayMenu.SEPARATOR,
            TrayItem("Quit Lucid", _quit_handler),
        ])

        return TrayMenu(*menu_items)

    def _run_tray(self):
        state = self._get_state()
        icon_img = get_tray_icon(state, size=64)

        self._icon = pystray.Icon(
            name="Lucid",
            icon=icon_img,
            title="Lucid // Standby",
            menu=self._build_menu(),
        )
        self._icon.run()
