"""
Authoritative Emergency State Machine (FSM) for NIRA Live Core.
Amazon Developer Hackathon 2026.

Implements the deterministic 10-state safety lifecycle:
NORMAL → DETECTED → VERIFYING → WELLNESS_CHECK → WAITING_FOR_RESPONSE →
RESPONSIVE → CAREGIVER_ESCALATION → EMERGENCY_ESCALATION → DISPATCH_READY → RESOLVED
"""

import logging
from typing import Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone

from Live.core.models import SafetyState, TimelineEntry

logger = logging.getLogger("NIRA.LiveCore.EmergencyWorkflow")

# Permitted state transitions (Strict Deterministic Graph)
VALID_TRANSITIONS: Dict[SafetyState, Set[SafetyState]] = {
    SafetyState.NORMAL: {
        SafetyState.DETECTED,
        SafetyState.NORMAL  # Idempotent
    },
    SafetyState.DETECTED: {
        SafetyState.VERIFYING,
        SafetyState.WELLNESS_CHECK,
        SafetyState.CAREGIVER_ESCALATION,
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED,
        SafetyState.NORMAL
    },
    SafetyState.VERIFYING: {
        SafetyState.WELLNESS_CHECK,
        SafetyState.CAREGIVER_ESCALATION,
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED,
        SafetyState.NORMAL
    },
    SafetyState.WELLNESS_CHECK: {
        SafetyState.WAITING_FOR_RESPONSE,
        SafetyState.RESPONSIVE,
        SafetyState.CAREGIVER_ESCALATION,
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED
    },
    SafetyState.WAITING_FOR_RESPONSE: {
        SafetyState.RESPONSIVE,
        SafetyState.CAREGIVER_ESCALATION,
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED
    },
    SafetyState.RESPONSIVE: {
        SafetyState.CAREGIVER_ESCALATION,
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED,
        SafetyState.NORMAL
    },
    SafetyState.CAREGIVER_ESCALATION: {
        SafetyState.EMERGENCY_ESCALATION,
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED
    },
    SafetyState.EMERGENCY_ESCALATION: {
        SafetyState.DISPATCH_READY,
        SafetyState.RESOLVED
    },
    SafetyState.DISPATCH_READY: {
        SafetyState.RESOLVED
    },
    SafetyState.RESOLVED: {
        SafetyState.NORMAL,
        SafetyState.DETECTED
    }
}


class EmergencyWorkflowFSM:
    """
    Authoritative Emergency State Machine for NIRA Live.
    Guarantees deterministic, idempotent state transitions with audit logging.
    """

    def __init__(self, initial_state: SafetyState = SafetyState.NORMAL):
        self._current_state: SafetyState = initial_state
        self._state_entered_at: str = datetime.now(timezone.utc).isoformat()
        self._history: list[TimelineEntry] = []

        # Record initial state
        self._history.append(TimelineEntry(
            state=initial_state,
            action="INITIALIZE_WORKFLOW",
            description="Safety workflow initialized in NORMAL state",
            actor="NIRA_WORKFLOW_ENGINE"
        ))

    @property
    def current_state(self) -> SafetyState:
        return self._current_state

    @property
    def state_entered_at(self) -> str:
        return self._state_entered_at

    def can_transition_to(self, target_state: SafetyState) -> bool:
        """Checks if transition from current state to target state is legally permitted."""
        if target_state == self._current_state:
            return True  # Idempotent transition is always allowed
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition(
        self,
        target_state: SafetyState,
        action: str,
        description: str,
        actor: str = "NIRA_WORKFLOW_ENGINE",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, TimelineEntry]:
        """
        Executes a deterministic state transition.
        Returns (success: bool, timeline_entry: TimelineEntry).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        meta = metadata or {}

        # Idempotent no-op check
        if target_state == self._current_state:
            entry = TimelineEntry(
                timestamp=now_iso,
                state=self._current_state,
                action=f"IDEMPOTENT_CONFIRM_{action}",
                description=f"Confirmed active state: {description}",
                actor=actor,
                metadata=meta
            )
            self._history.append(entry)
            return True, entry

        # Validation check
        if not self.can_transition_to(target_state):
            logger.warning(
                f"[EmergencyWorkflow] Invalid transition rejected: {self._current_state.value} -> {target_state.value} ({action})"
            )
            entry = TimelineEntry(
                timestamp=now_iso,
                state=self._current_state,
                action="INVALID_TRANSITION_REJECTED",
                description=f"Blocked invalid transition from {self._current_state.value} to {target_state.value}: {description}",
                actor=actor,
                metadata={"rejected_target": target_state.value, **meta}
            )
            self._history.append(entry)
            return False, entry

        # Valid transition
        prev_state = self._current_state
        self._current_state = target_state
        self._state_entered_at = now_iso

        entry = TimelineEntry(
            timestamp=now_iso,
            state=target_state,
            action=action,
            description=description,
            actor=actor,
            metadata={"previous_state": prev_state.value, **meta}
        )
        self._history.append(entry)
        logger.info(f"[EmergencyWorkflow] Transition: {prev_state.value} -> {target_state.value} [{action}]")
        return True, entry

    def get_history(self) -> list[TimelineEntry]:
        """Returns the full chronological audit history of state transitions."""
        return list(self._history)

    def reset_to_normal(self, reason: str = "Manual system reset"):
        """Resets workflow to NORMAL state."""
        self.transition(
            target_state=SafetyState.NORMAL,
            action="SYSTEM_RESET",
            description=reason,
            actor="NIRA_ADMIN"
        )
