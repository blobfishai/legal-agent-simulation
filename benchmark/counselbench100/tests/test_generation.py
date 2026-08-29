"""Causal depth, evidence partition, and native-format tests."""

from __future__ import annotations

import csv
import io
import json
import unittest
import xml.etree.ElementTree as ET
from email import policy
from email.parser import Parser
from pathlib import PurePosixPath

from benchmark.counselbench100.catalog import MATTERS
from benchmark.counselbench100.decision_specs import DECISION_RULES
from benchmark.counselbench100.generation import (
    MINIMUM_TOOL_CALLS,
    REQUIRED_EVIDENCE_READS,
    build_material,
    derive_disposition,
)


class SeededCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.material = build_material(MATTERS[0], 0)

    def test_sample_matter_has_deep_unique_folder_tree(self) -> None:
        documents = self.material["documents"]
        paths = [PurePosixPath(path) for path in documents]
        self.assertEqual(len(documents), 96)
        self.assertEqual(len({path.parent for path in paths}), 12)
        self.assertEqual(
            {path.suffix for path in paths},
            {".md", ".txt", ".eml", ".csv", ".json", ".xml", ".html"},
        )
        self.assertEqual(len(set(documents.values())), 96)
        self.assertGreaterEqual(
            min(len(value.encode("utf-8")) for value in documents.values()), 5_500
        )

    def test_format_native_documents_parse_without_answer_headers(self) -> None:
        by_suffix: dict[str, str] = {}
        for path, content in self.material["documents"].items():
            by_suffix.setdefault(PurePosixPath(path).suffix, content)

        parsed_json = json.loads(by_suffix[".json"])
        self.assertEqual(len(parsed_json["sections"]), 4)
        self.assertEqual(len(parsed_json["rows"]), 18)
        self.assertEqual(len(parsed_json["chronology"]), 6)

        csv_rows = list(csv.DictReader(io.StringIO(by_suffix[".csv"])))
        self.assertGreaterEqual(len(csv_rows), 35)
        self.assertIn("source_row", {row["row_type"] for row in csv_rows})

        xml_root = ET.fromstring(by_suffix[".xml"])
        self.assertEqual(xml_root.tag, "counsel-source-record")
        self.assertEqual(len(xml_root.findall("./supporting-rows/row")), 18)

        message = Parser(policy=policy.default).parsestr(by_suffix[".eml"])
        self.assertTrue(message["Message-ID"])
        self.assertTrue(message["X-Portfolio-Key"])
        self.assertIsNone(message["X-Finding-ID"])
        self.assertIn("-----Original Message-----", message.get_content())

        self.assertIn("<!doctype html>", by_suffix[".html"].casefold())
        self.assertIn("Native rows", by_suffix[".html"])
        self.assertIn("SCHEDULE 1 — NATIVE ROWS", by_suffix[".txt"])
        self.assertIn("## Related native records", by_suffix[".md"])

    def test_outcomes_are_derived_from_four_independent_sources(self) -> None:
        documents = self.material["documents"]
        self.assertEqual(len(self.material["cases"]), 12)
        self.assertGreaterEqual(self.material["action_count"], 5)
        self.assertGreaterEqual(self.material["hold_count"], 3)
        for case in self.material["cases"]:
            self.assertEqual(derive_disposition(case), case["disposition"])
            core_paths = [
                case["paths_by_role"][role]
                for role in (
                    "identity_crosswalk", "operative_authority",
                    "current_operations", "approval_and_capacity",
                )
            ]
            self.assertEqual(len(set(core_paths)), 4)
            self.assertIn(case["portfolio_key"], documents[core_paths[0]])
            self.assertIn(case["governing_statement"], documents[core_paths[1]])
            self.assertIn(case["observed_statement"], documents[core_paths[2]])
            self.assertIn(case["owner"], documents[core_paths[3]])

        joined = "\n".join(documents.values()).casefold()
        for token in (
            "finding_id", "record_role", "control_severity", "remediation_owner",
            '"selected_option_id"', '"disposition": "open_action"',
        ):
            self.assertNotIn(token, joined)
        for action in self.material["expected_decision"]["actions"]:
            self.assertNotIn(action["determination"].casefold(), joined)
            self.assertNotIn(action["recommended_action"].casefold(), joined)

    def test_employee_request_is_natural_and_not_a_tool_recipe(self) -> None:
        prompt = self.material["instruction"]
        self.assertGreaterEqual(len(prompt.split()), 45)
        self.assertLessEqual(len(prompt.split()), 120)
        for forbidden in (
            "required review procedure", "return exactly", "read_text_file",
            "decision.json", "matter-register.json", "step 1", "first,",
        ):
            self.assertNotIn(forbidden, prompt.casefold())
        self.assertIn("2026-09-04", prompt)

    def test_reference_has_causal_reads_writes_and_readbacks(self) -> None:
        self.assertGreaterEqual(
            len(self.material["required_document_paths"]), REQUIRED_EVIDENCE_READS
        )
        self.assertGreaterEqual(len(self.material["reference_calls"]), MINIMUM_TOOL_CALLS)
        self.assertEqual(len(self.material["decision_options"]), 3)
        self.assertEqual(
            sum(option["selected"] for option in self.material["decision_options"]), 1
        )
        phases = [call["phase"] for call in self.material["reference_calls"]]
        self.assertEqual(sum(phase.startswith("state-transition") for phase in phases), 3)
        self.assertEqual(sum(phase.startswith("postwrite-readback") for phase in phases), 3)
        first_write = next(i for i, phase in enumerate(phases) if phase.startswith("state-transition"))
        last_evidence = max(i for i, phase in enumerate(phases) if phase.startswith("evidence:"))
        self.assertLess(last_evidence, first_write)

    def test_all_matters_have_distinct_authored_rules_and_action_graphs(self) -> None:
        self.assertEqual(len(DECISION_RULES), 100)
        self.assertEqual(len({rule.signature for rule in DECISION_RULES.values()}), 100)
        raw_sequences: set[tuple[str, ...]] = set()
        semantic_sequences: set[tuple[str, ...]] = set()
        action_sizes: set[int] = set()
        for index, matter in enumerate(MATTERS):
            material = build_material(matter, index)
            raw_sequences.add(tuple(call["name"] for call in material["reference_calls"]))
            semantic_sequences.add(tuple(material["semantic_signature"]))
            action_sizes.add(material["action_count"])
            self.assertTrue(all(material["quality_gates"].values()))
            self.assertGreater(material["hold_count"], 0)
        self.assertEqual(len(raw_sequences), 100)
        self.assertEqual(len(semantic_sequences), 100)
        self.assertEqual(action_sizes, {5, 6, 7, 8, 9})


if __name__ == "__main__":
    unittest.main()
