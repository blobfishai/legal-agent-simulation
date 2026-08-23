#!/usr/bin/env python3
"""Render and mechanically inspect every v21 DOCX, XLSX, and PDF fixture.

The structural seed checker deliberately does not invoke office renderers.  This
gate complements it by exercising LibreOffice and Poppler against every fixture,
checking every rendered page for expected pagination, extractable text, nonblank
pixels, sane geometry, and content that does not touch the raster boundary.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageDraw, ImageOps
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "research" / "v21-seeded-documents"
EXPECTED_PACKS = 117
EXPECTED_FILES = 351
EXPECTED_PAGES = {"docx": 117, "xlsx": 351, "pdf": 117}
CATALOG_CORPUS_PREFIX = PurePosixPath("research/v21-seeded-documents")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_binary(name: str, extra: tuple[str, ...] = ()) -> str:
    located = shutil.which(name)
    if located:
        return located
    for candidate in extra:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(f"required renderer is unavailable: {name}")


def _run(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    if result.returncode:
        rendered = " ".join(command)
        raise RuntimeError(
            f"command failed ({result.returncode}): {rendered}\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )
    return result


def _version(command: list[str]) -> str:
    result = _run(command, timeout=30)
    text = (result.stdout or result.stderr).strip().splitlines()
    return text[0] if text else "unknown"


def _convert_office(soffice: str, source: Path, output_dir: Path) -> Path:
    profile = output_dir / f"lo-profile-{source.suffix[1:]}"
    profile.mkdir(parents=True, exist_ok=True)
    result = _run(
        [
            soffice,
            "--headless",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(source),
        ],
    )
    target = output_dir / f"{source.stem}.pdf"
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(
            f"LibreOffice did not create {target}; stdout={result.stdout!r}; stderr={result.stderr!r}"
        )
    return target


def _render_pdf(pdftoppm: str, source: Path, output_dir: Path, prefix: str) -> list[Path]:
    output_prefix = output_dir / prefix
    _run([pdftoppm, "-png", "-r", "110", str(source), str(output_prefix)])
    pages = sorted(
        output_dir.glob(f"{prefix}-*.png"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    if not pages:
        raise RuntimeError(f"Poppler produced no PNG pages for {source}")
    return pages


def _page_metric(image_path: Path, *, page_text: str, identity: str, page_number: int) -> dict[str, Any]:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        gray = rgb.convert("L")
        histogram = gray.histogram()
        ink_pixels = sum(histogram[:246])
        ink_fraction = ink_pixels / float(width * height)
        top_histogram = gray.crop((0, 0, width, min(5, height))).histogram()
        bottom_histogram = gray.crop((0, max(0, height - 5), width, height)).histogram()
        top_nonwhite_fraction = sum(top_histogram[:246]) / float(width * min(5, height))
        bottom_nonwhite_fraction = sum(bottom_histogram[:246]) / float(width * min(5, height))
        intentional_full_bleed_header = (
            identity.endswith("/pdf")
            and top_nonwhite_fraction > 0.95
            and bottom_nonwhite_fraction < 0.05
        )
        mask = gray.point(lambda pixel: 255 if pixel < 246 else 0)
        bounds = mask.getbbox()
        if bounds is None:
            margins = [0, 0, 0, 0]
        else:
            left, top, right, bottom = bounds
            margins = [left, top, width - right, height - bottom]
        body_margins = margins
        if intentional_full_bleed_header:
            # The generated source extracts deliberately paint an edge-to-edge
            # 62-point banner. Inspect the body below a conservative 12% header
            # band so that the banner does not mask clipped body content.
            header_cutoff = max(5, min(height - 1, round(height * 0.12)))
            body_mask = gray.crop((0, header_cutoff, width, height)).point(
                lambda pixel: 255 if pixel < 246 else 0
            )
            body_bounds = body_mask.getbbox()
            if body_bounds is None:
                body_margins = [0, 0, 0, 0]
            else:
                left, top, right, bottom = body_bounds
                body_margins = [
                    left,
                    header_cutoff + top,
                    width - right,
                    height - (header_cutoff + bottom),
                ]

    failures: list[str] = []
    if width < 700 or height < 700:
        failures.append("implausibly_small_raster")
    if not 0.001 <= ink_fraction <= 0.80:
        failures.append("blank_or_saturated_page")
    unsafe_edge = min(body_margins) < 3
    if unsafe_edge:
        failures.append("content_touches_raster_edge")
    text_chars = len("".join(page_text.split()))
    if text_chars < 24:
        failures.append("insufficient_extractable_text")

    return {
        "id": identity,
        "page": page_number,
        "width_px": width,
        "height_px": height,
        "orientation": "landscape" if width > height else "portrait",
        "ink_fraction": round(ink_fraction, 6),
        "content_margins_px": margins,
        "body_content_margins_px": body_margins,
        "edge_treatment": "intentional_full_bleed_header" if intentional_full_bleed_header else "clear_margin",
        "extractable_text_chars": text_chars,
        "checks_passed": not failures,
        "failures": failures,
        "_image_path": str(image_path),
    }


def _inspect_pdf(
    pdftoppm: str,
    source: Path,
    output_dir: Path,
    *,
    identity: str,
    expected_pages: int,
) -> list[dict[str, Any]]:
    reader = PdfReader(str(source))
    if len(reader.pages) != expected_pages:
        raise AssertionError(f"{identity}: expected {expected_pages} PDF pages, found {len(reader.pages)}")
    rasters = _render_pdf(pdftoppm, source, output_dir, identity.replace("/", "__"))
    if len(rasters) != expected_pages:
        raise AssertionError(f"{identity}: expected {expected_pages} PNG pages, found {len(rasters)}")
    metrics = []
    for index, (page, raster) in enumerate(zip(reader.pages, rasters, strict=True), start=1):
        metrics.append(
            _page_metric(
                raster,
                page_text=page.extract_text() or "",
                identity=identity,
                page_number=index,
            )
        )
    return metrics


def _render_pack(
    pack: dict[str, Any],
    *,
    corpus_root: Path,
    render_root: Path,
    soffice: str,
    pdftoppm: str,
) -> list[dict[str, Any]]:
    pack_id = pack["pack_id"]
    if not pack_id or Path(pack_id).name != pack_id or pack_id in {".", ".."}:
        raise RuntimeError(f"unsafe pack identifier: {pack_id!r}")
    declared_source = PurePosixPath(str(pack.get("documents_source") or ""))
    try:
        relative_source = declared_source.relative_to(CATALOG_CORPUS_PREFIX)
    except ValueError as exc:
        raise RuntimeError(
            f"{pack_id}: documents_source is outside the canonical corpus: {declared_source}"
        ) from exc
    if (
        declared_source.is_absolute()
        or ".." in relative_source.parts
        or len(relative_source.parts) < 4
        or relative_source.parts[0] != "packs"
        or relative_source.parts[1] != pack["domain"]
        or relative_source.parts[-1] != "documents"
    ):
        raise RuntimeError(f"{pack_id}: unsafe or inconsistent documents_source: {declared_source}")
    source_dir = corpus_root.joinpath(*relative_source.parts)
    if not source_dir.resolve().is_relative_to(corpus_root.resolve()):
        raise RuntimeError(f"{pack_id}: document directory escapes the corpus root")
    cursor = corpus_root
    for component in relative_source.parts:
        cursor /= component
        if cursor.is_symlink():
            raise RuntimeError(f"{pack_id}: symlinked document path component: {cursor}")
    if not source_dir.is_dir():
        raise RuntimeError(f"{pack_id}: document directory is missing or symlinked: {source_dir}")
    expected_files = {
        row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]}
        for row in pack["files"]
    }
    if set(expected_files) != {"matter-brief.docx", "evidence-register.xlsx", "source-extract.pdf"}:
        raise RuntimeError(f"{pack_id}: unexpected catalog file inventory: {sorted(expected_files)}")
    actual_entries = {path.name for path in source_dir.iterdir()}
    if actual_entries != set(expected_files):
        raise RuntimeError(
            f"{pack_id}: source inventory drifted; missing={sorted(set(expected_files) - actual_entries)}, "
            f"unexpected={sorted(actual_entries - set(expected_files))}"
        )
    for name, expected in expected_files.items():
        source = source_dir / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"{pack_id}: source is missing or symlinked: {name}")
        if source.stat().st_size != expected["bytes"] or _sha256(source) != expected["sha256"]:
            raise RuntimeError(f"{pack_id}: source bytes do not match the catalog: {name}")
    pack_out = render_root / pack_id
    pack_out.mkdir(parents=True, exist_ok=True)

    docx_pdf = _convert_office(soffice, source_dir / "matter-brief.docx", pack_out)
    xlsx_pdf = _convert_office(soffice, source_dir / "evidence-register.xlsx", pack_out)
    direct_pdf = source_dir / "source-extract.pdf"

    metrics: list[dict[str, Any]] = []
    metrics.extend(
        _inspect_pdf(
            pdftoppm,
            docx_pdf,
            pack_out,
            identity=f"{pack_id}/docx",
            expected_pages=1,
        )
    )
    metrics.extend(
        _inspect_pdf(
            pdftoppm,
            xlsx_pdf,
            pack_out,
            identity=f"{pack_id}/xlsx",
            expected_pages=3,
        )
    )
    metrics.extend(
        _inspect_pdf(
            pdftoppm,
            direct_pdf,
            pack_out,
            identity=f"{pack_id}/pdf",
            expected_pages=1,
        )
    )
    return metrics


def _contact_sheets(metrics: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    sheet_dir = output_dir / "contact-sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    columns, rows = 4, 4
    cell_width, cell_height, label_height = 520, 700, 34
    chunk_size = columns * rows
    sheets: list[Path] = []
    ordered = sorted(metrics, key=lambda row: (row["id"], row["page"]))
    for chunk_index in range(0, len(ordered), chunk_size):
        chunk = ordered[chunk_index : chunk_index + chunk_size]
        canvas = Image.new("RGB", (columns * cell_width, rows * (cell_height + label_height)), "white")
        draw = ImageDraw.Draw(canvas)
        for index, record in enumerate(chunk):
            x = (index % columns) * cell_width
            y = (index // columns) * (cell_height + label_height)
            with Image.open(record["_image_path"]) as page:
                thumb = ImageOps.contain(page.convert("RGB"), (cell_width - 16, cell_height - 16))
            paste_x = x + (cell_width - thumb.width) // 2
            paste_y = y + 8
            canvas.paste(thumb, (paste_x, paste_y))
            draw.rectangle((x, y, x + cell_width - 1, y + cell_height + label_height - 1), outline="#777777")
            draw.text((x + 8, y + cell_height + 7), f"{record['id']} p{record['page']}", fill="black")
        sheet = sheet_dir / f"contact-{len(sheets) + 1:03d}.png"
        canvas.save(sheet, format="PNG", optimize=True)
        sheets.append(sheet)
    return sheets


def _public_metric(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--keep-renders", action="store_true")
    parser.add_argument("--no-contact-sheets", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    corpus_root = args.root.resolve()
    catalog_path = corpus_root / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    packs = catalog["packs"]
    if catalog.get("schema_version") != 2:
        raise RuntimeError("unsupported v21 document catalog schema")
    if len(packs) != EXPECTED_PACKS:
        raise RuntimeError(f"expected {EXPECTED_PACKS} packs, found {len(packs)}")
    if len({pack.get("pack_id") for pack in packs}) != EXPECTED_PACKS:
        raise RuntimeError("v21 document pack identifiers must be unique")
    catalog_files = sum(len(pack.get("files") or []) for pack in packs)
    if catalog_files != EXPECTED_FILES:
        raise RuntimeError(f"expected {EXPECTED_FILES} catalog files, found {catalog_files}")

    soffice = _find_binary(
        "soffice",
        (
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/usr/bin/libreoffice",
        ),
    )
    pdftoppm = _find_binary("pdftoppm")

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if args.output_dir:
        render_root = args.output_dir.resolve()
        render_root.mkdir(parents=True, exist_ok=True)
    else:
        temporary = tempfile.TemporaryDirectory(prefix="v21-document-render-audit-")
        render_root = Path(temporary.name)

    metrics: list[dict[str, Any]] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                _render_pack,
                pack,
                corpus_root=corpus_root,
                render_root=render_root,
                soffice=soffice,
                pdftoppm=pdftoppm,
            ): pack["pack_id"]
            for pack in packs
        }
        for future in concurrent.futures.as_completed(futures):
            pack_id = futures[future]
            try:
                metrics.extend(future.result())
            except Exception as exc:  # aggregate failures so one bad pack does not hide later defects
                errors.append(f"{pack_id}: {exc}")

    if errors:
        if temporary is not None:
            temporary.cleanup()
        raise RuntimeError("document render failures:\n" + "\n".join(sorted(errors)))

    metrics.sort(key=lambda row: (row["id"], row["page"]))
    counts = {kind: sum(f"/{kind}" in row["id"] for row in metrics) for kind in EXPECTED_PAGES}
    if counts != EXPECTED_PAGES:
        raise RuntimeError(f"rendered page counts drifted: actual={counts}, expected={EXPECTED_PAGES}")
    failures = [row for row in metrics if not row["checks_passed"]]
    if failures:
        details = "; ".join(f"{row['id']} p{row['page']}: {','.join(row['failures'])}" for row in failures)
        raise AssertionError(f"{len(failures)} rendered pages failed: {details}")

    sheets = [] if args.no_contact_sheets else _contact_sheets(metrics, render_root)
    report = {
        "schema_version": 1,
        "catalog_sha256": _sha256(catalog_path),
        "packs": len(packs),
        "source_files": EXPECTED_FILES,
        "catalog_file_bytes_and_hashes_verified": True,
        "symlinked_sources": 0,
        "rendered_pages": counts,
        "total_rendered_pages": len(metrics),
        "automated_checks": {
            "expected_pagination": True,
            "extractable_text": True,
            "nonblank_rasters": True,
            "sane_page_geometry": True,
            "safe_edge_treatment": True,
            "all_passed": True,
        },
        "renderer_versions": {
            "libreoffice": _version([soffice, "--version"]),
            "poppler": _version([pdftoppm, "-v"]),
        },
        "contact_sheets_generated": len(sheets),
        "contact_sheet_visual_review": "pending",
        "page_metrics": [_public_metric(row) for row in metrics],
    }
    if args.report:
        report_path = args.report.resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "packs": len(packs),
                "source_files": EXPECTED_FILES,
                "rendered_pages": counts,
                "total_rendered_pages": len(metrics),
                "contact_sheets": len(sheets),
                "all_passed": True,
            },
            sort_keys=True,
        )
    )
    if args.keep_renders:
        print(f"render evidence retained at {render_root}")
        temporary = None
    if temporary is not None:
        temporary.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
