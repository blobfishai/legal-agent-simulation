from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "check_ghcr_public.py"
SPEC = importlib.util.spec_from_file_location("check_ghcr_public", SCRIPT)
assert SPEC and SPEC.loader
PUBLIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLIC)


class GhcrPublicTests(unittest.TestCase):
    digest = "sha256:" + "ab" * 32
    image = "ghcr.io/blobfishai/example@" + digest

    def test_parse_requires_an_immutable_lowercase_ghcr_reference(self) -> None:
        self.assertEqual(
            PUBLIC.parse_reference(self.image), ("blobfishai/example", self.digest)
        )
        for invalid in (
            "ghcr.io/blobfishai/example:v21",
            "docker.io/blobfishai/example@" + self.digest,
            "ghcr.io/BlobfishAI/example@" + self.digest,
            "ghcr.io/blobfishai/example@sha256:" + "AB" * 32,
        ):
            with self.assertRaises(ValueError):
                PUBLIC.parse_reference(invalid)

    def test_anonymous_manifest_requires_the_exact_digest(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            if "--head" not in command:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps({"token": "public-token"})
                    + "\nGHCR_TOKEN_HTTP_STATUS:200\n",
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                f"Docker-Content-Digest: {self.digest}\r\n\r\nGHCR_HTTP_STATUS:200\n",
                "",
            )

        self.assertEqual(
            PUBLIC.anonymous_manifest_digest(self.image, runner, "/usr/bin/curl"),
            self.digest,
        )
        self.assertNotIn("public-token", calls[0][0])
        self.assertIn("Authorization: Bearer public-token", calls[1][0])

    def test_digest_mismatch_fails_closed(self) -> None:
        def runner(command, **_kwargs):
            if "--head" not in command:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    '{"token":"public-token"}\nGHCR_TOKEN_HTTP_STATUS:200\n',
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                "Docker-Content-Digest: sha256:"
                + "cd" * 32
                + "\r\n\r\nGHCR_HTTP_STATUS:200\n",
                "",
            )

        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            PUBLIC.anonymous_manifest_digest(self.image, runner, "/usr/bin/curl")

    def test_private_manifest_reports_only_repository_and_status(self) -> None:
        def runner(command, **_kwargs):
            if "--head" not in command:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    '{"token":"public-token"}\nGHCR_TOKEN_HTTP_STATUS:200\n',
                    "",
                )
            return subprocess.CompletedProcess(
                command, 0, "HTTP/2 401\r\n\r\nGHCR_HTTP_STATUS:401\n", ""
            )

        with self.assertRaisesRegex(
            RuntimeError, "HTTP 401 for blobfishai/example"
        ) as raised:
            PUBLIC.anonymous_manifest_digest(self.image, runner, "/usr/bin/curl")
        self.assertNotIn("public-token", str(raised.exception))

    def test_main_audits_every_image_and_writes_failure_report(self) -> None:
        second_digest = "sha256:" + "cd" * 32
        second_image = "ghcr.io/blobfishai/second@" + second_digest
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "public.json"
            with (
                mock.patch.object(
                    PUBLIC,
                    "anonymous_manifest_digest",
                    side_effect=[RuntimeError("anonymous pull failed"), second_digest],
                ) as checker,
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        str(SCRIPT),
                        "--report", str(report_path),
                        self.image,
                        second_image,
                    ],
                ),
            ):
                result = PUBLIC.main()
            report = json.loads(report_path.read_text("utf-8"))
        self.assertEqual(result, 1)
        self.assertEqual(checker.call_count, 2)
        self.assertEqual(report["images_checked"], 2)
        self.assertEqual(report["public_images"], 1)
        self.assertFalse(report["all_public"])
        self.assertEqual(
            [row["anonymous_pull"] for row in report["results"]], [False, True]
        )


if __name__ == "__main__":
    unittest.main()
