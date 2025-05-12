"""
Local File System MCP Server.

This module implements an MCP server that provides access to the local file system,
enabling file operations through the Model Context Protocol (MCP).

The server provides:
1. Resource-based file reading via storage://local/{/path}
2. Tool-based file writing via write_file tool
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from mcp.types import CallToolResult, Resource, ResourceTemplate, TextContent, Tool
from pydantic import AnyUrl, BaseModel, ValidationError
from server.mcp_server import BaseMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class WriteFileParams(BaseModel):
    """Parameters for writing to a file"""
    
    path: str
    content: str
    
    model_config = {
        "json_schema_extra":{
            "examples": [{"path": "text.txt", "content": "Hello World"}]
        }
    }
    
class WriteFileResponse(BaseModel):
    """Response from writing to a file"""
    
    path: str
    bytes_written: int
    modified_at: datetime
    
class LocalFileServer(BaseMCPServer):
    """MCP Server implementation for local file system operations.
    
    This server provides MCP-compatible access to the local file system, supporting both resource-based file reading and tool-based file writing. All operations are restricted to the specified base_path for security.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize the local file server.
        
        Args:
            base_path: Optional base directory for file operations.
            Defaults to current working directory.
        """
        try:
            self.base_path = Path(base_path or os.getcwd()).resolve()
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True)
                logger.info(f"Created base directory: {self.base_path}")
                
            super().__init__("local-file-server")
            logger.info(f"LocalFileServer initialized with base path: {self.base_path}")
            
            # Register handlers during initialization
            self._register_handlers()
        except Exception as e:
            logger.error(f"Failed to initialize LocalFileServer: {e}")
            raise
        
    def _register_handlers(self):
        """Register all MCP protocol handlers."""
        try:
            # Resource handlers
            @self._server.list_resources()
            async def handle_list_resources():
                """List available resources in the file system."""
                return [
                    Resource(
                        uri="storage://local/",
                        name="Local Document Store",
                        description="A local document store",
                        mimeType="text/plain"
                    )
                ]
                
            @self._server.list_resource_templates()
            async def handle_list_resource_templates():
                """List available resource templates."""
                return [
                    ResourceTemplate(
                        uriTemplate="storage://local/{/path}",
                        name="Local Document Store",
                        description="A local document store",
                        mimeType="text/plain",
                    )
                ]