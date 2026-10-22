"""
Unit Tests for NIRA Response Analyzer.
Amazon Developer Hackathon 2026.

Tests:
  - SAFE responses
  - RISK responses
  - EMERGENCY responses
  - UNCERTAIN responses
  - Critical Negation Handling ("not okay" MUST NOT become SAFE)
  - Mixed Sentiment with Emergency Priority Override
  - Safety Fallback Guarantees
"""

import pytest
from Live.voice.models import VoiceInteractionStatus, VoiceUrgencyLevel, VoiceAction
from Live.voice.response_analyzer import ResponseAnalyzer


@pytest.fixture
def analyzer():
    return ResponseAnalyzer(use_llm=False)


# ---------------------------------------------------------------------------
# 1. SAFE Response Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", [
    "I'm okay.",
    "Yes, I'm fine.",
    "I'm doing good.",
    "Everything is alright.",
    "Yeah, I'm okay.",
    "I feel fine.",
    "All good, thank you.",
    "I am fine.",
    "False alarm, I'm okay.",
    "No problem at all, I'm fine."
])
def test_safe_responses(analyzer, phrase):
    res = analyzer.analyze(phrase)
    assert res.status == VoiceInteractionStatus.SAFE, f"Failed for: {phrase} (got {res.status})"
    assert res.urgency == VoiceUrgencyLevel.LOW
    assert res.action == VoiceAction.LOG_ONLY
    assert not res.is_negated


# ---------------------------------------------------------------------------
# 2. RISK Response Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", [
    "I'm feeling dizzy.",
    "I feel weak.",
    "I'm having some pain.",
    "I don't feel very well.",
    "I fell down.",
    "I'm having trouble walking.",
    "I feel lightheaded.",
    "My chest hurts a bit.",
    "I'm very unsteady on my feet."
])
def test_risk_responses(analyzer, phrase):
    res = analyzer.analyze(phrase)
    assert res.status == VoiceInteractionStatus.RISK, f"Failed for: {phrase} (got {res.status})"
    assert res.urgency in [VoiceUrgencyLevel.HIGH, VoiceUrgencyLevel.MEDIUM]
    assert res.action == VoiceAction.CREATE_INCIDENT


# ---------------------------------------------------------------------------
# 3. EMERGENCY Response Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", [
    "Help me.",
    "I fell and can't get up.",
    "I can't breathe.",
    "Call someone.",
    "Please help me.",
    "I am badly hurt.",
    "Call 911 right now.",
    "I cannot move, my hip is broken.",
    "I'm bleeding heavily.",
    "Emergency, please send help!"
])
def test_emergency_responses(analyzer, phrase):
    res = analyzer.analyze(phrase)
    assert res.status == VoiceInteractionStatus.EMERGENCY, f"Failed for: {phrase} (got {res.status})"
    assert res.urgency == VoiceUrgencyLevel.CRITICAL
    assert res.action == VoiceAction.ESCALATE_EMERGENCY_CAD


# ---------------------------------------------------------------------------
# 4. UNCERTAIN Response Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", [
    "I don't know.",
    "Maybe.",
    "I'm not sure.",
    "",
    "   ",
    "uh... what?",
    "who is speaking?",
    "random mumbled words"
])
def test_uncertain_responses(analyzer, phrase):
    res = analyzer.analyze(phrase)
    assert res.status == VoiceInteractionStatus.UNCERTAIN, f"Failed for: {phrase} (got {res.status})"
    assert res.action == VoiceAction.REPEAT_CHECK_IN


# ---------------------------------------------------------------------------
# 5. CRITICAL NEGATION Tests (MUST NOT BECOME SAFE)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("negated_phrase", [
    "I am NOT okay.",
    "I'm not okay.",
    "I'm not feeling well.",
    "No, I am not fine.",
    "I am not doing good.",
    "I don't feel okay.",
    "No, not alright.",
    "I ain't okay."
])
def test_negation_must_not_be_safe(analyzer, negated_phrase):
    res = analyzer.analyze(negated_phrase)
    assert res.status != VoiceInteractionStatus.SAFE, (
        f"CRITICAL VIOLATION: Negated phrase '{negated_phrase}' classified as SAFE!"
    )
    assert res.status in [VoiceInteractionStatus.RISK, VoiceInteractionStatus.EMERGENCY]
    assert res.is_negated is True


# ---------------------------------------------------------------------------
# 6. Mixed Response with Emergency Priority Override
# ---------------------------------------------------------------------------
def test_mixed_emergency_overrides_positive(analyzer):
    # "Yes, I'm okay, but I fell down and I can't get up."
    phrase = "Yes, I'm okay, but I fell down and I can't get up."
    res = analyzer.analyze(phrase)
    assert res.status == VoiceInteractionStatus.EMERGENCY, (
        f"Emergency priority failed! Got {res.status} instead of EMERGENCY"
    )
    assert res.urgency == VoiceUrgencyLevel.CRITICAL
    assert res.is_mixed is True


def test_mixed_call_someone_overrides_fine(analyzer):
    phrase = "I'm fine, but please call someone, I feel terrible."
    res = analyzer.analyze(phrase)
    assert res.status in [VoiceInteractionStatus.EMERGENCY, VoiceInteractionStatus.RISK]
    assert res.status != VoiceInteractionStatus.SAFE


# ---------------------------------------------------------------------------
# 7. Safety Fallback: Failure defaults to UNCERTAIN, never silently SAFE
# ---------------------------------------------------------------------------
def test_empty_string_safety_fallback(analyzer):
    res = analyzer.analyze("")
    assert res.status == VoiceInteractionStatus.UNCERTAIN
    assert res.status != VoiceInteractionStatus.SAFE


def test_gibberish_safety_fallback(analyzer):
    res = analyzer.analyze("blablabla xyz123")
    assert res.status == VoiceInteractionStatus.UNCERTAIN
    assert res.status != VoiceInteractionStatus.SAFE
