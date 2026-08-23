from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCKS = ROOT / "research" / "repos-commits.json"
HYDRATOR = ROOT / "research" / "clone-repos.sh"
MANIFEST = ROOT / "research" / "repos-manifest.tsv"

REQUIRED_MIRRORS = {
    "harbor-framework@harbor": {
        "category": "framework",
        "repo": "harbor-framework/harbor",
        "commit": "b37833221e27435a18d7acdd41d875cdc2831893",
    },
    "harveyai@harvey-labs": {
        "category": "eval",
        "repo": "harveyai/harvey-labs",
        "commit": "7be41d57fd5a6e97b5f246a029e810f83d09cd96",
    },
}


class RepositoryHydrationTests(unittest.TestCase):
    def test_required_mirrors_are_locked_and_recorded(self) -> None:
        locks = json.loads(LOCKS.read_text("utf-8"))
        with MANIFEST.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))

        for key, expected in REQUIRED_MIRRORS.items():
            with self.subTest(repository=expected["repo"]):
                lock = locks.get(key)
                self.assertEqual(lock, expected["commit"][:12])
                matching_rows = [row for row in rows if row["repo"] == expected["repo"]]
                self.assertEqual(len(matching_rows), 1)
                row = matching_rows[0]
                self.assertEqual(row["status"], "OK")
                self.assertEqual(row["category"], expected["category"])
                self.assertTrue(row["size"])
                self.assertEqual(row["note"], f"present@{lock}")

    def test_hydrator_persists_exact_pinned_provenance(self) -> None:
        script = HYDRATOR.read_text("utf-8")
        lines = script.splitlines()
        for expected in REQUIRED_MIRRORS.values():
            command = f'clone {expected["category"]} {expected["repo"]}'
            with self.subTest(repository=expected["repo"]):
                self.assertEqual(lines.count(command), 1)

        self.assertIn(
            'git -C "$dir" update-ref refs/remotes/origin/pinned "$actual"',
            script,
        )
        self.assertIn('"$resolved:refs/remotes/origin/pinned"', script)
        self.assertIn(
            "git -C \"$dir\" checkout --detach --quiet refs/remotes/origin/pinned",
            script,
        )
        self.assertNotIn("checkout --detach --quiet FETCH_HEAD", script)


if __name__ == "__main__":
    unittest.main()
