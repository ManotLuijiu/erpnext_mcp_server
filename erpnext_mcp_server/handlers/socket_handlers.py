import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback

import frappe

# Global variables to manage MCP process
mcp_processes = {}  # Store processes by user

print(f"mcp_processes {mcp_processes}")


@frappe.whitelist()
def start_test_echo_process():
    """Start a test echo process that clearly shows output"""
    try:
        user = frappe.session.user
        print(f"Starting test echo process for user {user}")

        # Kill any existing process
        if user in mcp_processes and mcp_processes[user].get("process"):
            try:
                process = mcp_processes[user]["process"]
                process.terminate()
                process.wait(timeout=2)
            except:
                pass

        # Create a simple test script
        script_content = """
import sys
import time

print("===== TEST ECHO SCRIPT STARTED =====")
sys.stdout.flush()

# Send 5 initial messages
for i in range(5):
    print(f"Initial message {i+1}")
    sys.stdout.flush()
    time.sleep(0.5)

print("Ready for commands...")
sys.stdout.flush()

while True:
    try:
        command = input()
        print(f"ECHO: You entered: {command}")
        sys.stdout.flush()
        
        # Special commands
        if command.lower() == "test":
            for i in range(3):
                print(f"Test output line {i+1}")
                sys.stdout.flush()
                time.sleep(0.5)
        elif command.lower() in ['exit', 'quit']:
            print("Exiting test script")
            sys.stdout.flush()
            break
    except EOFError:
        print("Received EOF, exiting")
        sys.stdout.flush()
        break
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()

print("===== TEST ECHO SCRIPT ENDED =====")
sys.stdout.flush()
"""

        # Create a temporary script file
        script_path = os.path.join(
            frappe.get_site_path("private", "files"), "mcp_echo_test.py"
        )
        with open(script_path, "w") as f:
            f.write(script_content)

        print(f"Created test script at {script_path}")
        os.chmod(script_path, 0o755)

        # Start the process with the test script
        mcp_command = [sys.executable, script_path]
        print(f"Executing command: {' '.join(mcp_command)}")

        # Start the process
        process = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        print(f"Process started with PID {process.pid}")

        # Store the process
        mcp_processes[user] = {"process": process, "stop_thread": False}

        # Start output reader thread
        output_thread = threading.Thread(target=read_mcp_output, args=(user,))
        output_thread.daemon = True
        output_thread.start()

        print(f"Output reader thread started")

        # Send direct message to confirm
        frappe.publish_realtime(
            "mcp_terminal_output",
            "\r\n[Direct message] Test echo process started\r\n",
            user=user,
        )

        return {"success": True, "message": "Test echo process started"}

    except Exception as e:
        error_msg = str(e)
        print(f"Error starting test echo process: {error_msg}")
        traceback.print_exc()
        return {"success": False, "error": error_msg}


@frappe.whitelist()
def test_realtime_output():
    """Test if realtime output works properly"""
    try:
        user = frappe.session.user

        # Send a series of test messages
        for i in range(5):
            frappe.publish_realtime(
                "mcp_terminal_output", f"\r\nTest message {i+1}\r\n", user=user
            )
            time.sleep(0.5)  # Small delay between messages

        return {"success": True, "message": "Sent 5 test messages"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def start_mcp_process_api(user):
    """Start the MCP server process - API method"""
    try:
        # user = frappe.session.user
        print(f"Starting MCP process for user {user}")

        # Kill any existing process for this user
        if user in mcp_processes and mcp_processes[user].get("process"):
            try:
                print(f"Killing existing process for user {user}")
                process = mcp_processes[user]["process"]
                process.terminate()
                process.wait(timeout=2)
            except Exception as e:
                print(f"Error terminating old process: {e}")

        # Create a simple test script in a temporary file
        # This is the most reliable way to ensure the script runs
        script_content = """
import sys
import time

print("MCP Server started!")
sys.stdout.flush()

print("Ready for commands...")
sys.stdout.flush()

while True:
    try:
        command = input()
        print(f"You entered: {command}")
        sys.stdout.flush()
        
        # If the command is exit, then exit
        if command.lower() in ['exit', 'quit']:
            print("Exiting MCP Server")
            sys.stdout.flush()
            break
    except EOFError:
        print("Received EOF, exiting")
        sys.stdout.flush()
        break
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()

print("MCP Server shut down")
sys.stdout.flush()
"""

        # Create a temporary script file
        script_path = os.path.join(
            frappe.get_site_path("private", "files"), "mcp_test_script.py"
        )
        with open(script_path, "w") as f:
            f.write(script_content)

        print(f"Created test script at {script_path}")

        # Very simple test command for debugging
        # mcp_command = [
        #     sys.executable,
        #     "-c",
        #     'import sys; print("MCP Server started!"); sys.stdout.flush(); '
        #     "while True: "
        #     "    try: "
        #     '        cmd = input(); print(f"Echo: {cmd}"); sys.stdout.flush(); '
        #     "    except EOFError: break "
        #     '    except Exception as e: print(f"Error: {e}"); sys.stdout.flush()',
        # ]

        mcp_command = [sys.executable, script_path]
        print(f"Executing command: {''.join(mcp_command)}")

        # Start the process
        process = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            bufsize=0,
        )

        print(f"Process started with PID {process.pid}")

        # Store the process
        mcp_processes[user] = {"process": process, "stop_thread": False}

        # Start output reader thread with safe error handling
        output_thread = threading.Thread(target=safe_read_mcp_output, args=(user,))
        output_thread.daemon = True
        output_thread.start()

        print(f"Output reader thread started {output_thread}")

        # Wait a moment to ensure process starts
        time.sleep(1)

        # Check if process is still running
        if process.poll() is not None:
            exit_code = process.poll()
            error_msg = f"Process exited immediately with code {exit_code}"
            print(f"error_msg {error_msg}")

            # Try to read any stderr output
            stdout_data, _ = process.communicate()
            if stdout_data:
                print(
                    f"Process output: {stdout_data.decode('utf-8', errors='replace')}"
                )
            return {"success": False, "error": error_msg}

        print("MCP process started successfully")
        return {"success": True, "message": "MCP Server started successfully"}

    except Exception as e:
        error_msg = str(e)
        # Print to stdout for debugging
        print(f"Error starting MCP process: {str(e)}")
        traceback.print_exc()

        # Try direct output to the client
        try:
            frappe.publish_realtime(
                "mcp_terminal_output",
                f"Error starting MCP Server: {str(e)}\r\n",
                user=frappe.session.user,
            )
        except:
            pass

        return {"success": False, "error": str(e)}


def safe_read_mcp_output(user):
    """Wrapper function with additional error handling"""
    try:
        read_mcp_output(user)
    except Exception as e:
        # Print to stdout for debugging
        print(f"Error in read_mcp_output: {str(e)}")
        traceback.print_exc()

        # Try direct output to the client
        try:
            frappe.publish_realtime(
                "mcp_terminal_output",
                f"\r\nError in output reader: {str(e)}\r\n",
                user=user,
            )
        except:
            pass


@frappe.whitelist()
def send_terminal_input(command):
    """Send input to the MCP process - API method"""
    user = frappe.session.user
    print(f"send_terminal_input called by {user} with command: {command}")

    try:
        # Echo the command back directly via realtime (for debugging)
        frappe.publish_realtime(
            "mcp_terminal_output", f"\r\n> {command}\r\n", user=user
        )

        # Check if process exists
        if user not in mcp_processes:
            print(f"No MCP process dictionary entry for user {user}")
            return {"success": False, "error": "MCP Server not running"}

        process = mcp_processes[user].get("process")
        if process is None:
            print(f"MCP process object is None for user {user}")
            return {"success": False, "error": "MCP Server not running"}

        # Check if process is still running
        if process.poll() is not None:
            print(f"MCP process terminated with exit code {process.poll()}")
            mcp_processes[user]["process"] = None
            return {"success": False, "error": "MCP Server terminated"}

        # Send command to process
        try:
            print(f"Sending command to process: {command}")
            process.stdin.write((command + "\n").encode("utf-8"))
            process.stdin.flush()
            print("Command sent successfully")
            return {"success": True}
        except Exception as e:
            error_msg = str(e)
            print(f"Error writing to stdin: {error_msg}")
            return {"success": False, "error": f"Failed to send command: {error_msg}"}
    except Exception as e:
        error_msg = str(e)
        print(f"Error in send_terminal_input: {error_msg}")
        traceback.print_exc()
        return {"success": False, "error": error_msg}

    # try:
    #     user = frappe.session.user

    #     # Check if process exists
    #     if user not in mcp_processes or mcp_processes[user].get("process") is None:
    #         return {"success": False, "error": "MCP Server not running"}

    #     process = mcp_processes[user]["process"]

    #     # Send command to process
    #     if process and process.poll() is None:
    #         try:
    #             process.stdin.write((command + "\n").encode("utf-8"))
    #             process.stdin.flush()
    #             return {"success": True}
    #         except Exception as e:
    #             return {"success": False, "error": f"Failed to send command: {str(e)}"}
    #     else:
    #         return {
    #             "success": False,
    #             "error": "Process not available or has terminated",
    #         }

    # except Exception as e:
    #     print(f"Error sending command to MCP: {str(e)}")
    #     frappe.log_error(f"Error sending command to MCP: {str(e)}")
    #     traceback.print_exc()
    #     return {"success": False, "error": str(e)}


def handle_terminal_input(user, message):
    """Handle terminal input from the client"""
    if not user:
        return

    # Start MCP process if not already running
    if user not in mcp_processes or mcp_processes[user]["process"] is None:
        start_mcp_process(user)

    # Send command to the process
    try:
        process = mcp_processes[user]["process"]
        command = message.get("command", "")

        if process and command:
            process.stdin.write((command + "\n").encode("utf-8"))
            process.stdin.flush()
    except Exception as e:
        frappe.log_error(f"Error sending command to MCP: {str(e)}")
        frappe.publish_realtime(
            "mcp_terminal_output", f"\r\nError: {str(e)}\r\n", user=user
        )


@frappe.whitelist()
def start_mcp_process(user):
    """Start an MCP process for a user"""
    try:
        # Simple test command
        mcp_command = [
            "python",
            frappe.get_app_path("erpnext_mcp_server", "api", "mcp_server.py"),
        ]

        # Start the process
        process = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            bufsize=0,
        )

        # Store the process
        mcp_processes[user] = {"process": process, "stop_thread": False}

        # Start output reader thread
        output_thread = threading.Thread(target=read_mcp_output, args=(user,))
        output_thread.daemon = True
        output_thread.start()

        frappe.publish_realtime(
            "mcp_terminal_output", f"MCP Server started successfully.\r\n", user=user
        )
    except Exception as e:
        frappe.log_error(f"Error starting MCP process: {str(e)}")
        frappe.publish_realtime(
            "mcp_terminal_output", f"Error starting MCP Server: {str(e)}\r\n", user=user
        )


def read_mcp_output(user):
    """Read output from MCP process and send to client"""
    print(f"Starting read_mcp_output for user {user}")

    if user not in mcp_processes:
        print(f"No MCP process found for user {user}")
        return

    # process = mcp_processes[user]["process"]
    process = mcp_processes[user].get("process")
    if not process:
        print(f"Process object is None for user {user}")
        return

    print(f"Reading output for process PID {process.pid}")

    # Send initial confirmation message directly
    frappe.publish_realtime(
        "mcp_terminal_output", "\r\n*** Output streaming started ***\r\n", user=user
    )

    try:
        # Use a simpler line-by-line reading approach
        for line in iter(process.stdout.readline, b""):
            if mcp_processes[user].get("stop_thread", True):
                print("Stop thread flag set, exiting reader loop")
                break

            decoded_line = line.decode("utf-8", errors="replace")
            print(f"Process output: {decoded_line.strip()}")

            # Send to client
            frappe.publish_realtime("mcp_terminal_output", decoded_line, user=user)

        # If we're here, the process has ended
        print("Process output ended")

    except Exception as e:
        print(f"Error in output reader: {str(e)}")
        traceback.print_exc()

    # Process has ended or errored
    try:
        if process and process.poll() is not None:
            exit_code = process.poll()
            print(f"MCP process exited with code {exit_code}")

            frappe.publish_realtime(
                "mcp_terminal_output",
                f"\r\n*** MCP Server exited with code {exit_code} ***\r\n",
                user=user,
            )

            mcp_processes[user]["process"] = None
    except Exception as e:
        print(f"Error handling process exit: {e}")
        traceback.print_exc()

    # while (
    #     process
    #     and process.poll() is None
    #     and not mcp_processes[user].get("stop_thread", True)
    # ):
    #     try:
    #         # Read output a byte at a time for responsive terminal
    #         byte = process.stdout.read(1)
    #         if byte:
    #             # Send to the client
    #             char = byte.decode("utf-8", errors="replace")
    #             frappe.publish_realtime("mcp_terminal_output", char, user=user)
    #         else:
    #             # Process has ended output
    #             break
    #     except Exception as e:
    #         frappe.log_error(f"Error reading MCP output: {str(e)}")
    #         break

    # If we're here, the process ended or errored
    # try:
    #     if process and process.poll() is not None:
    #         exit_code = process.poll()
    #         print(f"MCP process exited with code {exit_code}")

    #         # Try to notify via realtime
    #         try:
    #             frappe.publish_realtime(
    #                 "mcp_terminal_output",
    #                 f"\r\nMCP Server exited with code {exit_code}\r\n",
    #                 user=user,
    #             )
    #         except:
    #             pass
    #         mcp_processes[user]["process"] = None
    # except Exception as e:
    #     print(f"Error handling process exit: {e}")
    #     traceback.print_exc()


@frappe.whitelist()
def stop_mcp_process(user):
    """Stop the MCP process for a user"""
    # user = frappe.session.user
    if user not in mcp_processes:
        return

    # Signal the thread to stop
    mcp_processes[user]["stop_thread"] = True

    # Terminate the process
    try:
        process = mcp_processes[user]["process"]
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            mcp_processes[user]["process"] = None

            return {"success": True}
    except Exception as e:
        frappe.log_error(f"Error stopping MCP process: {str(e)}")

    return {"success": False}


# Event handlers for socket events
def cleanup_on_logout():
    """Stop MCP process when user logs out"""
    user = frappe.session.user
    stop_mcp_process(user)


def cleanup_all_processes():
    """Stop all MCP processes on server exit"""
    for user in list(mcp_processes.keys()):
        stop_mcp_process(user)


# Handle events from Redis
def realtime_handler(event, message):
    """Handle realtime events from socketio via Redis"""
    try:
        if event == "mcp_terminal_input" and isinstance(message, dict):
            user = message.get("user")
            data = message.get("data", {})
            if user:
                handle_terminal_input(user, data)
    except Exception as e:
        frappe.log_error(f"Error in realtime handler: {str(e)}")
