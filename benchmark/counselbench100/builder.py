#!/usr/bin/env python3
"""Build CounselBench-100 Harbor task packs and Hugging Face release files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from catalog import FAMILY_SETTINGS, MATTERS, Matter  # noqa: E402
from generation import (  # noqa: E402
    DOCUMENT_COUNT,
    DOCUMENT_ROOT,
    FINDING_COUNT,
    FIXED_FILE_TIMESTAMP,
    MINIMUM_TOOL_CALLS,
    OUTPUT_ROOT,
    build_material,
)
from runtime.contracts import MCP_PIN, tool_definitions  # noqa: E402


RELEASE_NAME = "CounselBench-100"
RELEASE_SLUG = "counselbench-100"
RELEASE_VERSION = "1.1.0"
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


def task_toml(matter: Matter, task_id: str, task_index: int) -> str:
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
document_count = {DOCUMENT_COUNT}
minimum_tool_calls = {MINIMUM_TOOL_CALLS}
deterministic_verifier = true
synthetic_data = true
data_license = "{DATA_LICENSE}"
code_license = "{CODE_LICENSE}"
mcp_upstream_package = "{MCP_PIN['package']}@{MCP_PIN['version']}"
mcp_upstream_commit = "{MCP_PIN['commit']}"

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
name = "filesystem"
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
      - type: bind
        source: ./documents
        target: /workspace/documents
        read_only: true
      - type: volume
        source: counselbench_output
        target: /workspace/output

  world:
    build:
      context: ./world
      dockerfile: Dockerfile
    environment:
      COUNSELBENCH_DOCUMENTS: /workspace/documents
      COUNSELBENCH_OUTPUT: /workspace/output
      COUNSELBENCH_STATE: /workspace/state
      COUNSELBENCH_SPEC: /opt/counselbench/spec.json
    expose:
      - "8972"
    volumes:
      - type: bind
        source: ./documents
        target: /workspace/documents
        read_only: true
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
COPY contracts.py scoring.py world.py server.py spec.json ./
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

call("list_allowed_directories", {})
call("directory_tree", {"path": "/workspace/documents", "excludePatterns": []})
call("search_files", {"path": "/workspace/documents", "pattern": "**/*.eml", "excludePatterns": []})
for path in REFERENCE["required_document_paths"]:
    call("read_text_file", {"path": path})
for path in REFERENCE["metadata_check_paths"]:
    call("get_file_info", {"path": path})
call("write_file", {"path": "/workspace/output/findings.json", "content": REFERENCE["findings_text"]})
call("write_file", {"path": "/workspace/output/advice.md", "content": REFERENCE["memo_text"]})
print(json.dumps({"task_id": REFERENCE["task_id"], "successful_tool_calls": request_id}))
if request_id < 109:
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
    findings = material["expected_findings"]["findings"]
    anchors = [matter.title, matter.matter_number, matter.client]
    for finding in findings:
        anchors.extend(
            [
                finding["id"], finding["issue"], finding["severity"],
                finding["primary_source"], finding["corroborating_source"],
            ]
        )
    return {
        "schema_version": "1.1",
        "task_id": material["task_id"],
        "matter_number": matter.matter_number,
        "fixed_file_timestamp": FIXED_FILE_TIMESTAMP,
        "minimum_tool_calls": MINIMUM_TOOL_CALLS,
        "required_document_paths": material["required_document_paths"],
        "metadata_check_paths": material["metadata_check_paths"],
        "deliverables": ["advice.md", "findings.json"],
        "expected_findings": material["expected_findings"],
        "expected_memo": material["expected_memo"],
        "scoring_findings": material["scoring_findings"],
        "memo_sections": [
            "Executive assessment", "Method and record coverage", "Findings",
            "Recommended next actions", "Assumptions and limitations",
        ],
        "memo_anchors": anchors,
        "forbidden_claims": [
            "no material issues", "all records are consistent", "no further action is required",
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

    write_text(task_dir / "task.toml", task_toml(matter, task_id, task_index))
    write_text(task_dir / "instruction.md", material["instruction"])
    write_text(environment / "Dockerfile", main_dockerfile())
    write_text(environment / "docker-compose.yaml", compose_yaml())
    write_text(environment / "tool", tool_cli(), executable=True)
    copy_runtime(world_dir)
    write_json(world_dir / "spec.json", spec)

    for absolute_path, content in material["documents"].items():
        relative = PurePosixPath(absolute_path).relative_to(DOCUMENT_ROOT)
        write_text(documents / Path(*relative.parts), content)

    reference = {
        "task_id": task_id,
        "required_document_paths": material["required_document_paths"],
        "metadata_check_paths": material["metadata_check_paths"],
        "findings_text": material["expected_findings_text"],
        "memo_text": material["expected_memo"],
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
    for absolute_path in material["required_document_paths"]:
        relative = PurePosixPath(absolute_path).relative_to(DOCUMENT_ROOT)
        source = documents / Path(*relative.parts)
        target = hf_root / "task_files" / task_id / Path(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        hf_context_paths.append(f"task_files/{task_id}/{relative.as_posix()}")

    record = {
        "task_id": task_id,
        "task_name": matter.title,
        "world_id": "counselbench-filesystem-mcp-v1",
        "prompt": material["instruction"],
        "context_files": hf_context_paths,
        "rubric": {
            "type": "deterministic",
            "metric": "weighted_criteria_score",
            "weights": {"procedure": 0.25, "findings": 0.55, "memo": 0.20},
            "minimum_tool_calls": MINIMUM_TOOL_CALLS,
            "required_document_reads": DOCUMENT_COUNT,
            "metadata_checks": 8,
            "required_deliverables": ["findings.json", "advice.md"],
            "gates": [
                "all_evidence_read_in_full", "chain_of_custody_metadata_checked",
                "findings_criteria_complete", "memo_criteria_complete",
                "deliverables_written_through_mcp",
            ],
        },
        "gold_output": {
            "findings": material["expected_findings"],
            "advice_markdown": material["expected_memo"],
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
            "document_count": DOCUMENT_COUNT,
            "reference_tool_calls": MINIMUM_TOOL_CALLS,
            "mcp_package": f"{MCP_PIN['package']}@{MCP_PIN['version']}",
            "mcp_commit": MCP_PIN["commit"],
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
        "documents": DOCUMENT_COUNT,
        "reference_tool_calls": MINIMUM_TOOL_CALLS,
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


def dataset_card() -> str:
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

{RELEASE_NAME} is a synthetic long-horizon legal-agent benchmark with 100 distinct matters across ten practice workflows. Every task contains 96 production-style source records in 12 folders and has a 109-call reference MCP trajectory. The v1.1 grader reports a deterministic weighted criteria score across review procedure (25%), structured findings (55%), and memo grounding (20%); full task pass still requires every criterion.

## Public release

- Runnable Harbor world: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Dataset and test assets: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark page: <https://blobfish.ai/benchmarks/counselbench-100>
- Builder and verifier source: <https://github.com/blobfishai/legal-agent-simulation/tree/master/benchmark/counselbench100>

## What is included

- `data/tasks.jsonl`: Apex-compatible task records (`task_id`, `task_name`, `world_id`, `prompt`, `context_files`, `rubric`, `gold_output`, `metadata`).
- `tasks/`: one readable JSON record per matter.
- `task_files/`: 9,600 seeded evidence documents (`md`, `txt`, `eml`, `csv`, `json`, `xml`, and `html`).
- `world/`: the offline Streamable HTTP MCP world and deterministic verifier source.
- `contracts/`: pinned live contract snapshots for the official MCP filesystem server.
- `tests/`: conformance and full-suite test programs.
- `SCORING.md`: the versioned 182-criterion scoring contract and v1.0 correction rationale.
- `EVALUATION_ARCHITECTURE.md`: the runtime map to Archipelago/APEX and the intentional deterministic-grading differences.
- `trajectories/` and `reports/`: all 100 generated reference traces, ten published model transcripts with verifier reports, and measured pass/failure evidence.

## Objective release gates

| Gate | Required |
|---|---:|
| Tasks | 100 |
| Practice workflows | 10 |
| Source records per task | 96 |
| Reference MCP calls per task | 109 |
| LLM or network calls in verifier | 0 |
| Oracle passes | 100/100 |
| Shortcut, incomplete-read, and wrong-fact false accepts | 0 |

Measured results are stored in `reports/qualification.json`; do not infer a model score from the reference trajectory.

## Deterministic v1.1 scoring

- Each task has 182 visible criteria: 8 procedure, 152 structured-findings, and 22 memo criteria.
- Each finding is graded field by field against record-control metadata exposed to the agent.
- Determinations must contain the seeded fact anchors and may not introduce controlled dates, amounts, percentages, addresses, or references absent from the cited source pair.
- Recommendations must preserve the seeded response deadline and remediation owner.
- Incomplete review procedure caps reward below 0.5, even when an output resembles the gold file.
- Full-output exact match is retained only as a diagnostic and does not erase legitimate partial credit.

## MCP fidelity

The world exposes an allowlisted subset of `{MCP_PIN['package']}@{MCP_PIN['version']}` using the same tool names, input JSON Schema, annotations, `content`, and `structuredContent` result shapes. The upstream repository is pinned to commit `{MCP_PIN['commit']}`. `tests/conformance.py` launches the real package and compares live behavior against the offline mock.

## Data and contamination

Every person, entity, amount, address, event, and document is synthetic. The catalog was written for this release; Harvey Labs and Apex Accounting informed packaging and depth targets only. No Harvey or Apex task text, evidence, rubric, or gold answer is included. Gold outputs are public, as in Apex Accounting, so this release is appropriate for transparent evaluation and RL experiments rather than secret-test claims.

## Licenses

Synthetic task data and documents are {DATA_LICENSE}. Benchmark code and test harnesses are {CODE_LICENSE}. Third-party MCP contract metadata remains subject to the upstream MIT license; provenance is recorded in `contracts/upstream-pin.json`.
"""


def source_readme() -> str:
    return f"""# {RELEASE_NAME} source

This directory contains the deterministic source generator, MCP world, and
qualification suite for {RELEASE_NAME}.

The v1.1.0 release contains 100 original synthetic matters, 9,600 seeded source
documents, 109-call accepted MCP trajectories, and a deterministic verifier.

Public artifacts:

- Harbor: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Hugging Face: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark page: <https://blobfish.ai/benchmarks/counselbench-100>
- Source: <https://github.com/blobfishai/legal-agent-simulation>

```bash
python3 benchmark/counselbench100/builder.py
python3 -m unittest \
  benchmark.counselbench100.tests.test_builder \
  benchmark.counselbench100.tests.test_generation \
  benchmark.counselbench100.tests.test_scoring
python3 benchmark/counselbench100/run_suite.py
python3 benchmark/counselbench100/tests/conformance.py
CODEX_FORCE_AUTH_JSON=1 uv run --project harbor/runner --locked harbor run \
  --config benchmark/counselbench100/real-agent-stratified-v1.1.json --yes
```

Generated release files are written to `dist/{RELEASE_SLUG}` and are intentionally ignored by Git. The committed catalog contains 100 hand-authored matter spines; generation is deterministic and makes no network calls.

The canonical interactive explorer is maintained in the Blobfish website
repository and deployed at the benchmark-page URL above. The page under
`site/` is retained only as the historical v1.0 launch artifact.
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

    for task_index, matter in enumerate(MATTERS):
        material = build_material(matter, task_index)
        record, index_entry = create_task_pack(
            tasks_root, hf_root, matter, task_index, material
        )
        records.append(record)
        index.append(index_entry)
        prompts.append(material["instruction"])
        document_paths = [PurePosixPath(path) for path in material["documents"]]
        task_folder_counts.append(len({path.parent for path in document_paths}))
        task_format_counts.append(len({path.suffix for path in document_paths}))
        for path, content in material["documents"].items():
            suffix = PurePosixPath(path).suffix.lstrip(".")
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            all_document_hashes.add(hashlib.sha256(content.encode("utf-8")).hexdigest())
            all_document_sizes.append(len(content.encode("utf-8")))

    data_path = hf_root / "data" / "tasks.jsonl"
    write_text(
        data_path,
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
    )
    write_text(hf_root / "README.md", dataset_card())
    shutil.copy2(HERE / "SCORING.md", hf_root / "SCORING.md")
    shutil.copy2(
        HERE / "EVALUATION_ARCHITECTURE.md",
        hf_root / "EVALUATION_ARCHITECTURE.md",
    )
    write_text(hf_root / "LICENSE-DATA", "Creative Commons Attribution 4.0 International\nhttps://creativecommons.org/licenses/by/4.0/\n")
    write_text(hf_root / "LICENSE-CODE", "Apache License 2.0\nhttps://www.apache.org/licenses/LICENSE-2.0\n")
    write_json(hf_root / "contracts" / "upstream-pin.json", MCP_PIN)
    write_json(hf_root / "contracts" / "filesystem-tools.json", {"tools": tool_definitions()})
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
    exact_duplicate_prompts = len(prompts) - len(set(prompts))
    exact_duplicate_documents = len(records) * DOCUMENT_COUNT - len(all_document_hashes)
    quality_gates = {
        "one_hundred_tasks": len(records) == 100,
        "ten_balanced_practice_areas": (
            len(FAMILY_SETTINGS) == 10
            and all(sum(matter.family == family for matter in MATTERS) == 10 for family in FAMILY_SETTINGS)
        ),
        "ninety_six_documents_per_task": all(
            entry["documents"] == DOCUMENT_COUNT for entry in index
        ),
        "twelve_folders_per_task": all(count == 12 for count in task_folder_counts),
        "seven_text_native_formats_per_task": all(count == 7 for count in task_format_counts),
        "all_expected_formats_present": set(extension_counts) == {
            "md", "txt", "eml", "csv", "json", "xml", "html",
        },
        "minimum_document_depth": min(all_document_sizes) >= 5_500,
        "median_document_depth": median_document_bytes >= 7_000,
        "bounded_document_size": max(all_document_sizes) <= 20_000,
        "no_exact_duplicate_documents": exact_duplicate_documents == 0,
        "no_exact_duplicate_prompts": exact_duplicate_prompts == 0,
        "prompt_similarity_below_limit": prompt_uniqueness["maximum_jaccard_5_shingle"] < 0.80,
        "hand_authored_matter_spines_unique": (
            len({matter.title for matter in MATTERS}) == len(MATTERS)
            and len({matter.narrative for matter in MATTERS}) == len(MATTERS)
        ),
    }
    build_report = {
        "schema_version": "1.0",
        "benchmark": RELEASE_NAME,
        "version": RELEASE_VERSION,
        "task_count": len(records),
        "practice_area_count": len(FAMILY_SETTINGS),
        "tasks_per_practice_area": {
            family: sum(matter.family == family for matter in MATTERS)
            for family in FAMILY_SETTINGS
        },
        "documents_per_task": DOCUMENT_COUNT,
        "document_count": len(records) * DOCUMENT_COUNT,
        "folders_per_task": min(task_folder_counts),
        "formats_per_task": min(task_format_counts),
        "format_counts": dict(sorted(extension_counts.items())),
        "unique_document_sha256_count": len(all_document_hashes),
        "minimum_document_bytes": min(all_document_sizes),
        "median_document_bytes": median_document_bytes,
        "maximum_document_bytes": max(all_document_sizes),
        "findings_per_task": FINDING_COUNT,
        "criteria_per_task": 182,
        "reference_tool_calls_per_task": MINIMUM_TOOL_CALLS,
        "reference_tool_calls_total": len(records) * MINIMUM_TOOL_CALLS,
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
description = "100 synthetic long-horizon legal-agent tasks with 109-call MCP trajectories and deterministic criterion-level verifiers."
authors = []
keywords = ["legal", "mcp", "deterministic", "long-horizon"]

# Publishing fills 100 [[tasks]] entries with registry content digests.
'''
    write_text(resolved / "harbor" / "dataset" / "dataset.toml.template", dataset_template)

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
