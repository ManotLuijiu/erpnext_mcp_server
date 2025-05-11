from typing import Any
import frappe
from mcp.server.fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("erpnext-core")

def init_erpnext():
    """Initialize ERPNext if not already initialized"""
    if not frappe.db:
        frappe.init()
        frappe.connect()
        
@mcp.tool()
async def list_doctypes() -> str:
    """
    List all doctypes in the current ERPNext site.

    Returns:
        str: a formatted list of all available doctypes.
    """
    init_erpnext()
    
    try:
        # Get all doctypes
        doctypes = frappe.get_all("DocType", 
                                 fields=["name", "module", "custom", "description"],
                                 order_by="name")
        print(f"doctypes list {doctypes}")
         
        if not doctypes:
            return "No doctypes found."
         
        # Format the list
        formatted_list = ["Available ERPNext DocTypes:", ""]
         
        # Group by module for better readability
        by_module = {}
        for dt in doctypes:
            module = dt.get("module", "Unknown")
            if module not in by_module:
                    by_module[module] = []
            
            by_module[module].append(dt)
        
        # Format output
        for module, docs in sorted(by_module.items()):
            formatted_list.append(f"\n{module}")
            for doc in docs:
                custom_flag = " (Custom)" if doc.get("custom") else ""
                desc = f" - {doc.get('description', '')}" if doc.get('description') else ""
                formatted_list.append(f"  • {doc['name']}{custom_flag}{desc}")
        
        formatted_list.append(f"\nTotal DocTypes: {len(doctypes)}")
        return "\n".join(formatted_list)
    except Exception as e:
        return f"Error listing doctypes: {str(e)}"
    
@mcp.tool()
async def get_doctype_info(doctype_name: str) -> str:
    """
    Get detailed information about a specific doctype

    Args:
        doctype_name (str): Name of the doctype to get info about

    Returns:
        str: doctype's info
    """
    init_erpnext()
    
    try:
        # Get doctype definition
        doctype = frappe.get_doc("Doctype", doctype_name)
        
        info = [f"DocType: {doctype.name}"]
        info.append(f"Module: {doctype.module}")
        info.append(f"Description: {doctype.description or 'No description'}")
        info.append(f"Custom: {'Yes' if doctype.custom else 'No'}")
        info.append(f"Is Single: {'Yes' if doctype.issingle else 'No'}")
        info.append(f"Document Type: {doctype.document_type or 'Standard'}")
        
        # List fields
        if doctype.fields:
            info.append("\nFields:")
            for field in doctype.fields:
                if field.fieldtype not in ["Section Break", "Column Break"]:
                    info.append(f"  • {field.label} ({field.fieldname}) - {field.fieldtype}")
        
        return "\n".join(info)
        
    except Exception as e:
        return f"Error getting doctype info: {str(e)}"
    
if __name__ == "__main__":
    # Run the server with stdio transport
    mcp.run(transport='stdio')