"""
Streamable HTTP and SSE Transport for Model Context Protocol (MCP).
Compatible with official MCP 2024-11-05/2025 specification.
"""

import uuid
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import settings
from app.mcp.protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError
from app.mcp.tools_registry import get_tools_manifest, dispatch_mcp_tool_call


router = APIRouter(tags=["MCP Protocol"])

# Track active SSE sessions
sse_sessions: Dict[str, asyncio.Queue] = {}


@router.post("/mcp", response_model=JSONRPCResponse)
async def handle_mcp_post(request_data: JSONRPCRequest, response: Response):
    """
    Core MCP Streamable HTTP JSON-RPC endpoint.
    Handles 'initialize', 'tools/list', 'tools/call', and 'ping'.
    """
    method = request_data.method
    req_id = request_data.id
    params = request_data.params or {}

    # Handle MCP Handshake: initialize
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "logging": {}
            },
            "serverInfo": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION
            }
        }
        return JSONRPCResponse(id=req_id, result=result)

    # Handle notifications/initialized
    if method == "notifications/initialized":
        return JSONRPCResponse(id=req_id, result={})

    # Handle ping
    if method == "ping":
        return JSONRPCResponse(id=req_id, result={})

    # Handle tools/list
    if method == "tools/list":
        tools_list = [t.model_dump() for t in get_tools_manifest()]
        return JSONRPCResponse(id=req_id, result={"tools": tools_list})

    # Handle tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=-32602, message="Missing 'name' in tools/call parameters")
            )

        call_result = await dispatch_mcp_tool_call(tool_name, arguments)
        return JSONRPCResponse(id=req_id, result=call_result.model_dump())

    # Method not found
    return JSONRPCResponse(
        id=req_id,
        error=JSONRPCError(code=-32601, message=f"Method '{method}' not found")
    )


from datetime import datetime, timezone


@router.get("/sse")
async def handle_mcp_sse(request: Request):
    """
    Standard MCP Server-Sent Events (SSE) connection endpoint.
    Also streams NIRA real-time safety pipeline events to web clients.
    """
    session_id = f"mcp_sess_{uuid.uuid4().hex[:10]}"
    queue: asyncio.Queue = asyncio.Queue()
    sse_sessions[session_id] = queue

    from app.services.event_pipeline import global_pipeline
    pipeline_queue = global_pipeline.subscribe()

    async def sse_event_stream():
        # First event: notify client of the message post endpoint with session ID
        endpoint_url = f"/messages?sessionId={session_id}"
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"

        # Emit initial state snapshot
        initial_event = {
            "type": "INITIAL_SNAPSHOT",
            "snapshot": global_pipeline.current_state.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        yield f"event: state_snapshot\ndata: {json.dumps(initial_event)}\n\n"
        yield f"event: message\ndata: {json.dumps(initial_event)}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                mcp_task = asyncio.create_task(queue.get())
                pipe_task = asyncio.create_task(pipeline_queue.get())
                done, pending = await asyncio.wait(
                    [mcp_task, pipe_task],
                    timeout=15.0,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for p in pending:
                    p.cancel()

                if not done:
                    yield ": ping\n\n"
                    continue

                for t in done:
                    try:
                        msg = t.result()
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                        event_type = "state_update" if isinstance(msg, dict) and msg.get("state_changed") else "event_ingested"
                        yield f"event: {event_type}\ndata: {json.dumps(msg)}\n\n"
                    except Exception:
                        pass
        finally:
            sse_sessions.pop(session_id, None)
            global_pipeline.unsubscribe(pipeline_queue)

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/messages")
async def handle_mcp_messages(
    request: Request,
    sessionId: str = Query(..., description="Active MCP session ID from SSE endpoint")
):
    """
    Message handler for SSE transport.
    """
    queue = sse_sessions.get(sessionId)
    if not queue:
        return JSONResponse(status_code=404, content={"error": "Session not found or expired"})

    body = await request.json()
    rpc_req = JSONRPCRequest(**body)

    # Process via handle_mcp_post logic
    resp = await handle_mcp_post(rpc_req, Response())
    await queue.put(resp.model_dump())

    return JSONResponse(status_code=202, content={"status": "accepted"})
