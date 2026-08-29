"""Depth, structure, and recoverability tests for seeded evidence."""

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
from benchmark.counselbench100.generation import build_material


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
        self.assertGreaterEqual(min(len(value.encode("utf-8")) for value in documents.values()), 5_500)

    def test_format_native_documents_parse(self) -> None:
        by_suffix: dict[str, str] = {}
        for path, content in self.material["documents"].items():
            by_suffix.setdefault(PurePosixPath(path).suffix, content)

        parsed_json = json.loads(by_suffix[".json"])
        self.assertEqual(len(parsed_json["record"]["analysis_sections"]), 6)
        self.assertEqual(len(parsed_json["chronology"]), 5)
        self.assertEqual(len(parsed_json["action_register"]), 3)

        csv_rows = list(csv.DictReader(io.StringIO(by_suffix[".csv"])))
        self.assertGreaterEqual(len(csv_rows), 50)
        self.assertIn("ledger_entry", {row["row_type"] for row in csv_rows})

        xml_root = ET.fromstring(by_suffix[".xml"])
        self.assertEqual(xml_root.tag, "legal-record")
        self.assertEqual(len(xml_root.findall("./analysis/section")), 6)

        eml_messages = [
            Parser(policy=policy.default).parsestr(content)
            for path, content in self.material["documents"].items()
            if PurePosixPath(path).suffix == ".eml"
        ]
        message = next(row for row in eml_messages if row["X-Finding-ID"] != "none")
        self.assertRegex(str(message["X-Finding-ID"]), r"^F-\d{2}$")
        self.assertIn("-----Original Message-----", message.get_content())

        self.assertIn("<!doctype html>", by_suffix[".html"].casefold())
        self.assertIn("Action register", by_suffix[".html"])
        self.assertIn("SCHEDULE 1 — RECORD CHRONOLOGY", by_suffix[".txt"])
        self.assertIn("## Participants", by_suffix[".md"])

    def test_every_finding_field_is_recoverable_from_both_sources(self) -> None:
        documents = self.material["documents"]
        for finding in self.material["scoring_findings"]:
            for path, role in (
                (finding["primary_source"], "primary"),
                (finding["corroborating_source"], "corroborating"),
            ):
                content = documents[path]
                for expected in (
                    finding["id"], finding["issue"], finding["severity"], role,
                    *finding["action_anchors"],
                ):
                    self.assertIn(expected, content, msg=f"{expected!r} missing from {path}")

    def test_employee_request_is_high_level_and_contract_lives_in_evidence(self) -> None:
        prompt = self.material["instruction"]
        self.assertGreaterEqual(len(prompt.split()), 45)
        self.assertLessEqual(len(prompt.split()), 120)
        self.assertNotIn("Required review procedure", prompt)
        self.assertNotIn("Return exactly", prompt)
        self.assertNotIn("read_text_file", prompt)
        self.assertTrue(
            any("# Matter work-product control" in value for value in self.material["documents"].values())
        )

    def test_public_contract_is_specific_and_requires_choice(self) -> None:
        self.assertEqual(len(self.material["required_document_paths"]), 33)
        self.assertEqual(len(self.material["reference_calls"]), 46)
        self.assertEqual(len(self.material["rubric_criteria"]), 182)
        self.assertEqual(len(self.material["decision_options"]), 3)
        self.assertEqual(
            sum(option["selected"] for option in self.material["decision_options"]),
            1,
        )

    def test_every_matter_has_a_distinct_reference_tool_sequence(self) -> None:
        sequences = {
            tuple(call["name"] for call in build_material(matter, index)["reference_calls"])
            for index, matter in enumerate(MATTERS)
        }
        self.assertEqual(len(sequences), 100)


if __name__ == "__main__":
    unittest.main()
