#!/usr/bin/env python3

import sys
import time


def main():
    # Print startup message
    print("MCP Server starting...")
    time.sleep(1)
    print("MCP Server ready for commands.")

    # Read commands from stdin and echo back
    while True:
        try:
            # Make sure to flush output to be seen in realtime
            sys.stdout.flush()

            # Read a line from stdin
            command = input()

            # Process the command (this is where your actual MCP logic would go)
            if command.lower() in ("exit", "quit"):
                print("Exiting MCP Server.")
                break

            # Echo the command back
            print(f"Received command: {command}")

            # Simulate some processing time for testing
            if command.lower() == "help":
                print("Available commands:")
                print("  help - Show this help")
                print("  echo <text> - Echo back text")
                print("  wait <seconds> - Wait for specified seconds")
                print("  exit/quit - Exit the MCP server")
            elif command.lower().startswith("echo "):
                text = command[5:]
                print(f"Echo: {text}")
            elif command.lower().startswith("wait "):
                try:
                    seconds = int(command[5:])
                    print(f"Waiting for {seconds} seconds...")
                    for i in range(seconds):
                        time.sleep(1)
                        print(f"{i+1}...")
                    print("Done waiting.")
                except ValueError:
                    print("Error: Please provide a valid number of seconds.")
            else:
                print(f"Unknown command: {command}")

        except EOFError:
            # Handle EOF (Ctrl+D)
            print("Received EOF. Exiting.")
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("Received interrupt. Exiting.")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
