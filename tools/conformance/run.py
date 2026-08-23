#!/usr/bin/env python3
"""Validate the mirrored-tool conformance registry and publish its honest status.

This is intentionally fail-closed about registry integrity and target resolution. It
does not call a tool "exact" merely because its declared endpoint exists: exactness
also requires validated wire inputs, success responses, pagination, and error shapes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "mcp" / "v3" / "contracts"
REGISTRY_PATH = ROOT / "tools" / "conformance" / "registry.json"
SPEC_DIR = ROOT / "tools" / "conformance" / "specs"
SPEC_MANIFEST_PATH = SPEC_DIR / "manifest.json"
REPORT_PATH = ROOT / "data" / "conformance.json"
DOC_PATH = ROOT / "docs" / "CONFORMANCE.md"
WIRE_REPORT_PATH = ROOT / "data" / "conformance-wire.json"
BEHAVIOR_REPORT_PATH = ROOT / "data" / "conformance-behavior.json"
COURTLISTENER_REPORT_PATH = ROOT / "data" / "conformance-courtlistener.json"
FIXTURE_DIR = ROOT / "tools" / "conformance" / "fixtures"

ROW_LENGTHS = {
    "openapi": 4,
    "swagger": 3,
    "google_discovery": 3,
    "live_diff": 4,
    "imanage_connector": 3,
    "partner_gated": 3,
    "documentation_fixture": 3,
    "published_standard": 3,
    "derived": 3,
    "simulator_extension": 3,
}

VENDOR_MODES = {
    "openapi",
    "swagger",
    "google_discovery",
    "live_diff",
    "imanage_connector",
    "partner_gated",
    "documentation_fixture",
    "published_standard",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def contract_tools() -> tuple[dict[str, dict[str, Any]], list[str]]:
    tools: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for path in sorted(CONTRACT_DIR.glob("*.json")):
        document = load_json(path)
        for tool in document.get("tools", []):
            if tool.get("agent_visible") is False:
                continue
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                failures.append(f"{path.name}: tool without a non-empty name")
                continue
            if name in tools:
                failures.append(f"duplicate contract tool name: {name}")
                continue
            tools[name] = {
                "contract": path.name,
                "dialect": document.get("dialect"),
                "mirror": tool.get("mirrors"),
                "params": tool.get("params", {}),
            }
    return tools, failures


def flatten_registry(registry: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    rows: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    products = registry.get("products", {})
    groups = registry.get("tools", {})
    if set(groups) != set(ROW_LENGTHS):
        failures.append(
            "registry mode set drift: "
            f"missing={sorted(set(ROW_LENGTHS) - set(groups))} "
            f"unknown={sorted(set(groups) - set(ROW_LENGTHS))}"
        )
    for mode, expected_length in ROW_LENGTHS.items():
        values = groups.get(mode, [])
        if not isinstance(values, list):
            failures.append(f"registry tools.{mode} must be an array")
            continue
        for index, value in enumerate(values):
            if not isinstance(value, list) or len(value) != expected_length:
                failures.append(f"registry tools.{mode}[{index}] must have {expected_length} fields")
                continue
            name, product, *target = value
            if name in rows:
                failures.append(f"duplicate registry tool name: {name}")
                continue
            if product not in products:
                failures.append(f"{name}: unknown product {product}")
            rows[name] = {"mode": mode, "product": product, "target": target}
    return rows, failures


def source_documents(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    documents: dict[str, Any] = {}
    failures: list[str] = []
    for name, entry in manifest.get("sources", {}).items():
        path = SPEC_DIR / entry.get("filename", "")
        if not path.is_file():
            failures.append(f"{name}: missing spec snapshot {path.relative_to(ROOT)}")
            continue
        compressed = path.read_bytes()
        if hashlib.sha256(compressed).hexdigest() != entry.get("sha256_gzip"):
            failures.append(f"{name}: spec snapshot checksum mismatch")
            continue
        try:
            documents[name] = load_gzip_json(path)
        except Exception as exc:
            failures.append(f"{name}: cannot parse spec snapshot: {exc}")
    return documents, failures


def google_methods(document: Any) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            method_id = value.get("id")
            if isinstance(method_id, str) and value.get("httpMethod") and value.get("path"):
                found[method_id] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    return found


def swagger_operations(document: dict[str, Any]) -> dict[str, tuple[str, str, dict[str, Any]]]:
    operations: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for path, path_item in document.get("paths", {}).items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id:
                operations[operation_id] = (method.lower(), path, operation)
    return operations


def operation_parameters(operation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["name"]: item
        for item in operation.get("parameters", [])
        if isinstance(item, dict) and item.get("in") != "header" and isinstance(item.get("name"), str)
    }


def body_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None
    content = request_body.get("content")
    if not isinstance(content, dict):
        return None
    for media_type in ("application/json", "application/*+json"):
        media = content.get(media_type)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"]
    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"]
    return None


def contract_param_names(tool: dict[str, Any]) -> set[str]:
    params = tool.get("params")
    return set(params) if isinstance(params, dict) else set()


def analyze_direct_input(
    tool: dict[str, Any], direct: dict[str, dict[str, Any]], has_body: bool
) -> dict[str, Any]:
    contract_names = contract_param_names(tool)
    direct_names = set(direct)
    wire_names = direct_names | ({"body"} if has_body else set())
    adapter_only = sorted(contract_names - wire_names)
    missing_required = sorted(
        name for name, value in direct.items() if value.get("required") and name not in contract_names
    )
    if has_body:
        request_shape = "wire-body" if "body" in contract_names else "flattened-adapter"
    elif adapter_only:
        request_shape = "renamed-or-simulator-parameter"
    else:
        request_shape = "direct-parameter-subset"
    return {
        "adapter_only_params": adapter_only,
        "missing_required_wire_params": missing_required,
        "request_shape": request_shape,
        "wire_input_exact": not adapter_only and not missing_required and (not has_body or "body" in contract_names),
    }


def base_tool_result(name: str, contract: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract": contract["contract"],
        "dialect": contract["dialect"],
        "exact": False,
        "mirror": contract["mirror"],
        "mode": row["mode"],
        "name": name,
        "product": row["product"],
        "registry_covered": True,
        "target": row["target"],
    }


def validate_tool(
    name: str,
    contract: dict[str, Any],
    row: dict[str, Any],
    products: dict[str, Any],
    specs: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    result = base_tool_result(name, contract, row)
    failures: list[str] = []
    mode = row["mode"]
    product = products.get(row["product"], {})
    target = row["target"]

    if not isinstance(contract.get("mirror"), str) or not contract["mirror"].strip():
        failures.append(f"{name}: contract has no mirrors citation")

    if mode == "openapi":
        method, path = target
        document = specs.get(product.get("source"))
        operation = document.get("paths", {}).get(path, {}).get(method) if isinstance(document, dict) else None
        if not isinstance(operation, dict):
            failures.append(f"{name}: unresolved OpenAPI operation {method.upper()} {path}")
            result["status"] = "target-unresolved"
            return result, failures
        direct = operation_parameters(operation)
        request_body = body_schema(operation)
        result.update(analyze_direct_input(contract, direct, request_body is not None))
        result.update(
            {
                "operation_id": operation.get("operationId"),
                "status": "spec-mapped-not-conformant",
                "target_resolved": True,
                "success_response_validated": False,
                "pagination_validated": False,
                "errors_validated": False,
            }
        )
    elif mode == "swagger":
        (operation_id,) = target
        document = specs.get(product.get("source"))
        operations = swagger_operations(document) if isinstance(document, dict) else {}
        operation = operations.get(operation_id)
        if not operation:
            failures.append(f"{name}: unresolved Swagger operation {operation_id}")
            result["status"] = "target-unresolved"
            return result, failures
        method, path, definition = operation
        direct = operation_parameters(definition)
        has_body = any(item.get("in") == "body" for item in definition.get("parameters", []))
        result.update(analyze_direct_input(contract, direct, has_body))
        result.update(
            {
                "http_method": method.upper(),
                "operation_id": operation_id,
                "path": path,
                "status": "spec-mapped-not-conformant",
                "target_resolved": True,
                "success_response_validated": False,
                "pagination_validated": False,
                "errors_validated": False,
            }
        )
    elif mode == "google_discovery":
        (method_id,) = target
        document = specs.get(product.get("source"))
        methods = google_methods(document) if document else {}
        operation = methods.get(method_id)
        if not operation:
            failures.append(f"{name}: unresolved Google discovery method {method_id}")
            result["status"] = "target-unresolved"
            return result, failures
        direct = {
            key: value
            for key, value in operation.get("parameters", {}).items()
            if isinstance(value, dict)
        }
        analysis = analyze_direct_input(contract, direct, bool(operation.get("request")))
        result.update(analysis)
        result.update(
            {
                "http_method": operation.get("httpMethod"),
                "operation_id": method_id,
                "path": operation.get("path"),
                "status": "spec-mapped-not-conformant",
                "target_resolved": True,
                "success_response_validated": False,
                "pagination_validated": False,
                "errors_validated": False,
            }
        )
    elif mode == "imanage_connector":
        (operation_id,) = target
        document = specs.get(product.get("source"))
        operations = swagger_operations(document) if isinstance(document, dict) else {}
        operation = operations.get(operation_id)
        if not operation:
            failures.append(f"{name}: unresolved iManage connector operation {operation_id}")
            result["status"] = "target-unresolved"
            return result, failures
        method, path, _ = operation
        result.update(
            {
                "connector_method": method.upper(),
                "connector_path": path,
                "status": "public-connector-mapped-fidelity-ceiling",
                "target_resolved": True,
                "ceiling": "The partner-gated Work API contract cannot be independently validated.",
            }
        )
    elif mode == "partner_gated":
        result.update(
            {
                "status": "unverifiable-partner-gated",
                "target_resolved": False,
                "ceiling": target[0],
            }
        )
    elif mode == "live_diff":
        method, path = target
        revision = product.get("source_revision")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            failures.append(f"{name}: live-diff source revision is not a full Git SHA")
        result.update(
            {
                "http_method": method.upper(),
                "path": path,
                "source_revision": revision,
                "status": "live-diff-required",
                "target_resolved": True,
            }
        )
    elif mode == "documentation_fixture":
        result.update({"fixture_id": target[0], "status": "golden-fixture-required", "target_resolved": True})
    elif mode == "published_standard":
        result.update({"fixture_id": target[0], "status": "standard-fixture-required", "target_resolved": True})
    elif mode == "derived":
        result.update({"derivation": target[0], "status": "derived-excluded-from-vendor-score"})
    elif mode == "simulator_extension":
        result.update({"reason": target[0], "status": "simulator-extension-gap"})
    else:
        failures.append(f"{name}: unsupported registry mode {mode}")
        result["status"] = "harness-error"
    return result, failures


def build_report() -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    registry = load_json(REGISTRY_PATH)
    manifest = load_json(SPEC_MANIFEST_PATH)
    contracts, contract_failures = contract_tools()
    rows, registry_failures = flatten_registry(registry)
    specs, spec_failures = source_documents(manifest)
    failures.extend(contract_failures)
    failures.extend(registry_failures)
    failures.extend(spec_failures)

    wire_by_name: dict[str, dict[str, Any]] = {}
    wire_summary = {"schema_applicable": 0, "schema_passed": 0,
                    "request_schema_applicable": 0, "request_schema_passed": 0,
                    "published_input_schema_applicable": 0,
                    "published_input_schema_passed": 0,
                    "success_calls": 0}
    if not WIRE_REPORT_PATH.is_file():
        failures.append(f"missing {WIRE_REPORT_PATH.relative_to(ROOT)}; run live.py --write")
    else:
        wire = load_json(WIRE_REPORT_PATH)
        if wire.get("specs_as_of") != manifest.get("as_of"):
            failures.append("wire report spec date differs from the registry spec date")
        wire_by_name = {item.get("name"): item for item in wire.get("tools", []) if item.get("name")}
        wire_summary = wire.get("summary", wire_summary)

    fixture_paths = [FIXTURE_DIR / "http-errors.json", FIXTURE_DIR / "pagination.json"]
    fixture_documents: dict[str, Any] = {}
    for path in fixture_paths:
        if not path.is_file():
            failures.append(f"missing conformance fixture {path.relative_to(ROOT)}")
            continue
        try:
            fixture_documents[path.stem] = load_json(path)
        except Exception as exc:
            failures.append(f"invalid conformance fixture {path.relative_to(ROOT)}: {exc}")
    error_dialects = set((fixture_documents.get("http-errors") or {}).get("cases", {}))
    pagination_dialects = set((fixture_documents.get("pagination") or {}).get("dialects", {}))
    behavior_by_name: dict[str, dict[str, Any]] = {}
    if not BEHAVIOR_REPORT_PATH.is_file():
        failures.append(f"missing {BEHAVIOR_REPORT_PATH.relative_to(ROOT)}; run behavior.py --write")
    else:
        behavior = load_json(BEHAVIOR_REPORT_PATH)
        behavior_by_name = {item["name"]: item for item in behavior.get("tools", [])}
    live_diff_by_name: dict[str, dict[str, Any]] = {}
    if not COURTLISTENER_REPORT_PATH.is_file():
        failures.append(
            f"missing {COURTLISTENER_REPORT_PATH.relative_to(ROOT)}; run cl_livediff.py --write"
        )
    else:
        live_diff = load_json(COURTLISTENER_REPORT_PATH)
        expected_revision = registry.get("products", {}).get("courtlistener-v4", {}).get("source_revision")
        if live_diff.get("courtlistener_revision") != expected_revision:
            failures.append("CourtListener live-diff revision differs from registry")
        live_diff_by_name = {
            item["name"]: item for item in live_diff.get("tools", []) if item.get("name")
        }

    contract_names = set(contracts)
    registry_names = set(rows)
    if contract_names != registry_names:
        failures.append(
            "registry coverage drift: "
            f"missing={sorted(contract_names - registry_names)} "
            f"unknown={sorted(registry_names - contract_names)}"
        )
    if set(wire_by_name) != contract_names:
        failures.append(
            "wire sample coverage drift: "
            f"missing={sorted(contract_names - set(wire_by_name))} "
            f"unknown={sorted(set(wire_by_name) - contract_names)}"
        )

    tool_results: list[dict[str, Any]] = []
    for name in sorted(contract_names & registry_names):
        result, tool_failures = validate_tool(
            name, contracts[name], rows[name], registry.get("products", {}), specs
        )
        wire_item = wire_by_name.get(name)
        if wire_item is None:
            failures.append(f"{name}: missing wire sample")
        else:
            schema = wire_item.get("schema") or {}
            result["sample_call_success"] = bool(wire_item.get("success_call"))
            request = wire_item.get("request") or {}
            result["request_schema_applicable"] = bool(request.get("applicable"))
            result["request_validated"] = bool(request.get("passed"))
            published = wire_item.get("published_input_schema") or {}
            result["published_input_schema_applicable"] = bool(published.get("applicable"))
            result["published_input_schema_validated"] = bool(published.get("passed"))
            if request.get("applicable") and not request.get("passed") and request.get("first_error"):
                result["request_first_error"] = request["first_error"]
            result["success_response_schema_applicable"] = bool(schema.get("applicable"))
            if schema.get("applicable"):
                result["success_response_validated"] = bool(schema.get("passed"))
                if not schema.get("passed") and schema.get("first_error"):
                    result["success_response_first_error"] = schema["first_error"]
        dialect = result.get("dialect")
        result["errors_validated"] = dialect in error_dialects
        operation = (load_json(CONTRACT_DIR / result["contract"]).get("tools") or [])
        op = next((item.get("op") or {} for item in operation if item.get("name") == name), {})
        paged = op.get("kind") in {"list", "search"}
        result["pagination_applicable"] = paged
        result["pagination_validated"] = (not paged) or dialect in pagination_dialects
        behavior_item = behavior_by_name.get(name)
        result["behavior_fixture_validated"] = bool(behavior_item and behavior_item.get("passed"))
        live_diff_item = live_diff_by_name.get(name)
        result["live_diff_validated"] = bool(live_diff_item and live_diff_item.get("passed"))
        result["exact"] = bool(
            result["mode"] in {"openapi", "swagger", "google_discovery"}
            and result.get("target_resolved")
            and result.get("wire_input_exact")
            and result.get("request_validated")
            and result.get("published_input_schema_validated")
            and result.get("success_response_validated")
            and result.get("pagination_validated")
            and result.get("errors_validated")
        )
        if result["exact"]:
            result["status"] = "exact-to-pinned-public-contract"
        if result["mode"] == "imanage_connector":
            result["verification_passed"] = bool(
                result.get("target_resolved")
                and result.get("sample_call_success")
                and result.get("request_validated")
                and result.get("published_input_schema_validated")
                and result.get("success_response_validated")
            )
            if result["verification_passed"]:
                result["status"] = "public-connector-conformant-fidelity-ceiling"
        elif result["mode"] == "live_diff":
            result["verification_passed"] = bool(
                result.get("target_resolved")
                and result.get("sample_call_success")
                and result.get("live_diff_validated")
                and result.get("pagination_validated")
                and result.get("errors_validated")
            )
            if result["verification_passed"]:
                result["status"] = "live-diff-conformant-to-pinned-source"
        elif result["mode"] in {"documentation_fixture", "published_standard"}:
            result["verification_passed"] = bool(
                result.get("target_resolved") and result.get("sample_call_success")
                and result.get("behavior_fixture_validated")
            )
            if result["verification_passed"]:
                result["status"] = (
                    "documentation-fixture-conformant" if result["mode"] == "documentation_fixture"
                    else "published-standard-conformant"
                )
        else:
            result["verification_passed"] = bool(result["exact"])
        tool_results.append(result)
        failures.extend(tool_failures)

    by_mode = Counter(item["mode"] for item in tool_results)
    by_product: dict[str, dict[str, int]] = defaultdict(lambda: {"exact": 0, "total": 0})
    for item in tool_results:
        by_product[item["product"]]["total"] += 1
        by_product[item["product"]]["exact"] += int(bool(item["exact"]))
    vendor_tools = [item for item in tool_results if item["mode"] in VENDOR_MODES]
    extensions = [item for item in tool_results if item["mode"] == "simulator_extension"]
    derived = [item for item in tool_results if item["mode"] == "derived"]
    resolved = [item for item in vendor_tools if item.get("target_resolved")]
    exact = [item for item in vendor_tools if item["exact"]]
    publicly_verifiable = [item for item in vendor_tools if item["mode"] != "partner_gated"]
    verified = [item for item in publicly_verifiable if item.get("verification_passed")]
    report = {
        "schema_version": 1,
        "specs_as_of": manifest.get("as_of"),
        "summary": {
            "contract_tools": len(contracts),
            "derived_tools_excluded": len(derived),
            "exact_vendor_tools": len(exact),
            "publicly_verifiable_vendor_tools": len(publicly_verifiable),
            "verification_passed_vendor_tools": len(verified),
            "harness_failures": len(failures),
            "registry_covered": len(contract_names & registry_names),
            "registry_total": len(registry_names),
            "response_schemas_applicable": int(wire_summary.get("schema_applicable", 0)),
            "response_schemas_passed": int(wire_summary.get("schema_passed", 0)),
            "request_schemas_applicable": int(wire_summary.get("request_schema_applicable", 0)),
            "request_schemas_passed": int(wire_summary.get("request_schema_passed", 0)),
            "published_input_schemas_applicable": int(wire_summary.get("published_input_schema_applicable", 0)),
            "published_input_schemas_passed": int(wire_summary.get("published_input_schema_passed", 0)),
            "sample_success_calls": int(wire_summary.get("success_calls", 0)),
            "simulator_extension_gaps": len(extensions),
            "vendor_targets_resolved": len(resolved),
            "vendor_tools": len(vendor_tools),
        },
        "by_mode": dict(sorted(by_mode.items())),
        "by_product": dict(sorted(by_product.items())),
        "failures": failures,
        "tools": tool_results,
    }
    return report, failures


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Tool conformance",
        "",
        "> **Scope:** this report measures the frozen v3 vendor-target baseline. The",
        "> canonical v21 world retains all 91 rows and adds 1,009 executable synthetic",
        "> legal-operations tools (19 RetailGuard and 990 CounselOps), for 1,100 visible",
        "> tools total. The added tools are covered by v21 execution and adversarial",
        "> verifier tests, not by the vendor-exactness score below. See",
        "> [the v21 release audit](V21-RELEASE-AUDIT.md).",
        "",
        f"Pinned specifications: **{report['specs_as_of']}**.",
        "",
        "> Endpoint mapping is not API exactness. A tool counts as exact only after its wire input, success response, pagination, and documented errors all validate. Derived helpers and simulator extensions are excluded from the vendor score.",
        "",
        "## Current result",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Contract tools covered by the registry | {summary['registry_covered']} / {summary['contract_tools']} |",
        f"| Vendor-targeted tools | {summary['vendor_tools']} |",
        f"| Vendor targets resolved to a pinned source | {summary['vendor_targets_resolved']} / {summary['vendor_tools']} |",
        f"| Deterministic success calls | {summary['sample_success_calls']} / {summary['contract_tools']} |",
        f"| Applicable request schemas passed | {summary['request_schemas_passed']} / {summary['request_schemas_applicable']} |",
        f"| Agent-visible MCP input schemas match pinned specs | {summary['published_input_schemas_passed']} / {summary['published_input_schemas_applicable']} |",
        f"| Applicable success-response schemas passed | {summary['response_schemas_passed']} / {summary['response_schemas_applicable']} |",
        f"| Fully exact vendor tools | {summary['exact_vendor_tools']} / {summary['vendor_tools']} |",
        f"| Passed best-public-contract verification | {summary['verification_passed_vendor_tools']} / {summary['publicly_verifiable_vendor_tools']} |",
        f"| Derived helpers (excluded) | {summary['derived_tools_excluded']} |",
        f"| Simulator-extension gaps | {summary['simulator_extension_gaps']} |",
        f"| Conformance-harness failures | {summary['harness_failures']} |",
        "",
        "Exactness is fail-closed and per tool. Only direct wire-parameter tools whose success response, pagination (when applicable), and vendor error fixtures pass against pinned public specifications count as exact. Flattened adapters, derived helpers, simulator extensions, partner-gated operations, and documentation-only mirrors remain explicitly outside that count.",
        "",
        "## Product coverage",
        "",
        "| Product | Tools | Exact | Verification state |",
        "| --- | ---: | ---: | --- |",
    ]
    product_statuses: dict[str, set[str]] = defaultdict(set)
    for item in report["tools"]:
        product_statuses[item["product"]].add(item["status"])
    for product, counts in report["by_product"].items():
        statuses = ", ".join(sorted(product_statuses[product]))
        lines.append(f"| `{product}` | {counts['total']} | {counts['exact']} | {statuses} |")

    lines.extend(
        [
            "",
            "## Tool rows",
            "",
            "| Tool | Product | Mode | Status | Target |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["tools"]:
        target = " · ".join(str(value) for value in item.get("target", []))
        target = target.replace("|", "\\|")
        lines.append(
            f"| `{item['name']}` | `{item['product']}` | `{item['mode']}` | `{item['status']}` | {target} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python3 tools/conformance/sync_specs.py --check",
            "python3 tools/conformance/live.py --base http://127.0.0.1:8974 --check",
            "python3 tools/conformance/run.py --check",
            "# The release gate requires every publicly verifiable contract and zero invented agent tools:",
            "python3 tools/conformance/run.py --strict",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def compare_file(path: Path, expected: str) -> str | None:
    if not path.is_file():
        return f"missing generated artifact {path.relative_to(ROOT)}; run --write"
    if path.read_text() != expected:
        return f"stale generated artifact {path.relative_to(ROOT)}; run --write"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="replace committed JSON and Markdown reports")
    mode.add_argument("--check", action="store_true", help="check registry and committed reports (default)")
    parser.add_argument("--strict", action="store_true", help="also require every vendor-targeted tool to be exact")
    args = parser.parse_args()

    report, failures = build_report()
    report_text = canonical_json(report)
    doc_text = render_markdown(report)
    required_scope_markers = (
        "frozen v3 vendor-target baseline",
        "1,100 visible",
        "not by the vendor-exactness score",
    )
    missing_scope_markers = [marker for marker in required_scope_markers if marker not in doc_text]
    if missing_scope_markers:
        failures.append(
            "conformance report lost its v3/v21 scope boundary: "
            + ", ".join(missing_scope_markers)
        )

    if args.write:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report_text)
        DOC_PATH.write_text(doc_text)
    else:
        for path, expected in ((REPORT_PATH, report_text), (DOC_PATH, doc_text)):
            mismatch = compare_file(path, expected)
            if mismatch:
                failures.append(mismatch)

    if args.strict:
        verified = report["summary"]["verification_passed_vendor_tools"]
        eligible = report["summary"]["publicly_verifiable_vendor_tools"]
        if verified != eligible:
            failures.append(f"strict conformance gate is red: {verified}/{eligible} publicly verifiable tools pass")
        extensions = report["summary"]["simulator_extension_gaps"]
        if extensions:
            failures.append(f"strict conformance gate is red: {extensions} invented agent-visible tools remain")

    summary = report["summary"]
    print(
        f"registry {summary['registry_covered']}/{summary['contract_tools']} covered; "
        f"targets {summary['vendor_targets_resolved']}/{summary['vendor_tools']} resolved; "
        f"exact {summary['exact_vendor_tools']}/{summary['vendor_tools']}; "
        f"extensions {summary['simulator_extension_gaps']}; harness failures {summary['harness_failures']}"
    )
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
