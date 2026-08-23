from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "check_harbor_dataset.py"
SPEC = importlib.util.spec_from_file_location("harbor_dataset_for_tests", SCRIPT)
assert SPEC and SPEC.loader
DATASET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DATASET)


class FakePackager:
    @staticmethod
    def compute_content_hash(task_dir: Path):
        files = sorted(
            path for path in task_dir.rglob("*")
            if path.is_file() and path.name != "rogue.txt"
        )
        digest = hashlib.sha256()
        for path in files:
            digest.update(path.read_bytes())
        return digest.hexdigest(), files


class HarborDatasetIntegrityTests(unittest.TestCase):
    def test_task_record_requires_every_file_to_be_publishable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harbor-dataset-task-") as temporary:
            task = Path(temporary) / "task_safe"
            task.mkdir()
            (task / "task.toml").write_text(
                "[task]\nname = 'legal-agent-simulation/task-safe'\n", "utf-8"
            )
            (task / "instruction.md").write_text("Synthetic task.\n", "utf-8")
            name, digest, count = DATASET.task_record(task, FakePackager)
            self.assertEqual(name, "legal-agent-simulation/task-safe")
            self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(count, 2)

            (task / "rogue.txt").write_text("not publishable\n", "utf-8")
            with self.assertRaisesRegex(RuntimeError, "unpublished files"):
                DATASET.task_record(task, FakePackager)

    def test_dataset_tree_rejects_extra_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harbor-dataset-tree-") as temporary:
            dataset = Path(temporary)
            (dataset / "README.md").write_text("dataset\n", "utf-8")
            (dataset / "dataset.toml").write_text("[dataset]\n", "utf-8")
            self.assertEqual(
                DATASET.validate_dataset_tree(dataset), dataset / "dataset.toml"
            )
            (dataset / "secret.txt").write_text("unexpected\n", "utf-8")
            with self.assertRaisesRegex(RuntimeError, "topology differs"):
                DATASET.validate_dataset_tree(dataset)

    def test_manifest_requires_exact_metadata_order_and_fields(self) -> None:
        rows = [
            {"name": "legal-agent-simulation/a", "digest": "sha256:" + "a" * 64},
            {"name": "legal-agent-simulation/b", "digest": "sha256:" + "b" * 64},
        ]
        payload = {
            "dataset": {
                "name": DATASET.DATASET_NAME,
                "version": "1.0.0",
                "description": DATASET.DATASET_DESCRIPTION,
                "authors": [],
                "keywords": [],
            },
            "tasks": rows,
        }
        self.assertEqual(DATASET.validate_dataset_manifest(payload, 2), rows)
        payload["tasks"] = list(reversed(rows))
        with self.assertRaisesRegex(RuntimeError, "canonical name order"):
            DATASET.validate_dataset_manifest(payload, 2)


if __name__ == "__main__":
    unittest.main()
