"""
Clinical Response Understanding & Safety Classification Engine for NIRA.
Amazon Developer Hackathon 2026.

Analyzes natural spoken resident responses to questions ("Are you okay?").
Key Architectural Guarantees:
  1. Priority Hierarchy: EMERGENCY > RISK > UNCERTAIN > SAFE
  2. Strict Negation Handling: "I am NOT okay" / "I'm not feeling well" NEVER become SAFE
  3. Mixed Response Resolution: "Yes, I'm okay, but I fell down and can't get up" -> EMERGENCY
  4. Safety Fallback: Any parsing error, empty transcript, or ambiguity defaults to UNCERTAIN (never silently SAFE)
"""

import re
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from .models import (
    VoiceInteractionStatus,
    VoiceUrgencyLevel,
    VoiceAction,
    VoiceAnalysisResult
)

logger = logging.getLogger("NIRA.ResponseAnalyzer")


# ---------------------------------------------------------------------------
# Lexicon and Pattern Definitions
# ---------------------------------------------------------------------------

# Emergency patterns (Highest Priority: IMMEDIATE CAD / DISPATCH)
EMERGENCY_PATTERNS = [
    r"\bhelp\b(?!\s*with\s*(the\s*)?(dishes|laundry|chores))",
    r"\bhelp\s+me\b",
    r"\bplease\s+help\b",
    r"\bneed\s+(some\s+|urgent\s+|immediate\s+)?help\b",
    r"\bi\s+need\s+help\b",
    r"\bcan't\s+get\s+up\b",
    r"\bcannot\s+get\s+up\b",
    r"\bunable\s+to\s+get\s+up\b",
    r"\bcan't\s+stand\s*(up)?\b",
    r"\bcannot\s+stand\s*(up)?\b",
    r"\bcan't\s+move\b",
    r"\bcannot\s+move\b",
    r"\bunable\s+to\s+move\b",
    r"\bcan't\s+breathe\b",
    r"\bcannot\s+breathe\b",
    r"\btrouble\s+breathing\b",
    r"\bhard\s+to\s+breathe\b",
    r"\bsuffocating\b",
    r"\bchoking\b",
    r"\bcall\s+(someone|911|an\s+ambulance|help|doctor|police|emergency|my\s+(son|daughter|family|caretaker|caregiver))\b",
    r"\bbadly\s+hurt\b",
    r"\bseverely\s+hurt\b",
    r"\bbroken\s+(hip|bone|arm|leg|rib)\b",
    r"\bbleeding\b",
    r"\bthere('?s)?\s+blood\b",
    r"\bheart\s+attack\b",
    r"\bstroke\b",
    r"\bpassed\s+out\b",
    r"\blost\s+consciousness\b",
    r"\bemergency\b",
    r"\bfell\s+and\s+(i\s+)?(can'?t|cannot)\b",
    r"\bhead\s+injury\b",
    r"\bunresponsive\b"
]

# Risk / Distress patterns (Urgency: HIGH or MEDIUM -> Incident / Caregiver)
RISK_PATTERNS = [
    r"\bdizzy\b",
    r"\blightheaded\b",
    r"\bweak\b",
    r"\bfeel(ing)?\s+faint\b",
    r"\bpain\b",
    r"\bhaving\s+pain\b",
    r"\bin\s+pain\b",
    r"\bhurts\b",
    r"\baching\b",
    r"\bfell\s+down\b",
    r"\bi\s+fell\b",
    r"\bslipped\b",
    r"\btripped\b",
    r"\btrouble\s+walking\b",
    r"\bunsteady\b",
    r"\bwobbly\b",
    r"\bshaky\b",
    r"\bchest\s+(pain|tightness|pressure|feels\s+(a\s+bit\s+|very\s+)?tight|tight)\b",
    r"\bnauseous\b",
    r"\bsick\b",
    r"\bvomi?ting\b",
    r"\bblurred\s+vision\b",
    r"\bheadache\b",
    r"\bmigraine\b",
    r"\blost\s+my\s+balance\b",
    r"\bshivering\b",
    r"\bcan'?t\s+reach\b",
    r"\bfrightened\b",
    r"\bscared\b"
]

# Explicit Negation + Positive words (CRITICAL: "not okay" -> RISK / DISTRESS)
NEGATED_POSITIVE_PATTERNS = [
    r"\bnot\s+okay\b",
    r"\bnot\s+doing\s+(okay|good|well|fine)\b",
    r"\bnot\s+fine\b",
    r"\bnot\s+good\b",
    r"\bnot\s+doing\s+well\b",
    r"\bnot\s+feeling\s+(very\s+|too\s+|so\s+|really\s+|quite\s+)?(good|well|fine|great|okay|alright|right)\b",
    r"\bdon'?t\s+feel\s+(very\s+|too\s+|so\s+|really\s+|quite\s+)?(good|well|fine|great|okay|alright|right)\b",
    r"\bnot\s+right\b",
    r"\bsomething\s+is\s+wrong\b",
    r"\bsomething('?s)?\s+wrong\b",
    r"\bdefinitely\s+not\s+(okay|fine|good|well)\b",
    r"\breally\s+not\s+(okay|fine|good|well)\b",
    r"\bcertainly\s+not\s+(okay|fine|good|well)\b",
    r"\bnot\s+all\s+right\b",
    r"\bnot\s+alright\b",
    r"\bain'?t\s+(okay|good|well|fine|doing\s+well)\b",
    r"\bnever\s+felt\s+worse\b",
    r"\bno[,\s]+(i'?m\s+|i\s+am\s+)?not\s+okay\b",
    r"\bno[,\s]+(i'?m\s+|i\s+am\s+)?not\s+fine\b",
    r"\bno[,\s]+(i'?m\s+|i\s+am\s+)?not\s+good\b",
    r"\bno[,\s]+(i'?m\s+|i\s+am\s+)?not\s+alright\b",
    r"\bno[,\s]+i\s+am\s+not\b"
]

# Safe affirmations (Lowest Priority: ONLY valid when NO risk/emergency/negation exists)
SAFE_PATTERNS = [
    r"\bi'?m\s+okay\b",
    r"\bi\s+am\s+okay\b",
    r"\byes[,\s]+i'?m\s+okay\b",
    r"\byeah[,\s]+i'?m\s+okay\b",
    r"\bi'?m\s+fine\b",
    r"\bi\s+am\s+fine\b",
    r"\byes[,\s]+i'?m\s+fine\b",
    r"\bno[,\s]+i'?m\s+(fine|okay|good|alright)\b",
    r"\b(i'?m|i\s+am)\s+doing\s+(good|fine|well|okay|alright)\b",
    r"\beverything\s+is\s+(alright|fine|okay|good)\b",
    r"\bi\s+feel\s+(fine|good|great|okay|alright)\b",
    r"\ball\s+good\b",
    r"\bno\s+problem(\s+at\s+all)?\b",
    r"\bno\s+worries\b",
    r"\bfalse\s+alarm\b",
    r"\bjust\s+dropped\s+my\b",
    r"\bi'?m\s+alright\b",
    r"\bi\s+am\s+alright\b",
    r"\bgot\s+back\s+up\b",
    r"\bi\s+don'?t\s+need\s+(any\s+)?help\b",
    r"\bno\s+help\s+needed\b"
]

# Ambiguity / Uncertainty patterns
UNCERTAIN_PATTERNS = [
    r"\bi\s+don'?t\s+know\b",
    r"\bnot\s+sure\b",
    r"\bmaybe\b",
    r"\bperhaps\b",
    r"\bkind\s+of\b",
    r"\bsorta\b",
    r"\bi\s+guess\b",
    r"\bhard\s+to\s+say\b",
    r"\bwhat\s+happened\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhere\s+am\s+i\b",
    r"\bconfused\b"
]


class ResponseAnalyzer:
    """
    Robust natural language understanding for conversational senior wellness checks.
    Combines deterministic clinical pattern recognition with optional LLM reasoning.
    """

    def __init__(self, use_llm: bool = False, openai_api_key: Optional[str] = None):
        self.use_llm = use_llm
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    @classmethod
    def analyze_deterministic(cls, transcript: str) -> VoiceAnalysisResult:
        """
        Pure deterministic semantic evaluation implementing all clinical safety rules:
          1. Check for empty / silence / unintelligible -> UNCERTAIN
          2. Check for explicit Negated Positives ("not okay", "not feeling well") -> RISK / DISTRESS
          3. Check for Emergency indicators -> EMERGENCY (Overrules all positive words)
          4. Check for Risk indicators -> RISK
          5. Check for Uncertain / Ambiguous indicators -> UNCERTAIN
          6. Check for Safe affirmations -> SAFE
          7. Unmatched or unclear utterances -> UNCERTAIN (Safety fallback)
        """
        raw_text = (transcript or "").strip()
        cleaned = raw_text.lower()

        # Step 1: Empty or pure whitespace or punctuation
        if not cleaned or len(re.sub(r"[^\w\s]", "", cleaned)) == 0:
            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.UNCERTAIN,
                urgency=VoiceUrgencyLevel.MEDIUM,
                reason="No intelligible speech detected or response was empty.",
                action=VoiceAction.REPEAT_CHECK_IN,
                is_negated=False,
                is_mixed=False
            )

        # Detect signals across categories
        emergency_matches: List[str] = []
        for pat in EMERGENCY_PATTERNS:
            found = re.findall(pat, cleaned)
            if found:
                emergency_matches.append(pat)

        negated_positive_matches: List[str] = []
        for pat in NEGATED_POSITIVE_PATTERNS:
            found = re.findall(pat, cleaned)
            if found:
                negated_positive_matches.append(pat)

        risk_matches: List[str] = []
        for pat in RISK_PATTERNS:
            found = re.findall(pat, cleaned)
            if found:
                risk_matches.append(pat)

        safe_matches: List[str] = []
        for pat in SAFE_PATTERNS:
            found = re.findall(pat, cleaned)
            if found:
                safe_matches.append(pat)

        uncertain_matches: List[str] = []
        for pat in UNCERTAIN_PATTERNS:
            found = re.findall(pat, cleaned)
            if found:
                uncertain_matches.append(pat)

        # Check for clause transitions ("but", "however", "except", "although")
        has_contrast = bool(re.search(r"\b(but|however|except|although|though)\b", cleaned))

        # Check general negation keywords, excluding safe idioms
        cleaned_neg = cleaned
        cleaned_neg = re.sub(r"\bno\s+problem(\s+at\s+all)?\b", "", cleaned_neg)
        cleaned_neg = re.sub(r"\bno\s+worries\b", "", cleaned_neg)
        cleaned_neg = re.sub(r"\bno[,\s]+(i'?m|i\s+am)\s+(fine|okay|good|alright)\b", "", cleaned_neg)
        cleaned_neg = re.sub(r"\b(don'?t|do\s+not)\s+need\s+(any\s+)?help\b", "", cleaned_neg)

        is_negated = bool(re.search(r"\b(not|n't|no|never|cannot|can't|unable)\b", cleaned_neg))
        is_mixed = has_contrast or (bool(safe_matches) and (bool(emergency_matches) or bool(risk_matches) or bool(negated_positive_matches)))

        # -----------------------------------------------------------------------
        # RULE 1: EMERGENCY PRIORITY OVERRIDE
        # Any genuine emergency indicator immediately escalates to EMERGENCY
        # (e.g., "Yes, I'm okay, but I fell down and I can't get up" -> EMERGENCY)
        # -----------------------------------------------------------------------
        if emergency_matches:
            reason = "Critical emergency signal detected in response"
            if "can't get up" in cleaned or "cannot get up" in cleaned:
                reason = "Resident reported falling and being unable to get back up."
            elif "can't breathe" in cleaned or "cannot breathe" in cleaned:
                reason = "Resident reported acute respiratory distress."
            elif "help" in cleaned:
                reason = "Resident explicitly called for emergency assistance."
            elif "call" in cleaned:
                reason = "Resident requested emergency or 911 dispatch."
            elif "badly hurt" in cleaned or "severely hurt" in cleaned:
                reason = "Resident reported severe bodily injury."

            if is_mixed:
                reason += " (Emergency condition overrode positive preface)"

            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.EMERGENCY,
                urgency=VoiceUrgencyLevel.CRITICAL,
                reason=reason,
                action=VoiceAction.ESCALATE_EMERGENCY_CAD,
                is_negated=is_negated,
                is_mixed=is_mixed,
                emergency_signals=emergency_matches,
                risk_signals=risk_matches,
                safe_signals=safe_matches
            )

        # -----------------------------------------------------------------------
        # RULE 2: CRITICAL NEGATION OF POSITIVES
        # "I am NOT okay", "I'm not feeling well", "No, I am not fine"
        # MUST NEVER BECOME SAFE!
        # -----------------------------------------------------------------------
        if negated_positive_matches:
            reason = "Resident explicitly denied being okay or reported not feeling well."
            if "not feeling well" in cleaned or "don't feel well" in cleaned:
                reason = "Resident reported not feeling well."
            elif "not okay" in cleaned:
                reason = "Resident stated they are not okay."
            elif "not fine" in cleaned:
                reason = "Resident stated they are not fine."

            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.RISK,
                urgency=VoiceUrgencyLevel.HIGH,
                reason=reason,
                action=VoiceAction.CREATE_INCIDENT,
                is_negated=True,
                is_mixed=is_mixed,
                risk_signals=negated_positive_matches,
                safe_signals=[]
            )

        # -----------------------------------------------------------------------
        # RULE 3: RISK INDICATORS
        # Dizziness, pain, weakness, slipping, unsteady gait
        # -----------------------------------------------------------------------
        if risk_matches:
            signals_desc = []
            if "dizzy" in cleaned or "lightheaded" in cleaned:
                signals_desc.append("dizziness (feeling dizzy)")
            if "weak" in cleaned:
                signals_desc.append("physical weakness")
            if "pain" in cleaned or "hurts" in cleaned:
                signals_desc.append("pain")
            if "fell" in cleaned or "slipped" in cleaned:
                signals_desc.append("fall/slip incident")
            if "trouble walking" in cleaned or "unsteady" in cleaned:
                signals_desc.append("unsteady mobility")

            desc = ", ".join(signals_desc) if signals_desc else "distress"
            reason = f"Resident reported experiencing {desc}."

            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.RISK,
                urgency=VoiceUrgencyLevel.HIGH,
                reason=reason,
                action=VoiceAction.CREATE_INCIDENT,
                is_negated=is_negated,
                is_mixed=is_mixed,
                risk_signals=risk_matches,
                safe_signals=[]
            )

        # -----------------------------------------------------------------------
        # RULE 4: UNCERTAINTY / CONFUSION
        # "I don't know", "Maybe", "I'm not sure", confusion
        # -----------------------------------------------------------------------
        if uncertain_matches:
            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.UNCERTAIN,
                urgency=VoiceUrgencyLevel.MEDIUM,
                reason="Resident gave an uncertain or ambiguous response ('I don't know' / 'not sure').",
                action=VoiceAction.REPEAT_CHECK_IN,
                is_negated=is_negated,
                is_mixed=is_mixed,
                risk_signals=[]
            )

        # -----------------------------------------------------------------------
        # RULE 5: SAFE CONFIRMATION
        # Must have safe matches AND no unresolved negation AND no contrast
        # -----------------------------------------------------------------------
        if safe_matches and not is_negated and not has_contrast:
            reason = "Resident verbally confirmed they are okay and require no assistance."
            if "fine" in cleaned:
                reason = "Resident confirmed they feel fine."
            elif "doing good" in cleaned or "doing well" in cleaned:
                reason = "Resident confirmed they are doing well."
            elif "everything is alright" in cleaned:
                reason = "Resident confirmed everything is alright."

            return VoiceAnalysisResult(
                status=VoiceInteractionStatus.SAFE,
                urgency=VoiceUrgencyLevel.LOW,
                reason=reason,
                action=VoiceAction.LOG_ONLY,
                is_negated=False,
                is_mixed=False,
                safe_signals=safe_matches
            )

        # -----------------------------------------------------------------------
        # RULE 6: SAFETY FALLBACK
        # Any ambiguous phrase ("hmm", "hello", "what", random words) -> UNCERTAIN
        # Never silently become SAFE!
        # -----------------------------------------------------------------------
        return VoiceAnalysisResult(
            status=VoiceInteractionStatus.UNCERTAIN,
            urgency=VoiceUrgencyLevel.MEDIUM,
            reason=f"Ambiguous or unrecognized conversational response: '{raw_text}'. Defaulting to UNCERTAIN safety state.",
            action=VoiceAction.REPEAT_CHECK_IN,
            is_negated=is_negated,
            is_mixed=is_mixed
        )

    def analyze(self, transcript: str) -> VoiceAnalysisResult:
        """
        Master analysis method.
        Executes deterministic rules first as ground truth or invokes LLM if enabled,
        with strict validation and guaranteed deterministic fallback.
        """
        deterministic_result = self.analyze_deterministic(transcript)

        # If LLM is not enabled or no API key, return deterministic result
        if not self.use_llm or not self.openai_api_key:
            return deterministic_result

        # Optional LLM semantic classification with validation
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)

            system_prompt = (
                "You are an ambient clinical safety evaluator for the NIRA elderly care system. "
                "Analyze the resident's response to the wellness check: 'Are you okay?'\n"
                "Return a strict JSON object with fields:\n"
                "- status: 'SAFE', 'UNCERTAIN', 'RISK', or 'EMERGENCY'\n"
                "- urgency: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'\n"
                "- reason: brief clinical explanation\n"
                "- action: 'LOG_ONLY', 'REPEAT_CHECK_IN', 'CREATE_INCIDENT', 'ESCALATE_EMERGENCY_CAD'\n\n"
                "CRITICAL RULES:\n"
                "1. If resident says 'I am NOT okay' or 'not feeling well', it MUST be RISK or EMERGENCY, NEVER SAFE.\n"
                "2. If resident says 'Help me' or 'can't get up' or 'can't breathe', it MUST be EMERGENCY.\n"
                "3. In mixed responses like 'I'm okay, but I fell and can't get up', EMERGENCY overrides.\n"
                "4. If ambiguous or unclear, return UNCERTAIN. NEVER silently default to SAFE."
            )

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript: \"{transcript}\""}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )

            raw_json = json.loads(resp.choices[0].message.content)

            status = VoiceInteractionStatus(raw_json.get("status", "UNCERTAIN").upper())
            urgency = VoiceUrgencyLevel(raw_json.get("urgency", "MEDIUM").upper())
            action = VoiceAction(raw_json.get("action", "REPEAT_CHECK_IN").upper())
            reason = raw_json.get("reason", "Evaluated by clinical response model.")

            # Validate safety constraint: If deterministic found emergency or negated positive, reject LLM false safe
            if deterministic_result.status == VoiceInteractionStatus.EMERGENCY and status != VoiceInteractionStatus.EMERGENCY:
                logger.warning("LLM downgraded EMERGENCY. Enforcing deterministic EMERGENCY priority.")
                return deterministic_result

            if deterministic_result.is_negated and status == VoiceInteractionStatus.SAFE:
                logger.warning("LLM classified negated distress as SAFE. Enforcing deterministic safety rule.")
                return deterministic_result

            return VoiceAnalysisResult(
                status=status,
                urgency=urgency,
                reason=reason,
                action=action,
                is_negated=deterministic_result.is_negated,
                is_mixed=deterministic_result.is_mixed,
                emergency_signals=deterministic_result.emergency_signals,
                risk_signals=deterministic_result.risk_signals,
                safe_signals=deterministic_result.safe_signals
            )

        except Exception as e:
            logger.warning(f"LLM evaluation failed or timed out: {e}. Falling back to deterministic analysis.")
            return deterministic_result
