"""
core/ipc.py — Lightweight Localhost IPC Server & Client for Lucid.
Enables CLI flags (--blackout, --wake, --status) and Lucid MCP server
to query and control the running Lucid instance over 127.0.0.1.
"""

import socket
import threading
import json
import os
import tempfile
import logging
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)

IPC_PORT_DEFAULT = 49152
IPC_HOST = "127.0.0.1"
LOCKFILE_PATH = os.path.join(tempfile.gettempdir(), "lucid_ipc.json")


def get_active_ipc_port() -> Optional[int]:
    """Read active IPC port from lockfile if running process is alive."""
    if not os.path.exists(LOCKFILE_PATH):
        return None
    try:
        with open(LOCKFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("port")
    except Exception:
        return None


def send_ipc_command(action: str, params: Optional[Dict[str, Any]] = None, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Send an IPC command to the active Lucid instance.
    Returns response dict on success, None if Lucid is not running or unreachable.
    """
    port = get_active_ipc_port()
    if not port:
        return None

    payload = {"action": action}
    if params:
        payload.update(params)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((IPC_HOST, port))
            message = json.dumps(payload) + "\n"
            s.sendall(message.encode("utf-8"))

            buffer = ""
            while "\n" not in buffer:
                chunk = s.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk

            if buffer:
                return json.loads(buffer.strip())
    except Exception as e:
        logger.debug(f"IPC send failed: {e}")
        return None
    return None


class IpcServer:
    """
    Background socket listener that executes dispatched callbacks on Lucid's main loop.
    """

    def __init__(self, command_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        self._handler = command_handler
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._active_port: Optional[int] = None

    def start(self) -> bool:
        """Bind and start listening on localhost with port fallback."""
        port = IPC_PORT_DEFAULT
        max_attempts = 5

        for attempt in range(max_attempts):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((IPC_HOST, port + attempt))
                s.listen(5)
                self._server_socket = s
                self._active_port = port + attempt
                break
            except Exception as e:
                logger.debug(f"IPC port {port + attempt} in use: {e}")
                continue

        if not self._server_socket or not self._active_port:
            logger.warning("Failed to bind IPC socket.")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, name="lucid-ipc", daemon=True)
        self._thread.start()

        # Write lockfile
        try:
            with open(LOCKFILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"port": self._active_port, "pid": os.getpid()}, f)
        except Exception as e:
            logger.warning(f"Failed to write IPC lockfile: {e}")

        logger.info(f"Lucid IPC server active on 127.0.0.1:{self._active_port}")
        return True

    def stop(self):
        """Shutdown IPC server and clean up lockfile."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if os.path.exists(LOCKFILE_PATH):
            try:
                os.remove(LOCKFILE_PATH)
            except Exception:
                pass

    def _listen_loop(self):
        while self._running and self._server_socket:
            try:
                client_sock, _ = self._server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock,),
                    daemon=True,
                )
                client_thread.start()
            except Exception:
                break

    def _handle_client(self, client_sock: socket.socket):
        try:
            client_sock.settimeout(3.0)
            buffer = ""
            while "\n" not in buffer:
                chunk = client_sock.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk

            if buffer.strip():
                req = json.loads(buffer.strip())
                action = req.get("action", "")
                res = self._handler(action, req)
                response_str = json.dumps(res) + "\n"
                client_sock.sendall(response_str.encode("utf-8"))
        except Exception as e:
            logger.debug(f"IPC client handle error: {e}")
            try:
                err_res = json.dumps({"status": "error", "error": str(e)}) + "\n"
                client_sock.sendall(err_res.encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
