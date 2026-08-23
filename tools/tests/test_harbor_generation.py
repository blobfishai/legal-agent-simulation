from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "harbor" / "generate.py"
SPEC = importlib.util.spec_from_file_location("harbor_generate_for_tests", SCRIPT)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class HarborGenerationTests(unittest.TestCase):
    task = {
        "task_id": "task_multistep_file_lane",
        "prompt": "Complete the staged matter.",
        "file_lane": {
            "deliverables": ["closeout.docx"],
            "assertions": [
                {
                    "criterion_id": "closeout",
                    "deliverables": ["closeout.docx"],
                    "anchor_groups": [["FINAL-ANCHOR"]],
                }
            ],
        },
    }

    def test_multistep_file_deliverable_is_deferred_until_final_step(self) -> None:
        early_instruction = GENERATOR.instruction_md(
            self.task,
            {"instruction": "Review the evidence."},
            include_file_deliverables=False,
        )
        early_test = GENERATOR.test_sh(
            self.task,
            "01-review",
            include_file_deliverables=False,
        )
        early_solution = GENERATOR.solve_sh(
            "a" * 64,
            self.task,
            "01-review",
            include_file_deliverables=False,
        )
        final_test = GENERATOR.test_sh(
            self.task,
            "02-closeout",
            include_file_deliverables=True,
        )
        final_solution = GENERATOR.solve_sh(
            "a" * 64,
            self.task,
            "02-closeout",
            include_file_deliverables=True,
        )

        self.assertIn(
            "do not anticipate later instructions",
            " ".join(early_instruction.split()),
        )
        self.assertNotIn("closeout.docx", early_instruction)
        self.assertIn("expected = []", early_test)
        self.assertIn("file_assertions = {}", early_test)
        self.assertNotIn("/workspace/output", early_solution)
        self.assertIn('expected = ["closeout.docx"]', final_test)
        self.assertIn("FINAL-ANCHOR", final_test)
        self.assertIn("/workspace/output", final_solution)


if __name__ == "__main__":
    unittest.main()
