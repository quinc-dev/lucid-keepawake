# Task Plan: Lucid v1.1.0 — OLED Blackout, MCP Server, Context Menu Fix & Ship

Status: Complete

## Phase 1: Context Menu Bugfix & UI Refinement
- [x] Fix context menu sticking when clicking "Hide to Tray" in `ui/widget.py`
- [x] Add `<FocusOut>` auto-dismiss handler for context menu
- [x] Refine context menu items (minimalist Titanium/Zinc aesthetic, remove cluttered emojis)

## Phase 2: OLED Blackout Curtain Module (`core/curtain.py`)
- [x] Implement multi-monitor `#000000` TopMost blackout window
- [x] Implement subtle 0.4s lens fade-in transition before complete black
- [x] Implement instant wake handlers (mouse movement >50px, keyboard key, programmatic wake)
- [x] Integrate with `core/awake.py` to maintain `ES_SYSTEM_REQUIRED` (keep CPU/GPU active)

## Phase 3: Local IPC Server & CLI Bridge (`core/ipc.py` & `lucid.py`)
- [x] Implement lightweight localhost IPC server in `core/ipc.py`
- [x] Add CLI flags to `lucid.py` (`--blackout`, `--wake`, `--status`, `--awake`, `--stop`)
- [x] Integrate IPC client for CLI and MCP communication

## Phase 4: Lucid MCP Server (`mcp_server.py`) & Config
- [x] Create standalone stdio JSON-RPC MCP server (`mcp_server.py`) exposing all 6 Lucid tools
- [x] Test MCP server stdio interaction (`tools/list`, `tools/call`)
- [x] Register `lucid` MCP server into `C:\Users\Admin\.gemini\config\mcp_config.json`

## Phase 5: Landing Page Update (`index.html`)
- [x] Update version to v1.1.0 and release date
- [x] Add feature card for OLED Blackout & 100% GPU Throughput
- [x] Add feature card for MCP & Agent Native integration
- [x] Update download link and SHA-256 placeholder

## Phase 6: DevGuard Verification & `/ship` Packaging
- [x] Run syntax check (`py_compile`) across all modified modules
- [x] Compile release binary with PyInstaller (`python -m PyInstaller Lucid.spec --noconfirm`)
- [x] Verify build timestamp on `dist/Lucid.exe`
- [x] Package `dist/Lucid-v1.1.0-win64.zip` and generate SHA-256 hash
- [x] Update `CHANGELOG.md` with v1.1.0 release notes
- [x] Final verification and delivery walkthrough
