"""Table-driven tests for the deterministic clinical-safety rules.

These rules are the medical-safety boundary: the LLM never decides escalation,
so every phrasing that must trigger (or must not trigger) an urgent path lives
here. Thresholds and wording need clinician sign-off before go-live; when they
change, change this table with them.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai import (  # noqa: E402
    assess_bp_risk, bp_band, detect_emergency, detect_reason_rule,
)


@pytest.mark.parametrize("message", [
    # Cardiac / breathing
    "I have chest pain", "my chest is tight", "I feel breathless", "I can't breathe well",
    "I'm out of breath just sitting", "it is hard to breathe",
    # Angioedema (ACE inhibitors)
    "my lips and face are swelling", "my tongue is swollen", "swelling of my lips since the new tablet",
    "my throat is closing", "my face is swollen this morning",
    # Stroke
    "weak on my left side", "my right side feels weak", "my arm is numb", "I can't move my leg",
    "I can't talk properly", "my face is drooping", "his speech is slurred",
    # Other red flags
    "I fainted this morning", "I am confused", "worst headache of my life", "blurred vision",
    # Ghanaian Pidgin
    "my chest dey pain me", "I no fit breathe", "my face don swell",
    # Twi (unverified drafts — see EMERGENCY_REGEXES)
    "me koko yɛ me ya", "mentumi nhome",
])
def test_emergency_symptoms_are_detected(message):
    assert detect_emergency(message)


@pytest.mark.parametrize("message", [
    "yes I took it", "I forgot my pills", "the price is too high", "I went to work early",
    "I have a small cough", "my face is fine thanks", "feeling better today", "128/82",
    "when is my next appointment?",
])
def test_routine_messages_are_not_emergencies(message):
    assert not detect_emergency(message)


@pytest.mark.parametrize("reading, band, risk", [
    ((200, 130), "crisis", "red"),
    ((180, 90), "crisis", "red"),
    ((150, 120), "crisis", "red"),
    ((179, 119), "high", "red"),
    ((160, 80), "high", "red"),
    ((130, 100), "high", "red"),
    ((159, 99), "elevated", "amber"),
    ((140, 80), "elevated", "amber"),
    ((139, 89), "normal", "green"),
    ((120, 80), "normal", "green"),
    ((90, 60), "normal", "green"),
    ((89, 60), "low", "amber"),
    ((100, 59), "low", "amber"),
    ((85, 50), "low", "amber"),
])
def test_bp_bands(reading, band, risk):
    assert bp_band(*reading) == band
    assert assess_bp_risk(*reading)[0] == risk


@pytest.mark.parametrize("reading", [(200, 130), (165, 95), (85, 50)])
def test_urgent_bp_replies_name_emergency_numbers(reading):
    note = assess_bp_risk(*reading)[1]
    assert "112" in note and "193" in note


def test_low_bp_is_never_praised():
    assert "Excellent" not in assess_bp_risk(85, 50)[1]


def test_cost_wins_over_forgot_in_rules():
    assert detect_reason_rule("I couldn't afford it so I forgot") == "cost"
