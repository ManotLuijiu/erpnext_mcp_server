"""
MCP Development Framework for Frappe/ERPNext

This module provides a standardized framework for developing MCP servers in Frappe/ERPNext,
inspired by the Doppio SPA development approach.

Features:
1. Development server on separate port (8080)
2. Production deployment integration
3. Hot-reloading during development
4. Consistent deployment pattern

Usage:
    # Development mode
    bench mcp-dev

    # Build for production
    bench mcp-build

    # Deploy to production
    bench mcp-deploy
"""

import importlib
import importlib.util
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import click
import frappe
from frappe.commands.utils import pass_context
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_dev")

# Global variables
DEV_PORT = 8080
PROD_PORT = 8100
MCP_SERVER_PROCESS = None
OBSERVER = None


class MCPDevConfig:
    """Configuration for MCP development"""

    def __init__(self, site: str, app_name: Optional[str] = None):
        """Initialize MCP development configuration

        Args:
            site: Frappe site name
            app_name: App name containing MCP server (auto-detected if None)
        """
        self.site = site
        self.bench_path = self._get_bench_path()
        self.site_path = os.path.join(self.bench_path, "sites", site)

        # Determine app name if not provided
        self.app_name = app_name or self._detect_mcp_app()

        if not self.app_name:
            raise ValueError("No MCP app found. Please specify app_name.")

        self.app_path = os.path.join(self.bench_path, "apps", self.app_name)

        # Configuration paths
        self.dev_config_path = os.path.join(self.site_path, "mcp_dev_config.json")

        # Load or create configuration
        self.config = self._load_or_create_config()

    def _get_bench_path(self) -> str:
        """Get bench path from Frappe"""
        return os.path.abspath(
            os.path.join(os.path.dirname(frappe.__file__), "..", "..")
        )

    def _detect_mcp_app(self) -> Optional[str]:
        """Detect app containing MCP server"""
        apps_path = os.path.join(self.bench_path, "apps")

        # Look for any app with mcp_server.py or server.py
        for app_name in os.listdir(apps_path):
            app_path = os.path.join(apps_path, app_name)

            if not os.path.isdir(app_path):
                continue

            # Check for common MCP server file patterns
            for filename in ["mcp_server.py", "server.py", "mcp/server.py"]:
                if os.path.exists(os.path.join(app_path, app_name, filename)):
                    return app_name

        return None

    def _load_or_create_config(self) -> Dict[str, Any]:
        """Load or create MCP development configuration"""
        if os.path.exists(self.dev_config_path):
            with open(self.dev_config_path, "r") as f:
                return json.load(f)

        # Default configuration
        default_config = {
            "app_name": self.app_name,
            "dev_port": DEV_PORT,
            "prod_port": PROD_PORT,
            "entry_point": f"{self.app_name}.mcp_server",
            "watched_paths": [
                f"{self.app_path}/{self.app_name}/**/*.py",
            ],
            "excluded_paths": [
                "**/__pycache__/**",
                "**/*.pyc",
                "**/.git/**",
            ],
            "auto_reload": True,
            "env_vars": {},
        }

        # Save default configuration
        with open(self.dev_config_path, "w") as f:
            json.dump(default_config, f, indent=4)

        return default_config

    def save_config(self):
        """Save configuration to file"""
        with open(self.dev_config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    def get_entry_point(self) -> Tuple[str, Optional[str]]:
        """Get server entry point module and object

        Returns:
            Tuple of (module_name, object_name)
        """
        entry_point = self.config.get("entry_point", f"{self.app_name}.mcp_server")

        if ":" in entry_point:
            module_name, object_name = entry_point.split(":", 1)
            return module_name, object_name

        return entry_point, None

    def get_watched_paths(self) -> List[str]:
        """Get paths to watch for changes

        Returns:
            List of path patterns to watch
        """
        return self.config.get("watched_paths", [])

    def get_excluded_paths(self) -> List[str]:
        """Get paths to exclude from watching

        Returns:
            List of path patterns to exclude
        """
        return self.config.get("excluded_paths", [])

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for MCP server

        Returns:
            Dict of environment variables
        """
        return self.config.get("env_vars", {})


class MCPFileHandler(FileSystemEventHandler):
    """Handler for file system events to reload MCP server"""

    def __init__(self, restart_func):
        """Initialize the file handler"""
        self.restart_func = restart_func
        self.last_event_time = 0
        self.debounce_seconds = 1.0  # Debounce time to avoid multiple reloads

    def on_any_event(self, event: FileSystemEvent):
        """Handle any file system event

        Args:
            event: The file system event
        """
        # Skip temporary files and directories
        if event.src_path.endswith(".pyc") or "__pycache__" in event.src_path:
            return

        # Debounce events to avoid multiple reloads
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_seconds:
            return

        self.last_event_time = current_time

        # Log the event
        logger.info(f"Detected change in {event.src_path}")

        # Restart the server
        self.restart_func()


def start_mcp_server(
    config: MCPDevConfig, port: int, dev_mode: bool = True
) -> subprocess.Popen:
    """Start the MCP server process

    Args:
        config: MCP development configuration
        port: Port to run the server on
        dev_mode: Whether to run in development mode

    Returns:
        Server process
    """
    # Get the entry point
    module_name, object_name = config.get_entry_point()

    # Build command
    cmd = [
        os.path.join(config.bench_path, "env", "bin", "python"),
        "-m",
        "frappe.utils.bench_helper",
        "--site",
        config.site,
        "mcp",
        "--port",
        str(port),
    ]

    if dev_mode:
        cmd.append("--dev")

    # Set environment variables
    env = os.environ.copy()
    env.update(config.get_env_vars())
    env["PYTHONPATH"] = config.bench_path

    # Start the process
    logger.info(f"Starting MCP server on port {port}")
    logger.info(f"Command: {' '.join(cmd)}")

    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )


def stop_mcp_server():
    """Stop the MCP server process"""
    global MCP_SERVER_PROCESS

    if MCP_SERVER_PROCESS:
        logger.info("Stopping MCP server")

        # Send SIGTERM to the process
        MCP_SERVER_PROCESS.terminate()

        # Wait for process to exit
        try:
            MCP_SERVER_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if not terminated
            logger.warning("MCP server did not terminate gracefully, force killing")
            MCP_SERVER_PROCESS.kill()

        MCP_SERVER_PROCESS = None


def restart_mcp_server(config: MCPDevConfig, port: int):
    """Restart the MCP server process

    Args:
        config: MCP development configuration
        port: Port to run the server on
    """
    global MCP_SERVER_PROCESS

    # Stop the server if running
    stop_mcp_server()

    # Start the server
    MCP_SERVER_PROCESS = start_mcp_server(config, port, dev_mode=True)

    logger.info(f"MCP server restarted on port {port}")

    # Start log streaming
    def log_stream_thread():
        if MCP_SERVER_PROCESS and MCP_SERVER_PROCESS.stdout:
            for line in iter(MCP_SERVER_PROCESS.stdout.readline, ""):
                sys.stdout.write(f"[MCP] {line}")
        if MCP_SERVER_PROCESS and MCP_SERVER_PROCESS.stderr:
            for line in iter(MCP_SERVER_PROCESS.stderr.readline, ""):
                sys.stderr.write(f"[MCP] {line}")

    import threading

    log_thread = threading.Thread(target=log_stream_thread)
    log_thread.daemon = True
    log_thread.start()


def setup_file_watcher(config: MCPDevConfig, restart_func):
    """Set up file watcher for auto-reloading

    Args:
        config: MCP development configuration
        restart_func: Function to call when files change
    """
    global OBSERVER

    # Stop existing observer if running
    if OBSERVER:
        OBSERVER.stop()
        OBSERVER.join()

    # Create a new observer
    OBSERVER = Observer()

    # Get paths to watch
    watched_paths = config.get_watched_paths()
    excluded_paths = config.get_excluded_paths()

    # Create handler
    handler = MCPFileHandler(restart_func)

    # Add watched paths
    for path_pattern in watched_paths:
        import glob

        # Get matching paths
        for path in glob.glob(path_pattern, recursive=True):
            if os.path.isdir(path):
                # Skip excluded paths
                if any(
                    os.path.normpath(path).startswith(os.path.normpath(excluded))
                    for excluded in excluded_paths
                ):
                    continue

                logger.info(f"Watching directory: {path}")
                OBSERVER.schedule(handler, path, recursive=True)

    # Start the observer
    OBSERVER.start()
    logger.info("File watcher started")


def cleanup():
    """Clean up resources when exiting"""
    global MCP_SERVER_PROCESS, OBSERVER

    # Stop the server
    stop_mcp_server()

    # Stop the observer
    if OBSERVER:
        OBSERVER.stop()
        OBSERVER.join()
        OBSERVER = None

    logger.info("Cleanup complete")


@click.command("mcp-dev")
@click.option("--port", default=DEV_PORT, help="Port to run development server on")
@click.option("--app", help="App name containing MCP server")
@click.option("--no-watch", is_flag=True, help="Disable file watching")
@pass_context
def mcp_dev_command(context, port, app, no_watch):
    """Run MCP server in development mode"""
    try:
        # Get site
        site = context.sites[0]

        # Initialize configuration
        config = MCPDevConfig(site, app_name=app)

        # Update port in configuration
        config.config["dev_port"] = port
        config.save_config()

        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the server
        def restart_func():
            restart_mcp_server(config, port)

        restart_func()

        # Set up file watcher if enabled
        if not no_watch and config.config.get("auto_reload", True):
            setup_file_watcher(config, restart_func)

        # Keep the process running
        while True:
            # Check if the server is still running
            if MCP_SERVER_PROCESS and MCP_SERVER_PROCESS.poll() is not None:
                logger.error("MCP server process terminated unexpectedly")
                restart_func()

            # Sleep to avoid high CPU usage
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup()

    except Exception as e:
        logger.exception(f"Error in MCP development server: {e}")
        cleanup()
        sys.exit(1)


@click.command("mcp-build")
@click.option("--app", help="App name containing MCP server")
@pass_context
def mcp_build_command(context, app):
    """Build MCP server for production"""
    try:
        # Get site
        site = context.sites[0]

        # Initialize configuration
        config = MCPDevConfig(site, app_name=app)

        # Ensure production port is set
        prod_port = config.config.get("prod_port", PROD_PORT)
        config.config["prod_port"] = prod_port
        config.save_config()

        # Run setup commands to prepare for production
        click.echo("Building MCP server for production...")

        # Configure NGINX
        subprocess.run(
            ["bench", "--site", site, "setup-mcp-nginx", "--port", str(prod_port)],
            check=True,
        )

        # Configure supervisor
        subprocess.run(
            ["bench", "--site", site, "setup-mcp-supervisor", "--port", str(prod_port)],
            check=True,
        )

        click.echo(f"MCP server built successfully for production on port {prod_port}")

        click.echo("\nTo deploy to production, run:")
        click.echo("  bench mcp-deploy")

    except Exception as e:
        logger.exception(f"Error building MCP server: {e}")
        sys.exit(1)


@click.command("mcp-deploy")
@click.option("--reload-nginx", is_flag=True, help="Reload NGINX after deployment")
@click.option(
    "--restart-supervisor", is_flag=True, help="Restart supervisor after deployment"
)
@pass_context
def mcp_deploy_command(context, reload_nginx, restart_supervisor):
    """Deploy MCP server to production"""
    try:
        # Get site
        site = context.sites[0]

        # Prompt for confirmation
        if not click.confirm(f"Deploy MCP server for site {site} to production?"):
            return

        click.echo("Deploying MCP server to production...")

        # Test NGINX configuration
        if reload_nginx:
            click.echo("Testing NGINX configuration...")
            subprocess.run(["sudo", "nginx", "-t"], check=True)

        # Reload NGINX if requested
        if reload_nginx:
            click.echo("Reloading NGINX...")
            subprocess.run(["sudo", "service", "nginx", "reload"], check=True)

        # Update supervisor if requested
        if restart_supervisor:
            click.echo("Updating supervisor...")
            subprocess.run(["sudo", "supervisorctl", "reread"], check=True)
            subprocess.run(["sudo", "supervisorctl", "update"], check=True)

            # Restart MCP server
            click.echo("Restarting MCP server...")
            subprocess.run(
                ["sudo", "supervisorctl", "restart", f"mcp-{site}"], check=True
            )

        click.echo("MCP server deployed successfully to production")

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Error deploying MCP server: {e}")
        sys.exit(1)


@click.command("mcp-config")
@click.option("--app", help="App name containing MCP server")
@click.option("--entry-point", help="Entry point module:object")
@click.option("--dev-port", type=int, help="Development port")
@click.option("--prod-port", type=int, help="Production port")
@click.option("--add-watch", help="Add path to watch")
@click.option("--remove-watch", help="Remove path from watch")
@click.option("--add-exclude", help="Add path to exclude")
@click.option("--remove-exclude", help="Remove path from exclude")
@click.option(
    "--set-env", nargs=2, multiple=True, help="Set environment variable (key value)"
)
@click.option("--unset-env", help="Unset environment variable")
@click.option("--auto-reload/--no-auto-reload", help="Enable/disable auto-reload")
@pass_context
def mcp_config_command(
    context,
    app,
    entry_point,
    dev_port,
    prod_port,
    add_watch,
    remove_watch,
    add_exclude,
    remove_exclude,
    set_env,
    unset_env,
    auto_reload,
):
    """Configure MCP development environment"""
    try:
        # Get site
        site = context.sites[0]

        # Initialize configuration
        config = MCPDevConfig(site, app_name=app)

        # Display current configuration if no options provided
        if not any(
            [
                entry_point,
                dev_port,
                prod_port,
                add_watch,
                remove_watch,
                add_exclude,
                remove_exclude,
                set_env,
                unset_env,
                auto_reload is not None,
            ]
        ):
            click.echo("Current MCP configuration:")
            click.echo(json.dumps(config.config, indent=4))
            return

        # Update configuration
        if entry_point:
            config.config["entry_point"] = entry_point

        if dev_port:
            config.config["dev_port"] = dev_port

        if prod_port:
            config.config["prod_port"] = prod_port

        if add_watch:
            watched_paths = config.config.get("watched_paths", [])
            if add_watch not in watched_paths:
                watched_paths.append(add_watch)
            config.config["watched_paths"] = watched_paths

        if remove_watch:
            watched_paths = config.config.get("watched_paths", [])
            if remove_watch in watched_paths:
                watched_paths.remove(remove_watch)
            config.config["watched_paths"] = watched_paths

        if add_exclude:
            excluded_paths = config.config.get("excluded_paths", [])
            if add_exclude not in excluded_paths:
                excluded_paths.append(add_exclude)
            config.config["excluded_paths"] = excluded_paths

        if remove_exclude:
            excluded_paths = config.config.get("excluded_paths", [])
            if remove_exclude in excluded_paths:
                excluded_paths.remove(remove_exclude)
            config.config["excluded_paths"] = excluded_paths

        if set_env:
            env_vars = config.config.get("env_vars", {})
            for key, value in set_env:
                env_vars[key] = value
            config.config["env_vars"] = env_vars

        if unset_env:
            env_vars = config.config.get("env_vars", {})
            if unset_env in env_vars:
                del env_vars[unset_env]
            config.config["env_vars"] = env_vars

        if auto_reload is not None:
            config.config["auto_reload"] = auto_reload

        # Save updated configuration
        config.save_config()

        click.echo("MCP configuration updated")
        click.echo(json.dumps(config.config, indent=4))

    except Exception as e:
        logger.exception(f"Error configuring MCP: {e}")
        sys.exit(1)


commands = [mcp_dev_command, mcp_build_command, mcp_deploy_command, mcp_config_command]
