# Technical Findings & Invariants: Lucid

## Architectural Discoveries & Gotchas
- **Tkinter Context Menu Ghosting**: On Windows, calling `self.withdraw()` while a `tk.Menu` popup is open leaves the native Win32 popup window hanging on the desktop. The fix requires explicitly calling `menu.unpost()` and `menu.destroy()` inside the command handler before hiding the widget, and binding `<FocusOut>` to auto-dismiss.
- **OLED vs GPU Power States**: Turning off display hardware via `SC_MONITORPOWER` (2) causes Nvidia Optimus and Windows Display Driver to drop GPU PCIe performance state and break remote desktop capture. A pure `#000000` TopMost fullscreen window turns off all OLED subpixels (0 nits, 0 burn-in) while keeping the display controller active so CUDA/PyTorch/NVENC runs at 100% throughput.
- **Win32 Execution State**: Must maintain `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` during Blackout so the system does not enter Modern Standby while the user is away.
- **MCP Server Protocol**: Fast, zero-dependency stdio JSON-RPC MCP server allows Antigravity and external agent harnesses to query status, trigger blackout, and wake the screen seamlessly.
