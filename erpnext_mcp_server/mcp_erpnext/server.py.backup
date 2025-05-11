#!/usr/bin/env python3
"""
ERPNext MCP Server

This module implements a Model Context Protocol (MCP) server for ERPNext,
allowing AI models to interact with ERPNext through a standardized interface.

The server exposes ERPNext functionality as tools, resources, and prompts that can be used
by LLMs to perform operations such as:
- Reading, creating, and updating ERPNext documents
- Running reports and queries
- Executing custom functions and workflows
- Analyzing ERPNext data
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# First, try to ensure Frappe can be imported
try:
    import frappe
    from frappe.utils import get_site_name, get_site_path
    from frappe.exceptions import DoesNotExistError, ValidationError
    from frappe.utils.background_jobs import execute_job
    from pydantic import AnyUrl
    from pydantic.networks import UrlConstraints
    import frappe.defaults
    from frappe.model.document import Document

    FRAPPE_AVAILABLE = True
    FRAPPE_ERROR = None
except ImportError as e:
    FRAPPE_AVAILABLE = False
    FRAPPE_ERROR = str(e)
    frappe = None
    print(f"Warning: ERPNext/Frappe not fully available: {e}")
    print("Some functionalities will be limited.")

# Import MCP components
try:
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.server.fastmcp.utilities.types import Image
    from mcp.server.fastmcp.resources import TextResource, FunctionResource

    MCP_AVAILABLE = True
    MCP_ERROR = None
except ImportError as e:
    MCP_AVAILABLE = False
    MCP_ERROR = str(e)
    print(f"Error: MCP modules not found: {e}")
    print("Please ensure the MCP library is installed: pip install mcp")
    if not FRAPPE_AVAILABLE:
        print("Additionally, Frappe is not available.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("erp_mcp_server")

# Initialize server status
FRAPPE_INITIALIZED = False
INITIALIZATION_ERROR = None


def initialize_frappe():
    """Initialize Frappe framework for database operations"""
    global FRAPPE_INITIALIZED, INITIALIZATION_ERROR

    if not FRAPPE_AVAILABLE:
        INITIALIZATION_ERROR = "Frappe/ERPNext is not installed"
        return False

    try:
        # Check if Frappe is already initialized
        if hasattr(frappe, "local") and frappe.local and frappe.local.site:
            FRAPPE_INITIALIZED = True
            return True

        # Get site from environment or detect it
        site = os.environ.get("FRAPPE_SITE") or os.environ.get("SITE")

        if not site:
            # Try to detect site from current directory
            current_dir = os.getcwd()
            if "sites" in current_dir:
                site_path = Path(current_dir)
                # Find the site name in the path
                for part in site_path.parts:
                    if part != "sites" and site_path.parent.name == "sites":
                        site = part
                        break

            if not site:
                # Try default site
                try:
                    from frappe.utils.commands import get_site_config_from_current_site

                    site = get_site_config_from_current_site().get("currentsite")
                except:
                    site = None

        if not site:
            raise ValueError(
                "Cannot determine ERPNext site. Please set FRAPPE_SITE environment variable."
            )

        # Initialize Frappe
        logger.info(f"Initializing Frappe for site: {site}")
        frappe.init(site=site, sites_path=os.environ.get("SITES_PATH"))

        # Connect to database
        if not frappe.db:
            frappe.connect()

        FRAPPE_INITIALIZED = True
        logger.info("Frappe initialized successfully")
        return True

    except Exception as e:
        INITIALIZATION_ERROR = str(e)
        logger.error(f"Failed to initialize Frappe: {e}")
        FRAPPE_INITIALIZED = False
        return False


def require_frappe_init(func):
    """Decorator to ensure Frappe is initialized before executing a function"""

    async def wrapper(*args, **kwargs):
        if not FRAPPE_INITIALIZED:
            initialize_frappe()

        if not FRAPPE_INITIALIZED:
            return {"error": f"Frappe not initialized: {INITIALIZATION_ERROR}"}

        return await func(*args, **kwargs)

    return wrapper


def frappe_method(func):
    """Decorator to safely execute Frappe methods with proper context"""

    async def wrapper(*args, **kwargs):
        try:
            # Ensure we have Frappe context
            if not FRAPPE_INITIALIZED:
                if not initialize_frappe():
                    return {
                        "error": f"Cannot initialize Frappe: {INITIALIZATION_ERROR}"
                    }

            # Create a new Frappe context if needed
            if not frappe.local or not frappe.local.site:
                initialize_frappe()

            # Execute the function
            result = await func(*args, **kwargs)

            # Commit any database transactions
            if frappe.db:
                frappe.db.commit()

            return result

        except Exception as e:
            # Rollback on error
            if frappe and frappe.db:
                frappe.db.rollback()

            logger.error(f"Error in {func.__name__}: {str(e)}")
            return {"error": str(e)}

    return wrapper


# Initialize the FastMCP server
erp_server = FastMCP(
    name="ERPNext MCP Server",
    instructions="""
    This server provides AI access to ERPNext functionality.
    
    Use the tools to:
    - Get information about documents (Customers, Invoices, etc.)
    - Create and update documents
    - Run reports and analyses
    - Execute workflows and custom functions
    
    Provide doctype names and document names accurately as they appear in ERPNext.
    
    Note: The server requires a properly initialized ERPNext environment.
    """,
)


# Helper functions
def sanitize_input(input_data: Dict) -> Dict:
    """Sanitize input data to prevent injection attacks"""
    if not isinstance(input_data, dict):
        return input_data

    result = {}
    for key, value in input_data.items():
        if isinstance(value, dict):
            result[key] = sanitize_input(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_input(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str):
            # Basic sanitization - remove any potential SQL injection patterns
            result[key] = value.replace(";", "").replace("--", "")
        else:
            result[key] = value

    return result


def get_fields_for_doctype(doctype: str) -> List[Dict]:
    """Get available fields for a doctype"""
    try:
        if not FRAPPE_INITIALIZED:
            raise RuntimeError("Frappe not initialized")

        meta = frappe.get_meta(doctype)
        return [
            {"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}
            for f in meta.fields
        ]
    except Exception as e:
        logger.error(f"Error getting fields for {doctype}: {str(e)}")
        return []


def handle_frappe_response(response: Any) -> Dict[str, Any]:
    """Convert Frappe responses to a consistent format"""
    try:
        if hasattr(response, "as_dict"):
            return response.as_dict()
        elif isinstance(response, dict):
            return response
        elif isinstance(response, list):
            return {"items": response, "count": len(response)}
        else:
            return {"result": str(response)}
    except Exception as e:
        return {"result": str(response), "conversion_error": str(e)}


# Status check tool
@erp_server.tool(
    name="check_status",
    description="Check the status of the ERPNext MCP server and Frappe initialization",
)
async def check_status(ctx: Context) -> Dict[str, Any]:
    """Check if Frappe is properly initialized and accessible"""
    await ctx.info("Checking ERPNext MCP server status")

    status = {
        "mcp_available": MCP_AVAILABLE,
        "frappe_available": FRAPPE_AVAILABLE,
        "frappe_initialized": FRAPPE_INITIALIZED,
        "initialization_error": INITIALIZATION_ERROR,
        "site": None,
        "apps": [],
        "version": None,
    }

    if FRAPPE_INITIALIZED:
        try:
            status["site"] = (
                frappe.local.site if hasattr(frappe, "local") and frappe.local else None
            )
            status["apps"] = (
                frappe.get_installed_apps()
                if hasattr(frappe, "get_installed_apps")
                else []
            )
            status["version"] = (
                frappe.__version__ if hasattr(frappe, "__version__") else None
            )
        except Exception as e:
            status["status_check_error"] = str(e)

    return status


# Add tools for ERPNext document operations
@erp_server.tool(
    name="get_document", description="Retrieve a document from ERPNext by type and name"
)
@frappe_method
async def get_document(
    doctype: str, name: str, ctx: Context, fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get a document from ERPNext.

    Args:
        doctype: The DocType (e.g., 'Customer', 'Sales Invoice')
        name: The document name or ID
        fields: Optional list of specific fields to fetch

    Returns:
        The document data
    """
    await ctx.info(f"Fetching {doctype} document: {name}")

    # Validate doctype exists
    if not frappe.db.exists("DocType", doctype):
        return {"error": f"DocType '{doctype}' does not exist"}

    # Get document
    if fields:
        # Get only specified fields
        result = frappe.db.get_value(doctype, name, fields, as_dict=True)
        if not result:
            return {"error": f"Document {doctype}/{name} not found"}
        return handle_frappe_response(result)
    else:
        # Get full document
        doc = frappe.get_doc(doctype, name)
        doc.check_permission()
        return handle_frappe_response(doc)


@erp_server.tool(
    name="list_documents",
    description="List documents of a given type with optional filters",
)
@frappe_method
async def list_documents(
    doctype: str,
    ctx: Context,
    filters: Optional[Dict] = None,
    fields: Optional[List[str]] = None,
    limit: int = 20,
    order_by: str = "modified desc",
) -> Dict[str, Any]:
    """
    List documents of a given type.

    Args:
        doctype: The DocType to list (e.g., 'Customer', 'Sales Invoice')
        filters: Optional filters to apply (e.g., {"status": "Draft"})
        fields: Optional list of fields to include
        limit: Maximum number of documents to return
        order_by: Field to order results by (default: "modified desc")

    Returns:
        List of documents
    """
    await ctx.info(f"Listing {doctype} documents")

    # Validate doctype exists
    if not frappe.db.exists("DocType", doctype):
        return {"error": f"DocType '{doctype}' does not exist"}

    # Sanitize input
    safe_filters = sanitize_input(filters) if filters else None

    # Default fields if none provided
    if not fields:
        fields = ["name", "creation", "modified"]
        # Try to get standard fields for the doctype
        try:
            meta = frappe.get_meta(doctype)
            title_field = meta.get_title_field()
            if title_field and title_field != "name":
                fields.append(title_field)
            if hasattr(meta, "get_field"):
                status_field = meta.get_field("status")
                if status_field:
                    fields.append("status")
        except:
            pass

    # Get the documents
    docs = frappe.get_all(
        doctype,
        filters=safe_filters,
        fields=fields,
        limit_page_length=min(limit, 100),  # Cap at 100 for performance
        order_by=order_by,
    )

    # Count total matching documents
    total_count = frappe.db.count(doctype, filters=safe_filters)

    return {
        "items": docs,
        "count": len(docs),
        "total_count": total_count,
        "has_more": total_count > len(docs),
    }


@erp_server.tool(name="create_document", description="Create a new document in ERPNext")
@frappe_method
async def create_document(
    doctype: str, values: Dict, ctx: Context, submit: bool = False
) -> Dict[str, Any]:
    """
    Create a new document in ERPNext.

    Args:
        doctype: The DocType to create (e.g., 'Customer', 'Sales Invoice')
        values: Field values for the new document
        submit: Whether to submit the document after creation

    Returns:
        The created document
    """
    await ctx.info(f"Creating new {doctype}")

    # Validate doctype exists
    if not frappe.db.exists("DocType", doctype):
        return {"error": f"DocType '{doctype}' does not exist"}

    # Sanitize input
    safe_values = sanitize_input(values)

    # Create the document
    doc = frappe.new_doc(doctype)
    doc.update(safe_values)
    doc.insert()

    # Submit if requested
    if submit and hasattr(doc, "submit"):
        doc.submit()

    # Return the document
    return handle_frappe_response(doc)


@erp_server.tool(
    name="update_document", description="Update an existing document in ERPNext"
)
@frappe_method
async def update_document(
    doctype: str, name: str, values: Dict, ctx: Context, submit: bool = False
) -> Dict[str, Any]:
    """
    Update an existing document in ERPNext.

    Args:
        doctype: The DocType to update (e.g., 'Customer', 'Sales Invoice')
        name: The document name or ID
        values: Field values to update
        submit: Whether to submit the document after update

    Returns:
        The updated document
    """
    await ctx.info(f"Updating {doctype}: {name}")

    # Validate document exists
    if not frappe.db.exists(doctype, name):
        return {"error": f"Document {doctype}/{name} does not exist"}

    # Sanitize input
    safe_values = sanitize_input(values)

    # Get and update the document
    doc = frappe.get_doc(doctype, name)
    doc.update(safe_values)
    doc.save()

    # Submit if requested
    if submit and hasattr(doc, "submit") and doc.docstatus == 0:
        doc.submit()

    # Return the document
    return handle_frappe_response(doc)


@erp_server.tool(
    name="execute_query", description="Execute a custom query with parameters"
)
@frappe_method
async def execute_query(
    query: str,
    ctx: Context,
    params: Optional[Dict] = None,
    as_dict: bool = True,
) -> Dict[str, Any]:
    """
    Execute a custom query with parameters.

    Args:
        query: The SQL query to execute (must use %(param)s format for parameters)
        params: Parameters for the query
        as_dict: Whether to return results as dictionaries

    Returns:
        The query results
    """
    await ctx.info(f"Executing query {query}")

    # Check if query is allowed (only SELECT queries)
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT "):
        return {"error": "Only SELECT queries are allowed"}

    # Check for potentially dangerous operations
    dangerous_patterns = [
        "DROP ",
        "DELETE ",
        "UPDATE ",
        "INSERT ",
        "ALTER ",
        "TRUNCATE ",
        ";",
    ]
    for pattern in dangerous_patterns:
        if pattern in query_upper:
            return {"error": f"Query contains disallowed pattern: {pattern}"}

    # Sanitize parameters
    safe_params = sanitize_input(params) if params else {}

    # Execute the query
    result = frappe.db.sql(query, safe_params, as_dict=as_dict)

    # Convert to list for JSON serialization
    if not isinstance(result, list):
        result = list(result)

    return {"results": result, "count": len(result)}


@erp_server.tool(
    name="get_system_info", description="Get system information from ERPNext"
)
@frappe_method
async def get_system_info(ctx: Context) -> Dict[str, Any]:
    """Get system information from ERPNext."""
    await ctx.info("Getting system information")

    # Get ERPNext information
    frappe_version = frappe.__version__
    site_name = get_site_name(
        frappe.local.request.host if hasattr(frappe.local, "request") else None
    )

    # Try to get ERPNext version if installed
    erpnext_version = None
    if frappe.db.exists("Module Def", "ERPNext"):
        try:
            from erpnext import __version__ as erpnext_version
        except ImportError:
            erpnext_version = "Unknown"

    # Get installation details
    config = frappe.get_site_config()
    db_name = config.get("db_name", "Unknown")
    installed_apps = frappe.get_installed_apps()

    # Get user counts
    user_count = frappe.db.count("User", {"enabled": 1})

    return {
        "frappe_version": frappe_version,
        "erpnext_version": erpnext_version,
        "site_name": site_name,
        "database": db_name,
        "installed_apps": installed_apps,
        "active_users": user_count,
        "timestamp": datetime.now().isoformat(),
    }


# Add a tool to run Frappe methods
@erp_server.tool(name="run_frappe_method", description="Run a Frappe method")
@frappe_method
async def run_frappe_method(
    method_path: str,
    ctx: Context,
    args: Optional[List] = None,
    kwargs: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run a Frappe method.

    Args:
        method_path: The path to the method (e.g., 'frappe.model.get_value')
        args: Positional arguments for the method
        kwargs: Keyword arguments for the method

    Returns:
        The method result
    """
    await ctx.info(f"Running Frappe method: {method_path}")

    args = args or []
    kwargs = kwargs or {}

    # Basic security check
    if method_path.startswith("frappe.") or method_path.startswith("erpnext."):
        try:
            # Import the method
            module_path, method_name = method_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[method_name])
            method = getattr(module, method_name)

            # Call the method
            result = method(*args, **kwargs)

            return handle_frappe_response(result)
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "Only frappe.* and erpnext.* methods are allowed"}


# Add resources
@erp_server.resource("resource://erp/status")
async def get_status_resource() -> str:
    """Resource for server status"""
    status = {
        "frappe_available": FRAPPE_AVAILABLE,
        "frappe_initialized": FRAPPE_INITIALIZED,
        "initialization_error": INITIALIZATION_ERROR,
        "mcp_version": "1.0.0",
        "server_time": datetime.now().isoformat(),
    }

    if FRAPPE_INITIALIZED:
        try:
            status.update(
                {
                    "site": frappe.local.site,
                    "frappe_version": frappe.__version__,
                    "apps": frappe.get_installed_apps(),
                }
            )
        except:
            pass

    return json.dumps(status, indent=2)


# Startup initialization
async def startup_initialization():
    """Initialize the server on startup"""
    logger.info("Starting ERPNext MCP Server...")

    # Try to initialize Frappe
    if initialize_frappe():
        logger.info("Frappe initialized successfully")
    else:
        logger.warning(f"Frappe initialization failed: {INITIALIZATION_ERROR}")
        logger.warning("Limited functionality available")

    return FRAPPE_INITIALIZED


# Run the server
async def run_server():
    """Run the MCP server"""
    # Initialize on startup
    await startup_initialization()

    # Get transport from environment
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    # Run the server
    erp_server.run(transport=transport)


if __name__ == "__main__":
    # Set up environment
    if not os.environ.get("FRAPPE_SITE") and not os.environ.get("SITE"):
        logger.warning("No FRAPPE_SITE environment variable set")
        logger.warning("Trying to auto-detect site...")

    # Run the server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
