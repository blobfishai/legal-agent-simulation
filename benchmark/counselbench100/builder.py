#!/usr/bin/env python3
"""Build CounselBench-100 Harbor task packs and Hugging Face release files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile
from difflib import SequenceMatcher
from email import policy
from email.parser import Parser
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from catalog import FAMILY_SETTINGS, MATTERS, Matter  # noqa: E402
from decision_specs import DECISION_RULES  # noqa: E402
from generation import (  # noqa: E402
    AGENT_VISIBLE_FILE_COUNT,
    DOCUMENT_COUNT,
    DOCUMENT_ROOT,
    FINDING_COUNT,
    FIXED_FILE_TIMESTAMP,
    MINIMUM_TOOL_CALLS,
    OUTPUT_ROOT,
    REQUIRED_EVIDENCE_READS,
    build_material,
)
from runtime.contracts import MCP_PIN, tool_definitions  # noqa: E402


RELEASE_NAME = "CounselBench-100"
RELEASE_SLUG = "counselbench-100"
RELEASE_VERSION = "3.2.2"
HARBOR_ORG = "blobfishai"
DATA_LICENSE = "CC-BY-4.0"
CODE_LICENSE = "Apache-2.0"


def write_text(path: Path, value: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verification_token(task_id: str) -> str:
    # The test container sees this capability token; the agent container does
    # not.  The world stores only its digest and exposes no solve endpoint.
    return hashlib.sha256(f"CounselBench-100 verifier capability::{task_id}".encode()).hexdigest()


def task_toml(
    matter: Matter,
    task_id: str,
    task_index: int,
    material: dict[str, Any],
) -> str:
    task_name = f"{HARBOR_ORG}/cb100-{task_index + 1:03d}-{matter.slug}"
    return f'''schema_version = "1.4"

[task]
name = "{task_name}"
version = "{RELEASE_VERSION}"
description = "{FAMILY_SETTINGS[matter.family]['label']}: {matter.title}"
authors = []
keywords = ["legal", "mcp", "deterministic", "long-horizon", "{matter.family}"]

[metadata]
benchmark = "{RELEASE_NAME}"
benchmark_version = "{RELEASE_VERSION}"
task_id = "{task_id}"
matter_number = "{matter.matter_number}"
practice_area = "{matter.family}"
document_count = {AGENT_VISIBLE_FILE_COUNT}
minimum_tool_calls = {material['minimum_tool_calls']}
required_evidence_reads = {len(material['required_document_paths'])}
supported_actions = {material['action_count']}
evidence_holds = {material['hold_count']}
provider_count = 4
metric = "CounselScore"
deterministic_verifier = true
synthetic_data = true
data_license = "{DATA_LICENSE}"
code_license = "{CODE_LICENSE}"
mcp_contract_mode = "{MCP_PIN['contract_mode']}"

[verifier]
timeout_sec = 180.0

[agent]
timeout_sec = 3600.0

[environment]
build_timeout_sec = 900.0
cpus = 1
memory_mb = 2048
storage_mb = 4096
gpus = 0

[[environment.mcp_servers]]
name = "enterprise-matter"
transport = "streamable-http"
url = "http://world:8972/mcp"
'''


def compose_yaml() -> str:
    return """services:
  main:
    depends_on:
      world:
        condition: service_healthy
    volumes:
      - type: volume
        source: counselbench_output
        target: /workspace/output

  world:
    build:
      context: .
      dockerfile: world/Dockerfile
    environment:
      COUNSELBENCH_DOCUMENTS: /workspace/documents
      COUNSELBENCH_OUTPUT: /workspace/output
      COUNSELBENCH_STATE: /workspace/state
      COUNSELBENCH_SPEC: /opt/counselbench/spec.json
    expose:
      - "8972"
    volumes:
      - type: volume
        source: counselbench_output
        target: /workspace/output
      - type: volume
        source: counselbench_state
        target: /workspace/state
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8972/health', timeout=2)"]
      interval: 2s
      timeout: 5s
      retries: 60
      start_period: 2s

volumes:
  counselbench_output:
  counselbench_state:
"""


def main_dockerfile() -> str:
    return """FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17
WORKDIR /workspace
COPY tool /usr/local/bin/tool
RUN chmod 0755 /usr/local/bin/tool && mkdir -p /workspace/output
CMD ["sleep", "infinity"]
"""


def world_dockerfile() -> str:
    return """FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17
WORKDIR /opt/counselbench
COPY world/contracts.py world/scoring.py world/world.py world/server.py world/spec.json ./
COPY documents /workspace/documents
RUN mkdir -p /workspace/output /workspace/state
EXPOSE 8972
CMD ["python3", "/opt/counselbench/server.py"]
"""


def tool_cli() -> str:
    return r'''#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

URL = os.environ.get("COUNSELBENCH_MCP_URL", "http://world:8972/mcp")

def request(method, params=None, request_id=1):
    value = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        value["params"] = params
    req = urllib.request.Request(URL, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    with urllib.request.urlopen(req, json.dumps(value).encode("utf-8"), timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise SystemExit(json.dumps(payload["error"]))
    return payload["result"]

if len(sys.argv) == 2 and sys.argv[1] == "list":
    print(json.dumps(request("tools/list"), indent=2, ensure_ascii=False))
elif len(sys.argv) == 4 and sys.argv[1] == "call":
    result = request("tools/call", {"name": sys.argv[2], "arguments": json.loads(sys.argv[3])})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("isError"):
        raise SystemExit(1)
else:
    raise SystemExit("usage: tool list | tool call TOOL_NAME '{\"argument\":\"value\"}'")
'''


def solution_script() -> str:
    return r'''#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = json.loads((HERE / "reference.json").read_text(encoding="utf-8"))
URL = os.environ.get("COUNSELBENCH_MCP_URL", "http://world:8972/mcp")
request_id = 0

def call(name, arguments):
    global request_id
    request_id += 1
    message = {
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    request = urllib.request.Request(URL, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/event-stream")
    with urllib.request.urlopen(request, json.dumps(message).encode("utf-8"), timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload.get("result") or {}
    if payload.get("error") or result.get("isError"):
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    return result

for step in REFERENCE["calls"]:
    call(step["name"], step["arguments"])
print(json.dumps({"task_id": REFERENCE["task_id"], "successful_tool_calls": request_id}))
if request_id < REFERENCE["minimum_tool_calls"]:
    raise SystemExit("reference trajectory was unexpectedly short")
'''


def test_script(token: str) -> str:
    return f'''#!/bin/bash
set -eu
python3 - <<'PYEOF'
import json
import os
import urllib.request

output = {{"reward": 0.0, "passed": 0.0}}
report = {{"passed": False, "reward": 0.0, "error": "verifier did not return"}}
try:
    request = urllib.request.Request("http://world:8972/verify", method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("X-Verify-Token", "{token}")
    with urllib.request.urlopen(request, b"{{}}", timeout=150) as response:
        report = json.loads(response.read().decode("utf-8"))
    output = {{
        "reward": float(report.get("reward", 0.0)),
        "passed": 1.0 if report.get("passed") else 0.0,
    }}
except Exception as error:
    report = {{"passed": False, "reward": 0.0, "error": repr(error)}}

root = os.path.join(os.environ.get("HARBOR_LOGS", "/logs"), "verifier")
os.makedirs(root, exist_ok=True)
with open(os.path.join(root, "report.json"), "w", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
with open(os.path.join(root, "reward.json"), "w", encoding="utf-8") as stream:
    json.dump(output, stream, sort_keys=True)
print(json.dumps({{"passed": bool(output["passed"]), "reward": output["reward"]}}))
PYEOF
'''


def make_spec(material: dict[str, Any], matter: Matter, token: str) -> dict[str, Any]:
    state = material["state_contract"]
    return {
        "schema_version": "counselbench.world.v4",
        "task_id": material["task_id"],
        "matter_number": matter.matter_number,
        "fixed_file_timestamp": FIXED_FILE_TIMESTAMP,
        "minimum_tool_calls": material["minimum_tool_calls"],
        "required_document_paths": material["required_document_paths"],
        "provider_assets": material["provider_assets"],
        "state_contract": state,
        "rubric_milestones": material["rubric_milestones"],
        "evaluation_narrative": material["evaluation_narrative"],
        "expected_matter": {
            "id": state["matter_id"],
            "etag": f'"matter-{state["matter_id"]}-v1"',
            "display_number": matter.matter_number,
            "description": matter.title,
            "status": "Open",
            "custom_field_values": [
                {
                    "id": state["custom_value_id"],
                    "field_name": "Review Disposition Register",
                    "field_type": "text_area",
                    "value": "",
                    "custom_field": {"id": state["custom_field_id"]},
                }
            ],
        },
        "expected_decision": material["expected_decision"],
        "expected_register": material["expected_register"],
        "expected_advice": material["expected_advice"],
        "decision_options": material["decision_options"],
        "evidence_requirements": [
            {
                "portfolio_key": case["portfolio_key"],
                "topic": case["topic"],
                "required_paths": case["required_paths"],
                "required_roles": case["required_roles"],
                "expected_disposition": case["disposition"],
            }
            for case in material["cases"]
        ],
        "forbidden_claims": [
            "every portfolio item is actionable",
            "every portfolio item must remain on hold",
            "the newest document always controls",
            "a display-name match is sufficient",
        ],
        "verify_token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "mcp_pin": MCP_PIN,
    }


def copy_runtime(world_dir: Path) -> None:
    world_dir.mkdir(parents=True, exist_ok=True)
    for name in ("contracts.py", "scoring.py", "world.py", "server.py"):
        shutil.copy2(RUNTIME / name, world_dir / name)
    write_text(world_dir / "Dockerfile", world_dockerfile())


def create_task_pack(
    tasks_root: Path,
    hf_root: Path,
    matter: Matter,
    task_index: int,
    material: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    task_id = material["task_id"]
    task_dir = tasks_root / task_id
    environment = task_dir / "environment"
    documents = environment / "documents"
    world_dir = environment / "world"
    token = verification_token(task_id)
    spec = make_spec(material, matter, token)

    write_text(
        task_dir / "task.toml",
        task_toml(matter, task_id, task_index, material),
    )
    write_text(task_dir / "instruction.md", material["instruction"])
    write_text(environment / "Dockerfile", main_dockerfile())
    write_text(environment / "docker-compose.yaml", compose_yaml())
    write_text(environment / "tool", tool_cli(), executable=True)
    copy_runtime(world_dir)
    write_json(world_dir / "spec.json", spec)

    for absolute_path, content in material["documents"].items():
        relative = PurePosixPath(absolute_path).relative_to(DOCUMENT_ROOT)
        write_text(documents / Path(*relative.parts), content)
    for absolute_path, content in material["binary_documents"].items():
        relative = PurePosixPath(absolute_path).relative_to(DOCUMENT_ROOT)
        write_bytes(documents / Path(*relative.parts), content)

    reference = {
        "task_id": task_id,
        "minimum_tool_calls": material["minimum_tool_calls"],
        "required_document_paths": material["required_document_paths"],
        "provider_assets": material["provider_assets"],
        "state_contract": material["state_contract"],
        "rubric_milestones": material["rubric_milestones"],
        "evaluation_narrative": material["evaluation_narrative"],
        "decision": material["expected_decision"],
        "register": material["expected_register"],
        "decision_text": material["decision_text"],
        "register_text": material["register_text"],
        "advice_text": material["expected_advice"],
        "calls": material["reference_calls"],
    }
    write_json(task_dir / "solution" / "reference.json", reference)
    write_text(task_dir / "solution" / "solve.py", solution_script(), executable=True)
    write_text(
        task_dir / "solution" / "solve.sh",
        '#!/bin/bash\nset -eu\npython3 "$(dirname "$0")/solve.py"\n',
        executable=True,
    )
    write_text(task_dir / "tests" / "test.sh", test_script(token), executable=True)

    hf_context_paths: list[str] = []
    for absolute_path in material["all_document_paths"]:
        relative = PurePosixPath(absolute_path).relative_to(DOCUMENT_ROOT)
        source = documents / Path(*relative.parts)
        target = hf_root / "task_files" / task_id / Path(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        hf_context_paths.append(f"task_files/{task_id}/{relative.as_posix()}")

    record = {
        "task_id": task_id,
        "task_name": matter.title,
        "world_id": "counselbench-enterprise-mcp-v4",
        "prompt": material["instruction"],
        "context_files": hf_context_paths,
        "assets": [
            {
                **{
                    key: value
                    for key, value in asset.items()
                    if key not in {"read_arguments", "read_tool", "path"}
                },
                "path": f"task_files/{task_id}/{PurePosixPath(asset['path']).relative_to(DOCUMENT_ROOT).as_posix()}",
                "read_contract": {
                    "tool": asset["read_tool"],
                    "arguments": asset["read_arguments"],
                },
            }
            for asset in material["provider_assets"]
        ],
        "rubric": {
            "type": "deterministic",
            "metric": "CounselScore",
            "maximum_score": 100,
            "minimum_tool_calls": material["minimum_tool_calls"],
            "required_material_reads": len(material["required_document_paths"]),
            "required_state": [
                "clio_manage.matters.update",
                "clio_manage.notes.create",
                material["state_contract"]["writes"][
                    next(
                        index
                        for index, call in enumerate(material["state_contract"]["writes"])
                        if call["phase"] == "state-transition:notification"
                    )
                ]["name"],
            ],
            "evaluation_narrative": material["evaluation_narrative"],
            "milestones": material["rubric_milestones"],
            "decision_options": [
                {key: value for key, value in option.items() if key != "selected"}
                for option in material["decision_options"]
            ],
            "gates": [
                "all_material_evidence_precedes_first_mutation",
                "exact_mutation_set",
                "core_provider_state_exact",
                "notification_state_exact",
                "core_state_precedes_notification",
                "all_provider_readbacks_complete",
                "no_rejected_mutation",
            ],
        },
        "gold_output": {
            "decision": material["expected_decision"],
            "matter_register": material["expected_register"],
            "advice_markdown": material["expected_advice"],
        },
        "metadata": {
            "benchmark": RELEASE_NAME,
            "version": RELEASE_VERSION,
            "practice_area": matter.family,
            "matter_number": matter.matter_number,
            "jurisdiction": matter.jurisdiction,
            "venue": matter.venue,
            "deadline": matter.deadline,
            "synthetic": True,
            "document_count": AGENT_VISIBLE_FILE_COUNT,
            "required_evidence_reads": len(material["required_document_paths"]),
            "reference_tool_calls": material["minimum_tool_calls"],
            "supported_actions": material["action_count"],
            "evidence_holds": material["hold_count"],
            "providers": sorted(MCP_PIN["providers"]),
            "mcp_contract_mode": MCP_PIN["contract_mode"],
            "material_asset_count": sum(asset["material"] for asset in material["provider_assets"]),
            "data_license": DATA_LICENSE,
            "code_license": CODE_LICENSE,
        },
    }
    write_json(hf_root / "tasks" / f"{task_id}.json", record)
    index_entry = {
        "task_id": task_id,
        "matter_number": matter.matter_number,
        "title": matter.title,
        "practice_area": matter.family,
        "task_pack": f"tasks/{task_id}",
        "harbor_name": f"{HARBOR_ORG}/cb100-{task_index + 1:03d}-{matter.slug}",
        "documents": AGENT_VISIBLE_FILE_COUNT,
        "reference_tool_calls": material["minimum_tool_calls"],
        "required_evidence_reads": len(material["required_document_paths"]),
        "supported_actions": material["action_count"],
        "evidence_holds": material["hold_count"],
    }
    return record, index_entry


def shingles(value: str, size: int = 5) -> set[tuple[str, ...]]:
    words = re_words(value)
    return {tuple(words[index : index + size]) for index in range(max(0, len(words) - size + 1))}


def re_words(value: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", value.casefold())


def maximum_pair_similarity(values: Iterable[str]) -> dict[str, Any]:
    sets = [shingles(value) for value in values]
    maximum = 0.0
    pair = [None, None]
    for left in range(len(sets)):
        for right in range(left + 1, len(sets)):
            union = sets[left] | sets[right]
            score = len(sets[left] & sets[right]) / len(union) if union else 1.0
            if score > maximum:
                maximum = score
                pair = [left, right]
    return {"maximum_jaccard_5_shingle": round(maximum, 6), "pair_indices": pair}


def maximum_sequence_similarity(sequences: list[list[str]]) -> dict[str, Any]:
    maximum = 0.0
    pair = [None, None]
    for left in range(len(sequences)):
        for right in range(left + 1, len(sequences)):
            score = SequenceMatcher(
                None, sequences[left], sequences[right], autojunk=False
            ).ratio()
            if score > maximum:
                maximum = score
                pair = [left, right]
    return {"maximum_sequence_match": round(maximum, 6), "pair_indices": pair}


def native_document_parses(path: str, content: str) -> bool:
    """Validate the actual text-native representation, not just its suffix."""

    suffix = PurePosixPath(path).suffix.casefold()
    try:
        if suffix == ".json":
            return isinstance(json.loads(content), dict)
        if suffix == ".csv":
            rows = list(csv.DictReader(io.StringIO(content)))
            return bool(rows) and "portfolio_key" in (rows[0] or {})
        if suffix == ".xml":
            return ET.fromstring(content).tag == "counsel-source-record"
        if suffix == ".eml":
            message = Parser(policy=policy.default).parsestr(content)
            return bool(message["Message-ID"] and message["X-Portfolio-Key"])
        if suffix == ".html":
            parser = HTMLParser()
            parser.feed(content)
            parser.close()
            return "<!doctype html>" in content.casefold() and "</html>" in content.casefold()
        if suffix == ".pdf":
            encoded = content.encode("ascii")
            startxref = re.search(rb"startxref\n(\d+)\n%%EOF\n?$", encoded)
            if not startxref:
                return False
            xref_offset = int(startxref.group(1))
            if encoded[xref_offset : xref_offset + 5] != b"xref\n":
                return False
            header = re.match(rb"xref\n0 (\d+)\n", encoded[xref_offset:])
            if not header:
                return False
            object_count = int(header.group(1)) - 1
            entries_start = xref_offset + header.end()
            entries = encoded[entries_start:].splitlines()[: object_count + 1]
            if len(entries) != object_count + 1 or entries[0] != b"0000000000 65535 f ":
                return False
            for object_id, entry in enumerate(entries[1:], start=1):
                if not re.fullmatch(rb"\d{10} 00000 n ", entry):
                    return False
                offset = int(entry[:10])
                if not encoded.startswith(f"{object_id} 0 obj\n".encode(), offset):
                    return False
            return (
                encoded.startswith(b"%PDF-1.4\n")
                and b"/Type /Catalog" in encoded
                and b"/Type /Page " in encoded
                and b"trailer\n" in encoded
            )
        if suffix in {".md", ".txt"}:
            return len(content.splitlines()) >= 40
    except (csv.Error, json.JSONDecodeError, UnicodeError, ET.ParseError, ValueError):
        return False
    return False


def native_binary_document_parses(path: str, content: bytes) -> bool:
    """Validate native binary formats using their container and XML contracts."""

    if PurePosixPath(path).suffix.casefold() != ".xlsx" or not content.startswith(b"PK\x03\x04"):
        return False
    required = {
        "[Content_Types].xml",
        "_rels/.rels",
        "xl/workbook.xml",
        "xl/_rels/workbook.xml.rels",
        "xl/worksheets/sheet1.xml",
    }
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if archive.testzip() is not None or not required <= set(archive.namelist()):
                return False
            for name in required:
                ET.fromstring(archive.read(name))
            sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            rows = sheet.findall(".//s:sheetData/s:row", namespace)
            values = [
                node.text or ""
                for node in sheet.findall(".//s:c/s:is/s:t", namespace)
            ]
            return (
                len(rows) == 13
                and "portfolio_key" in values
                and "impact_control_score" in values
                and any(value.startswith("CBP-") for value in values)
            )
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, ET.ParseError):
        return False


def dataset_card(
    *,
    prompt_similarity: float,
    reference_similarity: float,
    semantic_similarity: float,
) -> str:
    return f"""---
license: cc-by-4.0
task_categories:
- question-answering
- text-generation
language:
- en
tags:
- legal
- benchmark
- agents
- mcp
- deterministic-evaluation
pretty_name: {RELEASE_NAME}
size_categories:
- n<1K
configs:
- config_name: default
  data_files:
  - split: test
    path: data/tasks.jsonl
---

# {RELEASE_NAME}

{RELEASE_NAME} v{RELEASE_VERSION} is a synthetic legal-work benchmark with 100
authored matters across ten practice workflows. Every task has a natural employee
request, a 97-asset evidence room, twelve portfolio decisions, 5–9 supported
actions, 3–7 evidence holds, and a distinct deep multi-provider MCP trajectory.

The answer is not preclassified in the evidence. Each portfolio item requires an
immutable identity join, an operative-authority and revision lookup, a current-state
comparison, and an effective approval/owner-capacity check across Clio, Gmail,
Drive, and Slack. The agent then commits native provider state and reads each
changed record back.

## Public release

- Runnable Harbor world: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Dataset and assets: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark explorer: <https://blobfish.ai/benchmarks/counselbench-100>
- Builder and verifier: <https://github.com/blobfishai/legal-agent-simulation/tree/master/benchmark/counselbench100>

## Included files

- `data/tasks.jsonl`: prompt, provider-bound assets, 14 semantic milestones, gold output, and metadata.
- `task_files/`: 9,700 unique files across Markdown, TXT, EML, CSV, JSON, XML, HTML, PDF, and XLSX.
- `world/`: pinned offline MCP implementation and hidden deterministic verifier.
- `trajectories/`: 100 solvability traces; these are excluded from model ranking.
- `reports/`: exact-version build, qualification, and conformance evidence.
- `SCORING.md`: causal, branch, state, containment, and readback contract.

## Measured v3.2.2 release gates

| Gate | Measured |
|---|---:|
| Tasks | 100 |
| Agent-visible files | 9,700 unique; all nine native formats parse |
| Required evidence reads | 58–86 per task |
| Reference MCP calls | 69–97 per task |
| Raw tool sequences | 100 distinct; maximum pair match {reference_similarity:.6f} |
| Semantic action graphs | 100 distinct; maximum pair match {semantic_similarity:.6f} |
| Prompt maximum 5-shingle Jaccard | {prompt_similarity:.6f} |
| Oracle and deterministic replay | 100/100 each |
| Thirteen negative controls | 1,300/1,300 rejected |

No older or partial model score is carried onto v3.2. A leaderboard row is published
only after one model runs all 100 tasks on this exact release.

## MCP fidelity and licenses

The world maps each allowlisted tool to a documented Clio Manage v4, Gmail v1,
Google Drive v3, or Slack Web API operation. Contract metadata and source links
ship with the release. Synthetic data is {DATA_LICENSE}; benchmark code is
{CODE_LICENSE}. Every entity, person, event, amount, and address is fictitious.
"""


def source_readme() -> str:
    return (HERE / "README.md").read_text(encoding="utf-8")


def harbor_readme() -> str:
    return f"""# {RELEASE_NAME}

{RELEASE_NAME} v{RELEASE_VERSION} contains 100 executable legal-agent tasks. Each
task has 97 provider-bound assets, twelve evidence-derived portfolio decisions,
a closed multi-provider MCP sandbox, and a deterministic causal/state verifier.

- 58–86 required evidence reads and 69–97 calls per task
- 5–9 supported actions plus 3–7 evidence holds per task
- 100 distinct raw tool sequences and semantic action graphs
- exact matter-register state, write containment, and post-write readback
- 14 task-specific semantic milestones totaling 100 CounselScore points
- 100/100 oracle passes and 1,300/1,300 adversarial rejections

```bash
harbor download {HARBOR_ORG}/{RELEASE_SLUG}@v{RELEASE_VERSION} \
  --output-dir ./counselbench
```

The prompt asks for the employee outcome. A neutral protocol in the evidence room
defines the work products without selecting an answer. Gold and verifier state are
outside the MCP allowlist. Reference trajectories prove solvability and do not count
as leaderboard runs.

- Explorer: <https://blobfish.ai/benchmarks/counselbench-100>
- Dataset: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Source: <https://github.com/blobfishai/legal-agent-simulation/tree/master/benchmark/counselbench100>
"""


def build(output: Path) -> dict[str, Any]:
    resolved = output.resolve()
    if resolved.name != RELEASE_SLUG:
        raise ValueError(f"refusing to replace unexpected output path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    tasks_root = resolved / "harbor" / "tasks"
    hf_root = resolved / "huggingface"
    tasks_root.mkdir(parents=True)
    hf_root.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    index: list[dict[str, Any]] = []
    all_document_hashes: set[str] = set()
    all_document_sizes: list[int] = []
    extension_counts: dict[str, int] = {}
    task_folder_counts: list[int] = []
    task_format_counts: list[int] = []
    prompts: list[str] = []
    reference_sequences: list[list[str]] = []
    semantic_sequences: list[list[str]] = []
    reference_call_counts: list[int] = []
    evidence_read_counts: list[int] = []
    action_counts: list[int] = []
    hold_counts: list[int] = []
    milestone_counts: list[int] = []
    material_gate_results: list[dict[str, bool]] = []
    native_format_results: list[bool] = []

    for task_index, matter in enumerate(MATTERS):
        material = build_material(matter, task_index)
        record, index_entry = create_task_pack(
            tasks_root, hf_root, matter, task_index, material
        )
        records.append(record)
        index.append(index_entry)
        prompts.append(material["instruction"])
        reference_sequences.append(
            [call["name"] for call in material["reference_calls"]]
        )
        semantic_sequences.append(material["semantic_signature"])
        reference_call_counts.append(material["minimum_tool_calls"])
        evidence_read_counts.append(len(material["required_document_paths"]))
        action_counts.append(material["action_count"])
        hold_counts.append(material["hold_count"])
        milestone_counts.append(len(material["rubric_milestones"]))
        material_gate_results.append(material["quality_gates"])
        document_paths = [PurePosixPath(path) for path in material["all_document_paths"]]
        task_folder_counts.append(len({path.parent for path in document_paths}))
        task_format_counts.append(len({path.suffix for path in document_paths}))
        for path, content in material["documents"].items():
            suffix = PurePosixPath(path).suffix.lstrip(".")
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            all_document_hashes.add(hashlib.sha256(content.encode("utf-8")).hexdigest())
            all_document_sizes.append(len(content.encode("utf-8")))
            native_format_results.append(native_document_parses(path, content))
        for path, content in material["binary_documents"].items():
            suffix = PurePosixPath(path).suffix.lstrip(".")
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            all_document_hashes.add(hashlib.sha256(content).hexdigest())
            all_document_sizes.append(len(content))
            native_format_results.append(native_binary_document_parses(path, content))

    data_path = hf_root / "data" / "tasks.jsonl"
    write_text(
        data_path,
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
    )
    shutil.copy2(HERE / "SCORING.md", hf_root / "SCORING.md")
    shutil.copy2(
        HERE / "EVALUATION_ARCHITECTURE.md",
        hf_root / "EVALUATION_ARCHITECTURE.md",
    )
    write_text(hf_root / "LICENSE-DATA", "Creative Commons Attribution 4.0 International\nhttps://creativecommons.org/licenses/by/4.0/\n")
    write_text(hf_root / "LICENSE-CODE", "Apache License 2.0\nhttps://www.apache.org/licenses/LICENSE-2.0\n")
    write_json(hf_root / "contracts" / "upstream-pin.json", MCP_PIN)
    write_json(hf_root / "contracts" / "provider-tools.json", {"tools": tool_definitions()})
    (hf_root / "world").mkdir(parents=True, exist_ok=True)
    (hf_root / "tests").mkdir(parents=True, exist_ok=True)
    for name in ("contracts.py", "scoring.py", "world.py", "server.py"):
        shutil.copy2(RUNTIME / name, hf_root / "world" / name)
    for name in ("conformance.py", "test_scoring.py"):
        shutil.copy2(HERE / "tests" / name, hf_root / "tests" / name)
    shutil.copy2(HERE / "run_suite.py", hf_root / "tests" / "run_suite.py")

    sorted_document_sizes = sorted(all_document_sizes)
    median_document_bytes = sorted_document_sizes[len(sorted_document_sizes) // 2]
    prompt_uniqueness = maximum_pair_similarity(prompts)
    reference_sequence_similarity = maximum_sequence_similarity(reference_sequences)
    semantic_sequence_similarity = maximum_sequence_similarity(semantic_sequences)
    write_text(
        hf_root / "README.md",
        dataset_card(
            prompt_similarity=prompt_uniqueness["maximum_jaccard_5_shingle"],
            reference_similarity=reference_sequence_similarity[
                "maximum_sequence_match"
            ],
            semantic_similarity=semantic_sequence_similarity[
                "maximum_sequence_match"
            ],
        ),
    )
    unique_reference_sequences = len({tuple(sequence) for sequence in reference_sequences})
    unique_semantic_sequences = len({tuple(sequence) for sequence in semantic_sequences})
    unique_causal_narratives = len(
        {
            json.dumps(
                record["rubric"]["evaluation_narrative"],
                ensure_ascii=False,
                sort_keys=True,
            )
            for record in records
        }
    )
    unique_milestone_contracts = len(
        {
            tuple(row["description"] for row in record["rubric"]["milestones"])
            for record in records
        }
    )
    exact_duplicate_prompts = len(prompts) - len(set(prompts))
    exact_duplicate_documents = len(records) * AGENT_VISIBLE_FILE_COUNT - len(all_document_hashes)
    quality_gates = {
        "one_hundred_tasks": len(records) == 100,
        "ten_balanced_practice_areas": (
            len(FAMILY_SETTINGS) == 10
            and all(sum(matter.family == family for matter in MATTERS) == 10 for family in FAMILY_SETTINGS)
        ),
        "ninety_seven_agent_visible_files_per_task": all(
            entry["documents"] == AGENT_VISIBLE_FILE_COUNT for entry in index
        ),
        "twelve_folders_per_task": all(count == 12 for count in task_folder_counts),
        "nine_native_formats_per_task": all(count == 9 for count in task_format_counts),
        "all_expected_formats_present": set(extension_counts) == {
            "md", "txt", "eml", "csv", "json", "xml", "html", "pdf", "xlsx",
        },
        "all_native_formats_parse": all(native_format_results),
        "minimum_document_depth": min(all_document_sizes) >= 5_500,
        "median_document_depth": median_document_bytes >= 7_000,
        "bounded_document_size": max(all_document_sizes) <= 40_000,
        "no_exact_duplicate_documents": exact_duplicate_documents == 0,
        "no_exact_duplicate_prompts": exact_duplicate_prompts == 0,
        "prompt_similarity_below_limit": (
            prompt_uniqueness["maximum_jaccard_5_shingle"] <= 0.72
        ),
        "high_level_prompts": all(
            45 <= len(prompt.split()) <= 120
            and "required review procedure" not in prompt.casefold()
            and "return exactly" not in prompt.casefold()
            for prompt in prompts
        ),
        "three_decision_options_per_task": all(
            len(record["rubric"]["decision_options"]) == 3
            and all("selected" not in option for option in record["rubric"]["decision_options"])
            for record in records
        ),
        "fourteen_task_specific_semantic_milestones": all(
            count == 14 for count in milestone_counts
        ),
        "unique_task_specific_milestone_contracts": (
            unique_milestone_contracts == len(records)
        ),
        "causal_evaluation_narratives_are_complete_and_unique": (
            unique_causal_narratives == len(records)
            and all(
                len(record["rubric"]["evaluation_narrative"]["investigation_chain"]) == 6
                and len(record["rubric"]["evaluation_narrative"]["branch_contract"]) == 12
                and len(record["rubric"]["evaluation_narrative"]["authorized_state_transition"]) == 3
                and len(record["rubric"]["evaluation_narrative"]["verification_chain"]) == 3
                and all(
                    len(branch["source_join"]) == 4
                    for branch in record["rubric"]["evaluation_narrative"]["branch_contract"]
                )
                for record in records
            )
        ),
        "counsel_score_totals_one_hundred": all(
            sum(row["weight"] for row in record["rubric"]["milestones"]) == 100
            for record in records
        ),
        "provider_native_asset_rooms": all(
            {asset["provider"] for asset in record["assets"] if asset["material"]}
            == {"clio_manage", "gmail", "google_drive", "slack"}
            for record in records
        ),
        "supported_action_and_hold_mix": all(
            5 <= actions <= 9 and actions + holds == 12
            for actions, holds in zip(action_counts, hold_counts, strict=True)
        ),
        "action_sizes_cover_range": set(action_counts) == {5, 6, 7, 8, 9},
        "evidence_depth_varies": (
            min(evidence_read_counts) >= REQUIRED_EVIDENCE_READS
            and len(set(evidence_read_counts)) >= 10
        ),
        "tool_call_depth_varies": (
            min(reference_call_counts) >= MINIMUM_TOOL_CALLS
            and len(set(reference_call_counts)) >= 15
        ),
        "all_material_causality_gates": all(
            all(gates.values()) for gates in material_gate_results
        ),
        "unique_reference_tool_sequences": unique_reference_sequences == len(records),
        "reference_sequence_similarity_below_limit": (
            reference_sequence_similarity["maximum_sequence_match"] <= 0.985
        ),
        "unique_semantic_action_graphs": unique_semantic_sequences == len(records),
        "semantic_action_graph_similarity_below_limit": (
            semantic_sequence_similarity["maximum_sequence_match"] <= 0.85
        ),
        "hand_authored_matter_spines_unique": (
            len({matter.title for matter in MATTERS}) == len(MATTERS)
            and len({matter.narrative for matter in MATTERS}) == len(MATTERS)
        ),
        "hand_authored_decision_rules_unique": (
            len(DECISION_RULES) == 100
            and len({rule.signature for rule in DECISION_RULES.values()}) == 100
        ),
    }
    build_report = {
        "schema_version": "counselbench.build.v4",
        "benchmark": RELEASE_NAME,
        "version": RELEASE_VERSION,
        "task_count": len(records),
        "practice_area_count": len(FAMILY_SETTINGS),
        "tasks_per_practice_area": {
            family: sum(matter.family == family for matter in MATTERS)
            for family in FAMILY_SETTINGS
        },
        "documents_per_task": AGENT_VISIBLE_FILE_COUNT,
        "document_count": len(records) * AGENT_VISIBLE_FILE_COUNT,
        "folders_per_task": min(task_folder_counts),
        "formats_per_task": min(task_format_counts),
        "format_counts": dict(sorted(extension_counts.items())),
        "unique_document_sha256_count": len(all_document_hashes),
        "minimum_document_bytes": min(all_document_sizes),
        "median_document_bytes": median_document_bytes,
        "maximum_document_bytes": max(all_document_sizes),
        "portfolio_items_per_task": FINDING_COUNT,
        "supported_actions_per_task": {
            "minimum": min(action_counts), "maximum": max(action_counts),
            "sizes_present": sorted(set(action_counts)),
        },
        "evidence_holds_per_task": {
            "minimum": min(hold_counts), "maximum": max(hold_counts),
            "sizes_present": sorted(set(hold_counts)),
        },
        "semantic_milestones_per_task": {
            "minimum": min(milestone_counts), "maximum": max(milestone_counts),
        },
        "unique_task_specific_milestone_contracts": unique_milestone_contracts,
        "unique_causal_evaluation_narratives": unique_causal_narratives,
        "reference_tool_calls_per_task": {
            "minimum": min(reference_call_counts),
            "maximum": max(reference_call_counts),
            "distinct_counts": len(set(reference_call_counts)),
        },
        "reference_tool_calls_total": sum(reference_call_counts),
        "required_evidence_reads_per_task": {
            "minimum": min(evidence_read_counts),
            "maximum": max(evidence_read_counts),
            "distinct_counts": len(set(evidence_read_counts)),
        },
        "unique_reference_tool_name_sequences": unique_reference_sequences,
        "reference_sequence_similarity": reference_sequence_similarity,
        "unique_semantic_action_graphs": unique_semantic_sequences,
        "semantic_action_graph_similarity": semantic_sequence_similarity,
        "prompt_uniqueness": prompt_uniqueness,
        "exact_duplicate_prompts": exact_duplicate_prompts,
        "exact_duplicate_documents": exact_duplicate_documents,
        "quality_gates": quality_gates,
        "release_passed": all(quality_gates.values()),
        "verifier": {
            "deterministic": True,
            "network_calls": 0,
            "model_calls": 0,
            "wall_clock_reads": 0,
            "random_calls": 0,
        },
        "mcp_pin": MCP_PIN,
    }
    if not build_report["release_passed"]:
        failed = sorted(name for name, passed in quality_gates.items() if not passed)
        raise AssertionError(f"CounselBench build quality gates failed: {failed}")
    write_json(resolved / "reports" / "build.json", build_report)
    write_json(resolved / "task-index.json", index)
    write_json(hf_root / "reports" / "build.json", build_report)

    dataset_template = f'''[dataset]
name = "{HARBOR_ORG}/{RELEASE_SLUG}"
version = "{RELEASE_VERSION}"
description = "100 high-level legal-agent tasks with 97-asset multi-provider evidence rooms, distinct deep trajectories, and native causal state verification."
authors = []
keywords = ["legal", "mcp", "deterministic", "long-horizon"]

# Publishing fills 100 [[tasks]] entries with registry content digests.
'''
    write_text(resolved / "harbor" / "dataset" / "dataset.toml.template", dataset_template)
    write_text(resolved / "harbor" / "dataset" / "README.md", harbor_readme())

    release_files = sorted(path for path in resolved.rglob("*") if path.is_file())
    manifest = {
        "schema_version": "1.0",
        "benchmark": RELEASE_NAME,
        "version": RELEASE_VERSION,
        "files": [
            {
                "path": path.relative_to(resolved).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in release_files
        ],
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    write_json(resolved / "release-manifest.json", manifest)
    return build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE.parents[1] / "dist" / RELEASE_SLUG,
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    report = build(arguments.output)
    print(json.dumps(report, indent=2, sort_keys=True))
