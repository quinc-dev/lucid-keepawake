# Changelog

All notable changes to the **Lucid** keep-awake utility will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-11-02

### 🚀 Added
- **OLED Blackout Curtain (Eco GPU Mode)**: Fullscreen `#000000` blackout overlay shutting off OLED subpixels (0 nits, 0% burn-in risk) while preserving active display context so CUDA, AI vibecoding, and GPU renders run at 100% throughput.
- **Smooth 0.4s Lens-Fade Transition**: Gentle radial vignette transition into pure black without blinding flashes or jarring cuts.
- **Dual-Mode Instant Wake**: 0ms wake-up on keyboard input, mouse motion (>50px), or remote programmatic trigger.
- **Model Context Protocol (MCP) Server**: Stdio JSON-RPC MCP server (`mcp_server.py`) exposing 6 autonomous tools (`lucid_status`, `lucid_blackout`, `lucid_wake`, `lucid_set_awake`, `lucid_stop`, `lucid_toggle_hud`) for Antigravity, Cursor, and Claude agents.
- **Localhost IPC & CLI Bridge**: Fast socket daemon (`core/ipc.py`) supporting CLI controls (`--blackout`, `--wake`, `--status`, `--awake`, `--stop`).
- **Global Shortcut**: Hotkey `Ctrl + Shift + B` to instantly engage or toggle the OLED Blackout Curtain.

### 🛡️ Fixed
- **Context Menu Auto-Dismiss**: Fixed bug where right-clicking on the HUD and selecting "Hide to Tray" left the popup menu hanging on the screen; added `<FocusOut>` auto-dismiss and explicit teardown.
- **Minimalist Aesthetic Refinement**: Cleaned up context menu and system tray menu labels, removing cluttered emojis in favor of crisp Titanium/Zinc typography.

---

## [1.0.0] - 2026-08-05

### 🚀 Added
- **Zero-Side-Effect Keep-Awake Engine**: Native Windows Win32 `SetThreadExecutionState` (`ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED | ES_CONTINUOUS`) thread-safe manager. No mouse moving, no simulated keystrokes, no screen interference.
- **Cyber-HUD Floating Capsule**: 256×68px Obsidian (`#080B10`) dark-glass capsule with 4 dynamic HUD corner brackets, animated radar heartbeat blip, and real-time 2px neon laser countdown line.
- **Preset & Custom Countdown Controls**:
  - Instant duration chips: `[ 15m ]`, `[ 30m ]`, `[ 1h ]`, `[ 2h ]`.
  - Inline custom duration input: `[ min ]` supporting minutes (`45`, `90`), hours (`1.5h`), and seconds (`90s`).
  - Infinite Stay-Awake toggle: `[ ∞ ]` button and top-right power pill.
- **Dual-State Dynamic System Tray & Favicon**:
  - `icon_active.ico` / `icon_active.png` (Neon Emerald `#10B981` core with radiant orbital arcs).
  - `icon_idle.ico` / `icon_idle.png` (Inactive Titanium `#475569` standby core).
  - 4x Supersampled (2048px canvas -> 512px PNG & 256px multi-resolution ICO layers).
  - In-memory cached `pystray` system tray integration with right-click menu and single-click show/hide toggle.
- **Clean Lifecycle & Error-Free Shutdown**:
  - Hardened Tcl/Tk teardown with graceful timer cancellation preventing `invalid command name` errors.
  - Silent launcher script (`Lucid.bat` via `pythonw.exe`).
- **Standalone Windows Single-File Executable**:
  - Portable 64-bit `Lucid.exe` bundled with high-DPI assets and CustomTkinter theme assets.
