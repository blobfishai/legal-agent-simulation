"""Append deterministically compiled LAB practice tasks to a v17 world."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from world.local.evidence import LAB_ID_BASE
from world.v17.verifiers import practice_vcode

ROOT = Path(__file__).resolve().parents[2]
LAB_INDEX = ROOT / "world" / "corpus" / "lab" / "index.sqlite"
SOURCE_COMMIT = json.loads(
    (ROOT / "research" / "repos-commits.json").read_text(encoding="utf-8")
)["harveyai@harvey-labs"]


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{LAB_INDEX}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _deliverables(row: dict[str, Any]) -> list[str]:
    declared = row.get("deliverables") or {}
    names = list(declared) if isinstance(declared, dict) else list(declared)
    if not names:
        instruction = str(row.get("instructions") or "")
        names = [match.group(1).strip() for match in re.finditer(
            r"`([^`/\\]+\.(?:docx|xlsx|pptx|md|pdf))`", instruction, flags=re.I)]
        if not names:
            section = re.split(r"\bOutput:\s*", instruction, maxsplit=1, flags=re.I)
            if len(section) == 2:
                names = re.findall(r"([A-Za-z0-9][A-Za-z0-9_.() -]*\.(?:docx|xlsx|pptx|md|pdf))",
                                   section[1], flags=re.I)
    return list(dict.fromkeys(name.strip() for name in names if name.strip()))


def _task_source(connection: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT task_json FROM tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"LAB source task missing from evidence index: {task_id}")
    return json.loads(row["task_json"])


def _document_map(connection: sqlite3.Connection, task_id: str) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """SELECT f.file_id,f.ordinal,f.filename,b.parse_status
             FROM files f JOIN blobs b ON b.sha256=f.blob_sha256
            WHERE f.task_id=? ORDER BY f.ordinal""", (task_id,)
    ).fetchall()
    return {row["file_id"]: {"document_id": LAB_ID_BASE + int(row["ordinal"]),
                             "filename": row["filename"], "parsed": row["parse_status"] == "parsed"}
            for row in rows}


def _minimum_reads(criteria: list[dict[str, Any]], documents: dict[str, dict[str, Any]]) -> list[str]:
    universe: set[tuple[str, int, int]] = set()
    covers: dict[str, set[tuple[str, int, int]]] = defaultdict(set)
    for criterion in criteria:
        for index, assertion in enumerate(criterion["assertions"]):
            sources = list(assertion.get("source_files") or [])
            sources.extend(option["source_file"] for option in assertion.get("alternatives") or []
                           if option.get("source_file"))
            unique_sources = {source["file_id"]: source for source in sources}
            for source_index, source in enumerate(unique_sources.values()):
                key = (str(criterion["criterion_id"]), index, source_index)
                universe.add(key)
                file_id = source["file_id"]
                if file_id in documents and documents[file_id]["parsed"]:
                    covers[file_id].add(key)
    selected: list[str] = []
    uncovered = set(universe)
    while uncovered:
        candidates = [(len(items & uncovered), file_id) for file_id, items in covers.items()]
        count, best = max(candidates, default=(0, ""), key=lambda item: (item[0], item[1]))
        if count == 0:
            break
        selected.append(best)
        uncovered -= covers[best]
    if uncovered:
        raise RuntimeError(f"{len(uncovered)} assertions have no readable grounding source")
    return selected


def _compiled_criteria(compiled: dict[str, Any], source_task: dict[str, Any],
                       deliverables: list[str]) -> list[dict[str, Any]]:
    source_by_id = {str(row.get("id")): row for row in source_task.get("criteria") or []}
    rows = []
    for criterion in compiled["criteria"]:
        source = source_by_id.get(str(criterion["criterion_id"]), {})
        targets = [name for name in source.get("deliverables") or [] if name in deliverables]
        rows.append({
            "criterion_id": str(criterion["criterion_id"]),
            "deliverables": targets or deliverables,
            "anchor_groups": [assertion["variants"] for assertion in criterion["assertions"]],
            "reference_fragment": criterion["reference_fragment"],
        })
    return rows


def _task_id(source_task: str) -> str:
    import hashlib
    return "labp_" + hashlib.sha256(source_task.encode()).hexdigest()[:16]


def append_practice_tasks(
    world: dict[str, Any],
    rows: list[dict[str, Any]],
    existing: set[str],
    *,
    deliverable_overrides: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Append compiled practice tasks.

    ``deliverable_overrides`` is deliberately narrow: it lets a later world
    adapter supply an output contract when an upstream LAB task omitted only
    the filename.  The source mirror and source task JSON remain unchanged,
    and the override is keyed by the full upstream task path so it cannot
    silently alter unrelated imports.
    """
    if not LAB_INDEX.is_file():
        raise RuntimeError(f"LAB index missing: {LAB_INDEX}")
    connection = _connect()
    counts = defaultdict(int)
    quarantine: list[dict[str, str]] = []
    admitted_sources: list[str] = []
    try:
        for compiled in rows:
            task_id = _task_id(compiled["source_task"])
            source_task = _task_source(connection, compiled["task_id"])
            overridden = (deliverable_overrides or {}).get(compiled["source_task"])
            deliverables = list(overridden or _deliverables({
                **compiled,
                **{"deliverables": source_task.get("deliverables") or {},
                   "instructions": source_task.get("instructions") or compiled["instructions"]},
            }))
            if not deliverables:
                counts["quarantined_missing_output"] += 1
                quarantine.append({"source_task": compiled["source_task"],
                                   "reason": "missing_output_contract"})
                continue
            unsafe = [name for name in deliverables
                      if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts]
            if unsafe:
                counts["quarantined_unsafe_output"] += 1
                quarantine.append({"source_task": compiled["source_task"],
                                   "reason": "unsafe_output_path", "detail": ", ".join(unsafe)})
                continue
            criteria = _compiled_criteria(compiled, source_task, deliverables)
            documents = _document_map(connection, compiled["task_id"])
            if criteria:
                try:
                    read_files = _minimum_reads(compiled["criteria"], documents)
                except RuntimeError as error:
                    counts["quarantined_unreadable_grounding"] += 1
                    quarantine.append({"source_task": compiled["source_task"],
                                       "reason": "unreadable_grounding", "detail": str(error)})
                    continue
            else:
                # Thin tasks remain hosted and explicitly excluded from the
                # headline.  Requiring every readable task-local input still
                # gives them a deterministic read -> file -> state contract.
                read_files = [file_id for file_id, row in documents.items() if row["parsed"]]
                if not read_files:
                    counts["quarantined_unreadable_grounding"] += 1
                    quarantine.append({"source_task": compiled["source_task"],
                                       "reason": "no_readable_task_evidence"})
                    continue
            read_ids = [documents[file_id]["document_id"] for file_id in read_files]
            reference_by_deliverable: dict[str, list[str]] = {name: [] for name in deliverables}
            for criterion in criteria:
                for name in criterion["deliverables"]:
                    reference_by_deliverable[name].append(criterion["reference_fragment"])
            walk: list[str] = []
            reference_args: list[dict[str, Any]] = []
            for file_id, document_id in zip(read_files, read_ids):
                walk.extend(("documents_search_fulltext", "documents_download"))
                reference_args.extend((
                    {"query": documents[file_id]["filename"], "limit": 20},
                    {"id": document_id},
                ))
            for name in deliverables:
                walk.append("documents_create")
                reference_args.append({
                    "folder_id": 1, "workspace_id": 1, "name": name,
                    "doc_class": "MEMO", "author": "oracle@simulated-firm.example",
                    "body": "\n".join(reference_by_deliverable[name]) or compiled["reference_output"],
                })
            prompt = (compiled["instructions"].rstrip() +
                      "\n\nUse MatterVault to search and download the source record in full before drafting. "
                      "Create every requested file under `/workspace/output` and file the same deliverable(s) "
                      "to MatterVault DMS. Work left only in chat does not satisfy the assignment.")
            file_assertions = [{"criterion_id": criterion["criterion_id"],
                                "deliverables": criterion["deliverables"],
                                "anchor_groups": criterion["anchor_groups"],
                                "reference_fragment": criterion["reference_fragment"]}
                               for criterion in criteria]
            is_diligence = compiled["source_task"].startswith("diligence/")
            task = {
                "task_id": task_id,
                "outcome_class": "eligible_action",
                "prompt": prompt,
                "goal": compiled["title"] or compiled["instructions"][:120],
                "required_tools": ["documents_search_fulltext", "documents_download", "documents_create"],
                "complexity": "high" if len(read_ids) >= 8 or len(criteria) >= 40 else "medium",
                "method": "harvey_lab_determinate_import",
                "capability_type": 4 if is_diligence else (
                    5 if compiled.get("work_type") in {"draft", "review", "contracting"} else 1),
                "steps": ["Search for each grounding record", "Open every grounding document in full",
                          "Create requested file artifacts", "File matching deliverables to MatterVault"],
                "relevant_data": [{"external_store": "lab", "source_task": compiled["source_task"],
                                   "required_document_ids": read_ids}],
                "expected_state_changes": [{"table": "dm_documents", "field": "name", "value": name}
                                           for name in deliverables],
                "tables_affected": ["dm_documents"],
                "walk": walk,
                "reference_args": reference_args,
                "effects": [{"table": "dm_documents", "op": "insert"} for _ in deliverables],
                "provenance": {"source_repo": "harveyai/harvey-labs", "source_commit": SOURCE_COMMIT,
                               "source_task": compiled["source_task"]},
                "contamination": {"status": "public", "public_since": "2026",
                                  "lane": "verbatim_lab"},
                "difficulty_tier": "pending_triage",
                "acceptance_label": ("admitted_determinate" if compiled["admission"] == "compiled"
                                     else "admitted_thin_excluded_headline"),
                "evidence_store": {"kind": "lab", "task_id": compiled["task_id"]},
                "file_lane": {
                    "source_task": compiled["source_task"], "source_commit": SOURCE_COMMIT,
                    "documents_source": f"research/repos/harveyai@harvey-labs/tasks/{compiled['source_task']}/documents",
                    "deliverables": deliverables, "skills": ["docx", "xlsx", "pptx"],
                    "grading": "determinate" if file_assertions else "output_contract_only",
                    "assertions": file_assertions,
                },
                "grading": {"kind": "determinate_grounding", "criteria_total": compiled["criteria_total"],
                            "criteria_determinate": len(criteria), "assertions": compiled["assertion_count"],
                            "coverage": compiled["coverage"], "headline_eligible": compiled["admission"] == "compiled",
                            "reports": ["precision", "recall", "f_beta", "over_included"],
                            "metric_scope": "determinate criteria plus unsupported high-risk facts",
                            "beta": 2.0, "scale_review": is_diligence,
                            "corpus_documents": len(documents)},
            }
            if task_id in existing:
                raise RuntimeError(f"duplicate v17 task id {task_id}")
            verifier = {
                "task_id": task_id,
                "assertions": ["required_workflow_path", "required_search_discovery", "required_documents_read",
                               "all_deliverables_filed_to_dms", "grounded_criteria",
                               "no_unsupported_numeric_facts",
                               "no_offtask_table_changes", "no_documents_destroyed",
                               "no_undeclared_documents"],
                "key_assertions": ["grounded_criteria", "no_unsupported_numeric_facts"],
                "vcode": practice_vcode(task_id, deliverables, criteria, read_ids),
                "generated_by": "world/v17/practice.py",
            }
            world["tasks"].append(task)
            world["verifiers"].append(verifier)
            existing.add(task_id)
            admitted_sources.append(compiled["source_task"])
            counts["added"] += 1
            counts["headline"] += compiled["admission"] == "compiled"
            counts["thin"] += compiled["admission"] != "compiled"
    finally:
        connection.close()
    result: dict[str, Any] = {**dict(counts), "quarantined": len(quarantine),
                              "admitted_sources": admitted_sources,
                              "quarantine": quarantine}
    world["lab_practice_import"] = result
    return result
