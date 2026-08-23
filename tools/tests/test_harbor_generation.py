from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "harbor" / "generate.py"
SPEC = importlib.util.spec_from_file_location("harbor_generate_for_tests", SCRIPT)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)

CHECKER_SCRIPT = ROOT / "tools" / "check_harbor_export.py"
CHECKER_SPEC = importlib.util.spec_from_file_location(
    "check_harbor_export_for_tests", CHECKER_SCRIPT
)
assert CHECKER_SPEC and CHECKER_SPEC.loader
CHECKER = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(CHECKER)


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

    def test_task_layout_rejects_traversal_and_duplicate_components(self) -> None:
        invalid_tasks = [
            [{"task_id": "../escape"}],
            [{
                "task_id": "task_safe",
                "multi_step": {"phases": [{"name": "../../escape"}]},
            }],
            [{
                "task_id": "task_safe",
                "file_lane": {"deliverables": [], "skills": ["../docx"]},
            }],
            [{"task_id": "task_same"}, {"task_id": "task_same"}],
            [{
                "task_id": "task_safe",
                "multi_step": {
                    "phases": [{"name": "review"}, {"name": "review"}]
                },
            }],
            [{
                "task_id": "task_safe",
                "file_lane": {"deliverables": ["nested//result.docx"]},
            }],
        ]
        for tasks in invalid_tasks:
            with self.subTest(tasks=tasks), self.assertRaises(RuntimeError):
                GENERATOR.validate_task_layout(tasks)

    def test_output_root_is_confined_and_symlink_free(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "child of"):
            GENERATOR.resolve_output_root(ROOT)
        (ROOT / "dist").mkdir(exist_ok=True)
        with (
            tempfile.TemporaryDirectory(dir=ROOT / "dist") as safe_parent,
            tempfile.TemporaryDirectory() as outside,
        ):
            link = Path(safe_parent) / "escape"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with self.assertRaisesRegex(RuntimeError, "symlink component"):
                GENERATOR.resolve_output_root(link / "generated")

    def test_source_tree_rejects_nested_symlinks(self) -> None:
        (ROOT / "dist").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "dist") as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            link = source / "linked-input"
            try:
                link.symlink_to(ROOT / "package.json")
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with self.assertRaisesRegex(RuntimeError, "contains a symlink"):
                GENERATOR.validate_project_source_tree(source, "test source")


class HarborExportIntegrityTests(unittest.TestCase):
    token = "a" * 64
    world_image = "ghcr.io/example/world@sha256:" + "b" * 64
    lab_image = "ghcr.io/example/lab@sha256:" + "c" * 64

    def write_task(self, task_dir: Path) -> dict:
        task = {
            "task_id": task_dir.name,
            "prompt": "Review the synthetic matter and file the result.",
        }
        GENERATOR.write(
            str(task_dir / "instruction.md"), GENERATOR.instruction_md(task)
        )
        GENERATOR.write(
            str(task_dir / "task.toml"),
            GENERATOR.task_toml(task, self.world_image, 21),
        )
        GENERATOR.write(
            str(task_dir / "environment" / "Dockerfile"),
            GENERATOR.AGENT_DOCKERFILE,
        )
        GENERATOR.write(
            str(task_dir / "environment" / "tool"),
            (ROOT / "harbor" / "agent-image" / "tool").read_text("utf-8"),
            executable=True,
        )
        GENERATOR.write(
            str(task_dir / "environment" / "docker-compose.yaml"),
            GENERATOR.compose_yaml(task["task_id"], self.world_image),
        )
        GENERATOR.write(
            str(task_dir / "tests" / "test.sh"),
            GENERATOR.test_sh(task),
            executable=True,
        )
        GENERATOR.write(
            str(task_dir / "solution" / "solve.sh"),
            GENERATOR.solve_sh(self.token, task),
            executable=True,
        )
        return task

    def test_task_audit_rejects_unpublished_or_tampered_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harbor-export-integrity-") as temporary:
            task_dir = Path(temporary) / "task_safe"
            task = self.write_task(task_dir)
            result = CHECKER.audit_task(
                task_dir,
                task,
                self.world_image,
                self.lab_image,
                self.token,
                21,
            )
            self.assertEqual(len(result[3]), 7)

            rogue = task_dir / ".gitignore"
            rogue.write_text("solution/\n", "utf-8")
            with self.assertRaisesRegex(RuntimeError, "task package topology differs"):
                CHECKER.audit_task(
                    task_dir,
                    task,
                    self.world_image,
                    self.lab_image,
                    self.token,
                    21,
                )
            rogue.unlink()

            test_script = task_dir / "tests" / "test.sh"
            test_script.write_text("#!/bin/sh\nexit 0\n", "utf-8")
            test_script.chmod(0o755)
            with self.assertRaisesRegex(RuntimeError, "generated text differs"):
                CHECKER.audit_task(
                    task_dir,
                    task,
                    self.world_image,
                    self.lab_image,
                    self.token,
                    21,
                )

    def test_tasks_root_rejects_non_task_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harbor-task-root-") as temporary:
            tasks_root = Path(temporary)
            good = tasks_root / "task_good"
            good.mkdir()
            (good / "task.toml").write_text("schema_version = '1.4'\n", "utf-8")
            (tasks_root / "rogue.txt").write_text("not a task\n", "utf-8")
            with self.assertRaisesRegex(RuntimeError, "non-task entries"):
                CHECKER.discover_task_directories(tasks_root)

    def test_world_image_audit_rejects_runtime_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harbor-world-context-") as temporary:
            root = Path(temporary)
            world_path = root / "mini-world.json"
            world = {"version": 21, "tasks": []}
            world_path.write_text(json.dumps(world), "utf-8")
            GENERATOR.assemble_world_image(
                str(root / "export"),
                str(world_path),
                str(ROOT / "mcp" / "v5" / "contracts"),
            )
            stale = root / "export" / "world-image" / "stale-secret.txt"
            stale.write_text("must not survive regeneration\n", "utf-8")
            GENERATOR.assemble_world_image(
                str(root / "export"),
                str(world_path),
                str(ROOT / "mcp" / "v5" / "contracts"),
            )
            self.assertFalse(stale.exists())
            token_path = root / "export" / "world-image" / "solve-token.txt"
            token_path.write_text(self.token + "\n", "utf-8")
            checked = CHECKER.audit_world_image_context(
                root / "export", world_path, world
            )
            self.assertGreater(checked, 10)

            server = root / "export" / "world-image" / "server.py"
            server.write_text("print('tampered')\n", "utf-8")
            with self.assertRaisesRegex(RuntimeError, "byte count differs|SHA-256 differs"):
                CHECKER.audit_world_image_context(root / "export", world_path, world)


if __name__ == "__main__":
    unittest.main()
