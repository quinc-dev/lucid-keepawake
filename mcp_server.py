"""
mcp_server.py — Autonomous Model Context Protocol (MCP) Server for Lucid.
Enables AI Agents (Antigravity, Cursor, Claude, etc.) to query status,
engage OLED blackout curtains for GPU vibecoding, and wake the screen via MCP tools.
"""

import sys
import json
import os
import subprocess
import time
import logging

# Ensure project root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.ipc import send_ipc_command, get_active_ipc_port

logging.basicConfig(
    filename=os.path.join(os.environ.get("TEMP", "."), "lucid_mcp.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def ensure_lucid_running(timeout: float = 3.0) -> bool:
    """Launch Lucid in the background if it is not currently active."""
    if get_active_ipc_port() is not None:
        return True

    lucid_script = os.path.join(PROJECT_DIR, "lucid.py")
    try:
        # Launch with pythonw or python detached
        python_exe = sys.executable
        if python_exe.endswith("python.exe"):
            pythonw = python_exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw):
                python_exe = pythonw

        subprocess.Popen(
            [python_exe, lucid_script],
            cwd=PROJECT_DIR,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True,
        )

        start = time.time()
        while time.time() - start < timeout:
            if get_active_ipc_port() is not None:
                return True
            time.sleep(0.15)
    except Exception as e:
        logging.error(f"Failed to launch Lucid: {e}")
    return False


TOOLS_DEFINITIONS = [
    {
        "name": "lucid_status",
        "description": "Get active Lucid keep-awake status, timer remaining, and OLED blackout curtain state.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "lucid_blackout",
        "description": "Engage OLED Blackout Curtain. Completely turns off OLED subpixels (#000000, 0 nits, 0% burn-in, lowest display power) while keeping CPU & GPU running at 100% throughput for AI tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "lucid_wake",
        "description": "Wake the screen up immediately and dismiss the OLED Blackout Curtain (call this when AI agent completes a task or requests user review).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "lucid_set_awake",
        "description": "Set keep-awake state with optional duration in minutes. Use 0 for infinite keep-awake.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "Duration in minutes to keep machine awake. 0 for infinite.",
                    "default": 0,
                }
            },
            "required": [],
        },
    },
    {
        "name": "lucid_stop",
        "description": "Stop all keep-awake modes and return machine to normal power management.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "lucid_toggle_hud",
        "description": "Show, hide, or toggle the Lucid Cyber-HUD widget on screen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["toggle", "show", "hide"],
                    "description": "Action to perform on the HUD capsule.",
                    "default": "toggle",
                }
            },
            "required": [],
        },
    },
]


def handle_tool_call(name: str, args: dict) -> dict:
    if name == "lucid_status":
        res = send_ipc_command("status")
        if not res:
            return {"content": [{"type": "text", "text": "Lucid is not currently running. You can invoke lucid_blackout or lucid_set_awake to start it."}]}
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif name == "lucid_blackout":
        ensure_lucid_running()
        res = send_ipc_command("blackout")
        if res and res.get("status") == "ok":
            return {"content": [{"type": "text", "text": "OLED Blackout Curtain successfully engaged. OLED subpixels are turned off (0 nits, 0% burn-in). CPU & GPU are kept at 100% throughput."}]}
        return {"isError": True, "content": [{"type": "text", "text": f"Failed to engage blackout: {res}"}]}

    elif name == "lucid_wake":
        res = send_ipc_command("wake")
        if res and res.get("status") == "ok":
            return {"content": [{"type": "text", "text": "Screen awakened successfully. OLED Blackout Curtain dismissed."}]}
        return {"content": [{"type": "text", "text": "Lucid instance is not currently active, screen should be at default system state."}]}

    elif name == "lucid_set_awake":
        ensure_lucid_running()
        minutes = args.get("minutes", 0)
        seconds = int(minutes * 60) if minutes and minutes > 0 else 0
        res = send_ipc_command("awake", {"duration": seconds})
        if res and res.get("status") == "ok":
            desc = f"{minutes} minutes" if minutes > 0 else "infinite duration"
            return {"content": [{"type": "text", "text": f"Lucid keep-awake activated for {desc}."}]}
        return {"isError": True, "content": [{"type": "text", "text": f"Failed to set awake: {res}"}]}

    elif name == "lucid_stop":
        res = send_ipc_command("stop")
        if res and res.get("status") == "ok":
            return {"content": [{"type": "text", "text": "Keep-awake stopped. System returned to standby."}]}
        return {"content": [{"type": "text", "text": "Lucid was not running or already in standby."}]}

    elif name == "lucid_toggle_hud":
        ensure_lucid_running()
        act = args.get("action", "toggle")
        cmd_map = {"show": "show_hud", "hide": "hide_hud", "toggle": "toggle_hud"}
        cmd = cmd_map.get(act, "toggle_hud")
        res = send_ipc_command(cmd)
        if res and res.get("status") == "ok":
            return {"content": [{"type": "text", "text": f"Lucid HUD action '{act}' executed successfully."}]}
        return {"isError": True, "content": [{"type": "text", "text": f"Failed to perform HUD action: {res}"}]}

    return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


def main():
    """Stdio JSON-RPC loop adhering to Model Context Protocol specification."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            msg = json.loads(line)
            msg_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params", {})

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": "lucid-mcp",
                            "version": "1.1.0",
                        },
                    },
                }
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            elif method == "notifications/initialized":
                pass  # Client confirmation, no response required

            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": TOOLS_DEFINITIONS,
                    },
                }
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                result = handle_tool_call(tool_name, tool_args)
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result,
                }
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            elif method == "ping":
                res = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            else:
                if msg_id is not None:
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }
                    sys.stdout.write(json.dumps(res) + "\n")
                    sys.stdout.flush()

        except Exception as e:
            logging.error(f"Error in MCP main loop: {e}")


if __name__ == "__main__":
    main()
