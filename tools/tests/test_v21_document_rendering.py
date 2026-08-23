from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from tools.check_v21_document_rendering import _convert_office, _page_metric, _render_pack, main


ROOT = Path(__file__).resolve().parents[2]


class V21DocumentRenderingTests(unittest.TestCase):
    def _page(self, path: Path, *, clipped_body: bool) -> None:
        image = Image.new("RGB", (935, 1210), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 934, 95), fill="#17365D")
        draw.rectangle((72, 180, 862, 230), fill="#222222")
        if clipped_body:
            draw.rectangle((0, 260, 8, 360), fill="#222222")
        image.save(path)

    def test_full_bleed_header_keeps_body_edge_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image_path = Path(temporary) / "page.png"
            self._page(image_path, clipped_body=False)
            metric = _page_metric(
                image_path,
                page_text="Sufficient extractable synthetic text for deterministic inspection.",
                identity="pack-test/pdf",
                page_number=1,
            )
        self.assertEqual(metric["edge_treatment"], "intentional_full_bleed_header")
        self.assertTrue(metric["checks_passed"])
        self.assertGreaterEqual(min(metric["body_content_margins_px"]), 3)

    def test_full_bleed_header_does_not_hide_clipped_body(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image_path = Path(temporary) / "page.png"
            self._page(image_path, clipped_body=True)
            metric = _page_metric(
                image_path,
                page_text="Sufficient extractable synthetic text for deterministic inspection.",
                identity="pack-test/pdf",
                page_number=1,
            )
        self.assertFalse(metric["checks_passed"])
        self.assertIn("content_touches_raster_edge", metric["failures"])

    def test_render_pack_rejects_catalog_hash_substitution_before_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary)
            documents = corpus / "packs" / "test" / "variant-01" / "documents"
            documents.mkdir(parents=True)
            files = []
            for name in ("matter-brief.docx", "evidence-register.xlsx", "source-extract.pdf"):
                path = documents / name
                path.write_bytes(f"synthetic {name}".encode())
                files.append({
                    "path": name,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
            files[0]["sha256"] = "0" * 64
            pack = {
                "pack_id": "pack-test-01",
                "domain": "test",
                "variant": 1,
                "documents_source": (
                    "research/v21-seeded-documents/packs/test/variant-01/documents"
                ),
                "files": files,
            }
            with self.assertRaisesRegex(RuntimeError, "source bytes do not match the catalog"):
                _render_pack(
                    pack,
                    corpus_root=corpus,
                    render_root=corpus / "renders",
                    soffice="must-not-run",
                    pdftoppm="must-not-run",
                )

    def test_render_pack_rejects_catalog_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary)
            pack = {
                "pack_id": "pack-test-01",
                "domain": "test",
                "variant": 1,
                "documents_source": "research/v21-seeded-documents/../outside/documents",
                "files": [],
            }
            with self.assertRaisesRegex(RuntimeError, "unsafe or inconsistent documents_source"):
                _render_pack(
                    pack,
                    corpus_root=corpus,
                    render_root=corpus / "renders",
                    soffice="must-not-run",
                    pdftoppm="must-not-run",
                )

    def test_office_conversion_retries_with_a_fresh_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "matter-brief.docx"
            source.write_bytes(b"synthetic docx")
            calls = 0

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RuntimeError("transient LibreOffice process abort")
                (root / "matter-brief.pdf").write_bytes(b"%PDF-1.4\n")
                return subprocess.CompletedProcess(command, 0, stdout="converted", stderr="")

            with mock.patch("tools.check_v21_document_rendering._run", side_effect=fake_run) as runner:
                target = _convert_office("soffice", source, root)

            self.assertEqual(target.read_bytes(), b"%PDF-1.4\n")
            self.assertEqual(runner.call_count, 2)
            first = runner.call_args_list[0].args[0]
            second = runner.call_args_list[1].args[0]
            self.assertIn("lo-profile-docx-attempt-1", first[2])
            self.assertIn("lo-profile-docx-attempt-2", second[2])

    def test_office_conversion_rejects_stale_output_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "matter-brief.docx"
            source.write_bytes(b"synthetic docx")
            target = root / "matter-brief.pdf"
            target.write_bytes(b"stale prior output")

            with mock.patch(
                "tools.check_v21_document_rendering._run",
                side_effect=RuntimeError("persistent conversion failure"),
            ) as runner:
                with self.assertRaisesRegex(RuntimeError, "failed after 2 isolated attempts"):
                    _convert_office("soffice", source, root)

            self.assertEqual(runner.call_count, 2)
            self.assertFalse(target.exists())

    def test_keep_renders_requires_an_explicit_output_directory(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with mock.patch.object(sys, "argv", ["check_v21_document_rendering.py", "--keep-renders"]):
                with self.assertRaises(SystemExit) as raised:
                    main()
        self.assertEqual(raised.exception.code, 2)

    def test_default_npm_render_check_cannot_overwrite_attested_report(self) -> None:
        scripts = json.loads((ROOT / "package.json").read_text())["scripts"]
        command = scripts["v21:document-render-check"]
        self.assertIn("--no-contact-sheets", command)
        self.assertNotIn("--report", command)


if __name__ == "__main__":
    unittest.main()
