"""Unit tests for deterministic decision, state, and advice scoring."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

from benchmark.counselbench100.catalog import MATTERS
from benchmark.counselbench100.generation import build_material

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if not RUNTIME.exists():
    RUNTIME = Path(__file__).resolve().parents[1] / "world"
sys.path.insert(0, str(RUNTIME))

from scoring import (  # noqa: E402
    aggregate_scores,
    score_advice,
    score_decision,
    score_register,
)


def fixture() -> tuple[dict, dict, dict, str]:
    material = build_material(MATTERS[0], 0)
    spec = {
        "expected_decision": material["expected_decision"],
        "expected_register": material["expected_register"],
        "forbidden_claims": [
            "every portfolio item is actionable",
            "the newest document always controls",
        ],
    }
    return (
        spec,
        copy.deepcopy(material["expected_decision"]),
        copy.deepcopy(material["expected_register"]),
        material["expected_advice"],
    )


class ScoringTests(unittest.TestCase):
    def test_complete_causal_outputs_pass(self) -> None:
        spec, decision, register, advice = fixture()
        decision_score = score_decision(decision, spec)
        register_score = score_register(register, spec)
        advice_score = score_advice(advice, spec)
        procedure = {
            "all_required_evidence_precedes_first_write": True,
            "exact_deliverable_set": True,
            "write_scope_contained": True,
            "all_outputs_verified_by_readback": True,
        }
        aggregate = aggregate_scores(
            procedure, decision_score, register_score, advice_score
        )
        self.assertTrue(decision_score["passed"])
        self.assertTrue(register_score["passed"])
        self.assertTrue(advice_score["passed"])
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["reward"], 1.0)

    def test_wrong_action_value_loses_exact_task_criteria(self) -> None:
        spec, decision, _, _ = fixture()
        key = decision["actions"][0]["portfolio_key"]
        decision["actions"][0]["owner"] = "Unsupported Owner"
        result = score_decision(decision, spec)
        self.assertFalse(result["criteria"][f"{key}.action.owner"])
        self.assertTrue(result["criteria"][f"{key}.action.due_date"])
        self.assertFalse(result["passed"])
        self.assertGreater(result["score"], 0.9)

    def test_blanket_hold_of_supported_action_fails_branch_population(self) -> None:
        spec, decision, _, _ = fixture()
        moved = decision["actions"].pop(0)
        decision["holds"].append(
            {
                "id": f"HOLD-{moved['portfolio_key']}",
                "portfolio_key": moved["portfolio_key"],
                "issue": moved["issue"],
                "reason": "conservative hold",
                "required_next_evidence": "another reviewer",
                "source_paths": moved["source_paths"],
            }
        )
        result = score_decision(decision, spec)
        self.assertFalse(result["criteria"]["actions.exact_population"])
        self.assertFalse(result["criteria"]["holds.exact_population"])
        self.assertFalse(result["passed"])

    def test_collateral_register_edit_fails_exact_state(self) -> None:
        spec, _, register, _ = fixture()
        key = register["rows"][0]["portfolio_key"]
        register["rows"][0]["unapproved_field"] = "collateral edit"
        result = score_register(register, spec)
        self.assertFalse(result["criteria"][f"{key}.exact_state"])
        self.assertFalse(result["criteria"]["register.exact_state"])

    def test_missing_readback_caps_reward(self) -> None:
        perfect = {"score": 1.0, "passed": True}
        procedure = {
            "all_required_evidence_precedes_first_write": True,
            "exact_deliverable_set": True,
            "write_scope_contained": True,
            "all_outputs_verified_by_readback": False,
        }
        result = aggregate_scores(procedure, perfect, perfect, perfect)
        self.assertEqual(result["reward"], 0.35)
        self.assertEqual(result["cap_reason"], "state_not_verified_by_readback")
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
