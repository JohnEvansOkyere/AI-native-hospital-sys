"""The eval scenarios are data the team edits by hand; catch typos before a run does."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

from conversation_scenarios import PROGRAMS, SCENARIOS  # noqa: E402

EXPECT_KEYS = {"dose", "reason", "care_log", "escalation", "bp", "flow",
               "appointment", "emergency", "forbid", "require", "rubric"}
ALLOWED = {
    "dose": {"none", "taken", "missed"},
    "reason": {"cost", "forgot", "side_effect", "ran_out", "other"},
    "care_log": {"none", "done", "concern", "missed", "needs_clarification"},
    "escalation": {"none", "amber", "red"},
}


def test_ids_are_unique():
    ids = [s["id"] for s in SCENARIOS]
    assert len(ids) == len(set(ids))


def test_scenarios_are_well_formed():
    for s in SCENARIOS:
        assert s["program"] in PROGRAMS, s["id"]
        assert s["message"].strip(), s["id"]
        assert set(s["expect"]) <= EXPECT_KEYS, (s["id"], set(s["expect"]) - EXPECT_KEYS)
        for key, allowed in ALLOWED.items():
            if key in s["expect"]:
                value = s["expect"][key]
                values = set(value) if isinstance(value, list) else {value}
                assert values <= allowed, (s["id"], key, values - allowed)
        for direction, _ in s.get("setup", {}).get("history", []):
            assert direction in ("in", "out"), s["id"]
