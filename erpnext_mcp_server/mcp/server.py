"""
ERPNext MCP Server - Framework Level Implementation
Works like Doppio CLI: bench integration, not site-specific.

Usage:
  # With default site from environment
  python -m erpnext_mcp_server.mcp.server

  # With specific site
  FRAPPE_SITE=demo.bunchee.online python -m erpnext_mcp_server.mcp.server

  # Via SSH (for Hermes Agent on remote machine)
  ssh user@server "FRAPPE_SITE=your-site.com python -m erpnext_mcp_server.mcp.server"
"""

import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============================================================
# CONFIGURATION - Set before any Frappe imports
# ============================================================
BENCH_PATH = os.getenv("BENCH_PATH", "/home/frappe/frappe-bench")
SITE_ARG = os.getenv("FRAPPE_SITE", "")

# Fix logger issue: set stream_only to avoid file path problems
os.environ["FRAPPE_STREAM_LOGGING"] = "1"

# Change to bench directory for relative path resolution
os.chdir(BENCH_PATH)

# Add bench to path
sys.path.insert(0, os.path.join(BENCH_PATH, "apps", "frappe"))
sys.path.insert(0, BENCH_PATH)

# ============================================================
# FRAPPE BOOTSTRAP - Deferred until tool execution
# ============================================================
frappe = None


def get_frappe():
    """Lazy import of frappe - only when needed."""
    global frappe
    if frappe is None:
        import frappe as _frappe

        frappe = _frappe
    return frappe


# ============================================================
# MCP SERVER SETUP
# ============================================================
from mcp.server import InitializationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    ServerCapabilities,
    Tool,
    ToolsCapability,
)

# Server instance
server = Server("erpnext-mcp-server")


# ============================================================
# SITE CONTEXT MANAGEMENT
# ============================================================
class SiteContext:
    """Manages Frappe site context - switches on demand."""

    def __init__(self):
        self._current_site: Optional[str] = None
        self._frappe_initialized = False
        self._bench_path = BENCH_PATH
        self._sites_path = os.path.join(BENCH_PATH, "sites")

    def get_current_site(self) -> str:
        """Get current site name."""
        return self._current_site or SITE_ARG or ""

    def _get_site_path(self, site_name: str) -> str:
        """Get absolute path to site directory."""
        return os.path.join(self._sites_path, site_name)

    def _ensure_site_logs(self, site_name: str) -> None:
        """Create logs directory for site if it doesn't exist."""
        logs_path = os.path.join(self._get_site_path(site_name), "logs")
        os.makedirs(logs_path, exist_ok=True)

    def set_site(self, site_name: str) -> None:
        """Switch to a different site."""
        if not site_name:
            raise ValueError("Site name is required")

        f = get_frappe()

        # If already initialized with this site, do nothing
        if self._current_site == site_name and self._frappe_initialized:
            return

        # Clean up previous site
        if self._frappe_initialized:
            try:
                f.destroy()
            except Exception:
                pass

        # Ensure logs directory exists
        self._ensure_site_logs(site_name)

        # Initialize new site
        self._current_site = site_name
        os.environ["FRAPPE_SITE"] = site_name
        f.init(site=site_name, sites_path=self._sites_path)
        f.connect()
        self._frappe_initialized = True

    def ensure_initialized(self, site: Optional[str] = None) -> None:
        """Ensure Frappe is initialized with the specified or default site."""
        target_site = site or self._current_site or SITE_ARG

        if not target_site:
            raise ValueError(
                "No site specified. Set FRAPPE_SITE env or pass site parameter."
            )

        if self._current_site != target_site or not self._frappe_initialized:
            self.set_site(target_site)

    def list_sites(self) -> List[str]:
        """List all available sites."""
        if not os.path.exists(self._sites_path):
            return []

        sites = []
        for item in os.listdir(self._sites_path):
            site_path = os.path.join(self._sites_path, item)
            if os.path.isdir(site_path) and os.path.exists(
                os.path.join(site_path, "site_config.json")
            ):
                sites.append(item)

        return sorted(sites)


# Global site context
site_context = SiteContext()


# ============================================================
# TOOL DEFINITIONS
# ============================================================
@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available tools."""
    return ListToolsResult(
        tools=[
            # === SITE MANAGEMENT ===
            Tool(
                name="list_sites",
                description="List all available Frappe sites on this bench",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="switch_site",
                description="Switch to a different Frappe site context. Use this before other operations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site": {
                            "type": "string",
                            "description": "Site name to switch to",
                        }
                    },
                    "required": ["site"],
                },
            ),
            Tool(
                name="current_site",
                description="Get the current site name",
                inputSchema={"type": "object", "properties": {}},
            ),
            # === DOCUMENT CRUD ===
            Tool(
                name="get_document",
                description="Get a document by doctype and name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {
                            "type": "string",
                            "description": "Document type name",
                        },
                        "name": {
                            "type": "string",
                            "description": "Document name or ID",
                        },
                        "site": {
                            "type": "string",
                            "description": "Optional: Override site for this operation",
                        },
                    },
                    "required": ["doctype", "name"],
                },
            ),
            Tool(
                name="list_documents",
                description="List documents with optional filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "filters": {
                            "type": "object",
                            "description": 'Filter dict, e.g. {"status": "Open"}',
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to return",
                        },
                        "limit": {"type": "integer", "default": 20},
                        "order_by": {
                            "type": "string",
                            "description": "Order by clause",
                        },
                        "site": {"type": "string"},
                    },
                    "required": ["doctype"],
                },
            ),
            Tool(
                name="create_document",
                description="Create a new document",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "data": {
                            "type": "object",
                            "description": "Document field values",
                        },
                        "site": {"type": "string"},
                    },
                    "required": ["doctype", "data"],
                },
            ),
            Tool(
                name="update_document",
                description="Update an existing document",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "name": {"type": "string"},
                        "data": {"type": "object", "description": "Fields to update"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype", "name", "data"],
                },
            ),
            Tool(
                name="delete_document",
                description="Delete a document (soft delete via cancel)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "name": {"type": "string"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype", "name"],
                },
            ),
            Tool(
                name="count_documents",
                description="Count documents matching filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "filters": {"type": "object"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype"],
                },
            ),
            # === DOCTYPE METADATA ===
            Tool(
                name="list_doctypes",
                description="List all DocTypes with optional module filter",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module": {"type": "string"},
                        "site": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="get_doctype_meta",
                description="Get DocType metadata (fields, permissions, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype"],
                },
            ),
            # === DATABASE ===
            Tool(
                name="execute_sql",
                description="Execute safe SQL query (SELECT only)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 100},
                        "site": {"type": "string"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_table_info",
                description="Get table structure and row count",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string"},
                        "site": {"type": "string"},
                    },
                    "required": ["table"],
                },
            ),
            # === SYSTEM INFO ===
            Tool(
                name="get_system_info",
                description="Get system and site information",
                inputSchema={
                    "type": "object",
                    "properties": {"site": {"type": "string"}},
                },
            ),
            Tool(
                name="get_versions",
                description="Get installed app versions",
                inputSchema={
                    "type": "object",
                    "properties": {"site": {"type": "string"}},
                },
            ),
            Tool(
                name="bench_command",
                description="Execute safe bench commands",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": [
                                "version",
                                "status",
                                "list-apps",
                                "doctor",
                                "config",
                                "show-config",
                            ],
                        },
                        "site": {"type": "string"},
                    },
                    "required": ["command"],
                },
            ),
            # === WORKFLOW ===
            Tool(
                name="submit_document",
                description="Submit a document (docstatus 0 → 1)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "name": {"type": "string"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype", "name"],
                },
            ),
            Tool(
                name="cancel_document",
                description="Cancel a submitted document",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doctype": {"type": "string"},
                        "name": {"type": "string"},
                        "site": {"type": "string"},
                    },
                    "required": ["doctype", "name"],
                },
            ),
            # === SEARCH ===
            Tool(
                name="search",
                description="Search across all doctypes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "doctype": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                        "site": {"type": "string"},
                    },
                    "required": ["query"],
                },
            ),
            # === FILE OPERATIONS ===
            Tool(
                name="read_file",
                description="Read file contents (safe paths only)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "lines": {"type": "integer"},
                        "site": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="list_files",
                description="List files in directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "recursive": {"type": "boolean", "default": False},
                        "site": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
        ]
    )


# ============================================================
# TOOL HANDLERS
# ============================================================
@server.call_tool()
async def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> CallToolResult:
    """Handle tool calls with site context management."""
    try:
        args = arguments or {}

        # === SITE MANAGEMENT TOOLS ===
        if name == "list_sites":
            sites = site_context.list_sites()
            return CallToolResult(
                content=[{"type": "text", "text": json.dumps(sites, indent=2)}]
            )

        if name == "switch_site":
            site = args.get("site")
            if not site:
                return CallToolResult(
                    content=[
                        {"type": "text", "text": "Error: site parameter required"}
                    ],
                    isError=True,
                )

            try:
                site_context.set_site(site)
                return CallToolResult(
                    content=[{"type": "text", "text": f"Switched to site: {site}"}]
                )
            except Exception as e:
                return CallToolResult(
                    content=[{"type": "text", "text": f"Error switching to site: {e}"}],
                    isError=True,
                )

        if name == "current_site":
            return CallToolResult(
                content=[{"type": "text", "text": site_context.get_current_site()}]
            )

        # === ALL OTHER TOOLS: Ensure site is initialized ===
        target_site = args.get("site")
        site_context.ensure_initialized(target_site)

        f = get_frappe()

        # === DOCUMENT CRUD TOOLS ===
        if name == "get_document":
            doctype = args["doctype"]
            doc_name = args["name"]

            doc = f.get_doc(doctype, doc_name)
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(doc.as_dict(), indent=2, default=str),
                    }
                ]
            )

        if name == "list_documents":
            doctype = args["doctype"]
            filters = args.get("filters", {})
            fields = args.get("fields", ["name"])
            limit = args.get("limit", 20)
            order_by = args.get("order_by", "modified desc")

            docs = f.get_all(
                doctype, filters=filters, fields=fields, limit=limit, order_by=order_by
            )
            return CallToolResult(
                content=[
                    {"type": "text", "text": json.dumps(docs, indent=2, default=str)}
                ]
            )

        if name == "create_document":
            doctype = args["doctype"]
            data = args["data"]

            doc = f.new_doc(doctype)
            doc.update(data)
            doc.insert()
            f.db.commit()

            return CallToolResult(
                content=[{"type": "text", "text": f"Created {doctype} {doc.name}"}]
            )

        if name == "update_document":
            doctype = args["doctype"]
            doc_name = args["name"]
            data = args["data"]

            doc = f.get_doc(doctype, doc_name)
            doc.update(data)
            doc.save()
            f.db.commit()

            return CallToolResult(
                content=[{"type": "text", "text": f"Updated {doctype} {doc_name}"}]
            )

        if name == "delete_document":
            doctype = args["doctype"]
            doc_name = args["name"]

            doc = f.get_doc(doctype, doc_name)
            if doc.docstatus == 1:
                doc.cancel()
            else:
                doc.delete()
            f.db.commit()

            return CallToolResult(
                content=[{"type": "text", "text": f"Deleted {doctype} {doc_name}"}]
            )

        if name == "count_documents":
            doctype = args["doctype"]
            filters = args.get("filters", {})

            count = f.db.count(doctype, filters)
            return CallToolResult(content=[{"type": "text", "text": str(count)}])

        # === DOCTYPE METADATA ===
        if name == "list_doctypes":
            module_filter = args.get("module")

            filters = {"custom": 0, "istable": 0}
            if module_filter:
                filters["module"] = module_filter

            doctypes = f.get_all(
                "DocType",
                filters=filters,
                fields=["name", "module", "description", "is_submittable"],
                order_by="module, name",
            )

            return CallToolResult(
                content=[{"type": "text", "text": json.dumps(doctypes, indent=2)}]
            )

        if name == "get_doctype_meta":
            doctype = args["doctype"]

            meta = f.get_meta(doctype)
            fields = [
                {
                    "name": f.fieldname,
                    "label": f.label,
                    "type": f.fieldtype,
                    "reqd": f.reqd,
                }
                for f in meta.fields
            ]

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"name": doctype, "fields": fields}, indent=2
                        ),
                    }
                ]
            )

        # === DATABASE ===
        if name == "execute_sql":
            query = args["query"]
            limit = args.get("limit", 100)

            # Security: only SELECT
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return CallToolResult(
                    content=[
                        {"type": "text", "text": "Error: Only SELECT queries allowed"}
                    ],
                    isError=True,
                )

            result = f.db.sql(query, as_dict=True)
            if len(result) > limit:
                result = result[:limit]

            return CallToolResult(
                content=[
                    {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                ]
            )

        if name == "get_table_info":
            table = args["table"]
            if not table.startswith("tab"):
                table = f"tab{table}"

            columns = f.db.sql(f"DESCRIBE `{table}`", as_dict=True)
            count = f.db.sql(f"SELECT COUNT(*) as cnt FROM `{table}`", as_dict=True)[
                0
            ].cnt

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"table": table, "columns": columns, "row_count": count},
                            indent=2,
                        ),
                    }
                ]
            )

        # === SYSTEM INFO ===
        if name == "get_system_info":
            site_name = site_context.get_current_site()
            db_info = {
                "name": f.conf.db_name,
                "version": f.db.sql("SELECT VERSION() as v", as_dict=True)[0].v,
            }

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "site": site_name,
                                "db_name": db_info["name"],
                                "db_version": db_info["version"],
                            },
                            indent=2,
                        ),
                    }
                ]
            )

        if name == "get_versions":
            from frappe.utils.change_log import get_versions

            versions = get_versions()
            return CallToolResult(
                content=[{"type": "text", "text": json.dumps(versions, indent=2)}]
            )

        if name == "bench_command":
            import subprocess

            command = args["command"]
            allowed = [
                "version",
                "status",
                "list-apps",
                "doctor",
                "config",
                "show-config",
            ]

            if command not in allowed:
                return CallToolResult(
                    content=[
                        {"type": "text", "text": f"Command not allowed: {command}"}
                    ],
                    isError=True,
                )

            result = subprocess.run(
                ["bench", command],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=BENCH_PATH,
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": result.stdout or result.stderr or "Command executed",
                    }
                ]
            )

        # === WORKFLOW ===
        if name == "submit_document":
            doctype = args["doctype"]
            doc_name = args["name"]

            doc = f.get_doc(doctype, doc_name)
            doc.submit()
            f.db.commit()

            return CallToolResult(
                content=[{"type": "text", "text": f"Submitted {doctype} {doc_name}"}]
            )

        if name == "cancel_document":
            doctype = args["doctype"]
            doc_name = args["name"]

            doc = f.get_doc(doctype, doc_name)
            doc.cancel()
            f.db.commit()

            return CallToolResult(
                content=[{"type": "text", "text": f"Cancelled {doctype} {doc_name}"}]
            )

        # === SEARCH ===
        if name == "search":
            query_text = args["query"]
            doctype = args.get("doctype")
            limit = args.get("limit", 10)

            if doctype:
                meta = f.get_meta(doctype)
                title_field = meta.get_title_field() or "name"

                results = f.get_all(
                    doctype,
                    filters={title_field: ["like", f"%{query_text}%"]},
                    fields=["name", title_field],
                    limit=limit,
                )
            else:
                # Search across all doctypes
                results = []
                for dt in f.get_all("DocType", filters={"custom": 0}, pluck="name")[
                    :20
                ]:
                    try:
                        meta = f.get_meta(dt)
                        title_field = meta.get_title_field() or "name"
                        hits = f.get_all(
                            dt,
                            filters={title_field: ["like", f"%{query_text}%"]},
                            fields=["name", title_field],
                            limit=3,
                        )
                        for h in hits:
                            results.append(
                                {
                                    "doctype": dt,
                                    "name": h.name,
                                    "title": h.get(title_field),
                                }
                            )
                    except Exception:
                        pass

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(results[:limit], indent=2, default=str),
                    }
                ]
            )

        # === FILE OPERATIONS ===
        if name == "read_file":
            file_path = args["path"]

            # Security: check path - only allow safe directories
            safe_dirs = ["sites", "apps", "logs", "config"]
            path_obj = Path(file_path)
            parts = path_obj.parts if path_obj.is_absolute() else path_obj.parts

            if not any(p in safe_dirs for p in parts):
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": f"Path not allowed. Safe dirs: {safe_dirs}",
                        }
                    ],
                    isError=True,
                )

            # Resolve to absolute path
            if path_obj.is_absolute():
                full_path = path_obj
            else:
                full_path = Path(BENCH_PATH) / path_obj

            if not full_path.exists():
                return CallToolResult(
                    content=[{"type": "text", "text": f"File not found: {file_path}"}],
                    isError=True,
                )

            lines = args.get("lines")
            with open(full_path, "r") as fh:
                content = (
                    fh.read()
                    if not lines
                    else "\n".join(fh.read().splitlines()[:lines])
                )

            return CallToolResult(content=[{"type": "text", "text": content}])

        if name == "list_files":
            dir_path = args["path"]
            recursive = args.get("recursive", False)

            # Security check
            safe_dirs = ["sites", "apps", "logs", "config"]
            path_obj = Path(dir_path)
            parts = path_obj.parts if path_obj.is_absolute() else path_obj.parts

            if not any(p in safe_dirs for p in parts):
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": f"Path not allowed. Safe dirs: {safe_dirs}",
                        }
                    ],
                    isError=True,
                )

            # Resolve to absolute path
            if path_obj.is_absolute():
                full_path = path_obj
            else:
                full_path = Path(BENCH_PATH) / path_obj

            if not full_path.exists() or not full_path.is_dir():
                return CallToolResult(
                    content=[{"type": "text", "text": f"Not a directory: {dir_path}"}],
                    isError=True,
                )

            items = list(full_path.rglob("*") if recursive else full_path.iterdir())
            file_list = [
                {
                    "name": str(i.relative_to(full_path)),
                    "type": "dir" if i.is_dir() else "file",
                }
                for i in items[:100]
            ]

            return CallToolResult(
                content=[{"type": "text", "text": json.dumps(file_list, indent=2)}]
            )

        # Unknown tool
        return CallToolResult(
            content=[{"type": "text", "text": f"Unknown tool: {name}"}], isError=True
        )

    except Exception as e:
        return CallToolResult(
            content=[
                {"type": "text", "text": f"Error: {str(e)}\n{traceback.format_exc()}"}
            ],
            isError=True,
        )


# ============================================================
# MAIN ENTRY POINT
# ============================================================
async def main():
    """Main entry point - runs the MCP stdio server."""
    options = InitializationOptions(
        server_name="erpnext-mcp-server",
        server_version="1.0.0",
        capabilities=ServerCapabilities(tools=ToolsCapability()),
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=options,
        )


if __name__ == "__main__":
    asyncio.run(main())
