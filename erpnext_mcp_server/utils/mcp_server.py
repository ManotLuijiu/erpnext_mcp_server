import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import frappe

logger = logging.getLogger(__name__)


def setup_logging():
    """Set up logging"""
    log_level = os.environ.get("MCP_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_mcp_server_path():
    """Get path to MCP server binary"""
    app_path = frappe.get_app_path("erpnext_mcp_server")
    mcp_server_path = os.path.join(app_path, "bin", "mcp_server")

    # Check if file exists
    if not os.path.exists(mcp_server_path):
        logger.error(f"MCP server binary not found at {mcp_server_path}")
        return None

    # Ensure executable permission
    if not os.access(mcp_server_path, os.X_OK):
        logger.warning(
            f"MCP server binary is not executable, attempting to set permission"
        )
        try:
            os.chmod(mcp_server_path, 0o755)
        except Exception as e:
            logger.error(f"Failed to set executable permission: {e}")
            return None

    return mcp_server_path


def start_mcp_server():
    """Start the MCP server process"""
    mcp_server_path = get_mcp_server_path()
    if not mcp_server_path:
        return False

    # Get log directory
    log_dir = os.path.join(frappe.get_site_path(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "mcp_server.log")

    # Build command
    cmd = [mcp_server_path]

    try:
        # Start MCP server process
        with open(log_file, "a") as f:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=f,
                stderr=f,
                universal_newlines=True,
                shell=False,
                preexec_fn=os.setsid,
            )

        # Write PID file
        pid_file = os.path.join(frappe.get_site_path(), "mcp_server.pid")
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        logger.info(f"Started MCP server with PID {process.pid}")
        return True

    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return False


def stop_mcp_server():
    """Stop the MCP server process"""
    pid_file = os.path.join(frappe.get_site_path(), "mcp_server.pid")

    if not os.path.exists(pid_file):
        logger.warning("MCP server PID file not found")
        return False

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Send SIGTERM to process group
        os.killpg(os.getpgid(pid), signal.SIGTERM)

        # Wait for process to terminate
        for _ in range(10):
            try:
                os.kill(pid, 0)  # Check if process exists
                time.sleep(0.5)
            except OSError:
                break
        else:
            # Force kill if still running
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass

        # Remove PID file
        os.remove(pid_file)
        logger.info(f"Stopped MCP server with PID {pid}")
        return True

    except (OSError, ProcessLookupError) as e:
        logger.error(f"Failed to stop MCP server: {e}")
        # Remove PID file if process doesn't exist
        try:
            os.remove(pid_file)
        except OSError:
            pass
        return False


def check_mcp_server():
    """Check if MCP server is running"""
    pid_file = os.path.join(frappe.get_site_path(), "mcp_server.pid")

    if not os.path.exists(pid_file):
        return False

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, ValueError):
        # Process doesn't exist or invalid PID
        try:
            os.remove(pid_file)
        except OSError:
            pass
        return False


def main():
    """Main entry point"""
    setup_logging()

    parser = argparse.ArgumentParser(description="MCP Server management script")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Action to perform",
    )

    args = parser.parse_args()

    if args.action == "start":
        if check_mcp_server():
            logger.info("MCP server is already running")
            sys.exit(0)

        if start_mcp_server():
            logger.info("MCP server started successfully")
            sys.exit(0)
        else:
            logger.error("Failed to start MCP server")
            sys.exit(1)

    elif args.action == "stop":
        if not check_mcp_server():
            logger.info("MCP server is not running")
            sys.exit(0)

        if stop_mcp_server():
            logger.info("MCP server stopped successfully")
            sys.exit(0)
        else:
            logger.error("Failed to stop MCP server")
            sys.exit(1)

    elif args.action == "restart":
        if check_mcp_server():
            stop_mcp_server()

        if start_mcp_server():
            logger.info("MCP server restarted successfully")
            sys.exit(0)
        else:
            logger.error("Failed to restart MCP server")
            sys.exit(1)

    elif args.action == "status":
        if check_mcp_server():
            logger.info("MCP server is running")
            sys.exit(0)
        else:
            logger.info("MCP server is not running")
            sys.exit(1)


if __name__ == "__main__":
    main()
