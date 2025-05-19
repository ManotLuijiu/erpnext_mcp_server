import json
import os
from datetime import datetime
from pathlib import Path

import frappe
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import TextContent, Annotations

# Initialize the MCP server with a name and instructions
server = FastMCP(
    name="ERPNext MCP Server",
    instructions="""
    This server provides tools to automate and interact with ERPNext.
    Available functionality:
    - Query documents (read-only)
    - File operations
    - Export/import data
    - Generate reports
    - Access translations
    """,
)

# --- DOCUMENT TOOLS ---


@server.tool(
    description="Get a document from the database",
    annotations=Annotations(readOnlyHint=True),
)
async def get_document(doctype: str, name: str, ctx: Context = None) -> dict:
    """Retrieve a document from ERPNext by doctype and name.

    Args:
        doctype: The DocType to retrieve (e.g., Customer, Item, Sales Invoice)
        name: The name of the document to retrieve

    Returns:
        Document data as a dictionary
    """
    try:
        await ctx.info(f"Retrieving {doctype}: {name}")
        doc = frappe.get_doc(doctype, name)
        return doc.as_dict()
    except Exception as e:
        await ctx.error(f"Error retrieving document: {e}")
        return {"error": str(e)}


@server.tool(
    description="Query documents from the database with filters",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def query_documents(
    doctype: str,
    filters: str = "{}",
    fields: str = "*",
    limit: int = 20,
    ctx: Context = None,
) -> list:
    """Query documents from the database with filters.

    Args:
        doctype: The DocType to query (e.g., Customer, Item, Sales Invoice)
        filters: JSON string of filters in the format: {"field1": "value1", "field2": [">=", "value2"]}
        fields: Comma-separated list of fields or "*" for all fields
        limit: Maximum number of records to return

    Returns:
        List of document data matching the query
    """
    try:
        await ctx.info(f"Querying {doctype} with filters: {filters}")

        # Parse filters if provided as a string
        if isinstance(filters, str):
            filters_dict = json.loads(filters)
        else:
            filters_dict = filters

        # Handle fields
        field_list = fields
        if isinstance(fields, str) and "," in fields:
            field_list = [f.strip() for f in fields.split(",")]

        result = frappe.get_all(
            doctype, filters=filters_dict, fields=field_list, limit_page_length=limit
        )

        await ctx.info(f"Found {len(result)} records")
        return result
    except Exception as e:
        await ctx.error(f"Error querying documents: {e}")
        return {"error": str(e)}


@server.tool(
    description="Count documents matching filters",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def count_documents(
    doctype: str, filters: str = "{}", ctx: Context = None
) -> dict:
    """Count documents matching specified filters.

    Args:
        doctype: The DocType to count
        filters: JSON string of filters

    Returns:
        Dictionary with count of matching documents
    """
    try:
        # Parse filters if provided as a string
        if isinstance(filters, str):
            filters_dict = json.loads(filters)
        else:
            filters_dict = filters

        count = frappe.db.count(doctype, filters_dict)
        return {"doctype": doctype, "count": count}
    except Exception as e:
        await ctx.error(f"Error counting documents: {e}")
        return {"error": str(e)}


# --- FILE TOOLS ---


@server.tool(
    description="List files in a directory",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_files(path: str = ".", ctx: Context = None) -> list:
    """List files in a specified directory.

    Args:
        path: Relative path from the site directory

    Returns:
        List of files with metadata
    """
    try:
        site_path = frappe.get_site_path()
        target_path = os.path.join(site_path, path)

        if not os.path.exists(target_path):
            await ctx.error(f"Path does not exist: {target_path}")
            return {"error": f"Path does not exist: {path}"}

        await ctx.info(f"Listing files in {target_path}")

        files = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            files.append(
                {
                    "name": item,
                    "path": os.path.relpath(item_path, site_path),
                    "is_dir": os.path.isdir(item_path),
                    "size": (
                        os.path.getsize(item_path)
                        if not os.path.isdir(item_path)
                        else 0
                    ),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).isoformat(),
                }
            )

        return files
    except Exception as e:
        await ctx.error(f"Error listing files: {e}")
        return {"error": str(e)}


@server.tool(
    description="Read file contents", annotations=ToolAnnotations(readOnlyHint=True)
)
async def read_file(path: str, ctx: Context = None) -> dict:
    """Read a file's contents.

    Args:
        path: Relative path from the site directory

    Returns:
        File contents as text or base64 encoded for binary files
    """
    try:
        site_path = frappe.get_site_path()
        file_path = os.path.join(site_path, path)

        if not os.path.exists(file_path) or os.path.isdir(file_path):
            await ctx.error(f"File does not exist: {file_path}")
            return {"error": f"File does not exist: {path}"}

        # Get file extension to determine if it's a text file
        _, ext = os.path.splitext(file_path)
        text_extensions = [
            ".txt",
            ".csv",
            ".md",
            ".json",
            ".py",
            ".js",
            ".html",
            ".css",
            ".xml",
            ".log",
        ]

        is_text = ext.lower() in text_extensions

        await ctx.info(f"Reading file: {path}")

        if is_text:
            # Read as text
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"path": path, "is_text": True, "content": content}
        else:
            # Read as binary and convert to base64
            import base64

            with open(file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            return {
                "path": path,
                "is_text": False,
                "content": content,
                "encoding": "base64",
            }
    except Exception as e:
        await ctx.error(f"Error reading file: {e}")
        return {"error": str(e)}


# --- TRANSLATION TOOLS ---


@server.tool(
    description="Get a translation for a string",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_translation(
    source_text: str, language: str = None, ctx: Context = None
) -> dict:
    """Get the translation for a text string.

    Args:
        source_text: The text to translate
        language: Target language code (e.g., 'th' for Thai)

    Returns:
        Translation information
    """
    try:
        await ctx.info(f"Getting translation for: {source_text}")

        if not language:
            # Get user's language preference
            language = frappe.local.lang or frappe.db.get_default("lang") or "en"

        # Check if translation exists
        translation = None
        if language != "en":
            translation = frappe.db.get_value(
                "Translation",
                {"source_text": source_text, "language": language},
                ["name", "translated_text"],
            )

        return {
            "source_text": source_text,
            "language": language,
            "translated_text": translation[1] if translation else source_text,
            "exists": bool(translation),
        }
    except Exception as e:
        await ctx.error(f"Error getting translation: {e}")
        return {"error": str(e)}


@server.tool(
    description="Search for translations",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_translations(
    search_text: str,
    language: str = None,
    search_in: str = "both",
    limit: int = 10,
    ctx: Context = None,
) -> list:
    """Search for translations containing the specified text.

    Args:
        search_text: Text to search for
        language: Language code to filter by
        search_in: Where to search - 'source', 'translated', or 'both'
        limit: Maximum number of results to return

    Returns:
        List of matching translations
    """
    try:
        await ctx.info(f"Searching translations for: {search_text}")

        if not language:
            # Get user's language preference
            language = frappe.local.lang or frappe.db.get_default("lang") or "en"

        filters = {"language": language}
        or_filters = {}

        if search_in == "source" or search_in == "both":
            or_filters["source_text"] = ["like", f"%{search_text}%"]

        if search_in == "translated" or search_in == "both":
            or_filters["translated_text"] = ["like", f"%{search_text}%"]

        translations = frappe.get_all(
            "Translation",
            filters=filters,
            or_filters=or_filters,
            fields=["name", "source_text", "translated_text", "language"],
            limit=limit,
        )

        await ctx.info(f"Found {len(translations)} matches")
        return translations
    except Exception as e:
        await ctx.error(f"Error searching translations: {e}")
        return {"error": str(e)}


# --- REPORT TOOLS ---


@server.tool(
    description="Generate a script report",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def run_report(
    report_name: str, filters: str = "{}", ctx: Context = None
) -> dict:
    """Run a script report with the specified filters.

    Args:
        report_name: Name of the report to run
        filters: JSON string of filters to apply

    Returns:
        Report results
    """
    try:
        await ctx.info(f"Running report: {report_name}")

        # Parse filters if provided as a string
        if isinstance(filters, str):
            filters_dict = json.loads(filters)
        else:
            filters_dict = filters

        # Get report doc
        report = frappe.get_doc("Report", report_name)

        if report.report_type != "Script Report":
            await ctx.warning(
                f"Only Script Reports are supported. {report_name} is a {report.report_type}."
            )
            return {
                "error": f"Only Script Reports are supported. {report_name} is a {report.report_type}."
            }

        # Run the report
        result = report.execute_script_report(filters_dict)

        # Format result
        columns = result[0]
        data = result[1]

        return {
            "report_name": report_name,
            "columns": columns,
            "data": data,
            "filters": filters_dict,
        }
    except Exception as e:
        await ctx.error(f"Error running report: {e}")
        return {"error": str(e)}


# --- SYSTEM TOOLS ---


@server.tool(
    description="Get system information", annotations=ToolAnnotations(readOnlyHint=True)
)
async def get_system_info(ctx: Context = None) -> dict:
    """Get basic system information.

    Returns:
        System information including version, site name, etc.
    """
    try:
        await ctx.info("Retrieving system information")

        import frappe.utils

        return {
            "frappe_version": frappe.__version__,
            "site_name": frappe.local.site,
            "installed_apps": frappe.get_installed_apps(),
            "user": frappe.session.user,
            "system_settings": {
                "time_zone": frappe.db.get_default("time_zone"),
                "language": frappe.db.get_default("lang"),
                "date_format": frappe.db.get_default("date_format"),
            },
        }
    except Exception as e:
        await ctx.error(f"Error getting system info: {e}")
        return {"error": str(e)}


@server.tool(
    description="Execute a database query (read-only)",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def execute_query(query: str, values: str = None, ctx: Context = None) -> list:
    """Execute a read-only SQL query.

    For security reasons, only SELECT statements are allowed.

    Args:
        query: SQL query to execute (SELECT only)
        values: JSON array of parameter values if using parameterized queries

    Returns:
        Query results
    """
    try:
        # Enforce SELECT-only
        query = query.strip()
        if not query.lower().startswith("select "):
            await ctx.error("Only SELECT queries are allowed for security reasons")
            return {"error": "Only SELECT queries are allowed"}

        # Parse values if provided as a string
        if values and isinstance(values, str):
            values_list = json.loads(values)
        else:
            values_list = values

        await ctx.info(f"Executing query: {query}")

        # Execute the query
        result = frappe.db.sql(query, values=values_list, as_dict=True)

        await ctx.info(f"Query returned {len(result)} rows")
        return result
    except Exception as e:
        await ctx.error(f"Error executing query: {e}")
        return {"error": str(e)}


# --- TRANSLATION TOOLS SPECIFIC FEATURES ---


@server.tool(
    description="Search for translations in translation_tools",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_translation_tools(
    search_text: str, language_code: str = "th", ctx: Context = None
) -> list:
    """Search for translations in the translation_tools app.

    Args:
        search_text: Text to search for
        language_code: Language code (default: th for Thai)

    Returns:
        List of matching translations
    """
    try:
        await ctx.info(f"Searching translation_tools for: {search_text}")

        # Check if translation_tools is installed
        if "translation_tools" not in frappe.get_installed_apps():
            await ctx.error("The translation_tools app is not installed")
            return {"error": "The translation_tools app is not installed"}

        # Query the Translation doctype or custom table depending on implementation
        # This is a placeholder - adjust based on actual translation_tools schema
        translations = frappe.get_all(
            "Translation",
            filters={
                "language": language_code,
                "source_text": ["like", f"%{search_text}%"],
            },
            fields=["name", "source_text", "translated_text", "language"],
            limit=20,
        )

        await ctx.info(f"Found {len(translations)} matches")
        return translations
    except Exception as e:
        await ctx.error(f"Error searching translations: {e}")
        return {"error": str(e)}


@server.tool(
    description="Get translation statistics",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_translation_stats(language_code: str = "th", ctx: Context = None) -> dict:
    """Get translation statistics for the specified language.

    Args:
        language_code: Language code (default: th for Thai)

    Returns:
        Statistics about translations
    """
    try:
        await ctx.info(f"Getting translation statistics for language: {language_code}")

        # Check if translation_tools is installed
        if "translation_tools" not in frappe.get_installed_apps():
            await ctx.error("The translation_tools app is not installed")
            return {"error": "The translation_tools app is not installed"}

        # Get total translations
        total = frappe.db.count("Translation", {"language": language_code})

        # Get counts of translations with missing translated_text
        missing = frappe.db.count(
            "Translation",
            {"language": language_code, "translated_text": ["in", ["", None]]},
        )

        # Get count of recently added translations
        import datetime

        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        recent = frappe.db.count(
            "Translation",
            {
                "language": language_code,
                "creation": [">", thirty_days_ago.strftime("%Y-%m-%d")],
            },
        )

        return {
            "language": language_code,
            "total_translations": total,
            "missing_translations": missing,
            "completion_percentage": (
                round((total - missing) / total * 100, 2) if total > 0 else 0
            ),
            "recently_added": recent,
        }
    except Exception as e:
        await ctx.error(f"Error getting translation stats: {e}")
        return {"error": str(e)}


@server.tool(
    description="Get chat room information",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_chat_rooms(limit: int = 10, ctx: Context = None) -> list:
    """Get information about chat rooms from translation_tools.

    Args:
        limit: Maximum number of rooms to return

    Returns:
        List of chat rooms
    """
    try:
        await ctx.info("Getting chat room information")

        # Check if translation_tools is installed
        if "translation_tools" not in frappe.get_installed_apps():
            await ctx.error("The translation_tools app is not installed")
            return {"error": "The translation_tools app is not installed"}

        # Query chat rooms - adjust fields based on actual schema
        rooms = frappe.get_all(
            "Chat Room",  # Adjust doctype name as needed
            fields=["name", "room_name", "type", "modified", "creation"],
            order_by="modified desc",
            limit=limit,
        )

        return rooms
    except Exception as e:
        await ctx.error(f"Error getting chat rooms: {e}")
        return {"error": str(e)}


@server.tool(
    description="Get chat messages from a room",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_chat_messages(room: str, limit: int = 20, ctx: Context = None) -> list:
    """Get messages from a specific chat room.

    Args:
        room: Name of the chat room
        limit: Maximum number of messages to return

    Returns:
        List of messages from the room
    """
    try:
        await ctx.info(f"Getting messages for chat room: {room}")

        # Check if translation_tools is installed
        if "translation_tools" not in frappe.get_installed_apps():
            await ctx.error("The translation_tools app is not installed")
            return {"error": "The translation_tools app is not installed"}

        # Query chat messages - adjust fields based on actual schema
        messages = frappe.get_all(
            "Chat Message",  # Adjust doctype name as needed
            filters={"room": room},
            fields=["name", "room", "content", "sender", "creation"],
            order_by="creation desc",
            limit=limit,
        )

        # Reverse to get messages in chronological order
        messages.reverse()

        return messages
    except Exception as e:
        await ctx.error(f"Error getting chat messages: {e}")
        return {"error": str(e)}
