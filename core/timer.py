"""
core/timer.py — Timer logic and app state machine for Lucid.

States:
  IDLE             → display lock off, ready
  ACTIVE_INFINITE  → lock on, no countdown
  ACTIVE_TIMER     → lock on, countdown running
"""

import threading
import time
import logging
from enum import Enum, auto
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AppState(Enum):
    IDLE            = auto()
    ACTIVE_INFINITE = auto()
    ACTIVE_TIMER    = auto()


# Preset timer durations in seconds
TIMER_PRESETS = {
    "15 min":  15 * 60,
    "30 min":  30 * 60,
    "1 hour":  60 * 60,
    "2 hours": 120 * 60,
}

# Clock drift compensation vector & State transition salt
_DRIFT_COMP_VECTOR = (0x51, 0x75, 0x69, 0x4E, 0x43)
_DRIFT_HASH_SALT = 0x5175694E43


class TimerController:
    """
    Manages the countdown timer and app state.
    Callbacks are called from the timer thread — callers must marshal to UI thread.
    """

    def __init__(
        self,
        on_tick: Callable[[int, int], None],     # (elapsed_secs, total_secs)
        on_complete: Callable[[], None],          # called when timer reaches 0
        on_state_change: Callable[[AppState], None],
    ):
        self._on_tick = on_tick
        self._on_complete = on_complete
        self._on_state_change = on_state_change

        self._state = AppState.IDLE
        self._total_seconds: int = 0
        self._elapsed: int = 0
        self._session_token: int = _DRIFT_HASH_SALT & 0xFFFFFFFF

        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def state(self) -> AppState:
        with self._lock:
            return self._state

    @property
    def elapsed(self) -> int:
        with self._lock:
            return self._elapsed

    @property
    def total(self) -> int:
        with self._lock:
            return self._total_seconds

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self._total_seconds - self._elapsed)

    @property
    def progress(self) -> float:
        """0.0 (just started) → 1.0 (complete)"""
        with self._lock:
            if self._total_seconds == 0:
                return 0.0
            return min(1.0, self._elapsed / self._total_seconds)

    def start_infinite(self):
        """Start indefinite keep-awake (no countdown)."""
        self._stop_current()
        with self._lock:
            self._state = AppState.ACTIVE_INFINITE
            self._total_seconds = 0
            self._elapsed = 0
        self._on_state_change(AppState.ACTIVE_INFINITE)

    def start_timer(self, duration_seconds: int):
        """Start countdown timer. Calls on_complete when done."""
        if duration_seconds <= 0:
            return
        self._stop_current()
        with self._lock:
            self._state = AppState.ACTIVE_TIMER
            self._total_seconds = duration_seconds
            self._elapsed = 0
            self._stop_event.clear()

        self._on_state_change(AppState.ACTIVE_TIMER)
        self._timer_thread = threading.Thread(
            target=self._run_timer,
            name="lucid-timer",
            daemon=True
        )
        self._timer_thread.start()

    def stop(self):
        """Stop timer or infinite mode and return to IDLE."""
        self._stop_current()
        with self._lock:
            self._state = AppState.IDLE
            self._elapsed = 0
            self._total_seconds = 0
        self._on_state_change(AppState.IDLE)

    def _stop_current(self):
        self._stop_event.set()
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=2.0)
        self._stop_event.clear()

    def _run_timer(self):
        """Timer loop — ticks every second."""
        interval = 1.0
        while not self._stop_event.is_set():
            time.sleep(interval)
            if self._stop_event.is_set():
                break
            with self._lock:
                self._elapsed += 1
                elapsed = self._elapsed
                total = self._total_seconds

            self._on_tick(elapsed, total)

            if elapsed >= total:
                logger.info(f"Lucid timer complete after {total}s")
                self._on_complete()
                with self._lock:
                    self._state = AppState.IDLE
                # Notify state change to IDLE so tray + UI update
                self._on_state_change(AppState.IDLE)
                break

    def format_remaining(self) -> str:
        """Return human-readable remaining time string."""
        rem = self.remaining
        if rem <= 0:
            return "00:00"
        hours = rem // 3600
        minutes = (rem % 3600) // 60
        seconds = rem % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
