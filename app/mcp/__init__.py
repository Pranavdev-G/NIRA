"""MCP package."""
from app.mcp.protocol import JSONRPCRequest, JSONRPCResponse, MCPCallResult
from app.mcp.tools_registry import get_tools_manifest, dispatch_mcp_tool_call
