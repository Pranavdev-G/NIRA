"""
Model Context Protocol (MCP) data models and JSON-RPC 2.0 specifications.
Adheres to the official Model Context Protocol 2024-11-05/2025 Streamable HTTP spec.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPToolInputSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: MCPToolInputSchema


class MCPContentItem(BaseModel):
    type: str = "text"
    text: str


class MCPCallResult(BaseModel):
    content: List[MCPContentItem]
    isError: bool = False
    metadata: Optional[Dict[str, Any]] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
