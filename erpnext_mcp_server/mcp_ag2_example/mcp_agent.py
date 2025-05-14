"""
MCP-enabled AutoGen Assistant Agent.

This module provides an extension of AutoGen's AssistantAgent that can interact with
MCP (Model Context Protocol) servers, enabling dynamic tool discovery and resource access.
"""

from typing import Any, Dict, List, Optional, Union

from autogen import AssistantAgent
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class ERPNextMCPAgent(AssistantAgent):
    """An AutoGen assistant agent that works with the ERPNext MCP Server."""

    def __init__(
        self,
        name: str,
        system_message: str,
        server_url: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the ERPNext MCP agent.

        Args:
            name: Name for the agent
            system_message: System message for the agent
            server_url: URL of the ERPNext server
            api_key: Optional API key for authentication
            api_secret: Optional API secret for authentication
        """
        super().__init__(name=name, system_message=system_message, **kwargs)
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret

        @self.register_for_llm(description="Read content from an ERPNext MCP resource")
        def read_resource(uri: str) -> str:
            """Read content from an ERPNext MCP resource.

            Args:
                uri (str): The URI of the resource (format: erp://doctype/DocType or storage://local/path)

            Raises:
                ValueError: _description_

            Returns:
                str: The content of the resource
            """
            try:
                response = self._call_api("read_resource", {"uri": uri})
                if response.get("status") == "success":
                    return response.get("content", "")
                else:
                    return f"Error: {response.get('message', 'Unknown error')}"
            except Exception as e:
                return f"Error reading resource: {str(e)}"

        @self.register_for_llm(description="Call a tool to perform an operation")
        def call_tool(name: str, args: dict) -> Any:
            """Call an ERPNext MCP tool with the specified arguments.

            Args:
                name: Name of the tool to call
                args: Arguments to pass to the tool

            Returns:
                Any: The result of the tool operation
            """
            try:
                response = self._call_api(
                    "call_tool", {"name": name, "arguments": args}
                )
                if response.get("status") == "success":
                    content = response.get("content", [])
                    if len(content) == 1:
                        return content[0]
                    return content
                else:
                    return f"Error: {response.get('message', 'Unknown error')}"
            except Exception as e:
                return f"Error calling tool: {str(e)}"

        @self.register_for_llm(description="List available tools")
        def list_tools() -> List[Dict[str, Any]]:
            """Discover available tools from the ERPNext MCP server.

            Returns:
                list[dict[str, Any]]: List of available tools and their schemas
            """
            try:
                response = self._call_api("list_tools", {})
                if response.get("status") == "success":
                    return response.get("tools", [])
                else:
                    return []
            except Exception as e:
                print(f"Error listing tools: {e}")
                return []

        self.read_resource = read_resource
        self.call_tool = call_tool
        self.list_tools = list_tools

    def _call_api(self, endpoint: str, params: dict) -> dict:
        """Call the ERPNext MCP API.

        Args:
            endpoint: API endpoint name
            params: Parameters for the API call

        Returns:
            dict: API response
        """
        import requests

        url = f"{self.server_url}/api/method/erpnext_mcp_server.mcp_ag2_example.server.api.{endpoint}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Add authentication if provided
        if self.api_key and self.api_secret:
            auth = (self.api_key, self.api_secret)
        else:
            auth = None

        response = requests.post(url, json=params, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json().get("message", {})


class MCPAssistantAgent(AssistantAgent):
    """An AutoGen assistant agent with MCP capabilities.

    This agent extends the standard AutoGen AssistantAgent with the ability to:
    - Discover and use tools dynamically from MCP servers
    - Access resources through the MCP protocol
    - Handle both synchronous and asynchronous operations

    Attributes:
        server_params (StdioServerParameters): Configuration for the MCP server connection
        session (Optional[ClientSession]): Active MCP client session when connected
    """

    def __init__(
        self,
        name: str,
        system_message: str,
        mcp_server_command: str,
        mcp_server_args: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the MCP-enabled

        Args:
            name (str): _description_
            system_message (str): _description_
            mcp_server_command (str): _description_
            mcp_server_args (Optional[List[str]], optional): _description_. Defaults to None.
        """
        super().__init__(name=name, system_message=system_message, **kwargs)
        self.server_params = StdioServerParameters(
            command=mcp_server_command, args=mcp_server_args or []
        )

        @self.register_for_llm(description="Read content form a MCP resource")
        async def read_resource(uri: str) -> str:
            """Read content from an MCP resource

            Args:
                uri (str): The URI of the resource (format: storage://local/path)

            Returns:
                str: The content of the resource

            Raises:
                Exception: If reading the resource fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        from pydantic import AnyUrl, ValidationError

                        try:
                            validated_uri = AnyUrl(uri)
                        except ValidationError as e:
                            raise ValueError(f"Invalid URI format: {e}")

                        resource_result = await session.read_resource(validated_uri)
                        return str(
                            resource_result
                        )  # Adjusted to handle the result as a string
            except Exception as e:
                return f"Error reading resource: {str(e)}"

        @self.register_for_llm(description="Call a tool to perform an operation")
        async def call_tool(name: str, args: dict) -> Any:
            """Call an MCP tool with the specified arguments.

            Args:
                name: Name of the tool to call
                args: Arguments to pass to the tool

            Returns:
                Any: The result of the tool operation

            Raises:
                Exception: If the tool call fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(name, args)
                        if not result:
                            return {"status": "success"}
                        return result
            except Exception as e:
                return f"Error calling tool: {str(e)}"

        @self.register_for_llm(description="List available tools")
        async def list_tools() -> List[Dict[str, Any]]:
            """Discover available tools from the MCP server.

            Returns:
                list[dict[str, Any]]: List of available tools and their schemas

            Raises:
                Exception: If tool discovery fails
            """
            try:
                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        return [
                            {"name": tool[0], "details": tool[1]}
                            for tool in tools_result
                        ]
            except Exception as e:
                print(f"Error listing tools: {e}")
                raise

        self.read_resource = read_resource
        self.call_tool = call_tool
        self.list_tools = list_tools
