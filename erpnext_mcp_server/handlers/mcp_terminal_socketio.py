import fcntl
import json
import logging
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import threading

import frappe
from socketio import Namespace

# Configure logging
logger = logging.getLogger(__name__)


class MCPTerminalNamespace(Namespace):
    """Socket.IO namespace for handling MCP Terminal connections"""

    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.terminals = {}  # Store active terminal sessions

    def on_connect(self, sid, environ):
        """Handle client connection"""
        logger.info(f"Client connected: {sid}")

    def on_disconnect(self, sid):
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {sid}")
        self.cleanup_terminal(sid)

    def on_mcp_register(self, sid, data):
        """Register a new terminal session"""
        session_id = data.get("session_id", "anonymous")
        rows = data.get("rows", 24)
        cols = data.get("cols", 80)

        logger.info(f"Registering terminal for {session_id}")

        # Start the MCP server process
        self.create_terminal(sid, rows, cols)

    def on_mcp_input(self, sid, data):
        """Handle terminal input from client"""
        if sid not in self.terminals:
            logger.warning(f"Input received for unknown terminal: {sid}")
            return

        terminal = self.terminals[sid]
        if not terminal["active"]:
            return

        try:
            # Write input to the MCP server process
            input_data = data.get("data", "")
            os.write(terminal["pty_master"], input_data.encode())
            logger.debug(f"Input sent to MCP server: {repr(input_data)}")
        except Exception as e:
            logger.error(f"Error sending input to MCP server: {e}")

    def on_mcp_resize(self, sid, data):
        """Handle terminal resize request"""
        if sid not in self.terminals:
            return

        terminal = self.terminals[sid]
        rows = data.get("rows", 24)
        cols = data.get("cols", 80)

        try:
            # Update terminal size
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(terminal["pty_master"], termios.TIOCSWINSZ, winsize)
            logger.debug(f"Terminal resized to {rows}x{cols}")
        except Exception as e:
            logger.error(f"Error resizing terminal: {e}")

    def create_terminal(self, sid, rows, cols):
        """Create a new terminal session with MCP server process"""
        # Check if MCP server binary exists
        mcp_server_path = frappe.get_app_path("erpnext_mcp_server", "bin", "mcp_server")
        if not os.path.exists(mcp_server_path):
            logger.error(f"MCP server binary not found at {mcp_server_path}")
            self.emit(
                "mcp:output",
                f"\r\n\x1b[31mError: MCP server binary not found\x1b[0m\r\n",
                room=sid,
            )
            return

        # Create PTY
        master, slave = pty.openpty()

        # Set terminal size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master, termios.TIOCSWINSZ, winsize)

        # Configure non-blocking reads
        fl = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # Start MCP server process
        cmd = [mcp_server_path]

        try:
            process = subprocess.Popen(
                cmd,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                universal_newlines=False,
                shell=False,
                preexec_fn=os.setsid,
            )

            # Close slave fd as it's used by the child process
            os.close(slave)

            # Store terminal data
            self.terminals[sid] = {
                "process": process,
                "pty_master": master,
                "active": True,
                "output_thread": None,
            }

            # Start output listener
            self.terminals[sid]["output_thread"] = threading.Thread(
                target=self.read_output, args=(sid, master), daemon=True
            )
            self.terminals[sid]["output_thread"].start()

            logger.info(f"Created terminal session for {sid}, PID: {process.pid}")

        except Exception as e:
            logger.error(f"Error creating terminal: {e}")
            self.emit(
                "mcp:output",
                f"\r\n\x1b[31mError starting MCP server: {str(e)}\x1b[0m\r\n",
                room=sid,
            )
            os.close(master)
            os.close(slave)

    def read_output(self, sid, fd):
        """Read output from MCP server process and send to client"""
        try:
            buffer_size = 4096

            while sid in self.terminals and self.terminals[sid]["active"]:
                try:
                    # Try to read from fd (non-blocking)
                    r, _, _ = select.select([fd], [], [], 0.1)
                    if fd in r:
                        output = os.read(fd, buffer_size)
                        if output:
                            # Send output to client
                            self.emit(
                                "mcp:output",
                                output.decode("utf-8", errors="replace"),
                                room=sid,
                            )
                        else:
                            # EOF - process ended
                            break
                except (OSError, IOError) as e:
                    # Handle broken pipe or other read errors
                    logger.error(f"Error reading from process: {e}")
                    break

                # Check if process is still running
                if sid in self.terminals:
                    try:
                        if self.terminals[sid]["process"].poll() is not None:
                            # Process has ended
                            logger.info(f"MCP server process ended for {sid}")
                            break
                    except Exception:
                        break

            # Process ended, clean up
            self.cleanup_terminal(sid)

        except Exception as e:
            logger.error(f"Error in output reader thread: {e}")
            self.cleanup_terminal(sid)

    def cleanup_terminal(self, sid):
        """Clean up terminal session resources"""
        if sid in self.terminals:
            terminal = self.terminals[sid]
            terminal["active"] = False

            # Terminate process if still running
            if terminal["process"] and terminal["process"].poll() is None:
                try:
                    os.killpg(os.getpgid(terminal["process"].pid), signal.SIGTERM)
                    terminal["process"].wait(timeout=1)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(os.getpgid(terminal["process"].pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            # Close FD
            try:
                os.close(terminal["pty_master"])
            except OSError:
                pass

            # Clean up
            del self.terminals[sid]
            logger.info(f"Cleaned up terminal session for {sid}")


# Hook for Frappe to register the socket.io namespace
def get_socketio_namespaces():
    """Return socket.io namespaces for Frappe to register"""
    return {"/": MCPTerminalNamespace("/")}
