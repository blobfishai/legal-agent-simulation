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

    def test_human_readable_state_needs_no_hidden_json_serialization(self) -> None:
        world = self.world("human-readable-state")
        calls = deepcopy(self.reference["calls"])
        selected = self.material["expected_decision"]["decision"][
            "selected_option_id"
        ]
        register_lines = [
            f"Review Disposition Register — {self.spec['matter_number']}",
            f"Selected option: {selected}",
        ]
        for row in self.spec["semantic_state_contract"]:
            source = row["source_records"][0]["resource_id"]
            facts = "; ".join(str(value) for value in row["fact_anchors"])
            if row["disposition"] == "action":
                detail = (
                    f"OPEN ACTION | {row['topic']} | {row['entity_id']} | "
                    f"{facts} | Owner {row['owner']} | due {row['due_date']} | "
                    f"Source {source}"
                )
            else:
                detail = (
                    f"EVIDENCE HOLD | {row['topic']} | {facts} | "
                    f"Missing control: {row['required_next_evidence']} | Source {source}"
                )
            register_lines.append(f"{row['portfolio_key']} | {detail}")

        matter_write = next(
            call
            for call in calls
            if call.get("phase") == "state-transition:matter-register"
        )
        matter_write["arguments"]["data"]["custom_field_values"][0]["value"] = (
            "\n".join(register_lines)
        )
        note_write = next(
            call
            for call in calls
            if call.get("phase") == "state-transition:decision-note"
        )
        note_write["arguments"]["data"]["detail"] = (
            f"Prepared for {self.material['expected_decision']['prepared_for']} as of "
            f"{self.material['expected_decision']['as_of']}.\n\n"
            f"{self.material['expected_advice']}"
        )

        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertTrue(
            report["passed"],
            [row["id"] for row in report["atomic_checks"] if not row["passed"]],
        )
        self.assertEqual(
            report["criteria"]["register"]["serialization"], "human-readable"
        )
        self.assertEqual(
            report["criteria"]["decision"]["serialization"], "human-readable"
        )

    def test_keyword_stuffing_without_distinct_rows_cannot_fake_state(self) -> None:
        world = self.world("keyword-stuffing")
        calls = deepcopy(self.reference["calls"])
        matter_write = next(
            call
            for call in calls
            if call.get("phase") == "state-transition:matter-register"
        )
        all_keys = " ".join(
            row["portfolio_key"] for row in self.spec["semantic_state_contract"]
        )
        matter_write["arguments"]["data"]["custom_field_values"][0]["value"] = (
            f"{self.spec['matter_number']} {all_keys} open action evidence hold "
            "owner due source selected option"
        )
        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        self.assertFalse(report["criteria"]["register"]["criteria"]["rows.population"])

    def test_equivalent_provider_projections_count_as_evidence_and_readback(self) -> None:
        world = self.world("equivalent-provider-projections")
        calls = deepcopy(self.reference["calls"])
        for call in calls:
            name = call["name"]
            arguments = call["arguments"]
            if name == "clio_manage.notes.get":
                arguments["fields"] = "id,subject,detail"
            elif name == "clio_manage.matters.get":
                arguments["fields"] = "id,custom_field_values"
            elif name == "google_drive.files.get":
                arguments.pop("fields", None)
            elif name == "google_drive.comments.get":
                arguments.pop("fields", None)
            elif name == "slack.conversations_replies":
                arguments.pop("limit", None)

        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertTrue(
            report["passed"],
            [row["id"] for row in report["atomic_checks"] if not row["passed"]],
        )
        self.assertTrue(
            report["criteria"]["procedure"]["criteria"][
                "all_material_evidence_read"
            ]
        )
        self.assertTrue(all(report["diagnostics"]["readback_checks"].values()))

    def test_metadata_only_provider_lookup_does_not_count_as_evidence(self) -> None:
        world = self.world("metadata-only-provider-lookup")
        calls = deepcopy(self.reference["calls"])
        drive_read = next(
            call
            for call in calls
            if call["name"] == "google_drive.files.get"
            and call["phase"].startswith("evidence:")
        )
        drive_read["arguments"].pop("alt", None)
        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        self.assertFalse(
            report["criteria"]["procedure"]["criteria"][
                "all_material_evidence_read"
            ]
        )
        failed = {
            row["id"]
            for row in report["atomic_checks"]
            if row["id"].startswith("evidence.") and not row["passed"]
        }
        self.assertEqual(len(failed), 1)

    def test_investigation_credit_is_independent_from_required_mutations(self) -> None:
        world = self.world("investigation-without-mutations")
        investigation = [
            call
            for call in self.reference["calls"]
            if call["phase"].startswith(("discovery:", "evidence:"))
        ]
        self.replay(world, investigation)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        self.assertTrue(
            report["criteria"]["procedure"]["criteria"][
                "all_material_evidence_read"
            ]
        )
        self.assertTrue(
            report["criteria"]["procedure"]["criteria"][
                "all_material_evidence_precedes_first_mutation"
            ]
        )
        self.assertFalse(
            report["criteria"]["procedure"]["criteria"]["exact_mutation_set"]
        )
        required = len(self.material["required_document_paths"])
        self.assertEqual(
            report["diagnostics"]["evidence"],
            {
                "required": required,
                "content_reads": required,
                "prewrite_reads": required,
            },
        )
        self.assertFalse(
            any(
                not row["passed"]
                for row in report["atomic_checks"]
                if row["id"].startswith("evidence.")
            )
        )

    def test_neighboring_provider_object_does_not_count_as_exact_evidence(self) -> None:
        world = self.world("neighboring-provider-object")
        calls = deepcopy(self.reference["calls"])
        drive_reads = [
            call
            for call in calls
            if call["name"] == "google_drive.files.get"
            and call["phase"].startswith("evidence:")
        ]
        self.assertGreaterEqual(len(drive_reads), 2)
        drive_reads[0]["arguments"] = deepcopy(drive_reads[1]["arguments"])
        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        failed = {
            row["id"]
            for row in report["atomic_checks"]
            if row["id"].startswith("evidence.") and not row["passed"]
        }
        self.assertFalse(report["passed"])
        self.assertEqual(len(failed), 1)

    def test_readback_proof_rejects_stale_values_with_the_right_shape(self) -> None:
        world = self.world("stale-shaped-readback")
        self.replay(world, self.reference["calls"])
        state = self.material["state_contract"]
        notification_write = next(
            call
            for call in state["writes"]
            if call["name"] == "slack.chat_postMessage"
        )
        target = notification_write["arguments"]
        stale_matter = {
            "structuredContent": {
                "data": {
                    "id": state["matter_id"],
                    "custom_field_values": [
                        {
                            "custom_field": {"id": state["custom_field_id"]},
                            "value": "stale-but-well-shaped",
                        }
                    ],
                }
            }
        }
        stale_notification = {
            "structuredContent": {
                "messages": [
                    {
                        "ts": state["notification_id"],
                        "thread_ts": target["thread_ts"],
                        "text": "stale-but-well-shaped",
                    }
                ]
            }
        }
        self.assertIsNone(
            world._state_readback_proof(
                "clio_manage.matters.get",
                {"id": state["matter_id"]},
                stale_matter,
            )
        )
        self.assertIsNone(
            world._state_readback_proof(
                "slack.conversations_replies",
                {
                    "channel": target["channel"],
                    "ts": target["thread_ts"],
                },
                stale_notification,
            )
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

    def test_undisclosed_slack_thread_is_out_of_scope_even_when_it_exists(self) -> None:
        self.assertEqual(self.material["completion_route"]["provider"], "slack")
        world = self.world("wrong-existing-slack-thread")
        calls = deepcopy(self.reference["calls"])
        expected_thread = self.material["completion_route"]["thread_ts"]
        alternate = next(
            asset
            for asset in self.material["provider_assets"]
            if asset["provider"] == "slack" and asset["ts"] != expected_thread
        )
        notification_write = next(
            call
            for call in calls
            if call["phase"] == "state-transition:notification"
        )
        notification_write["arguments"]["thread_ts"] = alternate["ts"]
        notification_readback = next(
            call
            for call in calls
            if call["phase"] == "postwrite-readback:notification"
        )
        notification_readback["arguments"]["ts"] = alternate["ts"]
        self.replay(world, calls)
        report = world.verify(verification_token(self.spec["task_id"]))
        self.assertFalse(report["passed"])
        atomic = {row["id"]: row["passed"] for row in report["atomic_checks"]}
        self.assertFalse(atomic["state.write_scope_contained"])

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
