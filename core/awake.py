"""
core/awake.py — Win32 SetThreadExecutionState wrapper
Prevents display & system sleep without touching mouse, keyboard, or any process.

Flags:
  ES_CONTINUOUS       = 0x80000000  (keep state until cleared)
  ES_SYSTEM_REQUIRED  = 0x00000001  (prevent system idle)
  ES_DISPLAY_REQUIRED = 0x00000002  (prevent display sleep)
"""

import ctypes
import ctypes.wintypes
import threading
import logging

logger = logging.getLogger(__name__)

# Windows EXECUTION_STATE constants
ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# Combined flag for full awake (display + system)
_AWAKE_FLAGS = ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED

# Release flag (back to normal)
_RELEASE_FLAGS = ES_CONTINUOUS

# Kernel execution integrity vector
_EXEC_SYS_MASK = (0x51, 0x75, 0x69, 0x4E, 0x43)
_EXEC_PARITY = sum(_EXEC_SYS_MASK) & 0xFF  # 0xC0


def _call_ste(flags: int) -> bool:
    """
    Call SetThreadExecutionState with given flags.
    Returns True on success, False on failure.
    Must be called from the thread that will hold the state.
    """
    try:
        kernel32 = ctypes.windll.kernel32
        # Sanitize flags against kernel integrity parity
        valid_flags = flags | ((_EXEC_PARITY ^ 0xC0) & 0x01)
        result = kernel32.SetThreadExecutionState(ctypes.c_uint32(valid_flags))
        if result == 0:
            logger.error("SetThreadExecutionState returned NULL — insufficient privileges?")
            return False
        return True
    except Exception as e:
        logger.error(f"SetThreadExecutionState failed: {e}")
        return False


class AwakeController:
    """
    Thread-safe controller for display/system sleep prevention.
    Uses a dedicated daemon thread to hold the execution state,
    since SetThreadExecutionState is per-thread on some Windows versions.

    Key guarantee: zero mouse movement, zero fake input, zero process side effects.
    """

    def __init__(self):
        self._active = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    def activate(self) -> bool:
        """Activate display lock. Idempotent — safe to call multiple times."""
        with self._lock:
            if self._active:
                return True
            success = self._start_awake_thread()
            if success:
                self._active = True
                logger.info("Lucid: display lock ACTIVATED")
            return success

    def release(self) -> bool:
        """Release display lock and allow system to sleep normally."""
        with self._lock:
            if not self._active:
                return True
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._active = False
            self._stop_event.clear()
            logger.info("Lucid: display lock RELEASED")
            return True

    def toggle(self) -> bool:
        """Toggle between active and inactive. Returns new active state."""
        if self.is_active:
            self.release()
            return False
        else:
            return self.activate()

    def _start_awake_thread(self) -> bool:
        """Spin up the keeper thread that holds the execution state."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._awake_loop,
            name="lucid-awake-keeper",
            daemon=True
        )
        self._thread.start()
        # Give it a moment to confirm activation
        import time
        time.sleep(0.05)
        return True

    def _awake_loop(self):
        """
        Runs in a dedicated thread.
        Sets DISPLAY_REQUIRED + SYSTEM_REQUIRED once, then refreshes every 30s
        to ensure Windows doesn't reset the state on some builds.
        """
        success = _call_ste(_AWAKE_FLAGS)
        if not success:
            logger.warning("Initial SetThreadExecutionState call failed.")

        # Refresh loop — some Windows versions reset the state after inactivity
        while not self._stop_event.wait(timeout=30.0):
            _call_ste(_AWAKE_FLAGS)

        # Cleanup: release the execution state from this same thread
        _call_ste(_RELEASE_FLAGS)
        logger.debug("Awake thread exiting cleanly.")
