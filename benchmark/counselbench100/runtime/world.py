"""Deterministic filesystem MCP world and hidden verifier.

The tool payloads intentionally follow the official MCP filesystem server's
``content`` and ``structuredContent`` shapes.  This module contains no model,
network, clock, locale, or random dependency in its grading path.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
import threading
from pathlib import Path
from typing import Any

try:  # Package import in local qualification; flat import in generated image.
    from .contracts import TOOLS_BY_NAME, tool_definitions
    from .scoring import aggregate_scores, score_findings, score_memo
except ImportError:  # pragma: no cover - exercised inside the task container
    from contracts import TOOLS_BY_NAME, tool_definitions
    from scoring import aggregate_scores, score_findings, score_memo


class ToolFailure(Exception):
    """A tool-level failure returned using the MCP ``isError`` convention."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tool_result(text: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": {"content": text},
    }


class CounselWorld:
    """A per-trial, allowlisted MCP filesystem with append-only trace evidence."""

    def __init__(
        self,
        documents_root: str | Path,
        output_root: str | Path,
        state_root: str | Path,
        spec_path: str | Path,
    ) -> None:
        self.documents_root = Path(documents_root).resolve()
        self.output_root = Path(output_root).resolve()
        self.state_root = Path(state_root).resolve()
        self.spec_path = Path(spec_path).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.state_root / "trace.jsonl"
        self._lock = threading.Lock()
        self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.allowed_roots = (self.documents_root, self.output_root)
        self.virtual_roots = {
            Path("/workspace/documents"): self.documents_root,
            Path("/workspace/output"): self.output_root,
        }

    def reset(self) -> None:
        """Reset only generated trial state; seeded evidence remains immutable."""

        for path in sorted(self.output_root.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if self.trace_path.exists():
            self.trace_path.unlink()

    def list_tools(self) -> list[dict[str, Any]]:
        return tool_definitions()

    def _resolve(self, raw_path: Any, *, write: bool = False) -> Path:
        if not isinstance(raw_path, str) or not raw_path:
            raise ToolFailure("path must be a non-empty string")
        candidate = Path(raw_path)
        if candidate.is_absolute():
            for virtual, actual in self.virtual_roots.items():
                if candidate == virtual or candidate.is_relative_to(virtual):
                    candidate = actual / candidate.relative_to(virtual)
                    break
        else:
            candidate = self.documents_root / candidate
        resolved = candidate.resolve(strict=False)
        allowed = self.output_root if write else None
        roots = (allowed,) if allowed else self.allowed_roots
        if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
            raise ToolFailure(f"Access denied - path outside allowed directories: {raw_path}")
        if write and resolved == self.output_root:
            raise ToolFailure("output path must name a file")
        return resolved

    def _trace(self, name: str, arguments: dict[str, Any], result: dict[str, Any], ok: bool) -> None:
        safe_arguments = dict(arguments)
        if name == "write_file" and isinstance(safe_arguments.get("content"), str):
            content = safe_arguments.pop("content")
            safe_arguments["content_sha256"] = sha256_text(content)
            safe_arguments["content_bytes"] = len(content.encode("utf-8"))
        entry = {
            "index": self._trace_count() + 1,
            "tool": name,
            "arguments": safe_arguments,
            "ok": ok,
        }
        if ok:
            text = ((result.get("content") or [{}])[0]).get("text", "")
            entry["result_sha256"] = sha256_text(text)
        else:
            entry["error"] = ((result.get("content") or [{}])[0]).get("text", "")
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(entry) + "\n")

    def _trace_count(self) -> int:
        if not self.trace_path.exists():
            return 0
        with self.trace_path.open(encoding="utf-8") as stream:
            return sum(1 for _ in stream)

    def call_tool(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        arguments = arguments or {}
        if name not in TOOLS_BY_NAME:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }
        with self._lock:
            try:
                result = self._dispatch(name, arguments)
                self._trace(name, arguments, result, True)
                return result
            except Exception as error:
                result = {
                    "content": [{"type": "text", "text": str(error)}],
                    "isError": True,
                }
                self._trace(name, arguments, result, False)
                return result

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "list_allowed_directories":
            if arguments:
                raise ToolFailure("list_allowed_directories does not accept arguments")
            return tool_result("Allowed directories:\n/workspace/documents\n/workspace/output")

        if name == "read_text_file":
            path = self._resolve(arguments.get("path"))
            if not path.is_file():
                raise ToolFailure(f"ENOENT: no such file, open '{arguments.get('path')}'")
            head = arguments.get("head")
            tail = arguments.get("tail")
            if head is not None and tail is not None:
                raise ToolFailure("Cannot specify both head and tail parameters simultaneously")
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)
            if head is not None:
                if not isinstance(head, (int, float)) or head < 0:
                    raise ToolFailure("head must be a non-negative number")
                content = "".join(lines[: int(head)])
            elif tail is not None:
                if not isinstance(tail, (int, float)) or tail < 0:
                    raise ToolFailure("tail must be a non-negative number")
                content = "".join(lines[-int(tail) :]) if tail else ""
            return tool_result(content)

        if name == "write_file":
            path = self._resolve(arguments.get("path"), write=True)
            content = arguments.get("content")
            if not isinstance(content, str):
                raise ToolFailure("content must be a string")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.counselbench.tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
            return tool_result(f"Successfully wrote to {arguments.get('path')}")

        if name == "directory_tree":
            root = self._resolve(arguments.get("path"))
            patterns = arguments.get("excludePatterns", [])
            if not isinstance(patterns, list):
                raise ToolFailure("excludePatterns must be an array")

            def tree(directory: Path, base: Path) -> list[dict[str, Any]]:
                entries: list[dict[str, Any]] = []
                for child in sorted(directory.iterdir(), key=lambda item: item.name):
                    relative = child.relative_to(base).as_posix()
                    if any(fnmatch.fnmatch(relative, pattern) for pattern in patterns):
                        continue
                    item: dict[str, Any] = {
                        "name": child.name,
                        "type": "directory" if child.is_dir() else "file",
                    }
                    if child.is_dir():
                        item["children"] = tree(child, base)
                    entries.append(item)
                return entries

            return tool_result(json.dumps(tree(root, root), indent=2))

        if name == "search_files":
            root = self._resolve(arguments.get("path"))
            pattern = arguments.get("pattern")
            excludes = arguments.get("excludePatterns", [])
            if not isinstance(pattern, str) or not pattern:
                raise ToolFailure("pattern must be a non-empty string")
            if not isinstance(excludes, list):
                raise ToolFailure("excludePatterns must be an array")
            matches: list[str] = []
            for child in root.rglob("*"):
                relative = child.relative_to(root).as_posix()
                basename_match = "/" not in pattern and fnmatch.fnmatch(child.name, pattern)
                path_match = fnmatch.fnmatch(relative, pattern)
                double_star_match = pattern.startswith("**/") and fnmatch.fnmatch(
                    relative, pattern[3:]
                )
                if not (basename_match or path_match or double_star_match):
                    continue
                if any(fnmatch.fnmatch(relative, excluded) for excluded in excludes):
                    continue
                if child.resolve().is_relative_to(self.documents_root):
                    rendered = Path("/workspace/documents") / child.resolve().relative_to(
                        self.documents_root
                    )
                else:
                    rendered = Path("/workspace/output") / child.resolve().relative_to(
                        self.output_root
                    )
                matches.append(str(rendered))
            return tool_result("\n".join(sorted(matches)) if matches else "No matches found")

        if name == "get_file_info":
            path = self._resolve(arguments.get("path"))
            if not path.exists():
                raise ToolFailure(f"ENOENT: no such file or directory, stat '{arguments.get('path')}'")
            info = path.stat()
            # Field names, ordering, booleans, and permission representation match
            # getFileStats() in the pinned upstream TypeScript implementation.
            text = "\n".join(
                [
                    f"size: {info.st_size}",
                    f"created: {self.spec['fixed_file_timestamp']}",
                    f"modified: {self.spec['fixed_file_timestamp']}",
                    f"accessed: {self.spec['fixed_file_timestamp']}",
                    f"isDirectory: {'true' if path.is_dir() else 'false'}",
                    f"isFile: {'true' if path.is_file() else 'false'}",
                    f"permissions: {stat.S_IMODE(info.st_mode):03o}",
                ]
            )
            return tool_result(text)

        raise ToolFailure(f"Unknown tool: {name}")

    def _trace_entries(self) -> list[dict[str, Any]]:
        if not self.trace_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.trace_path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def verify(self, token: str | None) -> dict[str, Any]:
        """Return a complete report only to the verifier holding the task token."""

        if not token or sha256_text(token) != self.spec["verify_token_sha256"]:
            raise PermissionError("not found")

        trace = self._trace_entries()
        successful = [entry for entry in trace if entry.get("ok")]
        full_reads = {
            str(entry["arguments"].get("path"))
            for entry in successful
            if entry.get("tool") == "read_text_file"
            and "head" not in entry["arguments"]
            and "tail" not in entry["arguments"]
        }
        info_paths = {
            str(entry["arguments"].get("path"))
            for entry in successful
            if entry.get("tool") == "get_file_info"
        }
        simple_calls = {entry.get("tool") for entry in successful}
        procedure: dict[str, bool] = {
            "minimum_successful_tool_calls": len(successful) >= self.spec["minimum_tool_calls"],
            "all_evidence_read_in_full": set(self.spec["required_document_paths"]) <= full_reads,
            "chain_of_custody_metadata_checked": set(self.spec["metadata_check_paths"]) <= info_paths,
            "allowed_directories_checked": "list_allowed_directories" in simple_calls,
            "recursive_inventory_completed": "directory_tree" in simple_calls,
            "targeted_search_completed": "search_files" in simple_calls,
        }

        output_files = sorted(
            path.relative_to(self.output_root).as_posix()
            for path in self.output_root.rglob("*")
            if path.is_file()
        )
        expected_names = sorted(self.spec["deliverables"])
        procedure["exact_deliverable_set"] = output_files == expected_names

        current_digests: dict[str, str] = {}
        for relative in expected_names:
            path = self.output_root / relative
            if path.is_file():
                current_digests[relative] = sha256_text(path.read_text(encoding="utf-8"))

        writes = {
            Path(str(entry["arguments"].get("path"))).name: entry["arguments"].get(
                "content_sha256"
            )
            for entry in successful
            if entry.get("tool") == "write_file"
        }
        procedure["deliverables_written_through_mcp"] = all(
            writes.get(Path(name).name) == current_digests.get(name) for name in expected_names
        )

        findings_path = self.output_root / "findings.json"
        findings_value: Any = None
        try:
            findings_value = json.loads(findings_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        memo_path = self.output_root / "advice.md"
        memo = memo_path.read_text(encoding="utf-8") if memo_path.is_file() else ""
        findings_scoring = score_findings(findings_value, self.spec)
        memo_scoring = score_memo(memo, self.spec)
        aggregate = aggregate_scores(procedure, findings_scoring, memo_scoring)
        checks = {
            **procedure,
            "findings_criteria_complete": findings_scoring["passed"],
            "memo_criteria_complete": memo_scoring["passed"],
        }
        report = {
            "schema_version": "1.1",
            "task_id": self.spec["task_id"],
            "passed": aggregate["passed"],
            "reward": aggregate["reward"],
            "checks": checks,
            "category_scores": aggregate["category_scores"],
            "score_weights": aggregate["weights"],
            "uncapped_reward": aggregate["uncapped_reward"],
            "reward_cap_reason": aggregate["cap_reason"],
            "criteria": {
                "procedure": procedure,
                "findings": findings_scoring,
                "memo": memo_scoring,
            },
            "successful_tool_calls": len(successful),
            "required_tool_calls": self.spec["minimum_tool_calls"],
            "documents_read": len(set(self.spec["required_document_paths"]) & full_reads),
            "required_documents": len(self.spec["required_document_paths"]),
            "output_sha256": current_digests,
            "diagnostics": {
                "legacy_exact_findings_match": findings_value == self.spec["expected_findings"],
                "legacy_exact_memo_match": memo == self.spec.get("expected_memo", ""),
                "deterministic": True,
                "model_calls": 0,
                "network_calls": 0,
            },
        }
        report["report_sha256"] = sha256_text(canonical_json(report))
        return report
