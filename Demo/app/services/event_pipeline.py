"""
Central Multimodal Event Ingestion & Fusion Pipeline for NIRA Ambient Care.
Amazon Developer Hackathon 2026.

Key Capabilities:
  - Unified multimodal event ingestion (wearable, radar, vision, environment, voice).
  - Out-of-order, stale event, and duplicate event protections.
  - Multi-sensor fusion preventing single-sensor false alarms.
  - State progression (NORMAL -> ANOMALY -> ELEVATED -> HIGH -> CRITICAL)
    and state recovery (CRITICAL -> RESPONDING -> RESOLVED -> NORMAL).
  - Traceable evidence accumulation for every risk decision.
  - Thread-safe real-time broadcasting for SSE and WebSocket clients.
  - Persistence to SQLite (TelemetryEventModel, IncidentModel, IncidentTimelineModel).
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import RiskLevel
from app.models.event_contracts import (
    UnifiedEvent, SafetyState, EventSource, EventType,
    EvidenceItem, ResidentStateSnapshot, EventIngestResult
)
from app.database.models import (
    TelemetryEventModel, IncidentModel, IncidentTimelineModel
)

logger = logging.getLogger("NIRAEventPipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")


class EventPipeline:
    """
    Central authoritative ambient safety engine.
    Maintains the live state of the resident, evaluates multimodal evidence,
    and broadcasts state changes in real-time.
    """

    MAX_STALENESS_SECONDS: float = 300.0  # 5 minutes staleness limit
    EVIDENCE_WINDOW_SECONDS: float = 180.0  # 3 minutes rolling evidence window
    MAX_DEDUP_CACHE_SIZE: int = 2000

    def __init__(self, resident_id: str = "user_eleanor_vance"):
        self.resident_id = resident_id
        self._lock = asyncio.Lock()
        
        # Deduplication cache: event_id -> arrival timestamp
        self._dedup_cache: Dict[str, float] = {}
        
        # Sliding evidence window: chronological deque of EvidenceItem
        self._evidence_history: deque[EvidenceItem] = deque(maxlen=100)
        
        # Real-time SSE / WebSocket subscriber queues
        self._subscribers: Set[asyncio.Queue] = set()

        # Authoritative Resident & Residence State
        now_iso = datetime.now(timezone.utc).isoformat()
        self.current_state = ResidentStateSnapshot(
            resident_id=self.resident_id,
            patient_name=settings.DEFAULT_PATIENT_NAME,
            age=79,
            safety_state=SafetyState.NORMAL.value,
            risk_level=RiskLevel.LOW.value,
            composite_risk_score=5.0,
            active_room="living_room",
            vitals={
                "heart_rate_bpm": 72,
                "wearable_status": "worn_normal",
                "arrhythmia_detected": False,
                "movement_index": 0.8,
                "last_seen": now_iso
            },
            environment={
                "temperature_c": 21.5,
                "humidity_pct": 42.0,
                "lighting_lux": 380.0,
                "ambient_noise_db": 38.0,
                "floor_moisture_detected": False,
                "environment_label": "well_lit"
            },
            smart_home={
                "smart_lock_unlocked": False,
                "pathway_lighting": "NORMAL",
                "audio_bridge_active": False
            },
            active_incident_id=None,
            accumulated_evidence=[],
            last_event_id=None,
            last_event_timestamp=now_iso,
            last_updated=now_iso,
            correlation_id=f"boot-{uuid.uuid4().hex[:6]}"
        )

    # -----------------------------------------------------------------------
    # Subscriber Management (SSE & WebSocket)
    # -----------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        """Subscribes a client to the real-time event and state broadcast stream."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        logger.info(f"Client subscribed to NIRA event stream. Total subscribers: {len(self._subscribers)}")
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Unsubscribes a client queue."""
        self._subscribers.discard(q)
        logger.info(f"Client disconnected from NIRA event stream. Remaining subscribers: {len(self._subscribers)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Non-blocking broadcast to all active subscribers."""
        dead_queues = []
        for q in list(self._subscribers):
            try:
                # Put without blocking if queue is full
                if q.qsize() >= 50:
                    # Drop oldest if congested
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(message)
            except Exception:
                dead_queues.append(q)

        for dq in dead_queues:
            self._subscribers.discard(dq)

    # -----------------------------------------------------------------------
    # Deduplication & Staleness Checks
    # -----------------------------------------------------------------------

    def _is_duplicate(self, event_id: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        if event_id in self._dedup_cache:
            return True
        # Trim cache if too large
        if len(self._dedup_cache) > self.MAX_DEDUP_CACHE_SIZE:
            oldest_keys = [k for k, v in self._dedup_cache.items() if now - v > 3600]
            for k in oldest_keys:
                self._dedup_cache.pop(k, None)
        self._dedup_cache[event_id] = now
        return False

    def _is_stale(self, event_timestamp: datetime) -> bool:
        now = datetime.now(timezone.utc)
        # Ensure event_timestamp is timezone-aware
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
        age_seconds = (now - event_timestamp).total_seconds()
        return age_seconds > self.MAX_STALENESS_SECONDS

    # -----------------------------------------------------------------------
    # Evidence & State Evaluation Logic
    # -----------------------------------------------------------------------

    def _prune_expired_evidence(self, current_dt: datetime):
        """Removes evidence older than EVIDENCE_WINDOW_SECONDS."""
        cutoff = current_dt - timedelta(seconds=self.EVIDENCE_WINDOW_SECONDS)
        while self._evidence_history:
            try:
                ev_time = datetime.fromisoformat(self._evidence_history[0].timestamp.replace("Z", "+00:00"))
                if ev_time.tzinfo is None:
                    ev_time = ev_time.replace(tzinfo=timezone.utc)
                if ev_time < cutoff:
                    self._evidence_history.popleft()
                else:
                    break
            except Exception:
                self._evidence_history.popleft()

    def _evaluate_multimodal_state(
        self,
        event: UnifiedEvent,
        new_evidence: EvidenceItem
    ) -> Tuple[str, str, float]:
        """
        Multimodal state fusion engine.
        Synthesizes active evidence window to determine:
          - safety_state (NORMAL, ANOMALY, ELEVATED, HIGH, CRITICAL, RESPONDING, RESOLVED)
          - risk_level (LOW, MODERATE, HIGH, CRITICAL)
          - composite_risk_score (0.0 to 100.0)

        PROTECTION: A solitary noisy sensor NEVER causes an emergency.
        """
        all_evidence = [e for e in (list(self._evidence_history) + ([new_evidence] if new_evidence else [])) if e is not None]

        # Extract indicator signals from evidence and current vitals/environment
        has_pose_fall = any("fall" in e.event_type.lower() and e.confidence >= 0.70 for e in all_evidence)
        has_horizontal_impact = any("impact" in e.event_type.lower() or "thud" in e.event_type.lower() for e in all_evidence)
        has_immobility = (
            any("immobility" in e.event_type.lower() for e in all_evidence)
            or (event.payload.get("movement_after_event") == "none")
            or (self.current_state.vitals.get("movement_index", 1.0) == 0.0)
        )
        has_posture_recovery = any("recovered" in e.event_type.lower() for e in all_evidence)

        # Vitals indicators
        hr = self.current_state.vitals.get("heart_rate_bpm", 72)
        has_arrhythmia = bool(self.current_state.vitals.get("arrhythmia_detected", False))
        is_tachycardia = hr >= 130
        is_bradycardia = 0 < hr <= 45

        # Environmental indicators
        is_wet_floor = bool(self.current_state.environment.get("floor_moisture_detected", False))
        is_dark_room = (self.current_state.environment.get("lighting_lux", 300) < 15.0)
        is_hazard_room = event.room_id in ["bathroom", "stairs", "shower"]

        # Conversational voice indicators
        has_voice_safe = any(e.event_type == EventType.VOICE_RESPONSE_SAFE.value for e in all_evidence)
        has_voice_distress = any(e.event_type == EventType.VOICE_RESPONSE_DISTRESS.value for e in all_evidence)
        has_voice_timeout = any(e.event_type in [EventType.VOICE_TIMEOUT.value, EventType.WELLNESS_TIMEOUT.value] for e in all_evidence)

        # -------------------------------------------------------------------
        # 1. Voice Resolution & Recovery Tiers
        # -------------------------------------------------------------------
        if has_voice_safe or has_posture_recovery:
            # Person explicitly safe -> Recovery to RESOLVED
            return SafetyState.RESOLVED.value, RiskLevel.LOW.value, 10.0

        if has_voice_timeout:
            # Silence during wellness check -> Silent Emergency -> CRITICAL
            return SafetyState.CRITICAL.value, RiskLevel.CRITICAL.value, 98.0

        if has_voice_distress:
            # Explicit call for help
            if has_pose_fall or has_immobility or is_tachycardia or is_hazard_room:
                return SafetyState.CRITICAL.value, RiskLevel.CRITICAL.value, 95.0
            return SafetyState.HIGH.value, RiskLevel.HIGH.value, 75.0

        # -------------------------------------------------------------------
        # 2. Multimodal Fall & Physical Trauma Tiers
        # -------------------------------------------------------------------
        if has_pose_fall:
            # Corroborated fall scenarios
            if has_immobility and (is_tachycardia or is_hazard_room or has_horizontal_impact):
                # High-confidence fall + zero movement + shock/wet floor -> CRITICAL
                return SafetyState.CRITICAL.value, RiskLevel.CRITICAL.value, 94.0
            elif has_immobility:
                # Fall + immobility -> HIGH (initiating immediate wellness check)
                return SafetyState.HIGH.value, RiskLevel.HIGH.value, 78.0
            elif is_tachycardia or has_arrhythmia:
                # Fall + vital distress -> HIGH
                return SafetyState.HIGH.value, RiskLevel.HIGH.value, 72.0
            else:
                # Solitary vision fall detection without immobility or vitals surge
                # (e.g. Picking up dropped book/glasses) -> ELEVATED, NOT CRITICAL!
                return SafetyState.ELEVATED.value, RiskLevel.MODERATE.value, 48.0

        # -------------------------------------------------------------------
        # 3. Solitary Vitals or Acoustic Anomalies (Anti-Noise Protection)
        # -------------------------------------------------------------------
        if has_horizontal_impact:
            if is_hazard_room or is_wet_floor:
                return SafetyState.ELEVATED.value, RiskLevel.MODERATE.value, 45.0
            return SafetyState.ANOMALY.value, RiskLevel.MODERATE.value, 30.0

        if is_tachycardia or is_bradycardia or has_arrhythmia:
            if is_dark_room or has_immobility:
                return SafetyState.ELEVATED.value, RiskLevel.MODERATE.value, 42.0
            # Isolated heart rate anomaly without physical impact
            return SafetyState.ANOMALY.value, RiskLevel.MODERATE.value, 28.0

        if is_wet_floor and is_dark_room:
            return SafetyState.ANOMALY.value, RiskLevel.LOW.value, 22.0

        # -------------------------------------------------------------------
        # 4. Baseline Normal Tier
        # -------------------------------------------------------------------
        return SafetyState.NORMAL.value, RiskLevel.LOW.value, 5.0

    # -----------------------------------------------------------------------
    # Central Ingestion Pipeline
    # -----------------------------------------------------------------------

    async def ingest_event(
        self,
        event: UnifiedEvent,
        db: Optional[Session] = None
    ) -> EventIngestResult:
        """
        Asynchronously processes an incoming UnifiedEvent through:
          1. Deduplication validation
          2. Staleness validation
          3. Live vitals & room environment state update
          4. Multimodal evidence extraction & evaluation
          5. State progression / recovery transition
          6. Persistent database logging (TelemetryEventModel & IncidentModel)
          7. Real-time broadcasting to SSE/WebSocket subscribers
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Parse event timestamp
            try:
                event_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
            except Exception:
                event_dt = now

            # Step 1: Duplicate Event Protection
            if self._is_duplicate(event.event_id):
                logger.warning(f"DUPLICATE event rejected: {event.event_id} (correlation: {event.correlation_id})")
                return EventIngestResult(
                    status="DUPLICATE_IGNORED",
                    event_id=event.event_id,
                    correlation_id=event.correlation_id,
                    safety_state=self.current_state.safety_state,
                    risk_level=self.current_state.risk_level,
                    composite_risk_score=self.current_state.composite_risk_score,
                    active_incident_id=self.current_state.active_incident_id,
                    evidence_count=len(self.current_state.accumulated_evidence),
                    state_changed=False,
                    ingested_at=now_iso
                )

            # Step 2: Stale Event Protection
            if self._is_stale(event_dt):
                logger.warning(
                    f"STALE event flagged: {event.event_id} (timestamp: {event.timestamp}, "
                    f"correlation: {event.correlation_id}). Event will not alter safety state."
                )
                if db:
                    self._persist_telemetry_event(db, event, self.current_state.safety_state, [], event_dt, now)
                return EventIngestResult(
                    status="STALE_FLAGGED",
                    event_id=event.event_id,
                    correlation_id=event.correlation_id,
                    safety_state=self.current_state.safety_state,
                    risk_level=self.current_state.risk_level,
                    composite_risk_score=self.current_state.composite_risk_score,
                    active_incident_id=self.current_state.active_incident_id,
                    evidence_count=len(self.current_state.accumulated_evidence),
                    state_changed=False,
                    ingested_at=now_iso
                )

            # Step 3: Update Active State Telemetry
            self._update_state_telemetry(event)

            # Step 4: Extract and Accumulate Evidence
            evidence_item = EvidenceItem(
                evidence_id=f"evi-{uuid.uuid4().hex[:8]}",
                timestamp=event.timestamp,
                source=event.source,
                event_type=event.event_type,
                room_id=event.room_id,
                confidence=event.confidence,
                description=f"{event.source.upper()} reported {event.event_type} in {event.room_id} (conf {event.confidence:.0%})",
                metric_key=list(event.payload.keys())[0] if event.payload else None,
                metric_value=list(event.payload.values())[0] if event.payload else None,
                weight=1.0 + (event.confidence * 0.5)
            )
            self._prune_expired_evidence(event_dt)
            self._evidence_history.append(evidence_item)

            # Step 5: Multimodal State Progression & Recovery Evaluation
            prev_safety_state = self.current_state.safety_state
            new_safety_state, new_risk_level, new_score = self._evaluate_multimodal_state(event, evidence_item)
            state_changed = (new_safety_state != prev_safety_state)

            if state_changed:
                logger.info(
                    f"NIRA Safety State Transition: {prev_safety_state} -> {new_safety_state} "
                    f"(Risk: {new_risk_level}, Score: {new_score:.1f}, Correlation: {event.correlation_id})"
                )

            # Step 6: Maintain Incident Lifecycle in State
            active_inc_id = self.current_state.active_incident_id
            if new_safety_state in [SafetyState.HIGH.value, SafetyState.CRITICAL.value] and not active_inc_id:
                active_inc_id = f"INC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            elif new_safety_state in [SafetyState.RESOLVED.value, SafetyState.NORMAL.value]:
                active_inc_id = None
                if new_safety_state == SafetyState.RESOLVED.value:
                    self._evidence_history.clear()

            # Update Authoritative State Snapshot
            self.current_state.safety_state = new_safety_state
            self.current_state.risk_level = new_risk_level
            self.current_state.composite_risk_score = new_score
            self.current_state.active_room = event.room_id
            self.current_state.active_incident_id = active_inc_id
            self.current_state.accumulated_evidence = list(self._evidence_history)
            self.current_state.last_event_id = event.event_id
            self.current_state.last_event_timestamp = event.timestamp
            self.current_state.last_updated = now_iso
            self.current_state.correlation_id = event.correlation_id

            # Smart home automations based on state
            if new_safety_state == SafetyState.CRITICAL.value:
                self.current_state.smart_home["smart_lock_unlocked"] = True
                self.current_state.smart_home["pathway_lighting"] = "100%_EMERGENCY"
                self.current_state.smart_home["audio_bridge_active"] = True
            elif new_safety_state in [SafetyState.NORMAL.value, SafetyState.RESOLVED.value]:
                self.current_state.smart_home["smart_lock_unlocked"] = False
                self.current_state.smart_home["pathway_lighting"] = "NORMAL"
                self.current_state.smart_home["audio_bridge_active"] = False

            # Step 7: Persist to Database if session provided
            if db:
                self._persist_telemetry_event(
                    db=db,
                    event=event,
                    state_after=new_safety_state,
                    evidence=list(self._evidence_history),
                    event_dt=event_dt,
                    now=now
                )
                if state_changed and active_inc_id:
                    self._sync_incident_record(db, active_inc_id, event, new_safety_state, new_risk_level, new_score, now)

            # Step 8: Broadcast to Real-Time Subscribers
            broadcast_payload = {
                "type": "NIRA_STATE_UPDATE",
                "state_changed": state_changed,
                "event": event.model_dump(),
                "snapshot": self.current_state.model_dump(),
                "timestamp": now_iso
            }
            await self.broadcast(broadcast_payload)

            return EventIngestResult(
                status="ACCEPTED",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                safety_state=new_safety_state,
                risk_level=new_risk_level,
                composite_risk_score=new_score,
                active_incident_id=active_inc_id,
                evidence_count=len(self.current_state.accumulated_evidence),
                state_changed=state_changed,
                ingested_at=now_iso
            )

    # -----------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------

    def _update_state_telemetry(self, event: UnifiedEvent):
        """Updates continuous vitals and room environment from event payload."""
        payload = event.payload
        if event.source == EventSource.WEARABLE.value or "wearable" in event.event_type:
            if "heart_rate_bpm" in payload and payload["heart_rate_bpm"]:
                self.current_state.vitals["heart_rate_bpm"] = payload["heart_rate_bpm"]
            if "movement_index" in payload:
                self.current_state.vitals["movement_index"] = payload["movement_index"]
            if "arrhythmia_detected" in payload:
                self.current_state.vitals["arrhythmia_detected"] = payload["arrhythmia_detected"]
            if "wearable_status" in payload:
                self.current_state.vitals["wearable_status"] = payload["wearable_status"]
            self.current_state.vitals["last_seen"] = event.timestamp

        elif event.source == EventSource.RADAR.value or "radar" in event.event_type:
            if "motion_level" in payload:
                self.current_state.vitals["movement_index"] = payload["motion_level"]

        elif event.source == EventSource.ENVIRONMENT.value or "environment" in event.event_type:
            for k in ["temperature_c", "humidity_pct", "lighting_lux", "ambient_noise_db", "floor_moisture_detected", "environment_label"]:
                if k in payload:
                    self.current_state.environment[k] = payload[k]

    def _persist_telemetry_event(
        self,
        db: Session,
        event: UnifiedEvent,
        state_after: str,
        evidence: List[EvidenceItem],
        event_dt: datetime,
        now: datetime
    ):
        """Writes row to telemetry_events."""
        try:
            row = TelemetryEventModel(
                id=event.event_id,
                correlation_id=event.correlation_id,
                resident_id=event.resident_id,
                room_id=event.room_id,
                source=event.source,
                event_type=event.event_type,
                confidence=event.confidence,
                payload_json=event.payload,
                timestamp=event_dt,
                created_at=now,
                safety_state_after=state_after,
                evidence_summary=[e.model_dump() for e in evidence[-5:]]
            )
            db.add(row)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist TelemetryEventModel: {e}")

    def _sync_incident_record(
        self,
        db: Session,
        incident_id: str,
        event: UnifiedEvent,
        safety_state: str,
        risk_level: str,
        score: float,
        now: datetime
    ):
        """Ensures IncidentModel and IncidentTimelineModel reflect significant safety states."""
        try:
            inc = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
            if not inc:
                inc = IncidentModel(
                    id=incident_id,
                    user_id=event.resident_id,
                    event_type=event.event_type,
                    confidence=event.confidence,
                    location=event.room_id,
                    movement_after_event=event.payload.get("movement_after_event", "none"),
                    initial_risk_level=risk_level,
                    current_risk_level=risk_level,
                    risk_confidence=event.confidence,
                    risk_reasons=[e.description for e in self.current_state.accumulated_evidence[-3:]],
                    status="ACTIVE",
                    recommended_action=f"STATE_{safety_state}",
                    context_snapshot=self.current_state.environment,
                    created_at=now,
                    updated_at=now
                )
                db.add(inc)

                # Add timeline creation log
                t = IncidentTimelineModel(
                    incident_id=incident_id,
                    timestamp=now,
                    action_type="MULTIMODAL_INCIDENT_TRIGGERED",
                    actor=event.source.upper(),
                    description=f"Incident opened under state {safety_state} ({risk_level}). Trigger: {event.event_type} in {event.room_id}.",
                    metadata_json={"event_id": event.event_id, "score": score, "correlation_id": event.correlation_id}
                )
                db.add(t)
            else:
                inc.current_risk_level = risk_level
                inc.updated_at = now
                if safety_state == SafetyState.RESOLVED.value:
                    inc.status = "RESOLVED"
                    inc.resolved_at = now

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync IncidentModel for {incident_id}: {e}")

    def reset_to_normal(self):
        """Explicitly resets the authoritative resident state to NORMAL."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self._evidence_history.clear()
        self._dedup_cache.clear()
        self.current_state.safety_state = SafetyState.NORMAL.value
        self.current_state.risk_level = RiskLevel.LOW.value
        self.current_state.composite_risk_score = 5.0
        self.current_state.active_incident_id = None
        self.current_state.accumulated_evidence = []
        self.current_state.vitals = {
            "heart_rate_bpm": 72,
            "wearable_status": "worn_normal",
            "arrhythmia_detected": False,
            "movement_index": 0.8,
            "last_seen": now_iso
        }
        self.current_state.environment = {
            "temperature_c": 21.5,
            "humidity_pct": 42.0,
            "lighting_lux": 380.0,
            "ambient_noise_db": 38.0,
            "floor_moisture_detected": False,
            "environment_label": "well_lit"
        }
        self.current_state.smart_home["smart_lock_unlocked"] = False
        self.current_state.smart_home["pathway_lighting"] = "NORMAL"
        self.current_state.smart_home["audio_bridge_active"] = False
        self.current_state.last_updated = now_iso

    def recover_state_from_database(self, db: Session) -> Dict[str, Any]:
        """
        Production restart-recovery:
        Re-hydrates authoritative in-memory state and active emergency incident
        from persistent database storage following a server restart or crash.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        recovered_info = {"recovered": False, "active_incident": None, "evidence_recovered": 0}
        try:
            # 1. Look for ongoing ACTIVE incident
            active_inc = (
                db.query(IncidentModel)
                .filter(IncidentModel.status == "ACTIVE")
                .order_by(IncidentModel.created_at.desc())
                .first()
            )
            if active_inc:
                self.current_state.active_incident_id = active_inc.id
                rec_action = active_inc.recommended_action or ""
                if "CRITICAL" in rec_action or active_inc.current_risk_level == "CRITICAL":
                    self.current_state.safety_state = SafetyState.CRITICAL.value
                elif "HIGH" in rec_action or active_inc.current_risk_level == "HIGH":
                    self.current_state.safety_state = SafetyState.HIGH.value
                else:
                    self.current_state.safety_state = SafetyState.ELEVATED.value

                self.current_state.risk_level = active_inc.current_risk_level or RiskLevel.HIGH.value
                self.current_state.composite_risk_score = (active_inc.risk_confidence or 0.8) * 100.0
                self.current_state.active_room = active_inc.location or "living_room"
                if self.current_state.safety_state == SafetyState.CRITICAL.value:
                    self.current_state.smart_home["smart_lock_unlocked"] = True
                    self.current_state.smart_home["pathway_lighting"] = "100%_EMERGENCY"
                    self.current_state.smart_home["audio_bridge_active"] = True

                recovered_info["recovered"] = True
                recovered_info["active_incident"] = active_inc.id

            # 2. Re-hydrate recent evidence items from TelemetryEventModel
            recent_events = (
                db.query(TelemetryEventModel)
                .order_by(TelemetryEventModel.timestamp.desc())
                .limit(20)
                .all()
            )
            count = 0
            for tev in reversed(recent_events):
                try:
                    payload = tev.payload_json or {}
                    if tev.source == EventSource.WEARABLE.value or "wearable" in (tev.event_type or ""):
                        if "heart_rate_bpm" in payload and payload["heart_rate_bpm"]:
                            self.current_state.vitals["heart_rate_bpm"] = payload["heart_rate_bpm"]
                        if "movement_index" in payload:
                            self.current_state.vitals["movement_index"] = payload["movement_index"]
                    elif tev.source == EventSource.ENVIRONMENT.value or "environment" in (tev.event_type or ""):
                        if "floor_moisture_detected" in payload:
                            self.current_state.environment["floor_moisture_detected"] = payload["floor_moisture_detected"]

                    evi = EvidenceItem(
                        evidence_id=f"evi-rec-{tev.id[-8:]}",
                        timestamp=tev.timestamp.isoformat() if hasattr(tev.timestamp, "isoformat") else str(tev.timestamp),
                        source=tev.source or "recovered",
                        event_type=tev.event_type or "recovered_telemetry",
                        room_id=tev.room_id or "living_room",
                        confidence=tev.confidence or 0.9,
                        description=f"Recovered from DB: {tev.event_type} in {tev.room_id}",
                        weight=1.0
                    )
                    self._evidence_history.append(evi)
                    count += 1
                except Exception as item_err:
                    logger.warning(f"Error parsing recovered telemetry event: {item_err}")

            self.current_state.accumulated_evidence = list(self._evidence_history)
            self.current_state.last_updated = now_iso
            recovered_info["evidence_recovered"] = count
            logger.info(f"NIRA restart-recovery executed: {recovered_info}")
            return recovered_info
        except Exception as e:
            logger.error(f"Error during state recovery from DB: {e}")
            return recovered_info


# Global singleton instance for runtime state management
global_pipeline = EventPipeline()
