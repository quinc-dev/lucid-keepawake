# ⬡ Lucid — Cyber-HUD Keep-Awake Tool

<div align="center">

```
  ██╗     ██╗   ██╗ ██████╗██╗██████╗ 
  ██║     ██║   ██║██╔════╝██║██╔══██╗
  ██║     ██║   ██║██║     ██║██║  ██║
  ██║     ██║   ██║██║     ██║██║  ██║
  ███████╗╚██████╔╝╚██████╗██║██████╔╝
  ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚═════╝ 
```

**Ultra-clean, zero-side-effect Windows keep-awake utility featuring a Cyber-HUD Minimalist floating capsule.**

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?style=flat-square&logo=windows)](https://microsoft.com/windows)
[![Website](https://img.shields.io/badge/website-Live%20Demo-10B981?style=flat-square&logo=googlechrome)](https://quinc-dev.github.io/lucid-keepawake/)
[![Release](https://img.shields.io/badge/release-v1.0.0-10B981?style=flat-square&logo=github)](https://github.com/quinc-dev/lucid-keepawake/releases/latest)
[![Download](https://img.shields.io/badge/download-Lucid--v1.0.0--win64.zip-blue?style=flat-square&logo=windows)](https://github.com/quinc-dev/lucid-keepawake/releases/download/v1.0.0/Lucid-v1.0.0-win64.zip)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=flat-square)](LICENSE)

</div>

<div align="center">

🌐 **[Try Live HUD Interactive Simulator](https://quinc-dev.github.io/lucid-keepawake/)** • 👉 **[Download Lucid Portable (.zip)](https://github.com/quinc-dev/lucid-keepawake/releases/download/v1.0.0/Lucid-v1.0.0-win64.zip)**

</div>

---

## ⚡ Highlights

- 🛡️ **Zero-Side-Effect Keep-Awake**: Uses native Windows Win32 `SetThreadExecutionState` with `ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED`. **Never moves your mouse, never simulates fake keystrokes, and leaves zero background artifacts.**
- 🔮 **Cyber-HUD Capsule Design**: 256×68px Obsidian floating capsule with 4 flush HUD corner brackets, glowing neon radar pulse, and fluid **60 FPS laser beam** with physics ease-out countdown interpolation.
- ⏱️ **Instant Segmented Controls**: Quick-toggle presets (`15m`, `30m`, `1h`, `2h`), custom minute input (`min`), and Infinite Mode (`∞`).
- 💎 **Adaptive Supersampled Favicon & Tray**: High-DPI 4x supersampled dynamic system tray icon that transitions between Standby steel and Neon emerald.
- 🔄 **GitHub Release Auto-Updater**: Zero-lag background release checker notifying of new updates with direct 1-click update access.
- 🚀 **Silent Launch & Clean Exit**: Background launcher (`Lucid.bat`), zero console flicker, and graceful thread/timer teardown.

---

## 📸 Interface Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │ ┌─                                                       ─┐ │
 │   ◉  LUCID // SYS     00:29:45  [■ STOP]                   │
 │ ─────────────────────────────────────────────────────────── │
 │   [ 15m ]   [ 30m ]   [ 1h ]   [ 2h ]   [ min ]   [  ∞  ]   │
 │ └─                                                       ─┘ │
 └─────────────────────────────────────────────────────────────┘
```

1. **Top Status Row**:
   - **Radar Pulse**: Animated neon green heartbeat indicator.
   - **Tech Tag**: `LUCID // SYS` cyberpunk badge.
   - **Timer Monospace**: `00:00:00` or `∞ ACTIVE` status display.
   - **Master Action Pill**: Instant `[▶ ON]` / `[■ STOP]` toggle.
2. **Neon Laser Progress Bar**: 2px hairline real-time countdown progress indicator.
3. **Cyber Strip Segmented Presets**: One-click duration chips + custom modal input dialog.

---

## 📦 Quick Start & Portable Download

### Option 1: Download Standalone Executable (No Installation Required)
1. Download **[Lucid-v1.0.0-win64.zip](https://github.com/quinc-dev/lucid-keepawake/releases/download/v1.0.0/Lucid-v1.0.0-win64.zip)** from GitHub Releases.
2. Extract the archive anywhere on your system.
3. Double-click **`Lucid.exe`** to start immediately.

### Option 2: Try Live in Browser
Open the **[Lucid Web Simulator](https://quinc-dev.github.io/lucid-keepawake/)** to test the complete Cyber-HUD interface, 60 FPS laser interpolation, preset chips, and interactive controls directly in your web browser.

---

## 🎮 Controls & Shortcuts

| Action | Control |
|---|---|
| **Move Widget** | Left-click anywhere on the HUD background and drag |
| **Quick Infinite Awake** | Click `[ ∞ ]` chip or `[▶ ON]` button |
| **Start Preset Timer** | Click `[ 15m ]`, `[ 30m ]`, `[ 1h ]`, or `[ 2h ]` |
| **Custom Duration** | Click `[ min ]` → type duration (e.g., `45`, `90`, `1.5h`) → Enter |
| **Stop / Standby** | Click `[■ STOP]` button |
| **Context Menu** | Right-click anywhere on the widget for quick actions |
| **System Tray** | Click tray icon to show/hide widget; right-click for full menu |

---

## 🛡️ Security & Privacy Invariants

- **100% Offline Capable**: Zero telemetry, zero analytics, zero external dependencies required to run.
- **Zero Simulation**: Does not generate fake keyboard events or mouse jitters.
- **Native OS Execution Locks**: Uses official Windows kernel `SetThreadExecutionState` APIs.
- **Clean Background Exit**: Completely frees all system execution locks and cleans up memory upon exit.

---

## 📄 License

Copyright © 2026 **QuiNC**. All Rights Reserved.  
Distributed under the [QuiNC Proprietary End-User License Agreement](LICENSE). Unauthorized reverse-engineering, decompilation, or redistribution of source code is strictly prohibited.
