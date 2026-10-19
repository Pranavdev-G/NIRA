"""
Mock Caregiver Notification Service.
Simulates low-latency dispatch across Alexa Drop-In, Mobile Push, and SMS.
"""

import uuid
import time
from datetime import datetime, timezone
from typing import List, Optional
from app.config import settings
from app.models.schemas import (
    Risk, Event, Context, NotifyCaregiverRequest,
    CaregiverNotificationResponse, CaregiverNotificationChannelResult
)


class CaregiverService:
    """Dispatches real-time caregiver alerts for MODERATE and HIGH risk conditions."""

    @classmethod
    async def dispatch_notification(cls, request: NotifyCaregiverRequest) -> CaregiverNotificationResponse:
        start = time.perf_counter()
        notification_id = f"notif_{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build notification headline and content
        loc = request.event.location if request.event else "Home"
        event_label = request.event.event_type.replace("_", " ").title() if request.event else "Safety Alert"
        headline = f"Aegis Care Alert: {request.risk.risk_level} Risk - {event_label} in {loc}"

        reasons_summary = "; ".join(request.risk.reasons[:2]) if request.risk.reasons else "Telemetry baseline anomaly"
        body = (
            request.custom_message
            or f"Aegis CARE detected a potential incident ({event_label}) in the {loc}. "
               f"Risk Level: {request.risk.risk_level} (confidence {request.risk.confidence:.0%}). "
               f"Indicators: {reasons_summary}. An interactive voice check is underway."
        )

        channels = request.target_channels or [
            "alexa_drop_in",
            "push_notification",
            "sms"
        ]

        delivered_channels: List[CaregiverNotificationChannelResult] = []

        for ch in channels:
            ch_start = time.perf_counter()
            # Fast mock dispatch
            recipient = settings.PRIMARY_CAREGIVER_NAME
            if ch == "sms":
                recipient = settings.PRIMARY_CAREGIVER_PHONE
            elif ch == "alexa_drop_in":
                recipient = settings.PRIMARY_CAREGIVER_DEVICE_ID
            elif ch == "push_notification":
                recipient = f"push_token_sarah_vance_ios"

            ch_elapsed_ms = (time.perf_counter() - ch_start) * 1000.0 + 2.5

            delivered_channels.append(
                CaregiverNotificationChannelResult(
                    channel=ch,
                    status="DELIVERED",
                    recipient=recipient,
                    delivery_latency_ms=round(ch_elapsed_ms, 2)
                )
            )

        return CaregiverNotificationResponse(
            notification_id=notification_id,
            patient_id=settings.DEFAULT_PATIENT_ID,
            risk_level=request.risk.risk_level,
            headline=headline,
            body=body,
            channels_delivered=delivered_channels,
            dispatched_at=timestamp,
            caregiver_contact=f"{settings.PRIMARY_CAREGIVER_NAME} ({settings.PRIMARY_CAREGIVER_PHONE})"
        )
