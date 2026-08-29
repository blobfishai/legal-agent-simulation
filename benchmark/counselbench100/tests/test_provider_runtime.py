"""Provider-state, semantic-rubric, and mutation-containment tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from pathlib import PurePosixPath

from benchmark.counselbench100.builder import create_task_pack, verification_token
from benchmark.counselbench100.catalog import MATTERS
from benchmark.counselbench100.generation import build_material
from benchmark.counselbench100.runtime.contracts import MUTATION_TOOLS, TOOLS_BY_NAME
from benchmark.counselbench100.runtime.world import CounselWorld


class ProviderRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="counselbench-provider-test-")
        cls.root = Path(cls.temporary.name)
        cls.material = build_material(MATTERS[0], 0)
        create_task_pack(
            cls.root / "harbor" / "tasks",
            cls.root / "huggingface",
            MATTERS[0],
            0,
            cls.material,
        )
        cls.task = cls.root / "harbor" / "tasks" / cls.material["task_id"]
        cls.spec_path = cls.task / "environment" / "world" / "spec.json"
        cls.spec = json.loads(cls.spec_path.read_text(encoding="utf-8"))
        cls.reference = json.loads(
            (cls.task / "solution" / "reference.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def world(self, suffix: str) -> CounselWorld:
        return CounselWorld(
            self.task / "environment" / "documents",
            self.root / suffix / "output",
            self.root / suffix / "state",
            self.spec_path,
        )

    @staticmethod
    def replay(world: CounselWorld, calls: list[dict]) -> None:
        for call in calls:
            result = world.call_tool(call["name"], deepcopy(call["arguments"]))
            if result.get("isError"):
                raise AssertionError(f"oracle call failed: {call['name']}: {result}")

    def test_contracts_are_provider_operations_not_decision_pseudotools(self) -> None:
        self.assertEqual(
            {
                tool["_meta"]["counselbench"]["provider"]
                for tool in TOOLS_BY_NAME.values()
            },
            {"clio_manage", "gmail", "google_drive", "slack"},
        )
        self.assertEqual(
            MUTATION_TOOLS,
            {
                "clio_manage.matters.update",
                "clio_manage.notes.create",
                "gmail.messages.send",
                "google_drive.comments.create",
                "slack.chat_postMessage",
            },
        )
        self.assertFalse(
            any(
                token in name
                for name in TOOLS_BY_NAME
                for token in ("approve", "resolve", "decide", "complete_task")
            )
        )
        gmail_send = TOOLS_BY_NAME["gmail.messages.send"]["inputSchema"]
        self.assertEqual(gmail_send["required"], ["userId", "requestBody"])
        self.assertEqual(
            gmail_send["properties"]["requestBody"]["required"], ["raw"]
        )

    def test_asset_room_and_public_rubric_have_real_depth(self) -> None:
        assets = self.material["provider_assets"]
        material = [asset for asset in assets if asset["material"]]
        self.assertEqual(len(assets), 97)
        self.assertGreaterEqual(len(material), 49)
        self.assertEqual(
            {asset["provider"] for asset in material},
            {"clio_manage", "gmail", "google_drive", "slack"},
        )
        self.assertTrue(
            all(
                PurePosixPath(asset["path"]).suffix in {".md", ".txt"}
                for asset in material
                if asset["provider"] == "clio_manage"
            )
        )
        self.assertTrue(
            all(
                PurePosixPath(asset["path"]).suffix == ".eml"
                for asset in material
                if asset["provider"] == "gmail"
            )
        )
        self.assertTrue(
            all(
                PurePosixPath(asset["path"]).suffix == ".json"
                or asset["role"] == "approval_and_capacity"
                for asset in material
                if asset["provider"] == "slack"
            )
        )
        self.assertEqual(len(self.material["rubric_milestones"]), 14)
        self.assertEqual(
            sum(row["weight"] for row in self.material["rubric_milestones"]),
            100,
        )

    def test_oracle_reaches_exact_native_state_and_all_readbacks(self) -> None:
        world = self.world("oracle")
        self.replay(world, self.reference["calls"])
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertTrue(report["passed"])
        self.assertEqual(report["metric"], "CounselScore")
        self.assertEqual(report["score"], 100.0)
        self.assertEqual(len(report["milestones"]), 14)
        self.assertEqual(
            report["provider_mutations"],
            [call["name"] for call in self.material["state_contract"]["writes"]],
        )
        self.assertTrue(all(report["diagnostics"]["readback_checks"].values()))
        matter = world.call_tool(
            "clio_manage.matters.get",
            deepcopy(self.material["state_contract"]["readbacks"][0]["arguments"]),
        )["structuredContent"]["data"]
        field = matter["custom_field_values"][0]
        self.assertEqual(field["field_name"], "Review Disposition Register")
        self.assertEqual(field["field_type"], "text_area")
        self.assertEqual(
            field["custom_field"]["id"],
            self.material["state_contract"]["custom_field_id"],
        )

    def test_slack_json_export_is_served_as_a_human_thread(self) -> None:
        asset = next(
            row
            for row in self.material["provider_assets"]
            if row["provider"] == "slack"
            and PurePosixPath(row["path"]).suffix == ".json"
        )
        result = self.world("slack-thread").call_tool(
            "slack.conversations_replies", deepcopy(asset["read_arguments"])
        )
        self.assertFalse(result.get("isError"))
        payload = result["structuredContent"]
        self.assertGreaterEqual(len(payload["messages"]), 6)
        self.assertIn("Source:", payload["messages"][0]["text"])
        self.assertIn("Thread chronology", "\n".join(
            message["text"] for message in payload["messages"]
        ))
        self.assertNotIn('"chronology":', payload["messages"][0]["text"])

    def test_clio_note_discovery_returns_metadata_before_exact_get(self) -> None:
        world = self.world("clio-note-discovery")
        listed = world.call_tool(
            "clio_manage.notes.list",
            {
                "type": "matter",
                "query": self.spec["matter_number"],
                "fields": "id,etag,subject,updated_at,regarding{id,type}",
                "limit": 200,
            },
        )
        self.assertFalse(listed.get("isError"))
        notes = listed["structuredContent"]["data"]
        self.assertTrue(notes)
        self.assertTrue(all("detail" not in note for note in notes))
        asset = next(
            row
            for row in self.material["provider_assets"]
            if row["provider"] == "clio_manage"
        )
        self.assertIn(asset["resource_id"], {note["id"] for note in notes})
        fetched = world.call_tool(asset["read_tool"], deepcopy(asset["read_arguments"]))
        self.assertIn("detail", fetched["structuredContent"]["data"])

    def test_failed_exploratory_read_is_allowed_but_rejected_mutation_is_not(self) -> None:
        exploratory = self.world("exploratory")
        failed_read = exploratory.call_tool(
            "gmail.messages.get",
            {"userId": "me", "id": "missing-message", "format": "full"},
        )
        self.assertTrue(failed_read.get("isError"))
        self.replay(exploratory, self.reference["calls"])
        self.assertTrue(
            exploratory.verify(verification_token(self.spec["task_id"]))["passed"]
        )

        rejected = self.world("rejected")
        self.replay(rejected, self.reference["calls"])
        failed_write = rejected.call_tool(
            "clio_manage.matters.update",
            {"id": self.spec["state_contract"]["matter_id"] + 1, "data": {}},
        )
        self.assertTrue(failed_write.get("isError"))
        report = rejected.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        failed = {row["id"] for row in report["milestones"] if not row["passed"]}
        self.assertEqual(failed, {"containment.scope"})

    def test_notification_before_core_state_fails_collaboration(self) -> None:
        world = self.world("premature-notification")
        calls = deepcopy(self.reference["calls"])
        writes = [
            call
            for call in calls
            if call["phase"].startswith("state-transition:")
        ]
        readbacks = [
            call
            for call in calls
            if call["phase"].startswith("postwrite-readback:")
        ]
        investigation = [
            call for call in calls if call not in writes and call not in readbacks
        ]
        notification = next(
            call
            for call in writes
            if call["phase"] == "state-transition:notification"
        )
        core = [call for call in writes if call is not notification]
        self.replay(world, [*investigation, notification, *core, *readbacks])
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        failed = {row["id"] for row in report["milestones"] if not row["passed"]}
        self.assertEqual(failed, {"state.collaboration"})
        atomic = {row["id"]: row["passed"] for row in report["atomic_checks"]}
        self.assertFalse(atomic["state.core_state_precedes_notification"])

    def test_wrong_note_does_not_remove_exact_register_credit(self) -> None:
        world = self.world("wrong-note")
        calls = deepcopy(self.reference["calls"])
        note_call = next(
            call for call in calls
            if call.get("phase") == "state-transition:decision-note"
        )
        note = json.loads(note_call["arguments"]["data"]["detail"])
        note["decision"]["actions"][0]["owner"] = "Unapproved Owner"
        note_call["arguments"]["data"]["detail"] = json.dumps(
            note, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        milestones = {row["id"]: row for row in report["milestones"]}
        self.assertTrue(milestones["state.matter_register"]["passed"])
        self.assertFalse(milestones["state.legal_note"]["passed"])
        self.assertFalse(milestones["reasoning.actions"]["passed"])


if __name__ == "__main__":
    unittest.main()
