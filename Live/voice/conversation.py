"""
Conversational State and Multi-turn Dialogue Manager for NIRA.
Amazon Developer Hackathon 2026.

Coordinates two-way verbal checks with seniors:
  - Initial Question ("Eleanor, are you okay?")
  - Clarification / Second Turn upon UNCERTAIN status
  - Cadence pacing to avoid cutting off elderly speakers
"""

import time
import logging
from typing import Optional, List, Dict, Any, Callable
from .models import VoiceInteractionResult, VoiceInteractionStatus, VoiceAction
from .service import VoiceService

logger = logging.getLogger("NIRA.Conversation")


class WellnessConversationManager:
    """
    Manages conversational dialog turns with the elderly resident.
    Includes clarification turn support when first response is ambiguous or unintelligible.
    """

    def __init__(self, voice_service: Optional[VoiceService] = None):
        self.voice_service = voice_service or VoiceService()

    def conduct_wellness_check(
        self,
        elderly_id: str = "PT-84920",
        resident_name: str = "Eleanor",
        initial_question: Optional[str] = None,
        max_turns: int = 2,
        on_turn_start: Optional[Callable[[str], None]] = None
    ) -> List[VoiceInteractionResult]:
        """
        Executes a patient check-in dialogue.
        If first turn yields UNCERTAIN, performs a targeted follow-up prompt.
        """
        results: List[VoiceInteractionResult] = []

        q1 = initial_question or f"{resident_name}, are you okay?"
        if on_turn_start:
            on_turn_start(q1)

        r1 = self.voice_service.run_check_in(
            elderly_id=elderly_id,
            question=q1
        )
        results.append(r1)

        # If definitive outcome reached (SAFE, RISK, or EMERGENCY), return immediately
        if r1.status in [VoiceInteractionStatus.SAFE, VoiceInteractionStatus.RISK, VoiceInteractionStatus.EMERGENCY]:
            return results

        # If UNCERTAIN and turns remaining, ask gentle follow-up question
        if r1.status == VoiceInteractionStatus.UNCERTAIN and max_turns > 1:
            time.sleep(0.5)
            q2 = f"{resident_name}, I didn't quite catch that. Are you feeling hurt or do you need help?"
            if on_turn_start:
                on_turn_start(q2)

            r2 = self.voice_service.run_check_in(
                elderly_id=elderly_id,
                question=q2,
                silence_timeout_sec=2.5
            )
            results.append(r2)

        return results
