#!/usr/bin/env python3
"""Validate the committed M2 pagination and HTTP-error golden fixtures."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "world" / "local"))

from wire_errors import friction_http  # noqa: E402
from product_workflows import LEDES_1998B_FIELDS  # noqa: E402


def descend(value, path: str):
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise AssertionError(f"missing JSON path {path}")
        value = value[key]
    return value


def main() -> int:
    errors = json.loads((HERE / "http-errors.json").read_text())
    pagination = json.loads((HERE / "pagination.json").read_text())
    ledes = json.loads((HERE / "ledes-1998b.json").read_text())
    checked = 0
    for dialect, cases in errors["cases"].items():
        for signature, expected in cases.items():
            status, body, headers = friction_http(signature, dialect)
            assert status == expected["status"], (dialect, signature, status)
            for header in expected.get("required_headers", []):
                assert headers.get(header), (dialect, signature, header)
            for path in expected["required_json_paths"]:
                descend(body, path)
            assert "simulator_signature" not in body
            checked += 1
    assert set(pagination["dialects"]) == {
        "clio", "courtlistener", "google", "relativity", "imanage",
    }
    assert ledes["identifier"] == "LEDES1998B[]"
    assert tuple(ledes["fields"]) == LEDES_1998B_FIELDS
    assert len(ledes["fields"]) == 24
    print(f"conformance fixtures: {checked} HTTP errors + 5 pagination dialects + LEDES 24-field contract clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
