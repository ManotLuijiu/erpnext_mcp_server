"""ERPNext MCP Server using low-level implementation"""

import asyncio
import logging
import sys
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List

import frappe
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ERPNextContext:
    """Context for ERPNext operations."""

    def __init__(self) -> None:
        self.initialized = False
        self.site = None

    async def connect(self):
        """Initialize Frappe connection."""
        try:
            if not frappe.db:
                frappe.init_site()
                frappe.connect()

            self.site = frappe.local.site
            self.initialized = True
            logger.info(f"Connected to ERPNext site: {self.site}")

        except Exception as e:
            logger.error(f"Failed to connect to ERPNext; {e}")
            raise

    async def disconnect(self):
        """Clean up Frappe connection."""
        try:
            if frappe.db:
                frappe.db.close()
            logger.info("Disconnected from ERPNext")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    logger.info("Starting ERPNext MCP Server...")

    # Initialize ERPNext context
    erpnext_ctx = ERPNextContext()
    await erpnext_ctx.connect()

    try:
        yield {"erpnext": erpnext_ctx}
    finally:
        # Clean up on shutdown
        await erpnext_ctx.disconnect()
        logger.info("ERPNext MCP Server stopped")


# Create server with lifespan management
server = Server("erpnext-mcp-server", lifespan=server_lifespan)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="list_doctypes",
            description="List all available doctypes in ERPNext",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="okf_export_doctype",
            description="Export a Frappe DocType as an OKF (Open Knowledge Format) Markdown concept. Returns the path to the written concept.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {"type": "string", "description": "DocType name to export (e.g. 'Sales Invoice')"},
                    "site": {"type": "string", "description": "Frappe site (defaults to current)"},
                    "bundle": {"type": "string", "description": "Bundle directory name under okf/bundles/ (e.g. 'aws-solution')"},
                    "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False},
                },
                "required": ["doctype", "bundle"],
            },
        ),
        types.Tool(
            name="okf_list_concepts",
            description="List OKF concepts in a bundle, optionally filtered by type or tag.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle": {"type": "string", "description": "Bundle directory name (e.g. 'aws-solution')"},
                    "type": {"type": "string", "description": "Filter by concept type (e.g. 'Frappe DocType', 'Claude Skill')"},
                    "tag": {"type": "string", "description": "Filter by tag (e.g. 'kbank', 'billing')"},
                },
                "required": ["bundle"],
            },
        ),
        types.Tool(
            name="okf_get_concept",
            description="Read a single OKF concept by relative path. Returns parsed frontmatter + body. Unsafe paths are rejected.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle": {"type": "string", "description": "Bundle directory name"},
                    "path": {"type": "string", "description": "Concept path relative to bundle root (e.g. 'doctypes/sales-invoice.md')"},
                },
                "required": ["bundle", "path"],
            },
        ),
        types.Tool(
            name="okf_search",
            description="Text search across OKF concepts (frontmatter + body). Scores by title/tag/body matches. No embeddings in v1.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle": {"type": "string", "description": "Bundle directory name"},
                    "query": {"type": "string", "description": "Search query string"},
                    "limit": {"type": "integer", "description": "Max results (capped at 100)", "default": 20},
                    "type": {"type": "string", "description": "Optional type filter"},
                },
                "required": ["bundle", "query"],
            },
        ),
        types.Tool(
            name="okf_validate_bundle",
            description="Validate all concepts in a bundle. Checks frontmatter, required 'type' field, path safety. Auto-regenerates bundle index.md if present.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle": {"type": "string", "description": "Bundle directory name"},
                },
                "required": ["bundle"],
            },
        ),
        types.Tool(
            name="okf_export_site_catalog",
            description="Export all (or filtered) DocTypes from a Frappe site as OKF concepts. Creates a complete bundle with auto-generated index.md. Filters by module (not the unreliable 'custom' flag).",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Frappe site to export from"},
                    "bundle": {"type": "string", "description": "Bundle directory name (e.g. 'aws-solution')"},
                    "doctype_filter": {"type": "string", "description": "SQL LIKE filter for DocType name (e.g. 'Thai Bank %')"},
                    "module_filter": {"type": "string", "description": "SQL LIKE filter for DocType module (e.g. 'Thai %')"},
                    "include_custom": {"type": "boolean", "description": "Include custom (non-core) DocTypes", "default": True},
                    "include_core": {"type": "boolean", "description": "Include ERPNext/Frappe core DocTypes", "default": False},
                    "limit": {"type": "integer", "description": "Max DocTypes to export", "default": 200},
                },
                "required": ["site", "bundle"],
            },
        ),
        types.Tool(
            name="okf_recommend_skill",
            description="Recommend Claude Skills matching a task description. Returns skills with title, path, and snippet showing why they match.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle": {"type": "string", "description": "Bundle directory name"},
                    "task_description": {"type": "string", "description": "Description of the task (e.g. 'set up Gmail OAuth for Frappe')"},
                    "limit": {"type": "integer", "description": "Max recommendations", "default": 5},
                },
                "required": ["bundle", "task_description"],
            },
        ),
        types.Tool(
            name="get_document",
            description="Get a specific document from ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {"type": "string", "description": "Document type name"},
                    "name": {"type": "string", "description": "Document name/ID"},
                },
                "required": ["doctype", "name"],
            },
        ),
        types.Tool(
            name="search_documents",
            description="Search documents in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "Document type to search",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                },
                "required": ["doctype", "query"],
            },
        ),
        types.Tool(
            name="create_document",
            description="Create a new document in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {
                        "type": "string",
                        "description": "Document type to create",
                    },
                    "data": {
                        "type": "object",
                        "description": "Document data as JSON object",
                    },
                },
                "required": ["doctype", "data"],
            },
        ),
        types.Tool(
            name="update_document",
            description="Update an existing document in ERPNext",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctype": {"type": "string", "description": "Document type"},
                    "name": {"type": "string", "description": "Document name/ID"},
                    "data": {"type": "object", "description": "Updated document data"},
                },
                "required": ["doctype", "name", "data"],
            },
        ),
        types.Tool(
            name="execute_sql",
            description="Execute read-only SQL query on ERPNext database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_system_info",
            description="Get ERPNext system information",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="bench_command",
            description="Execute safe bench commands",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bench command to execute (status, version, migrate, etc.)",
                    }
                },
                "required": ["command"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""
    ctx = server.request_context
    erpnext_ctx = ctx.lifespan_context["erpnext"]

    if not erpnext_ctx.initialized:
        return [types.TextContent(type="text", text="Error: ERPNext not initialized")]

    try:
        result = await execute_tool(name, arguments)
        return [types.TextContent(type="text", text=result)]

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def execute_tool(name: str, arguments: dict) -> str:
    """Execute the requested tool."""
    if name == "list_doctypes":
        return await list_doctypes()

    elif name == "get_document":
        doctype = arguments["doctype"]
        doc_name = arguments["name"]
        return await get_document(doctype, doc_name)

    elif name == "search_documents":
        doctype = arguments["doctype"]
        query = arguments["query"]
        limit = arguments.get("limit", 20)
        return await search_documents(doctype, query, limit)

    elif name == "create_document":
        doctype = arguments["doctype"]
        data = arguments["data"]
        return await create_document(doctype, data)

    elif name == "update_document":
        doctype = arguments["doctype"]
        doc_name = arguments["name"]
        data = arguments["data"]
        return await update_document(doctype, doc_name, data)

    elif name == "execute_sql":
        query = arguments["query"]
        return await execute_sql_query(query)

    elif name == "get_system_info":
        return await get_system_info()

    elif name == "bench_command":
        command = arguments["command"]
        return await execute_bench_command(command)

    # ─── OKF tools ────────────────────────────────────────────────────────
    elif name == "okf_export_doctype":
        return await okf_export_doctype(
            arguments["doctype"],
            arguments.get("site") or frappe.local.site,
            arguments["bundle"],
            arguments.get("overwrite", False),
        )

    elif name == "okf_list_concepts":
        return await okf_list_concepts(
            arguments["bundle"],
            type=arguments.get("type"),
            tag=arguments.get("tag"),
        )

    elif name == "okf_get_concept":
        return await okf_get_concept(arguments["bundle"], arguments["path"])

    elif name == "okf_search":
        return await okf_search(
            arguments["bundle"],
            arguments["query"],
            limit=arguments.get("limit", 20),
            type=arguments.get("type"),
        )

    elif name == "okf_validate_bundle":
        return await okf_validate_bundle(arguments["bundle"])

    elif name == "okf_export_site_catalog":
        return await okf_export_site_catalog(
            arguments["site"],
            arguments["bundle"],
            doctype_filter=arguments.get("doctype_filter"),
            module_filter=arguments.get("module_filter"),
            include_custom=arguments.get("include_custom", True),
            include_core=arguments.get("include_core", False),
            limit=arguments.get("limit", 200),
        )

    elif name == "okf_recommend_skill":
        return await okf_recommend_skill(
            arguments["bundle"],
            arguments["task_description"],
            limit=arguments.get("limit", 5),
        )

    else:
        raise ValueError(f"Unknown tool: {name}")


# Tool implementations
async def list_doctypes() -> str:
    """List all doctypes."""
    try:
        doctypes = frappe.get_all(
            "DocType",
            fields=["name", "module", "is_custom", "description"],
            filters={"istable": 0},
            order_by="name",
        )
        result = "📋 Available DocTypes:\n\n"
        for dt in doctypes:
            icon = "🔧" if dt.get("is_custom") else "📄"
            result += f"{icon} {dt['name']} ({dt.get('module', 'Unknown')})\n"
            if dt.get("description"):
                result += f"   {dt['description']}\n"

        return result

    except Exception as e:
        raise Exception(f"Failed to list doctypes: {e}")


async def get_document(doctype: str, name: str) -> str:
    """Get a specific document."""
    try:
        doc = frappe.get_doc(doctype, name)
        doc_dict = doc.as_dict()

        result = f"📄 Document: {doctype} - {name}\n\n"

        # Show key fields first
        key_fields = [
            "name",
            "title",
            "subject",
            "customer",
            "supplier",
            "item_code",
            "status",
        ]
        shown_fields = set()

        for field in key_fields:
            if field in doc_dict and doc_dict[field]:
                result += f"{field}: {doc_dict[field]}\n"
                shown_fields.add(field)

        result += "\n--- All Fields ---\n"
        for field, value in doc_dict.items():
            if field not in shown_fields and not field.startswith("_"):
                if isinstance(value, (str, int, float)):
                    result += f"{field}: {value}\n"
                elif isinstance(value, list) and value:
                    result += f"{field}: [{len(value)} items]\n"
        return result
    except Exception as e:
        raise Exception(f"Failed to get document {doctype}/{name}: {e}")


async def search_documents(doctype: str, query: str, limit: int = 20) -> str:
    """Search documents."""
    try:
        results = frappe.get_all(
            doctype,
            filters=[["name", "like", f"%{query}%"]],
            fields=["name", "modified"],
            limit=limit,
            order_by="modified desc",
        )

        if not results:
            return f"🔍 No results found for '{query}' in {doctype}"

        result = f"🔍 Search Results for '{query}' in {doctype}:\n\n"
        for i, doc in enumerate(results, 1):
            result += (
                f"{i}. {doc['name']} (Modified: {doc.get('modified', 'Unknown')})\n"
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to search {doctype}: {e}")


async def create_document(doctype: str, data: dict) -> str:
    """Create a new document."""
    try:
        if not isinstance(data, dict):
            raise ValueError("The 'data' argument must be a dictionary.")
        doc = frappe.get_doc({"doctype": doctype, **data})
        doc.insert()
        frappe.db.commit()

        return f"✅ Created {doctype}: {doc.name}"

    except Exception as e:
        raise Exception(f"Failed to create {doctype}: {e}")


async def update_document(doctype: str, name: str, data: dict) -> str:
    """Update an existing document."""
    try:
        doc = frappe.get_doc(doctype, name)
        doc.update(data)
        doc.save()
        frappe.db.commit()

        return f"✅ Updated {doctype}: {name}"

    except Exception as e:
        raise Exception(f"Failed to update {doctype}/{name}: {e}")


async def execute_sql_query(query: str) -> str:
    """Execute SQL query."""
    try:
        # Security check
        if not query.strip().upper().startswith("SELECT"):
            raise Exception("Only SELECT queries are allowed for security")

        results = list(frappe.db.sql(query, as_dict=True))

        if not results:
            return "📊 Query executed successfully - No results"

        result = f"📊 Query Results ({len(results)} rows):\n\n"

        # Show first few rows in formatted way
        for i, row in enumerate(results[:10]):
            result += f"Row {i + 1}:\n"
            if isinstance(row, dict):
                for key, value in row.items():
                    result += f" {key}: {value}\n"
            elif isinstance(row, (list, tuple)):
                for idx, value in enumerate(row):
                    result += f" {idx}: {value}\n"
            else:
                result += f" {row}\n"
            result += "\n"

        if len(results) > 10:
            result += f"... and {len(results) - 10} more rows\n"

        return result
    except Exception as e:
        raise Exception(f"SQL query failed: {e}")


async def get_system_info() -> str:
    """Get system information."""
    try:
        info = {
            "site": frappe.local.site,
            "frappe_version": frappe.__version__,
            "apps": frappe.get_installed_apps(),
            "db_name": frappe.conf.db_name,
            "current_user": getattr(frappe.session, "user", "Unknown"),
        }

        result = "🖥️ ERPNext System Information:\n\n"
        result += f"Site: {info['site']}\n"
        result += f"Frappe Version: {info['frappe_version']}\n"
        result += f"Database: {info['db_name']}\n"
        result += f"Current User: {info['current_user']}\n"
        result += f"\nInstalled Apps ({len(info['apps'])}):\n"

        for app in info["apps"]:
            result += f"  • {app}\n"

        return result

    except Exception as e:
        raise Exception(f"Failed to get system info: {e}")


async def execute_bench_command(command: str) -> str:
    """Execute bench command."""
    import subprocess

    try:
        # Security: only allow safe commands
        safe_commands = ["status", "version", "migrate", "list", "restart"]
        cmd_parts = command.split()

        if not cmd_parts or cmd_parts[0] not in safe_commands:
            raise Exception(f"Command not allowed. Safe commands: {safe_commands}")

        # Execute command
        result = subprocess.run(
            ["bench"] + cmd_parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=frappe.get_site_path(".."),
        )

        output = f"🔧 Bench Command: {command}\n\n"

        if result.returncode == 0:
            output += f"✅ Success:\n{result.stdout}"
        else:
            output += f"❌ Failed (code {result.returncode}):\n{result.stderr}"

        return output

    except subprocess.TimeoutExpired:
        raise Exception("Command timed out after 30 seconds")
    except Exception as e:
        raise Exception(f"Bench command failed: {e}")


# ─── OKF (Open Knowledge Format) tool implementations ─────────────────────
#
# These wrap the erpnext_mcp_server.okf module. Bundles are stored under
# <frappe-bench>/apps/erpnext_mcp_server/erpnext_mcp_server/okf/bundles/<bundle>/

from pathlib import Path as _Path

OKF_BUNDLES_ROOT = _Path(__file__).parent / "okf" / "bundles"
OKF_BUNDLES_ROOT.mkdir(parents=True, exist_ok=True)


def _bundle_path(bundle: str) -> _Path:
    """Resolve a bundle name to its directory path. Raises if unsafe."""
    from erpnext_mcp_server.okf.validator import is_safe_bundle_name
    if not is_safe_bundle_name(bundle):
        raise ValueError(
            f"Invalid bundle name: '{bundle}'. "
            "Must match ^[a-z0-9][a-z0-9_-]{{0,63}}$"
        )
    return OKF_BUNDLES_ROOT / bundle


def _format_concept_summary(item: dict) -> str:
    """Format a single concept for MCP text response."""
    parts = [f"**{item.get('title', '?')}** — `{item.get('path', '?')}`"]
    if item.get("type"):
        parts.append(f"  - Type: `{item['type']}`")
    if item.get("description"):
        parts.append(f"  - {item['description'][:120]}")
    if item.get("tags"):
        tags_str = ", ".join(f"`{t}`" for t in item["tags"][:6])
        parts.append(f"  - Tags: {tags_str}")
    if item.get("snippet"):
        parts.append(f"  - Snippet: {item['snippet'][:200]}")
    if item.get("score") is not None:
        parts.append(f"  - Score: {item['score']}")
    return "\n".join(parts)


async def okf_export_doctype(doctype: str, site: str, bundle: str, overwrite: bool = False) -> str:
    """Export a single DocType as an OKF concept."""
    from erpnext_mcp_server.okf.exporter import export_doctype
    bundle_root = _bundle_path(bundle)
    bundle_root.mkdir(parents=True, exist_ok=True)
    result = export_doctype(doctype, bundle_root, site, overwrite=overwrite)
    return (
        f"✅ Exported DocType `{doctype}` to OKF concept\n"
        f"  - Path: `{result['path']}`\n"
        f"  - Fields: {result['fields_total']} total, {result['fields_redacted']} redacted\n"
        f"  - Child tables: {result['child_tables']}\n\n"
        f"Run `/usage` (well, `okf_validate_bundle {bundle}`) to regenerate the index."
    )


async def okf_list_concepts(bundle: str, type: str | None = None, tag: str | None = None) -> str:
    """List concepts in a bundle, optionally filtered."""
    from erpnext_mcp_server.okf.search import list_concepts
    bundle_root = _bundle_path(bundle)
    if not bundle_root.exists():
        return f"❌ Bundle '{bundle}' does not exist. Run `okf_export_site_catalog` first."
    concepts = list_concepts(bundle_root, type=type, tag=tag)
    if not concepts:
        return f"📭 No concepts found in bundle '{bundle}'" + (
            f" with type='{type}'" if type else ""
        ) + (f" tag='{tag}'" if tag else "")
    header = f"📚 {len(concepts)} concept(s) in bundle '{bundle}'"
    if type:
        header += f" (type={type})"
    if tag:
        header += f" (tag={tag})"
    body = "\n\n".join(_format_concept_summary(c) for c in concepts[:50])
    if len(concepts) > 50:
        body += f"\n\n_... and {len(concepts) - 50} more. Narrow with type/tag filter._"
    return f"{header}\n\n{body}"


async def okf_get_concept(bundle: str, path: str) -> str:
    """Read a single concept by path."""
    from erpnext_mcp_server.okf.search import get_concept
    bundle_root = _bundle_path(bundle)
    concept = get_concept(bundle_root, path)
    if concept is None:
        return (
            f"❌ Concept not found or unsafe path: `{path}`\n"
            f"  - Bundle: `{bundle}`\n"
            f"  - Allowed: relative paths like `doctypes/sales-invoice.md`\n"
            f"  - Rejected: `..`, absolute paths, paths with null bytes"
        )
    fm = concept.get("frontmatter") or {}
    body = concept.get("body", "").strip()
    fm_str = "\n".join(f"  {k}: {v}" for k, v in fm.items())
    return (
        f"📄 `{concept['path']}`\n\n"
        f"**Frontmatter:**\n```yaml\n{fm_str}\n```\n\n"
        f"**Body:**\n```markdown\n{body[:3000]}\n```\n"
        + ("\n\n_...truncated. Read the file directly for full content._" if len(body) > 3000 else "")
    )


async def okf_search(bundle: str, query: str, limit: int = 20, type: str | None = None) -> str:
    """Text search across concepts."""
    from erpnext_mcp_server.okf.search import search_bundle
    bundle_root = _bundle_path(bundle)
    if not bundle_root.exists():
        return f"❌ Bundle '{bundle}' does not exist."
    results = search_bundle(bundle_root, query, limit=limit, type=type)
    if not results:
        return f"📭 No matches for query '{query}'" + (f" (type={type})" if type else "")
    header = f"🔍 {len(results)} result(s) for '{query}' in '{bundle}'"
    body = "\n\n".join(_format_concept_summary(r) for r in results)
    return f"{header}\n\n{body}"


async def okf_validate_bundle(bundle: str) -> str:
    """Validate a bundle."""
    from erpnext_mcp_server.okf.validator import validate_bundle as _validate
    from erpnext_mcp_server.okf.bundle import generate_index
    bundle_root = _bundle_path(bundle)
    if not bundle_root.exists():
        return f"❌ Bundle '{bundle}' does not exist."
    result = _validate(bundle_root)
    # Regenerate index if it exists (or create if missing)
    try:
        idx_path = generate_index(bundle_root)
        regen_note = f"\n\n✅ Index regenerated at `{idx_path}`"
    except Exception as e:
        regen_note = f"\n\n⚠️ Index regen failed: {e}"
    status = "✅ VALID" if result["valid"] else "❌ INVALID"
    err_str = "\n".join(f"  - {e}" for e in result["errors"][:20]) or "  (none)"
    warn_str = "\n".join(f"  - {w}" for w in result["warnings"][:20]) or "  (none)"
    return (
        f"{status} bundle '{bundle}'\n"
        f"  - Concepts: {result['concepts']}\n"
        f"  - Index present: {result['index_present']}\n\n"
        f"**Errors ({len(result['errors'])}):**\n{err_str}\n\n"
        f"**Warnings ({len(result['warnings'])}):**\n{warn_str}"
        f"{regen_note}"
    )


async def okf_export_site_catalog(
    site: str,
    bundle: str,
    *,
    doctype_filter: str | None = None,
    module_filter: str | None = None,
    include_custom: bool = True,
    include_core: bool = False,
    limit: int = 200,
) -> str:
    """Export all (or filtered) DocTypes from a site as OKF concepts."""
    from erpnext_mcp_server.okf.bundle import export_site_catalog
    bundle_root = _bundle_path(bundle)
    bundle_root.mkdir(parents=True, exist_ok=True)
    result = export_site_catalog(
        site=site,
        bundle_root=bundle_root,
        doctype_filter=doctype_filter,
        module_filter=module_filter,
        include_custom=include_custom,
        include_core=include_core,
    )
    return (
        f"✅ Site catalog exported\n"
        f"  - Site: `{result['site']}`\n"
        f"  - Bundle: `{result['bundle_path']}`\n"
        f"  - DocTypes exported: {result['doctypes_exported']}\n"
        f"  - DocTypes skipped: {result['doctypes_skipped']}\n"
        f"  - Fields redacted (secrets): {result['fields_redacted']}\n"
        f"  - Index: `{result['index_path']}`\n\n"
        f"Try: `okf_list_concepts {bundle}` or `okf_search {bundle} 'KBank'`"
    )


async def okf_recommend_skill(bundle: str, task_description: str, limit: int = 5) -> str:
    """Recommend Claude Skills matching a task description."""
    from erpnext_mcp_server.okf.search import recommend_skill
    bundle_root = _bundle_path(bundle)
    if not bundle_root.exists():
        return f"❌ Bundle '{bundle}' does not exist."
    results = recommend_skill(bundle_root, task_description, limit=limit)
    if not results:
        return (
            f"📭 No Claude Skills found matching: '{task_description}'\n"
            f"  - Hint: skills are stored under `{bundle_root}/skills/`\n"
            f"  - Run `export_skills(skills_root, bundle_root)` to populate"
        )
    header = f"🎯 Top {len(results)} skill recommendation(s) for: '{task_description}'"
    body = "\n\n".join(_format_concept_summary(r) for r in results)
    return f"{header}\n\n{body}"


async def run_server():
    """Run the MCP server."""
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ERPNext MCP Server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def main():
    """Entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
