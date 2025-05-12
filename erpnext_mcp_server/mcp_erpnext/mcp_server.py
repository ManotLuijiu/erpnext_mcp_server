"""
ERPNext MCP Server - Model Context Protocol server for ERPNext

This module provides an MCP server implementation for ERPNext that allows AI assistants
to interact with ERPNext via the Model Context Protocol.

It can be used in three ways:
1. As a standalone server (for development or production)
2. Integrated with Frappe/ERPNext as a benchmark command
3. Via the Claude desktop app
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import frappe
from frappe.utils import cstr, get_files_path
from mcp.server.fastmcp import Context, FastMCP, Image

# Configure logging
logger = logging.getLogger(__name__)

class ERPNextMCPServer(FastMCP):
    """MCP Server for ERPNext integration"""
    
    def __init__(self, name: str = "ERPNext MCP", **settings: Any):
        """Initialize the ERPNext MCP server
        
        Args:
            name: Name of the server
            **settings: Additional settings to pass to FastMCP
        """
        # Default settings for production
        default_settings = {
            "debug": False,
            "log_level": "INFO",
            # Use 0.0.0.0 in production to bind to all interfaces
            # Use 127.0.0.1 in development for security
            "host": "0.0.0.0" if frappe.conf.get("env") == "production" else "127.0.0.1",
            "port": 8080,
        }
        
        # Override with any provided settings
        merged_settings = {**default_settings, **settings}
        
        # Initialize the FastMCP server
        super().__init__(
            name=name,
            instructions="ERPNext MCP Server provides access to ERPNext functionality via MCP",
            **merged_settings
        )
        
        # Register tools
        self._register_tools()
        # Register resources
        self._register_resources()
        # Register prompts
        self._register_prompts()

    def _register_tools(self):
        """Register all available tools"""
        # Document operations
        self.add_tool(self.get_doctype_info, 
                      description="Get information about a DocType's fields and structure")
        self.add_tool(self.get_document, 
                      description="Get a document by doctype and name")
        self.add_tool(self.search_documents, 
                      description="Search for documents of a specific doctype")
        
        # File operations
        self.add_tool(self.list_files, 
                      description="List files in the ERPNext file store")
        self.add_tool(self.get_file_info, 
                      description="Get information about a file")
        
        # System information
        self.add_tool(self.get_system_info, 
                      description="Get information about the ERPNext system")
        
        # User information
        self.add_tool(self.get_user_info, 
                      description="Get information about the current user")

    def _register_resources(self):
        """Register all available resources"""
        @self.resource("erp://system-info")
        def system_info_resource():
            """System information resource"""
            return self._get_system_info_dict()
        
        @self.resource("erp://user-info")
        def user_info_resource():
            """User information resource"""
            return self._get_user_info_dict()
    
    def _register_prompts(self):
        """Register all available prompts"""
        @self.prompt(name="document_analysis")
        def document_analysis_prompt(doctype: str, docname: str):
            """Analyze an ERPNext document"""
            doc = frappe.get_doc(doctype, docname)
            if not doc:
                return [{"role": "user", "content": f"No document found with doctype {doctype} and name {docname}"}]
            
            doc_json = doc.as_dict()
            
            return [
                {
                    "role": "user", 
                    "content": f"""Please analyze this {doctype} document:
                    
{json.dumps(doc_json, indent=2)}

What are the key pieces of information in this document? What actions might be appropriate based on this data?
                    """
                }
            ]

    async def get_doctype_info(self, doctype: str, ctx: Context) -> Dict[str, Any]:
        """Get information about a DocType
        
        Args:
            doctype: The DocType to get information about
            ctx: MCP context
        
        Returns:
            Dictionary containing DocType information
        """
        try:
            # Check if the DocType exists
            if not frappe.db.exists("DocType", doctype):
                await ctx.warning(f"DocType '{doctype}' not found")
                return {"error": f"DocType '{doctype}' not found"}
            
            # Get the DocType metadata
            meta = frappe.get_meta(doctype)
            
            # Extract field information
            fields = []
            for field in meta.fields:
                fields.append({
                    "fieldname": field.fieldname,
                    "label": field.label,
                    "fieldtype": field.fieldtype,
                    "reqd": field.reqd,
                    "options": field.options,
                    "description": field.description,
                })
            
            # Get child tables
            child_tables = []
            for field in meta.fields:
                if field.fieldtype == "Table":
                    child_tables.append(field.options)
            
            # Build the result
            result = {
                "doctype": doctype,
                "name": meta.name,
                "module": meta.module,
                "fields": fields,
                "child_tables": child_tables,
                "is_submittable": meta.is_submittable,
                "is_tree": meta.is_tree,
                "track_changes": meta.track_changes,
                "icon": meta.icon,
                "description": meta.description,
            }
            
            await ctx.info(f"Retrieved information for DocType '{doctype}'")
            return result
            
        except Exception as e:
            await ctx.error(f"Error getting DocType information: {e}")
            return {"error": str(e)}

    async def get_document(self, doctype: str, name: str, ctx: Context) -> Dict[str, Any]:
        """Get a document by doctype and name
        
        Args:
            doctype: The DocType of the document
            name: The name of the document
            ctx: MCP context
        
        Returns:
            The document as a dictionary
        """
        try:
            # Check if document exists
            if not frappe.db.exists(doctype, name):
                await ctx.warning(f"Document '{doctype}:{name}' not found")
                return {"error": f"Document '{doctype}:{name}' not found"}
            
            # Get the document
            doc = frappe.get_doc(doctype, name)
            
            # Convert document to dictionary
            doc_dict = doc.as_dict()
            
            # Clean up internal fields
            for field in list(doc_dict.keys()):
                if field.startswith("_"):
                    del doc_dict[field]
            
            await ctx.info(f"Retrieved document '{doctype}:{name}'")
            return doc_dict
            
        except Exception as e:
            await ctx.error(f"Error getting document: {e}")
            return {"error": str(e)}

    async def search_documents(self, 
                             doctype: str, 
                             filters: Optional[Dict[str, Any]] = None, 
                             fields: Optional[List[str]] = None,
                             limit: int = 20,
                             ctx: Context) -> Dict[str, Any]:
        """Search for documents of a specific doctype
        
        Args:
            doctype: The DocType to search
            filters: Filters to apply (Frappe filter format)
            fields: Fields to include in results (None for all)
            limit: Maximum number of results
            ctx: MCP context
        
        Returns:
            Dictionary with search results
        """
        try:
            # Check if the DocType exists
            if not frappe.db.exists("DocType", doctype):
                await ctx.warning(f"DocType '{doctype}' not found")
                return {"error": f"DocType '{doctype}' not found"}
            
            # Default fields if none provided
            if not fields:
                fields = ["name"]
                meta = frappe.get_meta(doctype)
                if meta.title_field:
                    fields.append(meta.title_field)
                if meta.search_fields:
                    fields.extend(meta.search_fields.split(","))
            
            # Convert fields to list if it's a string
            if isinstance(fields, str):
                fields = fields.split(",")
            
            # Ensure name is always included
            if "name" not in fields:
                fields.append("name")
            
            # Execute the query
            results = frappe.get_all(
                doctype,
                filters=filters or {},
                fields=fields,
                limit=limit
            )
            
            await ctx.info(f"Found {len(results)} {doctype} documents")
            return {
                "doctype": doctype,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            await ctx.error(f"Error searching documents: {e}")
            return {"error": str(e)}

    async def list_files(self, 
                       folder: str = "", 
                       extensions: Optional[List[str]] = None,
                       limit: int = 50,
                       ctx: Context) -> Dict[str, Any]:
        """List files in the ERPNext file store
        
        Args:
            folder: Folder path within ERPNext files
            extensions: Filter by file extensions (e.g. ["pdf", "csv"])
            limit: Maximum number of files to return
            ctx: MCP context
        
        Returns:
            Dictionary with file listing
        """
        try:
            # Get the base files path
            base_path = Path(get_files_path())
            folder_path = base_path / folder if folder else base_path
            
            # Safety check - prevent directory traversal
            if not str(folder_path.resolve()).startswith(str(base_path.resolve())):
                await ctx.error("Invalid folder path (attempted directory traversal)")
                return {"error": "Invalid folder path"}
            
            # Check if folder exists
            if not folder_path.exists() or not folder_path.is_dir():
                await ctx.warning(f"Folder '{folder}' not found or is not a directory")
                return {"error": f"Folder '{folder}' not found or is not a directory"}
            
            # List files and directories
            files = []
            folders = []
            
            for item in folder_path.iterdir():
                if len(files) + len(folders) >= limit:
                    break
                    
                if item.is_dir():
                    folders.append({
                        "name": item.name,
                        "type": "folder",
                        "path": str(item.relative_to(base_path)),
                    })
                else:
                    # Check extension filter if provided
                    if extensions and item.suffix.lstrip('.').lower() not in extensions:
                        continue
                        
                    files.append({
                        "name": item.name,
                        "type": "file",
                        "path": str(item.relative_to(base_path)),
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                        "extension": item.suffix.lstrip('.').lower(),
                    })
            
            await ctx.info(f"Listed {len(files)} files and {len(folders)} folders in '{folder}'")
            return {
                "folder": folder,
                "folders": folders,
                "files": files,
                "total": len(files) + len(folders),
                "has_more": len(files) + len(folders) >= limit,
            }
            
        except Exception as e:
            await ctx.error(f"Error listing files: {e}")
            return {"error": str(e)}

    async def get_file_info(self, file_path: str, ctx: Context) -> Dict[str, Any]:
        """Get information about a file
        
        Args:
            file_path: Path to the file (relative to ERPNext files folder)
            ctx: MCP context
        
        Returns:
            Dictionary with file information
        """
        try:
            # Get the base files path
            base_path = Path(get_files_path())
            full_path = base_path / file_path
            
            # Safety check - prevent directory traversal
            if not str(full_path.resolve()).startswith(str(base_path.resolve())):
                await ctx.error("Invalid file path (attempted directory traversal)")
                return {"error": "Invalid file path"}
            
            # Check if file exists
            if not full_path.exists():
                await ctx.warning(f"File '{file_path}' not found")
                return {"error": f"File '{file_path}' not found"}
            
            # Get file information
            stat = full_path.stat()
            
            # Check if it's a file or directory
            if full_path.is_dir():
                result = {
                    "name": full_path.name,
                    "path": file_path,
                    "type": "folder",
                    "size": 0,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_directory": True,
                }
            else:
                # Look up file in the File doctype if possible
                file_doc = None
                try:
                    file_doc = frappe.get_all(
                        "File",
                        filters={"file_url": f"/files/{file_path}"},
                        fields=["name", "file_name", "is_private", 
                                "file_size", "attached_to_doctype", 
                                "attached_to_name", "attached_to_field"],
                        limit=1
                    )
                except Exception:
                    # If lookup fails, continue without the File doc info
                    pass
                
                result = {
                    "name": full_path.name,
                    "path": file_path,
                    "type": "file",
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": full_path.suffix.lstrip('.').lower(),
                    "is_directory": False,
                    "content_type": self._get_content_type(full_path),
                }
                
                # Add file doc info if found
                if file_doc:
                    result.update({
                        "is_private": file_doc[0].get("is_private"),
                        "attached_to_doctype": file_doc[0].get("attached_to_doctype"),
                        "attached_to_name": file_doc[0].get("attached_to_name"),
                        "attached_to_field": file_doc[0].get("attached_to_field"),
                    })
            
            await ctx.info(f"Retrieved information for '{file_path}'")
            return result
            
        except Exception as e:
            await ctx.error(f"Error getting file information: {e}")
            return {"error": str(e)}

    async def get_system_info(self, ctx: Context) -> Dict[str, Any]:
        """Get information about the ERPNext system
        
        Args:
            ctx: MCP context
        
        Returns:
            Dictionary with system information
        """
        try:
            result = self._get_system_info_dict()
            await ctx.info("Retrieved system information")
            return result
            
        except Exception as e:
            await ctx.error(f"Error getting system information: {e}")
            return {"error": str(e)}

    async def get_user_info(self, ctx: Context) -> Dict[str, Any]:
        """Get information about the current user
        
        Args:
            ctx: MCP context
        
        Returns:
            Dictionary with user information
        """
        try:
            result = self._get_user_info_dict()
            await ctx.info("Retrieved user information")
            return result
            
        except Exception as e:
            await ctx.error(f"Error getting user information: {e}")
            return {"error": str(e)}

    def _get_system_info_dict(self) -> Dict[str, Any]:
        """Get system information as a dictionary"""
        frappe_version = getattr(frappe, "__version__", "unknown")
        
        # Try to get ERPNext version if available
        erpnext_version = "not installed"
        try:
            if frappe.db.exists("Module Def", "erpnext"):
                erpnext_version = frappe.get_attr("erpnext.__version__")
        except Exception:
            pass
        
        return {
            "frappe_version": frappe_version,
            "erpnext_version": erpnext_version,
            "site": frappe.local.site,
            "environment": frappe.conf.get("env", "development"),
            "python_version": sys.version,
            "current_datetime": datetime.now().isoformat(),
            "installed_apps": frappe.get_installed_apps(),
        }

    def _get_user_info_dict(self) -> Dict[str, Any]:
        """Get user information as a dictionary"""
        user = frappe.session.user
        
        # Get roles
        roles = frappe.get_roles(user)
        
        # Get user doc if possible
        user_info = {
            "user": user,
            "roles": roles,
            "is_system_user": "System User" in roles,
            "is_admin": "Administrator" in roles,
        }
        
        # Try to get more details if available
        try:
            user_doc = frappe.get_doc("User", user)
            user_info.update({
                "full_name": user_doc.full_name,
                "user_type": user_doc.user_type,
                "user_image": user_doc.user_image,
                "email": user_doc.email,
            })
        except Exception:
            # If we can't get the user doc, just continue with basic info
            pass
        
        return user_info

    def _get_content_type(self, file_path: Path) -> str:
        """Determine the content type for a file based on its extension"""
        extension = file_path.suffix.lower()
        content_types = {
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".html": "text/html",
        }
        return content_types.get(extension, "application/octet-stream")

# Initialize server instance for easy import
mcp_server = ERPNextMCPServer()

def get_server():
    """Get the MCP server instance"""
    return mcp_server
