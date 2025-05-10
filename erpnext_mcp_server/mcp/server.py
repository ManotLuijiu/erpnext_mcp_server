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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from frappe.query_builder.functions import Count
from pydantic import AnyUrl
from pydantic.networks import UrlConstraints
import frappe.defaults

# Import MCP components
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.utilities.types import Image
from mcp.server.fastmcp.resources import TextResource, FunctionResource

try:
    import frappe
    from frappe.utils import get_site_name, get_site_path
    from frappe.exceptions import DoesNotExistError, ValidationError
except ImportError:
    print(
        "ERPNext/Frappe not found. Make sure this is running in a Frappe environment."
    )
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("erp_mcp_server")

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
    if hasattr(response, "as_dict"):
        return response.as_dict()
    elif isinstance(response, dict):
        return response
    elif isinstance(response, list):
        return {"items": response, "count": len(response)}
    else:
        return {"result": str(response)}


# Add tools for ERPNext document operations
@erp_server.tool(
    name="get_document", description="Retrieve a document from ERPNext by type and name"
)
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
    try:
        # Validate doctype exists
        if not frappe.db.exists("DocType", doctype):
            return {"error": f"DocType '{doctype}' does not exist"}

        # Get document
        # doc = frappe.get_doc(doctype, name)

        # Check user permissions
        # doc.check_permission()

        if fields:
            # Get only specified fields
            # Type annotation in frappe.db.get_value expects a string for fieldname
            # but the actual implementation supports a list of fields
            from typing import cast

            result = frappe.db.get_value(doctype, name, cast(str, fields), as_dict=True)
            if not result:
                raise DoesNotExistError(f"Document {doctype}/{name} not found")
            return handle_frappe_response(result)
        else:
            # Get full document
            doc = frappe.get_doc(doctype, name)
            doc.check_permission()
            return handle_frappe_response(doc)
    except DoesNotExistError:
        await ctx.error(f"Document not found: {doctype}/{name}")
        return {"error": f"Document not found: {doctype}/{name}"}
    except Exception as e:
        await ctx.error(f"Error fetching document: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(
    name="list_documents",
    description="List documents of a given type with optional filters",
)
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
    try:
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
                # Use get_title_field() method if available, otherwise try to get title_field safely
                if hasattr(meta, "get_title_field"):
                    title_field = meta.get_title_field()
                else:
                    # Try to get title_field through getattr with a default value of None
                    title_field = getattr(meta, "title_field", None)

                if title_field and title_field != "name":
                    fields.append(title_field)
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
        DocType = frappe.qb.DocType(doctype)
        count_query = frappe.qb.from_(DocType).select(Count(DocType.name).as_("total"))

        # Apply filters if provided
        if safe_filters:
            for field, value in safe_filters.items():
                count_query = count_query.where(getattr(DocType, field) == value)

        result = list(frappe.db.sql(count_query, as_dict=True))

        print(f"result MCP_list_document {result}")
        # total_count = result[0].get("total", 0) if result else 0
        total_count = frappe.db.count(doctype, filters=safe_filters)

        return {
            "items": docs,
            "count": len(docs),
            "total_count": total_count,
            "has_more": total_count > len(docs),
        }
    except Exception as e:
        await ctx.error(f"Error listing documents: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(name="create_document", description="Create a new document in ERPNext")
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
    try:
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

        frappe.db.commit()

        # Return the document
        return handle_frappe_response(doc)
    except Exception as e:
        frappe.db.rollback()
        await ctx.error(f"Error creating document: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(
    name="update_document", description="Update an existing document in ERPNext"
)
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
    try:
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

        frappe.db.commit()

        # Return the document
        return handle_frappe_response(doc)
    except Exception as e:
        frappe.db.rollback()
        await ctx.error(f"Error updating document: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(name="delete_document", description="Delete a document in ERPNext")
async def delete_document(doctype: str, name: str, ctx: Context) -> Dict[str, Any]:
    """
    Delete a document in ERPNext.

    Args:
        doctype: The DocType to delete (e.g., 'Customer', 'Sales Invoice')
        name: The document name or ID

    Returns:
        Success status
    """
    await ctx.info(f"Deleting {doctype}: {name}")
    try:
        # Validate document exists
        if not frappe.db.exists(doctype, name):
            return {"error": f"Document {doctype}/{name} does not exist"}

        # Delete the document
        frappe.delete_doc(doctype, name)
        frappe.db.commit()

        # Return success
        return {
            "success": True,
            "message": f"Document {doctype}/{name} deleted successfully",
        }
    except Exception as e:
        frappe.db.rollback()
        await ctx.error(f"Error deleting document: {str(e)}")
        return {"error": str(e), "success": False}


@erp_server.tool(
    name="get_doctype_fields", description="Get field information for a DocType"
)
async def get_doctype_fields(doctype: str, ctx: Context) -> Dict[str, Any]:
    """
    Get field information for a DocType.

    Args:
        doctype: The DocType to get fields for

    Returns:
        List of fields with their properties
    """
    await ctx.info(f"Getting fields for {doctype}")
    try:
        # Validate doctype exists
        if not frappe.db.exists("DocType", doctype):
            return {"error": f"DocType '{doctype}' does not exist"}

        fields = get_fields_for_doctype(doctype)
        return {"doctype": doctype, "fields": fields, "count": len(fields)}
    except Exception as e:
        await ctx.error(f"Error getting fields: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(name="run_report", description="Run a standard ERPNext report")
async def run_report(
    report_name: str,
    ctx: Context,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run a standard ERPNext report.

    Args:
        report_name: The name of the report
        filters: Optional filters to apply to the report

    Returns:
        The report data
    """
    await ctx.info(f"Running report: {report_name}")
    try:
        # Validate report exists
        if not frappe.db.exists("Report", report_name):
            return {"error": f"Report '{report_name}' does not exist"}

        # Sanitize input
        safe_filters = sanitize_input(filters) if filters else {}

        # Run the report
        from frappe.desk.query_report import run

        result = run(report_name, safe_filters)

        # Process and return the result
        if isinstance(result, dict):
            # Some reports return different formats
            columns = result.get("columns", [])
            data = result.get("result", [])

            # Convert column data to be more usable
            parsed_columns = []
            for col in columns:
                if isinstance(col, dict):
                    parsed_columns.append(
                        col.get("label", col.get("fieldname", "Unknown"))
                    )
                else:
                    parsed_columns.append(str(col))

            return {
                "report_name": report_name,
                "columns": parsed_columns,
                "data": data,
                "filters": safe_filters,
            }
        else:
            return {"error": "Report returned unexpected format", "data": str(result)}
    except Exception as e:
        await ctx.error(f"Error running report: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(
    name="execute_query", description="Execute a custom query with parameters"
)
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

    try:
        # Sanitize parameters
        safe_params = sanitize_input(params) if params else {}

        # Execute the query, ensuring a concrete list is returned
        result = frappe.db.sql(query, safe_params, as_dict=as_dict)

        # Explicitly convert to list if it's a generator
        if not isinstance(result, (list, tuple)):
            result = list(result)

        return {"results": result, "count": len(result)}

        # Execute the query
        # result_list = list(safe_params)
        # result = frappe.db.sql(query, safe_params, as_dict=as_dict)
        # return {"results": result_list, "count": len(result_list)}

        # return {"results": result, "count": len(result)}
    except Exception as e:
        await ctx.error(f"Error executing query: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(
    name="run_custom_function", description="Run a custom function in ERPNext"
)
async def run_custom_function(
    function_path: str,
    ctx: Context,
    args: Dict,
    whitelist_only: bool = True,
) -> Dict[str, Any]:
    """
    Run a custom function in ERPNext.

    Args:
        function_path: The path to the function (e.g., 'frappe.desk.reportview.get')
        args: Arguments to pass to the function
        whitelist_only: Whether to only allow whitelisted functions

    Returns:
        The function result
    """
    await ctx.info(f"Running custom function: {function_path}")

    # Check if the function is allowed
    # if whitelist_only:
    #     from frappe.utils.safe_exec import WHITELISTED_MODULES

    #     # Check if the module is whitelisted
    #     module_whitelisted = False
    #     for wm in WHITELISTED_MODULES:
    #         if function_path.startswith(wm):
    #             module_whitelisted = True
    #             break

    #     if not module_whitelisted:
    #         return {"error": f"Function {function_path} is not in a whitelisted module"}

    try:
        # Sanitize input
        safe_args = sanitize_input(args)

        # Get the function
        module_path, function_name = function_path.rsplit(".", 1)

        try:
            module = __import__(module_path, fromlist=[function_name])
            function = getattr(module, function_name)
        except (ImportError, AttributeError) as e:
            return {"error": f"Function {function_path} not found: {str(e)}"}

        # Check if the function is whitelisted
        if whitelist_only:
            # Check for the whitelisted attribute directly
            if not getattr(function, "whitelisted", False):
                # Also check with frappe.allow_guest which is another way to mark functions as safe
                if not getattr(function, "allow_guest", False):
                    return {"error": f"Function {function_path} is not whitelisted"}

        # Execute the function
        result = function(**safe_args)

        # Handle the result
        return handle_frappe_response(result)
    except Exception as e:
        await ctx.error(f"Error running custom function: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(
    name="get_system_info", description="Get system information from ERPNext"
)
async def get_system_info(ctx: Context) -> Dict[str, Any]:
    """
    Get system information from ERPNext.

    Returns:
        System information including version, site name, etc.
    """
    await ctx.info("Getting system information")
    try:
        # Get ERPNext information
        frappe_version = frappe.__version__
        site_name = get_site_name(
            frappe.local.request.host if hasattr(frappe.local, "request") else None
        )

        # Try to get ERPNext version if installed
        erpnext_version = None
        if frappe.db.exists("DocType", "DocType"):
            if frappe.db.exists("Module Def", "ERPNext"):
                try:
                    from erpnext import __version__ as erpnext_version
                except ImportError:
                    # ERPNext module exists but can't be imported directly
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
    except Exception as e:
        await ctx.error(f"Error getting system info: {str(e)}")
        return {"error": str(e)}


@erp_server.tool(name="get_doctypes", description="Get a list of available DocTypes")
async def get_doctypes(
    ctx: Context,
    module: Optional[str] = None,
    custom_only: bool = False,
) -> Dict[str, Any]:
    """
    Get a list of available DocTypes.

    Args:
        module: Optional module to filter by
        custom_only: Whether to only return custom DocTypes

    Returns:
        List of DocTypes
    """
    await ctx.info("Getting DocTypes list")
    try:
        filters = {}
        if module:
            filters["module"] = module
        if custom_only:
            filters["custom"] = 1

        doctypes = frappe.get_all(
            "DocType",
            filters=filters,
            fields=["name", "module", "modified", "description", "custom"],
        )

        return {"count": len(doctypes), "doctypes": doctypes}
    except Exception as e:
        await ctx.error(f"Error getting DocTypes: {str(e)}")
        return {"error": str(e)}


# Calculator tool
@erp_server.tool(
    name="calculate_thai_tax",
    description="Calculate Thai taxes based on income and deductions",
)
async def calculate_thai_tax(
    income_type: str,  # "personal" or "corporate"
    ctx: Context,
    total_income: float,
    deductions: Dict[str, float],
    tax_year: int,
) -> Dict[str, Any]:
    """
    Calculate Thai taxes based on provided income and deductions.

    Args:
        income_type: Type of income ("personal" or "corporate")
        total_income: Total income amount in THB
        deductions: Dictionary of applicable deductions
        tax_year: Tax year for calculation (defaults to current year)

    Returns:
        Calculated tax details
    """
    await ctx.info(f"Calculating {income_type} tax for {total_income} THB")

    if not tax_year:
        tax_year = datetime.now().year

    deductions = deductions or {}

    try:
        if income_type == "personal":
            # Personal income tax calculation
            # This is a simplified example - actual calculations would be more complex

            # Standard deductions
            standard_deduction = min(
                total_income * 0.5, 100000
            )  # 50% up to 100,000 THB
            personal_allowance = 60000  # Personal allowance

            # Apply additional deductions
            total_deductions = standard_deduction + personal_allowance
            for deduction_type, amount in deductions.items():
                total_deductions += amount

            # Calculate taxable income
            taxable_income = max(0, total_income - total_deductions)

            # Apply tax rates (2021 rates)
            tax = 0
            if taxable_income > 5000000:
                tax += (taxable_income - 5000000) * 0.35
                taxable_income = 5000000
            if taxable_income > 2000000:
                tax += (taxable_income - 2000000) * 0.30
                taxable_income = 2000000
            if taxable_income > 1000000:
                tax += (taxable_income - 1000000) * 0.25
                taxable_income = 1000000
            if taxable_income > 750000:
                tax += (taxable_income - 750000) * 0.20
                taxable_income = 750000
            if taxable_income > 500000:
                tax += (taxable_income - 500000) * 0.15
                taxable_income = 500000
            if taxable_income > 300000:
                tax += (taxable_income - 300000) * 0.10
                taxable_income = 300000
            if taxable_income > 150000:
                tax += (taxable_income - 150000) * 0.05

            return {
                "income_type": "Personal Income Tax",
                "tax_year": tax_year,
                "total_income": total_income,
                "standard_deduction": standard_deduction,
                "personal_allowance": personal_allowance,
                "additional_deductions": sum(deductions.values()),
                "total_deductions": total_deductions,
                "taxable_income": total_income - total_deductions,
                "calculated_tax": tax,
                "effective_tax_rate": (tax / total_income) * 100
                if total_income > 0
                else 0,
            }

        elif income_type == "corporate":
            # Corporate income tax calculation (simplified)
            # SME rates for 2021

            if total_income <= 300000:
                tax_rate = 0
            elif total_income <= 3000000:
                tax_rate = 0.15
            else:
                tax_rate = 0.20

            # Apply deductions
            total_deductions = sum(deductions.values())
            taxable_income = max(0, total_income - total_deductions)

            # Calculate tax
            tax = taxable_income * tax_rate

            return {
                "income_type": "Corporate Income Tax",
                "tax_year": tax_year,
                "total_income": total_income,
                "total_deductions": total_deductions,
                "taxable_income": taxable_income,
                "tax_rate": tax_rate * 100,
                "calculated_tax": tax,
                "effective_tax_rate": (tax / total_income) * 100
                if total_income > 0
                else 0,
            }

        else:
            return {
                "error": f"Unsupported income type: {income_type}",
                "supported_types": ["personal", "corporate"],
            }

    except Exception as e:
        await ctx.error(f"Error calculating tax: {str(e)}")
        return {"error": str(e)}


# Vector DB semantic search tool
@erp_server.tool(
    name="search_tax_laws", description="Search Thai tax laws using semantic search"
)
async def search_tax_laws(
    query: str,
    ctx: Context,
    category: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search Thai tax laws using semantic search.

    Args:
        query: The search query
        top_k: Number of results to return
        category: Optional category to filter by

    Returns:
        Relevant tax laws
    """
    await ctx.info(f"Searching tax laws for: {query}")

    try:
        from path.to.tax_law_vector import search_similar_tax_laws

        # Perform semantic search
        results = search_similar_tax_laws(query, top_k)

        # Filter by category if specified
        if category:
            results = [r for r in results if r["category"] == category]

        # Fetch full details for top results
        detailed_results = []
        for result in results:
            tax_law = frappe.get_doc("Thai Tax Law", result["name"])
            detailed_results.append(
                {
                    "name": tax_law.name,
                    "title": tax_law.title,  # type: ignore
                    "category": tax_law.category,  # type: ignore
                    "subcategory": tax_law.subcategory,  # type: ignore
                    "summary": tax_law.summary,  # type: ignore
                    "content": tax_law.content_en or tax_law.content_th,  # type: ignore
                    "effective_date": str(tax_law.effective_date),  # type: ignore
                    "legal_reference": tax_law.legal_reference,  # type: ignore
                    "similarity_score": result["similarity"],
                }
            )

        return {
            "query": query,
            "results_count": len(detailed_results),
            "results": detailed_results,
        }
    except Exception as e:
        await ctx.error(f"Error searching tax laws: {str(e)}")
        return {"error": str(e)}


# Add prompts for ERPNext tasks
@erp_server.prompt()
def sales_invoice_analysis(invoice_id: str) -> List:
    """
    Analyze a sales invoice.

    Args:
        invoice_id: The ID of the sales invoice to analyze
    """
    # Get invoice data
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_id)
        invoice_data = invoice.as_dict()
        # Format the data
        formatted_data = json.dumps(invoice_data, indent=2)
    except:
        formatted_data = f"Could not find Sales Invoice with ID: {invoice_id}"

    return [
        {
            "role": "user",
            "content": f"""Please analyze this sales invoice and provide insights:

Invoice Data:
```json
{formatted_data}
```

Please provide:
1. A summary of the invoice (customer, date, total)
2. Analysis of the items and their pricing
3. Any patterns or unusual aspects worth noting
4. Recommendations for follow-up actions
""",
        }
    ]


@erp_server.prompt()
def customer_analysis(customer_id: str) -> List:
    """
    Analyze a customer's history and data.

    Args:
        customer_id: The ID of the customer to analyze
    """
    try:
        # Validate customer exists before proceeding
        if not frappe.db.exists("Customer", customer_id):
            return [
                {
                    "role": "user",
                    "content": f"Customer with ID '{customer_id}' does not exist. Please verify the customer ID and try again.",
                }
            ]
        # Get customer data
        customer = frappe.get_doc("Customer", customer_id)
        customer_data = customer.as_dict()

        # Get recent invoices with error handling
        try:
            invoices = frappe.get_all(
                "Sales Invoice",
                filters={"customer": customer_id, "docstatus": 1},
                fields=["name", "posting_date", "grand_total", "status", "due_date"],
                order_by="posting_date desc",
                limit=5,
            )
        except Exception as invoice_error:
            logger.error(
                f"Error fetching invoices for {customer_id}: {str(invoice_error)}"
            )
            invoices = []

        # Get customer's total sales with proper error handling
        try:
            total_sales_query = frappe.db.sql(
                """
                SELECT 
                    SUM(grand_total) as total, 
                    COUNT(*) as count,
                    MIN(posting_date) as first_invoice_date,
                    MAX(posting_date) as last_invoice_date,
                    AVG(grand_total) as average_invoice_amount
                FROM `tabSales Invoice`
                WHERE customer = %s AND docstatus = 1
                """,
                (customer_id,),
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            total_sales_result = list(total_sales_query) if total_sales_query else []

            # Safely get the first result or use a default
            total_sales = (
                total_sales_result[0]
                if total_sales_result and isinstance(total_sales_result[0], dict)
                else {
                    "total": 0,
                    "count": 0,
                    "first_invoice_date": None,
                    "last_invoice_date": None,
                    "average_invoice_amount": 0,
                }
            )
        except Exception as sales_error:
            logger.error(
                f"Error calculating sales totals for {customer_id}: {str(sales_error)}"
            )
            total_sales = {"total": 0, "count": 0, "error": str(sales_error)}

        # Get payment history
        try:
            payment_history = frappe.db.sql(
                """
                SELECT 
                    p.name, 
                    p.posting_date, 
                    p.paid_amount,
                    p.payment_type,
                    p.mode_of_payment
                FROM `tabPayment Entry` p
                INNER JOIN `tabPayment Entry Reference` ref ON p.name = ref.parent
                WHERE ref.reference_doctype = 'Sales Invoice'
                AND ref.reference_name IN (
                    SELECT name FROM `tabSales Invoice` 
                    WHERE customer = %s AND docstatus = 1
                )
                AND p.docstatus = 1
                ORDER BY p.posting_date DESC
                LIMIT 5
                """,
                (customer_id,),
                as_dict=True,
            )
        except Exception as payment_error:
            logger.error(
                f"Error fetching payment history for {customer_id}: {str(payment_error)}"
            )
            payment_history = []

        # Format data for the prompt
        formatted_customer = json.dumps(customer_data, indent=2)
        formatted_invoices = (
            json.dumps(invoices, indent=2) if invoices else "No recent invoices"
        )
        formatted_sales = json.dumps(total_sales, indent=2)
        formatted_payments = (
            json.dumps(payment_history, indent=2)
            if payment_history
            else "No payment history"
        )

        # Build a comprehensive analysis prompt
        return [
            {
                "role": "user",
                "content": f"""Please analyze this customer's data and provide insights:

Customer Profile:
```json
{formatted_customer}
```

Recent Invoices:
```json
{formatted_invoices}
```

Sales Summary:
```json
{formatted_sales}
```

Recent Payments:
```json
{formatted_payments}
```

Please provide:
1. A summary of the customer profile including customer type, territory, and other key information
2. Analysis of their purchase history and payment patterns
3. Customer lifetime value assessment and transaction frequency analysis
4. Any signs of payment delays or financial risk
5. Recommendations for improving customer relationship
6. Potential up-selling or cross-selling opportunities based on purchase history
7. Suggested next actions for the sales and finance teams
""",
            }
        ]
    except Exception as e:
        logger.error(f"Error in customer_analysis for {customer_id}: {str(e)}")
        return [
            {
                "role": "user",
                "content": f"Could not analyze Customer with ID: {customer_id}. Error: {str(e)}. Please check if the customer exists and you have appropriate permissions.",
            }
        ]


@erp_server.prompt()
def inventory_analysis() -> List:
    """
    Analyze current inventory status and make recommendations.
    """
    try:
        # Get stock items with low inventory
        try:
            low_stock_query = frappe.db.sql(
                """
                SELECT item_code, item_name, warehouse, actual_qty, valuation_rate, 
                       reorder_level, reorder_qty
                FROM `tabBin`
                WHERE actual_qty <= reorder_level
                AND reorder_level > 0
                ORDER BY actual_qty ASC
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            low_stock_items = list(low_stock_query) if low_stock_query else []
        except Exception as e:
            logger.error(f"Error fetching low stock items: {str(e)}")
            low_stock_items = []

        # Get overstock items
        try:
            overstock_query = frappe.db.sql(
                """
                SELECT item_code, item_name, warehouse, actual_qty, valuation_rate,
                       reorder_level, (actual_qty - reorder_level) as excess_qty
                FROM `tabBin`
                WHERE actual_qty > 2 * reorder_level
                AND reorder_level > 0
                ORDER BY excess_qty DESC
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            overstock_items = list(overstock_query) if overstock_query else []
        except Exception as e:
            logger.error(f"Error fetching overstock items: {str(e)}")
            overstock_items = []

        # Get total inventory value
        try:
            inventory_value_query = frappe.db.sql(
                """
                SELECT SUM(actual_qty * valuation_rate) as total_value
                FROM `tabBin`
                WHERE actual_qty > 0
            """,
                as_dict=True,
            )
            # Convert to a list explicitly for type checker
            inventory_value_result = (
                list(inventory_value_query) if inventory_value_query else []
            )
            # Handle the result safely
            inventory_value = (
                inventory_value_result[0]
                if inventory_value_result
                else {"total_value": 0}
            )
        except Exception as e:
            logger.error(f"Error calculating inventory value: {str(e)}")
            inventory_value = {"total_value": 0, "error": str(e)}

        # Get inventory aging data
        try:
            aging_data = frappe.db.sql(
                """
                SELECT 
                    i.item_code,
                    i.item_name, 
                    b.warehouse,
                    b.actual_qty,
                    b.valuation_rate,
                    DATEDIFF(CURDATE(), GREATEST(i.creation, i.modified)) as days_in_inventory
                FROM `tabBin` b
                JOIN `tabItem` i ON b.item_code = i.name
                WHERE b.actual_qty > 0
                ORDER BY days_in_inventory DESC
                LIMIT 10
            """,
                as_dict=True,
            )
        except Exception as e:
            logger.error(f"Error fetching inventory aging data: {str(e)}")
            aging_data = []

        # Calculate summary statistics
        total_items = frappe.db.count("Item", {"disabled": 0})
        low_stock_count = len(low_stock_items)
        overstock_count = len(overstock_items)

        # Get warehouse utilization
        try:
            warehouse_query = frappe.db.sql(
                """
                SELECT 
                    warehouse, 
                    COUNT(DISTINCT item_code) as unique_items,
                    SUM(actual_qty) as total_items,
                    SUM(actual_qty * valuation_rate) as inventory_value
                FROM `tabBin`
                WHERE actual_qty > 0
                GROUP BY warehouse
                ORDER BY inventory_value DESC
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            warehouse_util = list(warehouse_query) if warehouse_query else []
        except Exception as e:
            logger.error(f"Error calculating warehouse utilization: {str(e)}")
            warehouse_util = []

        # Format the data
        formatted_low_stock = (
            json.dumps(low_stock_items, indent=2)
            if low_stock_items
            else "No low stock items"
        )
        formatted_overstock = (
            json.dumps(overstock_items, indent=2)
            if overstock_items
            else "No overstocked items"
        )
        formatted_value = json.dumps(inventory_value, indent=2)
        formatted_aging = (
            json.dumps(aging_data, indent=2)
            if aging_data
            else "No aging data available"
        )
        formatted_warehouse = (
            json.dumps(warehouse_util, indent=2)
            if warehouse_util
            else "No warehouse data available"
        )

        # Create inventory summary
        inventory_summary = {
            "total_active_items": total_items,
            "low_stock_count": low_stock_count,
            "low_stock_percentage": round(
                (low_stock_count / total_items * 100) if total_items > 0 else 0, 2
            ),
            "overstock_count": overstock_count,
            "overstock_percentage": round(
                (overstock_count / total_items * 100) if total_items > 0 else 0, 2
            ),
            "total_inventory_value": inventory_value["total_value"]
            if isinstance(inventory_value, dict) and "total_value" in inventory_value
            else 0,
            "warehouse_count": len(warehouse_util),
        }
        formatted_summary = json.dumps(inventory_summary, indent=2)

    except Exception as e:
        logger.error(f"Error in inventory analysis: {str(e)}")
        return [
            {
                "role": "user",
                "content": f"Could not retrieve inventory data: {str(e)}. Please check if the Bin DocType exists and you have appropriate permissions.",
            }
        ]

    return [
        {
            "role": "user",
            "content": f"""Please analyze the current inventory status and provide recommendations:

Inventory Summary:
```json
{formatted_summary}
```

Low Stock Items (Below Reorder Level):
```json
{formatted_low_stock}
```

Overstocked Items (Above 2x Reorder Level):
```json
{formatted_overstock}
```

Slow-Moving Inventory (Oldest Items):
```json
{formatted_aging}
```

Warehouse Distribution:
```json
{formatted_warehouse}
```

Total Inventory Value:
```json
{formatted_value}
```

Please provide:
1. A comprehensive analysis of the current inventory status
2. Prioritized list of items that need to be reordered soon with suggested quantities
3. Recommendations for reducing excess inventory and improving cash flow
4. Strategies for addressing slow-moving inventory items
5. Insights on warehouse utilization and potential optimization
6. Key inventory KPIs the business should track
7. Actionable recommendations for overall inventory management improvement
""",
        }
    ]


@erp_server.prompt()
def financial_dashboard() -> List:
    """
    Generate a financial dashboard with key metrics.
    """
    try:
        # Get accounts receivable
        try:
            ar_query = frappe.db.sql(
                """
                SELECT 
                    SUM(outstanding_amount) as total,
                    COUNT(*) as invoice_count,
                    MIN(due_date) as earliest_due
                FROM `tabSales Invoice`
                WHERE docstatus = 1 AND outstanding_amount > 0
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            ar_result = list(ar_query) if ar_query else []
            accounts_receivable = (
                ar_result[0]
                if ar_result and isinstance(ar_result[0], dict)
                else {"total": 0, "invoice_count": 0}
            )
        except Exception as e:
            logger.error(f"Error getting accounts receivable: {str(e)}")
            accounts_receivable = {"total": 0, "invoice_count": 0, "error": str(e)}

        # Get accounts payable
        try:
            ap_query = frappe.db.sql(
                """
                SELECT 
                    SUM(outstanding_amount) as total,
                    COUNT(*) as invoice_count,
                    MIN(due_date) as earliest_due
                FROM `tabPurchase Invoice`
                WHERE docstatus = 1 AND outstanding_amount > 0
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            ap_result = list(ap_query) if ap_query else []
            accounts_payable = (
                ap_result[0]
                if ap_result and isinstance(ap_result[0], dict)
                else {"total": 0, "invoice_count": 0}
            )
        except Exception as e:
            logger.error(f"Error getting accounts payable: {str(e)}")
            accounts_payable = {"total": 0, "invoice_count": 0, "error": str(e)}

        # Get monthly sales trend
        try:
            sales_query = frappe.db.sql(
                """
                SELECT 
                    DATE_FORMAT(posting_date, '%Y-%m') as month,
                    SUM(base_grand_total) as total,
                    COUNT(*) as invoice_count
                FROM `tabSales Invoice`
                WHERE docstatus = 1
                AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(posting_date, '%Y-%m')
                ORDER BY month DESC
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            monthly_sales = list(sales_query) if sales_query else []
        except Exception as e:
            logger.error(f"Error getting monthly sales trend: {str(e)}")
            monthly_sales = []

        # Get top customers by sales
        try:
            customers_query = frappe.db.sql(
                """
                SELECT 
                    customer, 
                    SUM(base_grand_total) as total,
                    COUNT(*) as invoice_count,
                    MAX(posting_date) as last_invoice_date
                FROM `tabSales Invoice`
                WHERE docstatus = 1
                AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                GROUP BY customer
                ORDER BY total DESC
                LIMIT 5
            """,
                as_dict=True,
            )
            # Convert to list explicitly for type checker
            top_customers = list(customers_query) if customers_query else []
        except Exception as e:
            logger.error(f"Error getting top customers: {str(e)}")
            top_customers = []

        # Get financial ratios and key metrics
        try:
            # Calculate current ratio (Current Assets / Current Liabilities)
            current_assets_query = frappe.db.sql(
                """
                SELECT SUM(debit) - SUM(credit) as value
                FROM `tabGL Entry`
                WHERE account LIKE 'Current Assets%'
                AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                """,
                as_dict=True,
            )
            current_assets_result = (
                list(current_assets_query) if current_assets_query else []
            )
            current_assets = (
                current_assets_result[0]["value"]
                if current_assets_result
                and isinstance(current_assets_result[0], dict)
                and "value" in current_assets_result[0]
                else 0
            )

            current_liabilities_query = frappe.db.sql(
                """
                SELECT SUM(credit) - SUM(debit) as value
                FROM `tabGL Entry`
                WHERE account LIKE 'Current Liabilities%'
                AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                """,
                as_dict=True,
            )
            current_liabilities_result = (
                list(current_liabilities_query) if current_liabilities_query else []
            )
            current_liabilities = (
                current_liabilities_result[0]["value"]
                if current_liabilities_result
                and isinstance(current_liabilities_result[0], dict)
                and "value" in current_liabilities_result[0]
                else 0
            )

            # Calculate current ratio
            current_ratio = (
                round(current_assets / current_liabilities, 2)
                if current_liabilities
                else 0
            )

            # Calculate other key metrics
            financial_metrics = {
                "current_ratio": current_ratio,
                "accounts_receivable_total": accounts_receivable.get("total", 0),
                "accounts_payable_total": accounts_payable.get("total", 0),
                "cash_position": current_assets - accounts_receivable.get("total", 0),
                "ar_to_ap_ratio": round(
                    accounts_receivable.get("total", 0)
                    / accounts_payable.get("total", 1),
                    2,
                ),
            }
        except Exception as e:
            logger.error(f"Error calculating financial metrics: {str(e)}")
            financial_metrics = {
                "error": str(e),
                "current_ratio": 0,
                "accounts_receivable_total": accounts_receivable.get("total", 0),
                "accounts_payable_total": accounts_payable.get("total", 0),
            }

        # Format data for the prompt
        formatted_ar = json.dumps(accounts_receivable, indent=2)
        formatted_ap = json.dumps(accounts_payable, indent=2)
        formatted_sales = (
            json.dumps(monthly_sales, indent=2)
            if monthly_sales
            else "No sales data available"
        )
        formatted_customers = (
            json.dumps(top_customers, indent=2)
            if top_customers
            else "No customer data available"
        )
        formatted_metrics = json.dumps(financial_metrics, indent=2)

    except Exception as e:
        logger.error(f"Error generating financial dashboard: {str(e)}")
        return [
            {
                "role": "user",
                "content": f"Could not retrieve financial data: {str(e)}. Please check your database structure and permissions.",
            }
        ]

    return [
        {
            "role": "user",
            "content": f"""Please analyze this financial data and provide a dashboard overview:

Accounts Receivable:
```json
{formatted_ar}
```

Accounts Payable:
```json
{formatted_ap}
```

Monthly Sales (Last 6 Months):
```json
{formatted_sales}
```

Top Customers (Last 3 Months):
```json
{formatted_customers}
```

Financial Key Metrics:
```json
{formatted_metrics}
```

Please provide:
1. A comprehensive summary of the current financial position
2. Analysis of cash flow based on AR and AP trends
3. Liquidity assessment based on the current ratio and other metrics
4. Insights from the sales trend data including month-over-month growth
5. Customer concentration analysis (are we too dependent on a few customers?)
6. Key financial metrics and KPIs to track going forward
7. Recommendations for improving financial health
8. Potential areas of concern that require further investigation
""",
        }
    ]


# Add resource endpoints for ERPNext data
def get_doctypes_list() -> Dict:
    """Returns a list of available DocTypes"""
    try:
        doctypes = frappe.get_all(
            "DocType", fields=["name", "module", "description", "custom"], limit=100
        )
        return {"count": len(doctypes), "doctypes": doctypes}
    except Exception as e:
        return {"error": str(e)}


# Create the AnyUrl instance properly
doctypes_uri = AnyUrl.build(
    scheme="resource",
    host="erp",
    path="/doctypes",
)
erp_server.add_resource(
    FunctionResource(
        # uri="resource://erp/doctypes",
        uri=doctypes_uri,
        name="Available DocTypes",
        description="List of available DocTypes in the system",
        mime_type="application/json",
        fn=get_doctypes_list,
    )
)


def get_workflow_actions() -> Dict:
    """Returns available workflow actions"""
    try:
        workflow_actions = frappe.get_all(
            "Workflow Action",
            fields=[
                "name",
                "status",
                "reference_name",
                "reference_doctype",
                "workflow_state",
                "created_by",
            ],
            filters={"status": "Open"},
            limit=50,
            order_by="creation desc",
        )
        return {"count": len(workflow_actions), "workflow_actions": workflow_actions}
    except Exception as e:
        return {"error": str(e)}


workflow_actions_uri = AnyUrl.build(
    scheme="resource",
    host="erp",
    path="/workflow-actions",
)

erp_server.add_resource(
    FunctionResource(
        # uri="resource://erp/workflow-actions",
        uri=workflow_actions_uri,
        name="Pending Workflow Actions",
        description="List of pending workflow actions that need attention",
        mime_type="application/json",
        fn=get_workflow_actions,
    )
)


def get_system_settings() -> Dict:
    """Returns system settings"""
    try:
        settings = frappe.get_doc("System Settings")
        # Exclude sensitive information
        safe_settings = {
            k: v
            for k, v in settings.as_dict().items()
            if not k.startswith("_")
            and k
            not in (
                "password",
                "api_key",
                "api_secret",
                "mail_password",
                "slack_api_token",
                "webhook_secret",
            )
        }
        return safe_settings
    except Exception as e:
        return {"error": str(e)}


# For system settings
system_settings_uri = AnyUrl.build(
    scheme="resource",
    host="erp",
    path="/system-settings",
)

erp_server.add_resource(
    FunctionResource(
        # uri="resource://erp/system-settings",
        uri=system_settings_uri,
        name="System Settings",
        description="Current system settings (non-sensitive fields only)",
        mime_type="application/json",
        fn=get_system_settings,
    )
)


@erp_server.resource("resource://erp/document/{doctype}/{name}")
async def get_document_resource(doctype: str, name: str) -> str:
    """Resource to get a document by type and name"""
    try:
        if not frappe.db.exists(doctype, name):
            return json.dumps({"error": f"Document {doctype}/{name} does not exist"})

        doc = frappe.get_doc(doctype, name)
        doc_dict = doc.as_dict()

        # Add links to related documents if available
        if hasattr(doc, "links") and doc.links:  # type: ignore
            doc_dict["_links"] = [
                {"link_doctype": l.link_doctype, "link_name": l.link_name}
                for l in doc.links  # type: ignore  # noqa: E741
            ]

        return json.dumps(doc_dict, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@erp_server.resource("resource://erp/report/{report_name}")
async def get_report_resource(report_name: str) -> str:
    """Resource to get report metadata"""
    try:
        if not frappe.db.exists("Report", report_name):
            return json.dumps({"error": f"Report {report_name} does not exist"})

        report = frappe.get_doc("Report", report_name)

        # Get report columns
        if report.report_type == "Query Report":  # type: ignore
            # For query reports, we need to execute the module to get columns
            from frappe.desk.query_report import get_report_doc

            report_doc = get_report_doc(report_name)
            columns = report_doc.columns
        else:
            # For script and custom reports, columns already exist
            columns = report.columns  # type: ignore

        result = {
            "name": report.name,
            "report_name": report.report_name,  # type: ignore
            "report_type": report.report_type,  # type: ignore
            "ref_doctype": report.ref_doctype,  # type: ignore
            "module": report.module,  # type: ignore
            "columns": columns,
            "filters": report.filters,  # type: ignore
            "description": report.description,  # type: ignore
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Add Thai tax law to AI
@erp_server.resource("resource://erp/tax-law/thailand")
async def get_thai_tax_law() -> str:
    """Resource providing information about Thai tax laws and regulations"""
    try:
        # Structure tax law information in a organized format
        # This would ideally come from a maintained database in your system
        thai_tax_laws = {
            "meta": {
                "last_updated": "2023-12-15",
                "source": "Revenue Department of Thailand",
                "disclaimer": "This information is provided for reference only. For official information, please consult the Revenue Department of Thailand.",
            },
            "personal_income_tax": {
                "summary": "Personal Income Tax (PIT) in Thailand is a direct tax levied on income earned by individuals.",
                "tax_rates": [
                    {"income_range": "0-150,000", "rate": "0%", "notes": "Tax exempt"},
                    {"income_range": "150,001-300,000", "rate": "5%"},
                    {"income_range": "300,001-500,000", "rate": "10%"},
                    {"income_range": "500,001-750,000", "rate": "15%"},
                    {"income_range": "750,001-1,000,000", "rate": "20%"},
                    {"income_range": "1,000,001-2,000,000", "rate": "25%"},
                    {"income_range": "2,000,001-5,000,000", "rate": "30%"},
                    {"income_range": "Over 5,000,000", "rate": "35%"},
                ],
                "deductions": [
                    {"type": "Personal allowance", "amount": "60,000 THB"},
                    {
                        "type": "Spouse allowance",
                        "amount": "60,000 THB",
                        "conditions": "If spouse has no income",
                    },
                    {"type": "Child allowance", "amount": "30,000 THB per child"},
                ],
            },
            "corporate_income_tax": {
                "summary": "Corporate Income Tax (CIT) is imposed on companies and juristic entities in Thailand.",
                "standard_rate": "20%",
                "sme_rates": [
                    {"profit_range": "0-300,000", "rate": "0%"},
                    {"profit_range": "300,001-3,000,000", "rate": "15%"},
                    {"profit_range": "Over 3,000,000", "rate": "20%"},
                ],
            },
            "value_added_tax": {
                "summary": "Value Added Tax (VAT) is an indirect tax imposed on the consumption of goods and services.",
                "standard_rate": "7%",
                "exemptions": [
                    "Unprocessed agricultural products",
                    "Healthcare services",
                    "Educational services",
                    "Religious and charitable organizations",
                ],
            },
            "withholding_tax": {
                "summary": "Withholding tax is collected at source from certain types of income payments.",
                "rates": [
                    {"payment_type": "Dividends", "rate": "10%"},
                    {"payment_type": "Interest", "rate": "15%"},
                    {"payment_type": "Royalties", "rate": "15%"},
                    {"payment_type": "Service and professional fees", "rate": "3%"},
                    {"payment_type": "Rent", "rate": "5%"},
                ],
            },
            "filing_deadlines": {
                "personal_income_tax": "March 31 (following the tax year)",
                "corporate_income_tax": "150 days from the end of the accounting period",
                "value_added_tax": "15th of the following month",
                "withholding_tax": "7 days from the end of the month in which payment was made",
            },
            "resources": {
                "official_website": "https://www.rd.go.th/",
                "tax_laws": "https://www.rd.go.th/674.html",
                "contact": {
                    "call_center": "1161",
                    "email": "rdcustomerservice@rd.go.th",
                },
            },
        }

        return json.dumps(thai_tax_laws, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Get Thai tax law by section
@erp_server.resource("resource://erp/tax-law/thailand/{section}")
async def get_thai_tax_law_section(section: str = "overview") -> str:
    """Resource providing specific sections of Thai tax law information

    Sections: overview, personal, corporate, vat, withholding, filing
    """
    try:
        # Here you could implement a web scraper to fetch the latest information
        # from the Revenue Department website or use an API if available
        # For this example, we'll use a static approach with regular updates

        # Check which section was requested
        if section == "overview":
            # Return a general overview of Thai tax system
            return json.dumps(
                {
                    "title": "Overview of Thailand's Tax System",
                    "description": "Thailand's tax system includes several types of taxes administered by the Revenue Department",
                    "main_taxes": [
                        "Personal Income Tax (PIT)",
                        "Corporate Income Tax (CIT)",
                        "Value Added Tax (VAT)",
                        "Specific Business Tax (SBT)",
                        "Withholding Tax",
                    ],
                    "fiscal_year": "Calendar year (January 1 - December 31)",
                    "important_note": "Tax rates and regulations are subject to change. Always consult with a qualified tax professional.",
                    "source": "Based on information from the Revenue Department of Thailand",
                },
                indent=2,
            )

        elif section == "personal":
            # Return personal income tax information
            # Actual implementation would include more details and calculations
            return json.dumps(
                {
                    "title": "Personal Income Tax (PIT)",
                    "description": "Tax levied on income of individuals residing in Thailand",
                    "assessable_income": [
                        "Employment income",
                        "Business income",
                        "Passive income (dividends, interest, royalties)",
                        "Capital gains",
                        "Rental income",
                        "Professional income",
                    ],
                    "current_rates": "Progressive rates from 0% to 35%",
                    "filing_deadline": "March 31 of the following year",
                    "source": "Based on information from the Revenue Department of Thailand",
                },
                indent=2,
            )

        elif section == "corporate":
            # Return corporate tax information
            return json.dumps(
                {
                    "title": "Corporate Income Tax (CIT)",
                    "description": "Tax imposed on the net profit of companies and juristic entities",
                    "standard_rate": "20% on net profits",
                    "sme_rates": "Reduced rates for small and medium enterprises",
                    "filing_periods": "Within 150 days from the end of the accounting period",
                    "source": "Based on information from the Revenue Department of Thailand",
                },
                indent=2,
            )

        # Add more sections as needed

        else:
            return json.dumps(
                {
                    "error": f"Section '{section}' not found",
                    "available_sections": [
                        "overview",
                        "personal",
                        "corporate",
                        "vat",
                        "withholding",
                        "filing",
                    ],
                }
            )

    except Exception as e:
        return json.dumps({"error": str(e)})


# Permission checks
@erp_server.resource("resource://erp/tax-law/thailand")
async def get_thai_tax_law_resource_new() -> str:
    """Resource providing Thai tax law information from the database"""
    try:
        # Check if user has permission to read Thai Tax Law
        if not frappe.has_permission("Thai Tax Law", "read"):
            return json.dumps(
                {"error": "You don't have permission to access tax law information"}
            )

        tax_laws = get_thai_tax_laws_from_db()
        return json.dumps(tax_laws, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Get Thai tax law from MariaDB
def get_thai_tax_laws_from_db() -> Dict:
    """Retrieve Thai tax laws from the database"""
    try:
        # Check if we have a Tax Law DocType
        if not frappe.db.exists("DocType", "Tax Law"):
            return {"error": "Tax Law DocType not found in the system"}

        # Get tax laws from the database
        tax_laws = frappe.get_all(
            "Tax Law",
            filters={"country": "Thailand", "is_active": 1},
            fields=[
                "name",
                "section",
                "title",
                "description",
                "content",
                "url_reference",
                "last_updated",
            ],
        )

        # Organize by sections
        organized_laws = {
            "meta": {
                "last_updated": max([law.get("last_updated") for law in tax_laws])
                if tax_laws
                else None,
                "count": len(tax_laws),
                "source": "Revenue Department of Thailand",
            },
            "sections": {},
        }

        for law in tax_laws:
            section = law.get("section", "other")
            if section not in organized_laws["sections"]:
                organized_laws["sections"][section] = []

            organized_laws["sections"][section].append(
                {
                    "name": law.get("name"),
                    "title": law.get("title"),
                    "description": law.get("description"),
                    "content": law.get("content"),
                    "reference_url": law.get("url_reference"),
                    "last_updated": law.get("last_updated"),
                }
            )

        return organized_laws
    except Exception as e:
        return {"error": str(e)}


# Filter results based on User permissions
def get_thai_tax_laws_from_db_new() -> Dict:
    """Retrieve Thai tax laws from the database with permission checks"""
    try:
        # This respects user permissions
        tax_laws = frappe.get_list(
            "Thai Tax Law",
            filters={"is_active": 1},
            fields=["name", "section_code", "title", "category", "summary"],
            ignore_permissions=False,  # This is key for respecting permissions
        )

        # Fetch full details for each law (also with permission checks)
        detailed_laws = []
        for law in tax_laws:
            full_doc = frappe.get_doc("Thai Tax Law", law.name)
            detailed_laws.append(
                {
                    "name": full_doc.name,
                    "section_code": full_doc.section_code,  # type: ignore
                    "title": full_doc.title,  # type: ignore
                    "category": full_doc.category,  # type: ignore
                    "subcategory": full_doc.subcategory,  # type: ignore
                    "summary": full_doc.summary,  # type: ignore
                    "content_th": full_doc.content_th,  # type: ignore
                    "content_en": full_doc.content_en,  # type: ignore
                    "effective_date": str(full_doc.effective_date),  # type: ignore
                }
            )

        return {"count": len(detailed_laws), "laws": detailed_laws}
    except Exception as e:
        return {"error": str(e)}


@erp_server.resource("resource://erp/tax-law/thailand")
async def get_thai_tax_law_resource() -> str:
    """Resource providing Thai tax law information from the database"""
    try:
        tax_laws = get_thai_tax_laws_from_db()
        return json.dumps(tax_laws, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Add resource for the company dashboard
def get_company_dashboard(company: str = "") -> Dict:
    """Returns company dashboard data"""
    try:
        # If no company is specified, get the default company
        if not company:
            company = (
                frappe.defaults.get_user_default("Company")
                or frappe.get_all("Company")[0].name
            )

        # Get company information
        company_doc = frappe.get_doc("Company", company)
        company_info = {
            "name": company_doc.name,
            "abbr": company_doc.abbr,  # type: ignore
            "country": company_doc.country,  # type: ignore
            "default_currency": company_doc.default_currency,  # type: ignore
            "chart_of_accounts": company_doc.chart_of_accounts,  # type: ignore
        }

        # Get financial data
        from erpnext.accounts.dashboard_fixtures import get_company_dashboard_data

        try:
            dashboard_data = get_company_dashboard_data(company=company)
        except:
            # Fallback if not available
            dashboard_data = {
                "financial_stats": frappe.db.sql(
                    """
                    SELECT 
                        DATE_FORMAT(posting_date, '%Y-%m') as month,
                        SUM(base_grand_total) as sales
                    FROM `tabSales Invoice`
                    WHERE docstatus = 1
                    AND company = %s
                    AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                    GROUP BY DATE_FORMAT(posting_date, '%Y-%m')
                    ORDER BY month ASC
                """,
                    (company,),
                    as_dict=True,
                )
            }

        result = {"company": company_info, "dashboard_data": dashboard_data}

        return result
    except Exception as e:
        return {"error": str(e)}


company_dashboard_uri = AnyUrl.build(
    scheme="resource", host="erp", path="/company-dashboard"
)

erp_server.add_resource(
    FunctionResource(
        # uri="resource://erp/company-dashboard",
        uri=company_dashboard_uri,
        name="Company Dashboard",
        description="Company dashboard with key financial metrics",
        mime_type="application/json",
        fn=get_company_dashboard,
    )
)


# Helper function to run the MCP server
def run_erp_mcp_server(transport: str = "stdio"):
    """
    Run the ERPNext MCP server with the specified transport.

    Args:
        transport: Transport protocol to use ("stdio" or "sse")
    """
    # Validate transport parameter
    if transport not in ("stdio", "sse"):
        logger.warning(f"Invalid transport '{transport}'. Defaulting to 'stdio'.")
        transport_literal = "stdio"  # Default to stdio if invalid
    else:
        # Type casting for linter - we know it's a valid literal after the check
        transport_literal = transport

    # Initialize Frappe if not already initialized
    if not frappe.local:
        # Get site name from environment or use a default empty string
        # frappe.init() requires a site parameter, even if it's just an empty string
        site_name = os.environ.get("FRAPPE_SITE", "")

        # Initialize with the site name (which might be an empty string)
        frappe.init(site=site_name)

    # Connect to database if not already connected
    if not frappe.db:
        frappe.connect()

    try:
        # Start the server with the validated transport
        erp_server.run(transport=transport_literal)
    finally:
        # Cleanup
        if frappe.db:
            frappe.db.close()


async def handle_query_mode(query_data, result_file=None):
    """
    Special handler for direct query mode that bypasses the MCP protocol

    Args:
        query_data: The query data as a dict with 'query' and 'context' keys
        result_file: Optional path to write the result to

    Returns:
        Query response dict
    """
    try:
        # Extract query and context
        query_text = query_data.get("query", "")
        context = query_data.get("context", {})

        # Process the query
        # Here we'd typically pass it to an LLM, but for testing we'll just return a simple response
        response = f"Processed query: {query_text}"

        # In a real implementation, you would:
        # 1. Check what the query is asking for
        # 2. Use the appropriate tools to fulfill the query
        # 3. Format the response nicely

        # For now, let's make a basic implementation that detects a few query types
        if "sales invoice" in query_text.lower() or "invoice" in query_text.lower():
            # Handle invoice query
            invoice_info = "No specific invoice ID provided"

            # Look for invoice numbers in the query
            import re

            invoice_match = re.search(r"INV-\d+", query_text)
            if invoice_match:
                invoice_id = invoice_match.group()
                try:
                    # Try to get invoice data
                    invoice_data = await get_document("Sales Invoice", invoice_id, None)
                    if "error" not in invoice_data:
                        invoice_info = f"Sales Invoice {invoice_id}:\n"
                        invoice_info += f"Customer: {invoice_data.get('customer')}\n"
                        invoice_info += f"Date: {invoice_data.get('posting_date')}\n"
                        invoice_info += f"Total: {invoice_data.get('grand_total')}\n"
                        invoice_info += f"Status: {invoice_data.get('status')}"
                    else:
                        invoice_info = f"Could not find invoice {invoice_id}: {invoice_data.get('error')}"
                except Exception as e:
                    invoice_info = f"Error retrieving invoice: {str(e)}"

            response = f"Here's the information about the invoice you requested:\n\n{invoice_info}"

        elif "customer" in query_text.lower():
            # Handle customer query
            customer_info = "No specific customer ID provided"

            # Look for customer names in the query
            words = query_text.split()
            for word in words:
                if len(word) > 3 and word.lower() not in (
                    "customer",
                    "about",
                    "info",
                    "tell",
                    "give",
                    "list",
                ):
                    try:
                        # Try to find customer data
                        customers = await list_documents(
                            "Customer",
                            None,
                            ["name", "customer_name", "customer_type", "territory"],
                            5,
                            "name",
                        )
                        if "error" not in customers and customers.get("items"):
                            customer_info = "Here are some customers:\n"
                            for cust in customers.get("items", []):
                                customer_info += f"• {cust.get('customer_name')} ({cust.get('name')})\n"
                        else:
                            customer_info = "No customers found"
                    except Exception as e:
                        customer_info = f"Error retrieving customers: {str(e)}"
                    break

            response = (
                f"Here's the customer information you requested:\n\n{customer_info}"
            )

        elif "doctype" in query_text.lower() or "doctypes" in query_text.lower():
            # Handle DocType query
            try:
                doctypes = await get_doctypes(None)
                if "error" not in doctypes:
                    doctype_info = "Here are some DocTypes:\n"
                    for dt in doctypes.get("doctypes", [])[:10]:  # Limit to 10
                        doctype_info += f"• {dt.get('name')} ({dt.get('module')})\n"
                else:
                    doctype_info = f"Error getting DocTypes: {doctypes.get('error')}"
            except Exception as e:
                doctype_info = f"Error retrieving DocTypes: {str(e)}"

            response = f"Here are some DocTypes in ERPNext:\n\n{doctype_info}"

        elif (
            "system info" in query_text.lower() or "about system" in query_text.lower()
        ):
            # Handle system info query
            try:
                info = await get_system_info(None)
                if "error" not in info:
                    system_info = "System Information:\n"
                    system_info += f"Frappe Version: {info.get('frappe_version')}\n"
                    system_info += f"ERPNext Version: {info.get('erpnext_version')}\n"
                    system_info += f"Site Name: {info.get('site_name')}\n"
                    system_info += f"Active Users: {info.get('active_users')}\n"
                    system_info += (
                        f"Installed Apps: {', '.join(info.get('installed_apps', []))}"
                    )
                else:
                    system_info = f"Error getting system info: {info.get('error')}"
            except Exception as e:
                system_info = f"Error retrieving system info: {str(e)}"

            response = f"Here's information about your ERPNext system:\n\n{system_info}"

        elif "calculate" in query_text.lower() and "tax" in query_text.lower():
            # Handle tax calculation query
            import re

            try:
                # Extract a sample income value from the query
                income_match = re.search(r"(\d[\d,]*\.?\d*)", query_text)
                income = 1000000  # Default
                if income_match:
                    income_str = income_match.group(1).replace(",", "")
                    income = float(income_str)

                # Choose between personal and corporate tax
                tax_type = (
                    "personal" if "personal" in query_text.lower() else "corporate"
                )

                # Call the tax calculation tool
                tax_result = await calculate_thai_tax(tax_type, None, income, {}, 2023)

                if "error" not in tax_result:
                    tax_info = f"Tax Calculation ({tax_type}):\n"
                    tax_info += f"Income: {tax_result.get('total_income'):,.2f} THB\n"
                    tax_info += f"Deductions: {tax_result.get('total_deductions', 0):,.2f} THB\n"
                    tax_info += (
                        f"Taxable Income: {tax_result.get('taxable_income'):,.2f} THB\n"
                    )
                    tax_info += (
                        f"Tax Amount: {tax_result.get('calculated_tax'):,.2f} THB\n"
                    )
                    tax_info += (
                        f"Effective Rate: {tax_result.get('effective_tax_rate'):.2f}%"
                    )
                else:
                    tax_info = f"Error calculating tax: {tax_result.get('error')}"
            except Exception as e:
                tax_info = f"Error with tax calculation: {str(e)}"

            response = f"Here's the tax calculation result:\n\n{tax_info}"

        elif "help" in query_text.lower() or "what can you do" in query_text.lower():
            # Help message
            response = """I can help you with various ERPNext tasks, such as:

1. Looking up information about Sales Invoices
2. Finding customer data
3. Listing DocTypes in the system
4. Getting system information
5. Calculating taxes
6. Running reports

You can ask me things like:
- "Show me invoice INV-12345"
- "List customers"
- "What DocTypes are available?"
- "What's the system info?"
- "Calculate personal tax on 1,000,000 THB"
- "Help me find information about a customer"

How can I assist you today?"""

        # Create the result to return
        import time

        result = {
            "response": response,
            "query": query_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Write to result file if specified
        if result_file:
            with open(result_file, "w") as f:
                json.dump(result, f)

        return result

    except Exception as e:
        error_result = {
            "error": str(e),
            "query": query_data.get("query", ""),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Write error to result file if specified
        if result_file:
            with open(result_file, "w") as f:
                json.dump(error_result, f)

        return error_result


# Modify the main entry point to support query mode
if __name__ == "__main__":
    # Check if running in query mode
    if os.environ.get("MCP_QUERY_MODE") == "1":
        import asyncio
        import json

        query_data = json.loads(os.environ.get("MCP_QUERY_DATA", "{}"))
        result_file = os.environ.get("MCP_RESULT_FILE")

        # Run in query mode
        result = asyncio.run(handle_query_mode(query_data, result_file))

        # If no result file was specified, print the result to stdout
        if not result_file:
            print(json.dumps(result))

        # Exit after handling query
        sys.exit(0)

    # Original code for standard MCP server mode
    # Use environment variable for transport
    transport_env = os.environ.get("MCP_TRANSPORT", "stdio")

    # Validate the transport value
    if transport_env not in ("stdio", "sse"):
        logger.warning(
            f"Invalid transport '{transport_env}' in environment. Defaulting to 'stdio'."
        )
        transport_env = "stdio"

    # Set up Frappe site from environment if available
    site = os.environ.get("FRAPPE_SITE")
    if site:
        os.environ["FRAPPE_SITE"] = site

    # Run the server
    run_erp_mcp_server(transport_env)


# Main entry point
# if __name__ == "__main__":
#     # Use environment variable for transport
#     transport_env = os.environ.get("MCP_TRANSPORT", "stdio")

#     # Validate the transport value
#     if transport_env not in ("stdio", "sse"):
#         logger.warning(
#             f"Invalid transport '{transport_env}' in environment. Defaulting to 'stdio'."
#         )
#         transport_env = "stdio"

#     # Set up Frappe site from environment if available
#     site = os.environ.get("FRAPPE_SITE")
#     if site:
#         os.environ["FRAPPE_SITE"] = site

#     # Run the server
#     run_erp_mcp_server(transport_env)
