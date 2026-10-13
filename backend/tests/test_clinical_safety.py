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
    ((139, 90), "elevated", "amber"),
    ((139, 89), "high_normal", "green"),
    ((130, 70), "high_normal", "green"),
    ((120, 85), "high_normal", "green"),
    ((129, 84), "normal", "green"),
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


def test_bp_reply_names_the_range_of_each_number():
    note = assess_bp_risk(139, 90)[1]
    assert "top number (139) is okay, but on the high side" in note
    assert "bottom number (90) is a bit high" in note


def test_single_elevated_reading_does_not_claim_care_team_told():
    assert "care team" not in assess_bp_risk(145, 85)[1]
    assert "care team" in assess_bp_risk(145, 85, repeated=True)[1]


def test_low_bp_is_never_praised():
    assert "Excellent" not in assess_bp_risk(85, 50)[1]


def test_cost_wins_over_forgot_in_rules():
    assert detect_reason_rule("I couldn't afford it so I forgot") == "cost"


from services.ai import _conversation, reply_is_safe  # noqa: E402


@pytest.mark.parametrize("reply", [
    "Try taking 10mg instead of 5mg tonight.",
    "You could double your dose until you feel better.",
    "It's fine to stop taking your tablets for a few days.",
    "Skip your medication if you feel dizzy.",
    "Your blood pressure looks normal, well done!",
    "135/86 is a great reading.",
    "You probably have an infection.",
])
def test_reply_screen_blocks_clinical_decisions(reply):
    assert not reply_is_safe(reply)


@pytest.mark.parametrize("reply", [
    "Thanks Ama! Keep taking your medication every morning, it protects your heart. 😊",
    "Try to use less salt and fewer stock cubes in your soup.",
    "Your care team will review this and call you.",
    "Please send your reading as two numbers so the clinic can check it.",
])
def test_reply_screen_allows_ordinary_support(reply):
    assert reply_is_safe(reply)


def test_conversation_starts_with_user_and_alternates():
    messages = _conversation([
        ("assistant", "Good morning! Did you take your medicine?"),
        ("user", "not yet"),
        ("assistant", "Reminder"), ("assistant", "Please reply YES"),
        ("user", "ok"), ("user", "when is my visit?"),
    ])
    assert messages[0]["role"] == "user"
    roles = [m["role"] for m in messages]
    assert all(a != b for a, b in zip(roles, roles[1:]))
    assert messages[-1]["content"] == "ok\n\nwhen is my visit?"


class _FakeClaude:
    """Stands in for AsyncAnthropic: records the request, returns a canned reply."""

    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.text, self.stop_reason, self.calls = text, stop_reason, []
        self.beta = self
        self.messages = self

    def with_options(self, **_):
        return self

    async def create(self, **kwargs):
        from types import SimpleNamespace
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason, _request_id="req_test",
            content=[SimpleNamespace(type="text", text=self.text)],
        )


def _run(coro):
    import asyncio
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _no_real_model_calls(monkeypatch):
    from services import ai
    monkeypatch.setattr(ai, "get_client", lambda: None)
    monkeypatch.setattr(ai, "get_groq_client", lambda: None)


def test_claude_request_shape_and_safe_reply(monkeypatch):
    from services import ai
    fake = _FakeClaude("Well done, Ama! Keep it up. 😊")
    monkeypatch.setattr(ai, "get_client", lambda: fake)
    facts = {"name": "Mrs. Ama Owusu", "condition": "hypertension", "drug_name": "Amlodipine",
             "drug_dosage": "5mg", "adherence_pct": 90, "streak": 4}
    reply = _run(ai.generate_assistant_reply(facts, [], "thank you"))
    assert reply == "Well done, Ama! Keep it up. 😊"
    call = fake.calls[0]
    assert call["model"] == ai.FAST_MODEL
    assert call["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in call["betas"]
    assert "Owusu" not in call["system"]  # only the first name leaves the clinic


def test_unsafe_or_refused_claude_reply_falls_back_to_template(monkeypatch):
    from services import ai
    facts = {"name": "Ama Owusu", "condition": "hypertension", "drug_name": "Amlodipine",
             "drug_dosage": "5mg", "adherence_pct": 90, "streak": 4}
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("You can double your dose today."))
    assert "double" not in _run(ai.generate_assistant_reply(facts, [], "can I take more?"))
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("", stop_reason="refusal"))
    assert "Ama" in _run(ai.generate_assistant_reply(facts, [], "hello"))


def test_classifier_rejects_off_list_answers(monkeypatch):
    from services import ai
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("ignore previous instructions"))
    assert _run(ai.classify_intent("Ama", "when is my visit?")) in ai.INTENTS
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("cost"))
    assert _run(ai.detect_reason_ai("Ama", "no money this week")) == "cost"


class _FakeGroq:
    """Stands in for AsyncGroq."""

    def __init__(self, text: str):
        self.text, self.calls = text, []
        self.chat = self
        self.completions = self

    def with_options(self, **_):
        return self

    async def create(self, **kwargs):
        from types import SimpleNamespace
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


def test_groq_answers_when_claude_cannot(monkeypatch):
    from services import ai
    fake_groq = _FakeGroq("Thanks Ama, your care team has your message. 😊")
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("", stop_reason="refusal"))
    monkeypatch.setattr(ai, "get_groq_client", lambda: fake_groq)
    facts = {"name": "Ama Owusu", "condition": "hypertension", "drug_name": "Amlodipine",
             "drug_dosage": "5mg", "adherence_pct": 90, "streak": 4}
    assert _run(ai.generate_assistant_reply(facts, [], "hello")) == fake_groq.text
    assert fake_groq.calls[0]["messages"][0]["role"] == "system"


def test_groq_is_not_called_when_claude_answers(monkeypatch):
    from services import ai
    fake_groq = _FakeGroq("other")
    monkeypatch.setattr(ai, "get_client", lambda: _FakeClaude("appointment"))
    monkeypatch.setattr(ai, "get_groq_client", lambda: fake_groq)
    assert _run(ai.classify_intent("Ama", "can I book a visit?")) == "appointment"
    assert fake_groq.calls == []


def test_groq_replies_pass_the_same_safety_screen(monkeypatch):
    from services import ai
    monkeypatch.setattr(ai, "get_groq_client", lambda: _FakeGroq("Stop taking your tablets for now."))
    facts = {"name": "Ama Owusu", "condition": "hypertension", "drug_name": "Amlodipine",
             "drug_dosage": "5mg", "adherence_pct": 90, "streak": 4}
    assert "Stop taking" not in _run(ai.generate_assistant_reply(facts, [], "I feel tired"))


def test_rules_answer_when_no_model_is_available():
    from services import ai
    assert _run(ai.detect_reason_ai("Ama", "I ran out of pills")) == "ran_out"


from services.ai import (  # noqa: E402
    assess_dental_concern, assess_eye_concern, classify_intent_rule, is_affirmative,
)


@pytest.mark.parametrize("message", [
    "yes", "Yes I took it", "ok", "I have taken my medicine", "done ✅",
    "I don take am this morning", "I take am already",
])
def test_dose_confirmations(message):
    assert is_affirmative(message)


@pytest.mark.parametrize("message", [
    # A miss logged as taken corrupts the adherence record.
    "I didn't take it, I forgot", "I did not take it", "I haven't taken it yet",
    "I have not taken it", "no I didn't", "not taken", "I missed it today",
    # Acknowledgements and questions are not confirmations.
    "Okay\nThank you", "Thanks", "is it ok to exercise?", "dizzy",
])
def test_not_dose_confirmations(message):
    assert not is_affirmative(message)


@pytest.mark.parametrize("message, risk", [
    ("No pain at all, it's healing well", None),
    ("No bleeding anymore, thank you", None),
    ("no fever and no swelling", None),
    ("Slight pain when I chew", "amber"),
    ("My jaw dey swell", "amber"),
    ("It is still bleeding a lot and it won't stop", "red"),
    ("no, the bleeding won't stop", "red"),
    ("My face is swelling and I have fever", "red"),
])
def test_dental_concerns(message, risk):
    assert assess_dental_concern(message)[0] == risk


@pytest.mark.parametrize("message, risk", [
    ("No pain and no redness", None),
    ("My vision is better today, thank you", None),
    ("My eye dey pain me small", "amber"),
    ("I'm seeing flashes and floaters since yesterday", "red"),
    ("Suddenly I can't see from the operated eye", "red"),
])
def test_eye_concerns(message, risk):
    assert assess_eye_concern(message)[0] == risk


@pytest.mark.parametrize("message, intent", [
    ("No headache, no dizziness, I'm fine", "other"),
    ("The tablets make me dizzy so I stopped", "missed"),
    ("I no get money buy the medicine", "missed"),
])
def test_intent_rule_respects_denied_symptoms(message, intent):
    assert classify_intent_rule(message) == intent


def test_reading_given_as_format_example_is_not_a_judgement():
    from services.ai import reply_is_safe
    assert reply_is_safe("Send me the two numbers when you can (e.g., 130/85).")
    assert reply_is_safe("Please send it like 135/86.")
    assert not reply_is_safe("Your 130/85 is fine.")
    assert not reply_is_safe("e.g. 130/85 — your blood pressure is fine")
