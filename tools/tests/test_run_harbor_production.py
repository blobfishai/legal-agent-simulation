from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "run_harbor_production.py"
SPEC = importlib.util.spec_from_file_location("run_harbor_production", SCRIPT)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class RunHarborProductionTests(unittest.TestCase):
    image = "ghcr.io/blobfishai/legal-agent-sim-world@sha256:" + "ab" * 32

    def test_remote_inspection_failure_has_a_distinct_exception(self) -> None:
        failed = subprocess.CalledProcessError(1, ["docker", "buildx"])
        with (
            mock.patch.object(RUNNER.shutil, "which", return_value="/usr/bin/docker"),
            mock.patch.object(RUNNER.subprocess, "run", side_effect=failed),
            self.assertRaisesRegex(
                RUNNER.ImageInspectionUnavailable,
                "cannot inspect immutable production image",
            ),
        ):
            RUNNER.image_environment(self.image)

    def test_oracle_report_preserves_the_failure_class(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "world-image").mkdir()
            (output / "world-image" / "solve-token.txt").write_text(
                "a" * 64 + "\n", "utf-8"
            )
            report_path = output / "oracle-report.json"
            with mock.patch.object(RUNNER, "ORACLE_PROOF_REPORT", report_path):
                RUNNER.write_oracle_proof_report(
                    self.image,
                    output,
                    image_proof_sha256=None,
                    failure_class="remote_image_inspection_unavailable",
                    error="cannot inspect immutable production image",
                )
            report = json.loads(report_path.read_text("utf-8"))
        self.assertFalse(report["matched"])
        self.assertEqual(
            report["runner_sha256"], RUNNER.hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        )
        self.assertEqual(
            report["failure_class"], "remote_image_inspection_unavailable"
        )
        self.assertIsNone(report["image_oracle_proof_sha256"])

    def test_report_derives_match_from_the_observed_image_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "world-image").mkdir()
            (output / "world-image" / "solve-token.txt").write_text(
                "c" * 64 + "\n", "utf-8"
            )
            expected = RUNNER.hashlib.sha256(("c" * 64).encode()).hexdigest()
            report_path = output / "oracle-report.json"
            with mock.patch.object(RUNNER, "ORACLE_PROOF_REPORT", report_path):
                RUNNER.write_oracle_proof_report(
                    self.image,
                    output,
                    image_proof_sha256=expected,
                    failure_class="oracle_integrity_failure",
                    error="caller tried to forge a failure",
                )
            report = json.loads(report_path.read_text("utf-8"))
        self.assertTrue(report["matched"])
        self.assertEqual(report["image_oracle_proof_sha256"], expected)
        self.assertIsNone(report["failure_class"])
        self.assertIsNone(report["error"])

    def test_mismatched_observed_proof_cannot_be_reported_as_matched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "world-image").mkdir()
            (output / "world-image" / "solve-token.txt").write_text(
                "d" * 64 + "\n", "utf-8"
            )
            actual = "e" * 64
            report_path = output / "oracle-report.json"
            with mock.patch.object(RUNNER, "ORACLE_PROOF_REPORT", report_path):
                RUNNER.write_oracle_proof_report(
                    self.image,
                    output,
                    image_proof_sha256=actual,
                    failure_class=None,
                    error=None,
                )
            report = json.loads(report_path.read_text("utf-8"))
        self.assertFalse(report["matched"])
        self.assertEqual(report["image_oracle_proof_sha256"], actual)
        self.assertEqual(report["failure_class"], "oracle_integrity_failure")

    def test_integrity_failure_is_not_classified_as_registry_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "world-image").mkdir()
            (output / "world-image" / "solve-token.txt").write_text(
                "b" * 64 + "\n", "utf-8"
            )
            report_path = output / "oracle-report.json"
            with (
                mock.patch.object(RUNNER, "ORACLE_PROOF_REPORT", report_path),
                mock.patch.object(
                    RUNNER,
                    "verify_oracle_proof",
                    side_effect=RuntimeError("oracle proof mismatch"),
                ),
            ):
                matched = RUNNER.audit_oracle_proof(self.image, output)
            report = json.loads(report_path.read_text("utf-8"))
        self.assertFalse(matched)
        self.assertEqual(report["failure_class"], "oracle_integrity_failure")
        self.assertEqual(report["error"], "oracle proof mismatch")


if __name__ == "__main__":
    unittest.main()
