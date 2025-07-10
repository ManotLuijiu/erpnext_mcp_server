#!/usr/bin/env python3
"""
ERPNext MCP Server
Model Context Protocol server for ERPNext automation and management.
Provides secure, whitelisted operations for document management, database queries,
system information, and file operations.
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import Frappe modules
import frappe
import frappe.utils

# Import MCP modules
import mcp.server.stdio
import mcp.types as types
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions


class ERPNextMCPServer:
    """ERPNext MCP Server with integrated Frappe framework support."""

    def __init__(self):
        self.server = Server("erpnext-mcp-server")
        self.safe_bench_commands = {
            "version",
            "status",
            "list-apps",
            "doctor",
            "config",
            "--version",
            "--help",
            "list-sites",
        }
        self.setup_handlers()

    @asynccontextmanager
    async def server_lifespan(self, server: Server) -> AsyncIterator[Dict[str, Any]]:
        """Manage server startup and shutdown lifecycle."""
        try:
            # Initialize Frappe if not already initialized
            if not frappe.db:
                frappe.init()
                frappe.connect()

            context = {
                "frappe_initialized": True,
                "start_time": frappe.utils.now(),
                "safe_commands": self.safe_bench_commands,
            }

            yield context

        except Exception as e:
            print(f"Error initializing Frappe context: {e}")
            yield {"frappe_initialized": False}
        finally:
            # Cleanup if needed
            if frappe.db:
                frappe.db.close()

    def setup_handlers(self):
        """Setup all MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available MCP tools."""
            return [
                types.Tool(
                    name="list_doctypes",
                    description="List all available document types, optionally filtered by module",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "module": {
                                "type": "string",
                                "description": "Optional module name to filter doctypes",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="get_document",
                    description="Retrieve a specific document by doctype and name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doctype": {
                                "type": "string",
                                "description": "The document type (e.g., 'Customer', 'Sales Invoice')",
                            },
                            "name": {
                                "type": "string",
                                "description": "The document name/ID",
                            },
                        },
                        "required": ["doctype", "name"],
                    },
                ),
                types.Tool(
                    name="search_documents",
                    description="Search documents of a specific type with filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doctype": {
                                "type": "string",
                                "description": "The document type to search",
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query string",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 20,
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific fields to retrieve",
                            },
                        },
                        "required": ["doctype", "query"],
                    },
                ),
                types.Tool(
                    name="execute_sql",
                    description="Execute SQL SELECT queries (read-only for security)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL SELECT query to execute",
                            }
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="get_system_info",
                    description="Get comprehensive system information",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="list_files",
                    description="List files and directories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path to list",
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to list recursively",
                                "default": False,
                            },
                        },
                        "required": ["path"],
                    },
                ),
                types.Tool(
                    name="read_file",
                    description="Read file contents with safety restrictions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to read",
                            },
                            "lines": {
                                "type": "integer",
                                "description": "Maximum number of lines to read",
                            },
                        },
                        "required": ["path"],
                    },
                ),
                types.Tool(
                    name="bench_command",
                    description="Execute safe bench commands",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Bench command to execute (limited to safe commands)",
                            }
                        },
                        "required": ["command"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[types.TextContent]:
            """Handle tool execution requests."""
            try:
                if name == "list_doctypes":
                    return await self._list_doctypes(arguments.get("module"))

                elif name == "get_document":
                    return await self._get_document(
                        arguments["doctype"], arguments["name"]
                    )

                elif name == "search_documents":
                    return await self._search_documents(
                        arguments["doctype"],
                        arguments["query"],
                        arguments.get("limit", 20),
                        arguments.get("fields"),
                    )

                elif name == "execute_sql":
                    return await self._execute_sql(arguments["query"])

                elif name == "get_system_info":
                    return await self._get_system_info()

                elif name == "list_files":
                    return await self._list_files(
                        arguments["path"], arguments.get("recursive", False)
                    )

                elif name == "read_file":
                    return await self._read_file(
                        arguments["path"], arguments.get("lines")
                    )

                elif name == "bench_command":
                    return await self._bench_command(arguments["command"])

                else:
                    return [
                        types.TextContent(type="text", text=f"❌ Unknown tool: {name}")
                    ]

            except Exception as e:
                return [
                    types.TextContent(
                        type="text", text=f"❌ Error executing {name}: {str(e)}"
                    )
                ]

    async def _list_doctypes(
        self, module: Optional[str] = None
    ) -> List[types.TextContent]:
        """List all available document types."""
        try:
            query = DocType("DocType").select(
                "name", "module", "is_custom", "description"
            )

            if module:
                query = query.where(DocType("DocType").module == module)

            doctypes = query.run(as_dict=True)

            if not doctypes:
                return [
                    types.TextContent(type="text", text="📋 No document types found")
                ]

            # Group by module
            modules_dict = {}
            for dt in doctypes:
                mod = dt.get("module", "Unknown")
                if mod not in modules_dict:
                    modules_dict[mod] = []
                modules_dict[mod].append(dt)

            result = ["📋 Available Document Types\n" + "=" * 50]

            for mod, dts in sorted(modules_dict.items()):
                result.append(f"\n🗂️  {mod} ({len(dts)} types)")
                result.append("─" * 40)

                for dt in sorted(dts, key=lambda x: x["name"]):
                    custom = " 🔧" if dt.get("is_custom") else ""
                    desc = dt.get("description", "")
                    desc_text = f" - {desc}" if desc else ""
                    result.append(f"  • {dt['name']}{custom}{desc_text}")

            return [types.TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"❌ Error listing doctypes: {str(e)}"
                )
            ]

    async def _get_document(self, doctype: str, name: str) -> List[types.TextContent]:
        """Get a specific document."""
        try:
            if not frappe.db.exists(doctype, name):
                return [
                    types.TextContent(
                        type="text", text=f"❌ Document {doctype} '{name}' not found"
                    )
                ]

            doc = frappe.get_doc(doctype, name)

            # Format document data
            result = [f"📄 {doctype}: {name}\n" + "=" * 50]

            # Basic info
            result.append(f"Status: {doc.get('status', 'N/A')}")
            result.append(f"Owner: {doc.get('owner', 'N/A')}")
            result.append(f"Created: {doc.get('creation', 'N/A')}")
            result.append(f"Modified: {doc.get('modified', 'N/A')}")
            result.append("")

            # Document fields
            result.append("📊 Document Fields:")
            result.append("─" * 30)

            meta = frappe.get_meta(doctype)
            for field in meta.fields:
                if field.fieldtype not in [
                    "Section Break",
                    "Column Break",
                    "Tab Break",
                ]:
                    value = doc.get(field.fieldname)
                    if value:
                        result.append(f"  {field.label}: {value}")

            return [types.TextContent(type="text", text="\n".join(result))]

        except frappe.PermissionError:
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Permission denied accessing {doctype} '{name}'",
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"❌ Error retrieving document: {str(e)}"
                )
            ]

    async def _search_documents(
        self,
        doctype: str,
        query: str,
        limit: int = 20,
        fields: Optional[List[str]] = None,
    ) -> List[types.TextContent]:
        """Search documents with filters."""
        try:
            # Build search query
            filters = []
            if query:
                # Search in name and common text fields
                search_fields = ["name"]
                meta = frappe.get_meta(doctype)
                for field in meta.fields:
                    if (
                        field.fieldtype in ["Data", "Text", "Small Text", "Long Text"]
                        and field.search_in_list
                    ):
                        search_fields.append(field.fieldname)

                for field in search_fields:
                    filters.append([field, "like", f"%{query}%"])

            # Get documents
            docs = frappe.get_list(
                doctype,
                fields=fields or ["name", "creation", "modified"],
                filters=filters,
                limit=limit,
                order_by="modified desc",
            )

            if not docs:
                return [
                    types.TextContent(
                        type="text",
                        text=f"🔍 No {doctype} documents found matching '{query}'",
                    )
                ]

            result = [f"🔍 Search Results: {doctype} ('{query}')\n" + "=" * 50]
            result.append(f"Found {len(docs)} documents (limit: {limit})\n")

            for i, doc in enumerate(docs, 1):
                result.append(f"{i}. {doc['name']}")
                if "creation" in doc:
                    result.append(f"   Created: {doc['creation']}")
                if fields:
                    for field in fields:
                        if field in doc and field not in [
                            "name",
                            "creation",
                            "modified",
                        ]:
                            result.append(f"   {field}: {doc[field]}")
                result.append("")

            return [types.TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"❌ Error searching documents: {str(e)}"
                )
            ]

    async def _execute_sql(self, query: str) -> List[types.TextContent]:
        """Execute SQL SELECT queries only (for security)."""
        try:
            # Security check - only allow SELECT queries
            query_clean = query.strip().upper()
            if not query_clean.startswith("SELECT"):
                return [
                    types.TextContent(
                        type="text",
                        text="❌ Only SELECT queries are allowed for security reasons",
                    )
                ]

            # Additional security checks
            dangerous_keywords = [
                "DROP",
                "DELETE",
                "UPDATE",
                "INSERT",
                "ALTER",
                "CREATE",
                "TRUNCATE",
            ]
            if any(keyword in query_clean for keyword in dangerous_keywords):
                return [
                    types.TextContent(
                        type="text", text="❌ Query contains forbidden keywords"
                    )
                ]

            results = frappe.db.sql(query, as_dict=True)

            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text="🗄️ Query executed successfully - No results returned",
                    )
                ]

            result = [f"🗄️ SQL Query Results\n" + "=" * 50]
            result.append(f"Query: {query}")
            result.append(f"Rows returned: {len(results)}\n")

            # Format results
            if len(results) <= 100:  # Limit output for large result sets
                for i, row in enumerate(results, 1):
                    result.append(f"Row {i}:")
                    for key, value in row.items():
                        result.append(f"  {key}: {value}")
                    result.append("")
            else:
                result.append(
                    f"⚠️ Result set too large ({len(results)} rows). Showing first 10 rows:"
                )
                for i, row in enumerate(results[:10], 1):
                    result.append(f"Row {i}: {dict(row)}")

            return [types.TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            return [types.TextContent(type="text", text=f"❌ SQL Error: {str(e)}")]

    async def _get_system_info(self) -> List[types.TextContent]:
        """Get comprehensive system information."""
        try:
            info = []

            # Frappe/ERPNext versions
            info.append("🖥️ System Information\n" + "=" * 50)
            info.append(f"Frappe Version: {frappe.__version__}")

            try:
                import erpnext

                info.append(f"ERPNext Version: {erpnext.__version__}")
            except ImportError:
                info.append("ERPNext: Not installed")

            # Site information
            info.append(f"Site: {frappe.local.site}")
            info.append(f"Database: {frappe.conf.db_name}")
            info.append(f"Database Type: {frappe.conf.db_type}")

            # System information
            import platform

            info.append(f"Platform: {platform.platform()}")
            info.append(f"Python Version: {platform.python_version()}")
            info.append(f"Architecture: {platform.architecture()[0]}")

            # Bench information
            try:
                bench_path = os.environ.get("BENCH_PATH", os.getcwd())
                info.append(f"Bench Path: {bench_path}")
            except:
                pass

            # Additional ERPNext info
            info.append("\n📊 Database Statistics:")
            info.append("─" * 30)

            # Count some common doctypes
            common_doctypes = [
                "User",
                "Customer",
                "Item",
                "Sales Invoice",
                "Purchase Invoice",
            ]
            for doctype in common_doctypes:
                try:
                    count = frappe.db.count(doctype)
                    info.append(f"{doctype}: {count}")
                except:
                    pass

            return [types.TextContent(type="text", text="\n".join(info))]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"❌ Error getting system info: {str(e)}"
                )
            ]

    async def _list_files(
        self, path: str, recursive: bool = False
    ) -> List[types.TextContent]:
        """List files and directories safely."""
        try:
            path_obj = Path(path)

            # Security check - prevent access outside bench directory
            bench_path = Path(os.environ.get("BENCH_PATH", os.getcwd()))
            try:
                path_obj.resolve().relative_to(bench_path.resolve())
            except ValueError:
                return [
                    types.TextContent(
                        type="text",
                        text="❌ Access denied: Path outside allowed directory",
                    )
                ]

            if not path_obj.exists():
                return [
                    types.TextContent(type="text", text=f"❌ Path not found: {path}")
                ]

            if not path_obj.is_dir():
                return [
                    types.TextContent(type="text", text=f"❌ Not a directory: {path}")
                ]

            result = [f"📁 Directory Listing: {path}\n" + "=" * 50]

            if recursive:
                items = list(path_obj.rglob("*"))
            else:
                items = list(path_obj.iterdir())

            # Sort items
            dirs = [item for item in items if item.is_dir()]
            files = [item for item in items if item.is_file()]

            result.append(f"Directories: {len(dirs)}, Files: {len(files)}\n")

            # Show directories first
            for item in sorted(dirs):
                rel_path = item.relative_to(path_obj)
                result.append(f"📁 {rel_path}/")

            # Then files
            for item in sorted(files):
                rel_path = item.relative_to(path_obj)
                try:
                    size = item.stat().st_size
                    size_str = (
                        frappe.utils.file_size(size)
                        if hasattr(frappe.utils, "file_size")
                        else f"{size} bytes"
                    )
                    result.append(f"📄 {rel_path} ({size_str})")
                except:
                    result.append(f"📄 {rel_path}")

            return [types.TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            return [
                types.TextContent(type="text", text=f"❌ Error listing files: {str(e)}")
            ]

    async def _read_file(
        self, path: str, lines: Optional[int] = None
    ) -> List[types.TextContent]:
        """Read file contents with safety restrictions."""
        try:
            path_obj = Path(path)

            # Security check - prevent access outside bench directory
            bench_path = Path(os.environ.get("BENCH_PATH", os.getcwd()))
            try:
                path_obj.resolve().relative_to(bench_path.resolve())
            except ValueError:
                return [
                    types.TextContent(
                        type="text",
                        text="❌ Access denied: Path outside allowed directory",
                    )
                ]

            if not path_obj.exists():
                return [
                    types.TextContent(type="text", text=f"❌ File not found: {path}")
                ]

            if not path_obj.is_file():
                return [types.TextContent(type="text", text=f"❌ Not a file: {path}")]

            # Check file size
            file_size = path_obj.stat().st_size
            if file_size > 1024 * 1024:  # 1MB limit
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ File too large: {frappe.utils.file_size(file_size) if hasattr(frappe.utils, 'file_size') else f'{file_size} bytes'}",
                    )
                ]

            try:
                with open(path_obj, "r", encoding="utf-8") as f:
                    if lines:
                        content_lines = []
                        for i, line in enumerate(f):
                            if i >= lines:
                                break
                            content_lines.append(line.rstrip("\n\r"))
                        content = "\n".join(content_lines)
                        truncated = (
                            f"\n\n⚠️ Showing first {lines} lines only"
                            if lines < sum(1 for _ in open(path_obj, "r"))
                            else ""
                        )
                    else:
                        content = f.read()
                        truncated = ""
            except UnicodeDecodeError:
                return [
                    types.TextContent(
                        type="text",
                        text="❌ File contains binary data or unsupported encoding",
                    )
                ]

            result = [f"📄 File Content: {path}\n" + "=" * 50]
            result.append(
                f"Size: {frappe.utils.file_size(file_size) if hasattr(frappe.utils, 'file_size') else f'{file_size} bytes'}"
            )
            if lines:
                result.append(f"Lines shown: {lines}")
            result.append("─" * 40)
            result.append(content)
            if truncated:
                result.append(truncated)

            return [types.TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            return [
                types.TextContent(type="text", text=f"❌ Error reading file: {str(e)}")
            ]

    async def _bench_command(self, command: str) -> List[types.TextContent]:
        """Execute safe bench commands only."""
        try:
            # Parse command
            cmd_parts = command.split()
            if not cmd_parts:
                return [types.TextContent(type="text", text="❌ Empty command")]

            # Security check - only allow whitelisted commands
            base_cmd = cmd_parts[0].replace("bench ", "").strip()
            if base_cmd not in self.safe_bench_commands:
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ Command '{base_cmd}' not allowed. Safe commands: {', '.join(self.safe_bench_commands)}",
                    )
                ]

            # Execute bench command
            bench_path = os.environ.get("BENCH_PATH", os.getcwd())
            full_command = ["bench"] + cmd_parts

            try:
                result = subprocess.run(
                    full_command,
                    cwd=bench_path,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                )

                output = []
                output.append(f"🔧 Bench Command: {command}\n" + "=" * 50)
                output.append(f"Exit Code: {result.returncode}")
                output.append("─" * 40)

                if result.stdout:
                    output.append("📤 Output:")
                    output.append(result.stdout)

                if result.stderr:
                    output.append("📥 Errors:")
                    output.append(result.stderr)

                return [types.TextContent(type="text", text="\n".join(output))]

            except subprocess.TimeoutExpired:
                return [
                    types.TextContent(
                        type="text", text="❌ Command timed out after 30 seconds"
                    )
                ]
            except subprocess.CalledProcessError as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ Command failed with exit code {e.returncode}: {e.output}",
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"❌ Error executing bench command: {str(e)}"
                )
            ]

    async def run(self):
        """Run the MCP server."""
        # Set the lifespan for the server
        self.server.lifespan = self.server_lifespan

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="erpnext-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(
                            tools_changed=True,
                            resources_changed=False,
                            prompts_changed=False,
                        ),
                        experimental_capabilities={
                            "erpnext_integration": {
                                "version": "1.0.0",
                                "features": [
                                    "document_operations",
                                    "database_queries",
                                    "system_info",
                                    "file_operations",
                                    "bench_commands",
                                ],
                            }
                        },
                    ),
                    instructions="ERPNext MCP Server provides secure access to ERPNext document operations, database queries, system information, and file management. All operations are whitelisted and run with proper security controls.",
                ),
            )


def main():
    """Main entry point for the MCP server."""
    try:
        # Initialize the server
        server = ERPNextMCPServer()

        # Run the server
        asyncio.run(server.run())

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
