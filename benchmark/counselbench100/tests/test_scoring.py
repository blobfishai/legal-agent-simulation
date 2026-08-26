"""Unit tests for the deterministic CounselBench criterion scorer."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if not RUNTIME.exists():
    RUNTIME = Path(__file__).resolve().parents[1] / "world"
sys.path.insert(0, str(RUNTIME))

from scoring import aggregate_scores, score_findings, score_memo  # noqa: E402


def fixture() -> tuple[dict, dict, str]:
    expected = {
        "schema_version": "1.0",
        "task_id": "cb100-test",
        "matter_number": "CB-TEST-001",
        "prepared_for": "Test Client, Inc.",
        "as_of": "2026-09-04",
        "findings": [
            {
                "id": "F-01",
                "issue": "consent deadline mismatch",
                "severity": "high",
                "primary_source": "/workspace/documents/primary.md",
                "corroborating_source": "/workspace/documents/status.csv",
                "determination": "The agreement requires consent by 2026-09-01; the status record remains pending on 2026-09-03.",
                "recommended_action": "Deal Team must obtain consent by 2026-09-04.",
            }
        ],
    }
    scoring_row = {
        **{key: expected["findings"][0][key] for key in (
            "id", "issue", "severity", "primary_source", "corroborating_source",
        )},
        "fact_anchors": ["2026-09-01", "pending", "2026-09-03"],
        "action_anchors": ["Deal Team", "obtain consent", "2026-09-04"],
        "allowed_fact_text": "2026-09-01 pending 2026-09-03",
    }
    spec = {
        "expected_findings": expected,
        "scoring_findings": [scoring_row],
        "memo_sections": [
            "Executive assessment",
            "Method and record coverage",
            "Findings",
            "Recommended next actions",
            "Assumptions and limitations",
        ],
        "forbidden_claims": ["not present in the production"],
    }
    memo = "\n".join(
        [
            "# Executive assessment",
            "## Method and record coverage",
            "## Findings",
            "F-01 consent deadline mismatch high /workspace/documents/primary.md ",
            "/workspace/documents/status.csv 2026-09-01 pending 2026-09-03",
            "## Recommended next actions",
            "Deal Team obtain consent by 2026-09-04",
            "## Assumptions and limitations",
        ]
    )
    return spec, expected, memo


class ScoringTests(unittest.TestCase):
    def test_complete_grounded_outputs_pass(self) -> None:
        spec, findings, memo = fixture()
        finding_score = score_findings(findings, spec)
        memo_score = score_memo(memo, spec)
        procedure = {f"gate_{index}": True for index in range(8)}
        procedure.update({
            "exact_deliverable_set": True,
            "deliverables_written_through_mcp": True,
        })
        aggregate = aggregate_scores(procedure, finding_score, memo_score)

        self.assertEqual(len(finding_score["criteria"]), 17)
        self.assertEqual(len(memo_score["criteria"]), 7)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["reward"], 1.0)

    def test_unsupported_controlled_fact_loses_only_its_criterion(self) -> None:
        spec, findings, _ = fixture()
        mutated = copy.deepcopy(findings)
        mutated["findings"][0]["determination"] += " Exposure is $99,999,999."

        result = score_findings(mutated, spec)

        self.assertFalse(result["criteria"]["F-01.facts_source_bounded"])
        self.assertEqual(result["details"][0]["unsupported_fact_tokens"], ["$99,999,999"])
        self.assertGreater(result["score"], 0)
        self.assertLess(result["score"], 1)

    def test_wrong_source_path_does_not_erase_other_credit(self) -> None:
        spec, findings, _ = fixture()
        mutated = copy.deepcopy(findings)
        mutated["findings"][0]["primary_source"] = "/workspace/documents/wrong.md"

        result = score_findings(mutated, spec)

        self.assertFalse(result["criteria"]["F-01.primary_source"])
        self.assertTrue(result["criteria"]["F-01.issue"])
        self.assertAlmostEqual(result["score"], 16 / 17, places=6)

    def test_incomplete_procedure_caps_reward(self) -> None:
        findings = {"score": 1.0, "passed": True}
        memo = {"score": 1.0, "passed": True}
        procedure = {
            "review_complete": False,
            "exact_deliverable_set": True,
            "deliverables_written_through_mcp": True,
        }

        result = aggregate_scores(procedure, findings, memo)

        self.assertEqual(result["reward"], 0.49)
        self.assertEqual(result["cap_reason"], "required_review_procedure_incomplete")
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
