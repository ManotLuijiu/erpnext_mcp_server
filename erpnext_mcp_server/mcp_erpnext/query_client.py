#!/usr/bin/env python3
"""
Query client for the MCP server in stdio mode.
This script is used to send a query to the MCP server and get the response.
"""

import os
import sys
import json
import subprocess
import tempfile
import time


def query_mcp_server(input_file):
    """
    Query the MCP server with input from a file

    Args:
        input_file: Path to a JSON file with query data

    Returns:
        JSON response from the MCP server
    """
    try:
        # Load the input data
        with open(input_file, "r") as f:
            input_data = json.load(f)

        # Get the MCP server script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_script = os.path.join(script_dir, "server.py")

        # Create a temporary file for the result
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as f:
            result_file = f.name

        # Prepare environment variables
        env = os.environ.copy()
        env["MCP_QUERY_MODE"] = "1"  # Special flag for query mode
        env["MCP_QUERY_DATA"] = json.dumps(input_data)
        env["MCP_RESULT_FILE"] = result_file

        # Run the MCP server in query mode
        process = subprocess.Popen(
            [env.get("PYTHONBIN", "python3"), server_script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = process.communicate(timeout=25)  # 25 seconds timeout
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise TimeoutError("MCP query timed out")

        # Check for errors
        if process.returncode != 0:
            error_message = stderr.decode("utf-8") if stderr else "Unknown error"
            raise RuntimeError(f"MCP query failed: {error_message}")

        # Wait briefly for file to be fully written
        time.sleep(0.1)

        # Read the result file
        try:
            with open(result_file, "r") as f:
                result_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to read MCP result: {str(e)}")
        finally:
            # Clean up the result file
            try:
                os.unlink(result_file)
            except:
                pass

        # Return the result
        return result_data

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Check for input file argument
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python query_client.py <input_file>"}))
        sys.exit(1)

    input_file = sys.argv[1]
    result = query_mcp_server(input_file)

    # Output the result as JSON
    print(json.dumps(result))
