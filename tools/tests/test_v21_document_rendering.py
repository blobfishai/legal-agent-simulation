from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
import unittest

from PIL import Image, ImageDraw

from tools.check_v21_document_rendering import _page_metric, _render_pack


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


if __name__ == "__main__":
    unittest.main()
