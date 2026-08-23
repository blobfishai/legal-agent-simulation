from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PREFIXES = ("tools/", "world/", "harbor/", "research/")


def production_python_files() -> list[Path]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "*.py"], cwd=ROOT
    ).split(b"\0")
    paths = []
    for raw in tracked:
        if not raw:
            continue
        relative = raw.decode()
        if not relative.startswith(SOURCE_PREFIXES):
            continue
        if "/tests/" in relative or relative.startswith("research/repos/"):
            continue
        paths.append(ROOT / relative)
    return paths


class AssertionGuardTests(unittest.TestCase):
    def test_every_production_assert_is_guarded_against_python_optimization(self) -> None:
        assertion_count = 0
        unguarded = []
        for path in production_python_files():
            tree = ast.parse(path.read_text("utf-8"), filename=str(path))
            count = sum(isinstance(node, ast.Assert) for node in ast.walk(tree))
            if not count:
                continue
            assertion_count += count
            has_guard = any(
                isinstance(node, ast.If)
                and ast.unparse(node.test) == "not __debug__"
                for node in tree.body
            )
            if not has_guard:
                unguarded.append(path.relative_to(ROOT).as_posix())
        self.assertGreaterEqual(assertion_count, 600)
        self.assertEqual(unguarded, [])

    def test_optimized_checker_fails_before_skipping_assertions(self) -> None:
        result = subprocess.run(
            [sys.executable, "-O", "tools/check_ch_fts.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python optimization is unsupported", result.stderr)


if __name__ == "__main__":
    unittest.main()
