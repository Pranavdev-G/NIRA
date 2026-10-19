"""
Tool Registry and Dispatcher for Aegis MCP Tools.
Complies with Model Context Protocol tools/list and tools/call interface.
"""

import json
import time
from typing import Dict, Any, List
from app.mcp.protocol import MCPToolDefinition, MCPToolInputSchema, MCPCallResult, MCPContentItem
from app.models.schemas import (
    Event, Context, Risk, AssessRiskRequest,
    StartWellnessCheckRequest, WellnessCheckReplyRequest,
    NotifyCaregiverRequest, GenerateEmergencyPacketRequest,
    EscalateEmergencyRequest
)
from app.services.risk_engine import RiskEngine
from app.services.state_machine import WellnessStateMachine
from app.services.caregiver_service import CaregiverService
from app.services.emergency_service import EmergencyService


EVENT_SCHEMA_PROPERTIES = {
    "event_type": {
        "type": "string",
        "description": "Type of event, e.g. 'fall_detected', 'loud_thud', 'prolonged_inactivity', 'vital_anomaly'"
    },
    "confidence": {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": "Detection confidence score between 0.0 and 1.0"
    },
    "location": {
        "type": "string",
        "description": "Location within residence, e.g. 'living_room', 'bathroom', 'kitchen'"
    },
    "timestamp": {
        "type": "string",
        "description": "ISO 8601 formatted timestamp string, e.g. '2026-10-17T08:15:30Z'"
    },
    "movement_after_event": {
        "type": "string",
        "description": "Telemetry status of post-event movement, e.g. 'none', 'slight_twitch', 'normal', 'crawling'"
    }
}

CONTEXT_SCHEMA_PROPERTIES = {
    "activity": {
        "type": "string",
        "description": "Pre-event baseline activity, e.g. 'walking_to_kitchen', 'sleeping', 'showering'"
    },
    "time_context": {
        "type": "string",
        "description": "Temporal/circadian slot, e.g. 'night_time', 'early_morning', 'afternoon'"
    },
    "baseline_deviation": {
        "type": "number",
        "description": "Normalized deviation from personal baseline (0.0=normal, 1.0+=severe anomaly)"
    },
    "wearable_status": {
        "type": "string",
        "description": "Wearable sensor status, e.g. 'worn_normal', 'high_heart_rate', 'disconnected'"
    },
    "environment": {
        "type": "string",
        "description": "Ambient environmental state, e.g. 'dark_room_wet_floor', 'well_lit'"
    }
}

RISK_SCHEMA_PROPERTIES = {
    "risk_level": {
        "type": "string",
        "enum": ["LOW", "MODERATE", "HIGH", "CRITICAL"],
        "description": "Clinical and safety risk tier"
    },
    "confidence": {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": "Risk confidence score between 0.0 and 1.0"
    },
    "reasons": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of rationale factors driving the risk score"
    }
}


def get_tools_manifest() -> List[MCPToolDefinition]:
    """Returns the MCP tool definitions for Alexa+ discovery."""
    return [
        MCPToolDefinition(
            name="assess_risk",
            description="Consumes ambient event and contextual sensor data to return an updated clinical risk assessment (LOW, MODERATE, HIGH, CRITICAL).",
            inputSchema=MCPToolInputSchema(
                properties={
                    "event": {
                        "type": "object",
                        "properties": EVENT_SCHEMA_PROPERTIES,
                        "required": ["event_type", "confidence", "location", "timestamp", "movement_after_event"]
                    },
                    "context": {
                        "type": "object",
                        "properties": CONTEXT_SCHEMA_PROPERTIES,
                        "required": ["activity", "time_context", "baseline_deviation", "wearable_status", "environment"]
                    }
                },
                required=["event", "context"]
            )
        ),
        MCPToolDefinition(
            name="start_wellness_check",
            description="Initiates an interactive conversational Alexa voice prompt asking the user if they are okay, setting up state tracking and timeout escalation.",
            inputSchema=MCPToolInputSchema(
                properties={
                    "session_id": {"type": "string", "description": "Optional session identifier"},
                    "event": {"type": "object", "properties": EVENT_SCHEMA_PROPERTIES},
                    "context": {"type": "object", "properties": CONTEXT_SCHEMA_PROPERTIES},
                    "initial_risk": {"type": "object", "properties": RISK_SCHEMA_PROPERTIES},
                    "prompt_override": {"type": "string", "description": "Custom prompt text if needed"}
                }
            )
        ),
        MCPToolDefinition(
            name="notify_caregiver",
            description="Triggers multi-channel mock caregiver notifications (Alexa Drop-In, Push, SMS) for MODERATE or HIGH risk incidents.",
            inputSchema=MCPToolInputSchema(
                properties={
                    "risk": {
                        "type": "object",
                        "properties": RISK_SCHEMA_PROPERTIES,
                        "required": ["risk_level", "confidence", "reasons"]
                    },
                    "event": {"type": "object", "properties": EVENT_SCHEMA_PROPERTIES},
                    "context": {"type": "object", "properties": CONTEXT_SCHEMA_PROPERTIES},
                    "custom_message": {"type": "string", "description": "Optional custom message for caregiver"},
                    "target_channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Channels: alexa_drop_in, push_notification, sms"
                    }
                },
                required=["risk"]
            )
        ),
        MCPToolDefinition(
            name="generate_emergency_packet",
            description="Compiles incident metadata, clinical risk breakdown, temporal signals, and patient medical profile into a structured CAD summary.",
            inputSchema=MCPToolInputSchema(
                properties={
                    "event": {
                        "type": "object",
                        "properties": EVENT_SCHEMA_PROPERTIES,
                        "required": ["event_type", "confidence", "location", "timestamp", "movement_after_event"]
                    },
                    "context": {
                        "type": "object",
                        "properties": CONTEXT_SCHEMA_PROPERTIES,
                        "required": ["activity", "time_context", "baseline_deviation", "wearable_status", "environment"]
                    },
                    "risk": {
                        "type": "object",
                        "properties": RISK_SCHEMA_PROPERTIES,
                        "required": ["risk_level", "confidence", "reasons"]
                    },
                    "patient_id": {"type": "string", "description": "Optional patient identifier"}
                },
                required=["event", "context", "risk"]
            )
        ),
        MCPToolDefinition(
            name="escalate_emergency",
            description="Directs CRITICAL alerts to a simulated emergency service (EMS CAD) endpoint, unlocking entry doors and establishing ambient audio link.",
            inputSchema=MCPToolInputSchema(
                properties={
                    "emergency_packet": {
                        "type": "object",
                        "description": "Optional compiled emergency packet from generate_emergency_packet"
                    },
                    "event": {"type": "object", "properties": EVENT_SCHEMA_PROPERTIES},
                    "context": {"type": "object", "properties": CONTEXT_SCHEMA_PROPERTIES},
                    "risk": {"type": "object", "properties": RISK_SCHEMA_PROPERTIES},
                    "cad_agency_code": {"type": "string", "default": "EMS-CAD-MA-02108"}
                }
            )
        ),
        MCPToolDefinition(
            name="respond_wellness_check",
            description="Evaluates user speech response ('I'm okay' vs 'Help me' vs timeout) in the ambient wellness check state machine.",
            inputSchema=MCPToolInputSchema(
                properties={
                    "session_id": {"type": "string", "description": "Active session ID"},
                    "user_speech_transcript": {"type": "string", "description": "Transcribed user utterance"},
                    "is_timeout": {"type": "boolean", "default": False, "description": "True if user did not answer in time"}
                },
                required=["session_id"]
            )
        )
    ]


async def dispatch_mcp_tool_call(tool_name: str, arguments: Dict[str, Any]) -> MCPCallResult:
    """
    Executes a requested MCP tool with argument validation and formats standard MCP response.
    """
    start_time = time.perf_counter()

    try:
        if tool_name == "assess_risk":
            event = Event(**arguments.get("event", {}))
            context = Context(**arguments.get("context", {}))
            result = RiskEngine.evaluate_and_respond(event, context)
            latency = (time.perf_counter() - start_time) * 1000.0
            result.latency_ms = round(latency, 2)
            
            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": result.latency_ms}
            )

        elif tool_name == "start_wellness_check":
            req = StartWellnessCheckRequest(**arguments)
            result = WellnessStateMachine.start_wellness_check(
                session_id=req.session_id,
                event=req.event,
                context=req.context,
                initial_risk=req.initial_risk,
                prompt_override=req.prompt_override
            )
            latency = (time.perf_counter() - start_time) * 1000.0

            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": round(latency, 2)}
            )

        elif tool_name == "notify_caregiver":
            req = NotifyCaregiverRequest(**arguments)
            result = await CaregiverService.dispatch_notification(req)
            latency = (time.perf_counter() - start_time) * 1000.0

            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": round(latency, 2)}
            )

        elif tool_name == "generate_emergency_packet":
            req = GenerateEmergencyPacketRequest(**arguments)
            result = EmergencyService.generate_packet(
                event=req.event,
                context=req.context,
                risk=req.risk,
                patient_id=req.patient_id
            )
            latency = (time.perf_counter() - start_time) * 1000.0

            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": round(latency, 2)}
            )

        elif tool_name == "escalate_emergency":
            req = EscalateEmergencyRequest(**arguments)
            result = await EmergencyService.escalate_to_cad(req)
            latency = (time.perf_counter() - start_time) * 1000.0

            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": round(latency, 2)}
            )

        elif tool_name == "respond_wellness_check":
            req = WellnessCheckReplyRequest(**arguments)
            result = await WellnessStateMachine.process_reply(req)
            latency = (time.perf_counter() - start_time) * 1000.0

            return MCPCallResult(
                content=[MCPContentItem(text=result.model_dump_json(indent=2))],
                isError=False,
                metadata={"latency_ms": round(latency, 2)}
            )

        else:
            return MCPCallResult(
                content=[MCPContentItem(text=f"Unknown tool name: '{tool_name}'")],
                isError=True
            )

    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000.0
        return MCPCallResult(
            content=[MCPContentItem(text=f"Error executing tool '{tool_name}': {str(e)}")],
            isError=True,
            metadata={"latency_ms": round(latency, 2)}
        )
