"""Deterministic multi-provider MCP world and hidden CounselScore verifier.

The world serves synthetic, task-scoped Clio Manage, Gmail, Drive, and Slack
resources through documented provider-operation contracts. It has no model,
network, wall-clock, locale, or random dependency in the grading path.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from copy import deepcopy
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any

try:  # Package import in local qualification; flat import in generated image.
    from .contracts import MUTATION_TOOLS, TOOLS_BY_NAME, tool_definitions
    from .scoring import (
        score_advice,
        score_decision,
        score_notification,
        score_register,
    )
except ImportError:  # pragma: no cover - exercised inside the task container
    from contracts import MUTATION_TOOLS, TOOLS_BY_NAME, tool_definitions
    from scoring import score_advice, score_decision, score_notification, score_register


class ToolFailure(Exception):
    """A tool-level failure returned using the MCP ``isError`` convention."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_base64url(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def tool_result(value: Any) -> dict[str, Any]:
    text = value if isinstance(value, str) else canonical_json(value)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": value if isinstance(value, dict) else {"content": value},
    }


def _result_text(result: dict[str, Any]) -> str:
    return str(((result.get("content") or [{}])[0]).get("text", ""))


def _mime_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.casefold()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".eml": "message/rfc822",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(suffix, "application/octet-stream")


class CounselWorld:
    """One isolated enterprise matter with append-only provider trace evidence."""

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
        self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.assets = list(self.spec["provider_assets"])
        self.assets_by_provider = {
            provider: [asset for asset in self.assets if asset["provider"] == provider]
            for provider in ("clio_manage", "gmail", "google_drive", "slack")
        }
        # Fail the world at startup if its immutable provider objects are not
        # actually readable. Search results without retrievable source bytes
        # create a misleading MCP that passes schema tests but cannot support a
        # real agent trajectory.
        for asset in self.assets:
            self._asset_bytes(asset)
        self._lock = threading.Lock()
        self._next_trace_index = 1
        self._mutations: list[dict[str, Any]] = []
        self._rejected_mutations: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Reset generated episode state; seeded source records remain immutable."""

        if self.trace_path.exists():
            self.trace_path.unlink()
        self._next_trace_index = 1
        self._mutations.clear()
        self._rejected_mutations.clear()

    def list_tools(self) -> list[dict[str, Any]]:
        return tool_definitions()

    def _asset_bytes(self, asset: dict[str, Any]) -> bytes:
        virtual = PurePosixPath(asset["path"])
        root = PurePosixPath("/workspace/documents")
        try:
            relative = virtual.relative_to(root)
        except ValueError as error:
            raise ToolFailure(f"invalid seeded asset path: {asset['path']}") from error
        path = self.documents_root.joinpath(*relative.parts).resolve()
        if not path.is_relative_to(self.documents_root) or not path.is_file():
            raise ToolFailure(f"seeded provider object is unavailable: {asset['evidence_id']}")
        value = path.read_bytes()
        if hashlib.sha256(value).hexdigest() != asset["sha256"]:
            raise ToolFailure(f"seeded provider object digest mismatch: {asset['evidence_id']}")
        return value

    def _asset_text(self, asset: dict[str, Any]) -> str:
        return self._asset_bytes(asset).decode("utf-8", errors="replace")

    def _find_asset(self, provider: str, resource_id: Any) -> dict[str, Any]:
        for asset in self.assets_by_provider[provider]:
            if str(asset["resource_id"]) == str(resource_id):
                return asset
        raise ToolFailure(f"{provider} record not found for id={resource_id!r}")

    def _safe_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in MUTATION_TOOLS:
            return deepcopy(arguments)

        def redact(value: Any, key: str = "") -> Any:
            if isinstance(value, dict):
                return {child: redact(item, child) for child, item in value.items()}
            if isinstance(value, list):
                return [redact(item, key) for item in value]
            if isinstance(value, str) and key in {"raw", "text", "content", "detail", "value"}:
                return {
                    "sha256": sha256_text(value),
                    "bytes": len(value.encode("utf-8")),
                }
            return value

        return redact(arguments)

    def _evidence_proof(
        self,
        name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, str] | None:
        """Bind a successful content-bearing provider read to its source object.

        Provider SDKs commonly expose optional response projections (for example,
        Google Drive ``fields`` or Clio ``fields``).  Those projections are not
        part of the employee's evidentiary act.  The immutable object identifier
        and the bytes actually returned are.  Record a server-authored proof so
        the verifier can accept equivalent projections without accepting a list,
        metadata-only lookup, or a neighboring object.
        """

        asset: dict[str, Any] | None = None
        returned_bytes: bytes | None = None
        structured = result.get("structuredContent") or {}
        if name == "clio_manage.notes.get":
            identifier = arguments.get("id")
            if str(identifier) != str(self.spec["state_contract"]["note_id"]):
                asset = self._find_asset("clio_manage", identifier)
                detail = (structured.get("data") or {}).get("detail")
                if not isinstance(detail, str):
                    return None
                returned_bytes = detail.encode("utf-8")
        elif name == "gmail.messages.get":
            format_name = str(arguments.get("format") or "full")
            if format_name not in {"full", "raw"}:
                return None
            identifier = arguments.get("id")
            if str(identifier) == str(self.spec["state_contract"]["notification_id"]):
                return None
            asset = self._find_asset("gmail", identifier)
            if format_name == "raw":
                encoded = structured.get("raw")
                if not isinstance(encoded, str):
                    return None
            else:
                encoded = ((structured.get("payload") or {}).get("body") or {}).get(
                    "data"
                )
                if not isinstance(encoded, str):
                    return None
            try:
                returned_bytes = _decode_base64url(encoded)
            except (ValueError, UnicodeError):
                return None
        elif name == "google_drive.files.get":
            if arguments.get("alt") != "media":
                return None
            asset = self._find_asset("google_drive", arguments.get("fileId"))
            encoded = (structured.get("media") or {}).get("data")
            if not isinstance(encoded, str):
                return None
            try:
                returned_bytes = _decode_base64url(encoded)
            except (ValueError, UnicodeError):
                return None
        elif name == "slack.conversations_replies":
            asset = next(
                (
                    item
                    for item in self.assets_by_provider["slack"]
                    if item["channel"] == arguments.get("channel")
                    and item["ts"] == arguments.get("ts")
                ),
                None,
            )
            if asset is None:
                return None
            messages = structured.get("messages") or []
            if messages != self._slack_messages(asset):
                return None
        if asset is None:
            return None
        if (
            returned_bytes is not None
            and hashlib.sha256(returned_bytes).hexdigest() != asset["sha256"]
        ):
            return None
        return {
            "evidence_id": asset["evidence_id"],
            "provider": asset["provider"],
            "sha256": asset["sha256"],
        }

    def _state_readback_proof(
        self,
        name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> str | None:
        """Identify a successful response that actually exposes persisted state."""

        state = self.spec["state_contract"]
        structured = result.get("structuredContent") or {}
        if name == "clio_manage.matters.get" and arguments.get("id") == state["matter_id"]:
            mutation = self._latest_mutation("clio_manage.matters.update")
            if mutation is None:
                return None
            expected_values = (
                (mutation.get("arguments") or {}).get("data") or {}
            ).get("custom_field_values") or []
            expected = next(
                (
                    value
                    for value in expected_values
                    if isinstance(value, dict)
                    and str(value.get("id")) == str(state["custom_value_id"])
                ),
                None,
            )
            data = structured.get("data") or {}
            values = data.get("custom_field_values") or []
            if str(data.get("id")) == str(state["matter_id"]) and any(
                isinstance(value, dict)
                and str((value.get("custom_field") or {}).get("id"))
                == str(state["custom_field_id"])
                and isinstance(expected, dict)
                and value.get("value") == expected.get("value")
                for value in values
            ):
                return "matter-register"
        if name == "clio_manage.notes.get" and arguments.get("id") == state["note_id"]:
            mutation = self._latest_mutation("clio_manage.notes.create")
            if mutation is None:
                return None
            expected = (mutation.get("arguments") or {}).get("data") or {}
            data = structured.get("data") or {}
            if str(data.get("id")) == str(state["note_id"]) and all(
                data.get(key) == expected.get(key)
                for key in ("subject", "detail", "detail_text_type", "regarding")
            ):
                return "decision-note"
        if name == "gmail.messages.get" and str(arguments.get("id")) == str(
            state["notification_id"]
        ):
            mutation = self._latest_mutation("gmail.messages.send")
            if mutation is None:
                return None
            expected_raw = (
                (mutation.get("arguments") or {}).get("requestBody") or {}
            ).get("raw")
            format_name = str(arguments.get("format") or "full")
            if format_name == "raw" and structured.get("raw") == expected_raw:
                return "notification"
            if format_name == "full" and (
                ((structured.get("payload") or {}).get("body") or {}).get("data")
                == expected_raw
            ):
                return "notification"
        if name == "google_drive.comments.get":
            mutation = self._latest_mutation("google_drive.comments.create")
            expected_content = (
                (((mutation or {}).get("arguments") or {}).get("requestBody") or {}).get(
                    "content"
                )
            )
            if (
                mutation is not None
                and str(structured.get("id")) == str(state["notification_id"])
                and structured.get("content") == expected_content
            ):
                return "notification"
        if name == "slack.conversations_replies":
            mutation = self._latest_mutation("slack.chat_postMessage")
            if mutation is None:
                return None
            expected = mutation.get("arguments") or {}
            messages = structured.get("messages") or []
            if any(
                isinstance(message, dict)
                and str(message.get("ts")) == str(state["notification_id"])
                and message.get("text") == expected.get("text")
                and message.get("thread_ts") == expected.get("thread_ts")
                and arguments.get("channel") == expected.get("channel")
                and arguments.get("ts") == expected.get("thread_ts")
                for message in messages
            ):
                return "notification"
        return None

    def _trace(
        self,
        name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
        ok: bool,
    ) -> int:
        index = self._next_trace_index
        self._next_trace_index += 1
        entry: dict[str, Any] = {
            "index": index,
            "tool": name,
            "arguments": self._safe_arguments(name, arguments),
            "ok": ok,
        }
        if ok:
            entry["result_sha256"] = sha256_text(_result_text(result))
            evidence_proof = self._evidence_proof(name, arguments, result)
            if evidence_proof is not None:
                entry["evidence_proof"] = evidence_proof
            state_readback = self._state_readback_proof(name, arguments, result)
            if state_readback is not None:
                entry["state_readback"] = state_readback
        else:
            entry["error"] = _result_text(result)
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(entry) + "\n")
        return index

    def call_tool(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        arguments = arguments or {}
        if name not in TOOLS_BY_NAME:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }
        if not isinstance(arguments, dict):
            arguments = {}
        with self._lock:
            try:
                result = self._dispatch(name, arguments)
                index = self._trace(name, arguments, result, True)
                if name in MUTATION_TOOLS:
                    self._mutations.append(
                        {
                            "index": index,
                            "tool": name,
                            "arguments": deepcopy(arguments),
                            "response_sha256": sha256_text(_result_text(result)),
                        }
                    )
                return result
            except Exception as error:
                result = {
                    "content": [{"type": "text", "text": str(error)}],
                    "isError": True,
                }
                index = self._trace(name, arguments, result, False)
                if name in MUTATION_TOOLS:
                    self._rejected_mutations.append(
                        {"index": index, "tool": name, "arguments": deepcopy(arguments)}
                    )
                return result

    def _latest_mutation(self, tool: str) -> dict[str, Any] | None:
        return next(
            (entry for entry in reversed(self._mutations) if entry["tool"] == tool),
            None,
        )

    @staticmethod
    def _merge_clio_matter_patch(
        matter: dict[str, Any], patch: dict[str, Any]
    ) -> dict[str, Any]:
        data = deepcopy(matter)
        changes = deepcopy(patch)
        custom_values = changes.pop("custom_field_values", None)
        data.update(changes)
        if isinstance(custom_values, list):
            existing = {
                str(value.get("id")): value
                for value in data.get("custom_field_values") or []
                if isinstance(value, dict)
            }
            for value in custom_values:
                if not isinstance(value, dict):
                    continue
                identifier = str(value.get("id"))
                if identifier in existing:
                    existing[identifier].update(value)
                else:
                    data.setdefault("custom_field_values", []).append(value)
        return data

    def _clio_matter(self) -> dict[str, Any]:
        state = self.spec["state_contract"]
        expected = self.spec["expected_matter"]
        data = deepcopy(expected)
        update = self._latest_mutation("clio_manage.matters.update")
        if update:
            data = self._merge_clio_matter_patch(
                data, update["arguments"].get("data") or {}
            )
            data["etag"] = f'"matter-{state["matter_id"]}-v2"'
        return {"data": data}

    def _clio_seeded_note(self, asset: dict[str, Any]) -> dict[str, Any]:
        return {
            "data": {
                "id": asset["resource_id"],
                "etag": f'"{asset["sha256"][:16]}"',
                "subject": asset["name"],
                "detail": self._asset_text(asset),
                "detail_text_type": "plain_text",
                "updated_at": asset["modified_time"],
                "regarding": {"id": asset["matter_id"], "type": "Matter"},
            }
        }

    @staticmethod
    def _clio_note_summary(note: dict[str, Any]) -> dict[str, Any]:
        return {
            key: deepcopy(note[key])
            for key in ("id", "etag", "subject", "updated_at", "regarding")
            if key in note
        }

    def _clio_created_note(self) -> dict[str, Any] | None:
        mutation = self._latest_mutation("clio_manage.notes.create")
        if not mutation:
            return None
        data = deepcopy(mutation["arguments"].get("data") or {})
        data.update(
            {
                "id": self.spec["state_contract"]["note_id"],
                "etag": f'"note-{self.spec["state_contract"]["note_id"]}-v1"',
                "created_at": self.spec["fixed_file_timestamp"],
                "updated_at": self.spec["fixed_file_timestamp"],
            }
        )
        return {"data": data}

    def _gmail_seeded_message(self, asset: dict[str, Any], format_name: str) -> dict[str, Any]:
        raw = self._asset_bytes(asset)
        value: dict[str, Any] = {
            "id": asset["resource_id"],
            "threadId": asset["thread_id"],
            "labelIds": ["INBOX"],
            "snippet": self._asset_text(asset)[:180].replace("\n", " "),
            "sizeEstimate": len(raw),
            "historyId": str(50_000_000 + int(asset["evidence_id"].split("-")[-1])),
        }
        if format_name == "raw":
            value["raw"] = _base64url(raw)
        elif format_name not in {"minimal", "metadata"}:
            value["payload"] = {
                "mimeType": _mime_type(asset["path"]),
                "filename": asset["name"],
                "headers": [
                    {"name": "Subject", "value": asset["name"]},
                    {"name": "X-Matter-Evidence-ID", "value": asset["evidence_id"]},
                ],
                "body": {"size": len(raw), "data": _base64url(raw)},
            }
        return value

    def _gmail_sent_message(self, format_name: str) -> dict[str, Any] | None:
        mutation = self._latest_mutation("gmail.messages.send")
        if not mutation:
            return None
        body = mutation["arguments"].get("requestBody") or {}
        raw = str(body.get("raw") or "")
        try:
            decoded = _decode_base64url(raw).decode("utf-8", errors="replace")
        except (ValueError, UnicodeError):
            decoded = ""
        value: dict[str, Any] = {
            "id": self.spec["state_contract"]["notification_id"],
            "threadId": body.get("threadId", f"sent-thread-{self.spec['task_id']}"),
            "labelIds": ["SENT"],
            "snippet": decoded.split("\r\n\r\n", 1)[-1][:180],
            "sizeEstimate": len(decoded.encode("utf-8")),
            "historyId": "99000001",
        }
        if format_name == "raw":
            value["raw"] = raw
        elif format_name not in {"minimal", "metadata"}:
            value["payload"] = {
                "mimeType": "message/rfc822",
                "body": {"size": len(decoded.encode("utf-8")), "data": raw},
            }
        return value

    def _drive_file(self, asset: dict[str, Any], *, media: bool) -> dict[str, Any]:
        raw = self._asset_bytes(asset)
        metadata = {
            "kind": "drive#file",
            "id": asset["resource_id"],
            "name": asset["name"],
            "mimeType": _mime_type(asset["path"]),
            "modifiedTime": asset["modified_time"],
            "version": "1",
            "md5Checksum": hashlib.md5(raw, usedforsecurity=False).hexdigest(),
            "size": str(len(raw)),
        }
        if media:
            metadata["media"] = {"encoding": "base64url", "data": _base64url(raw)}
            metadata["text"] = raw.decode("utf-8", errors="replace")
        return metadata

    def _drive_comment(self) -> dict[str, Any] | None:
        mutation = self._latest_mutation("google_drive.comments.create")
        if not mutation:
            return None
        body = mutation["arguments"].get("requestBody") or {}
        return {
            "kind": "drive#comment",
            "id": self.spec["state_contract"]["notification_id"],
            "content": body.get("content", ""),
            "createdTime": self.spec["fixed_file_timestamp"],
            "modifiedTime": self.spec["fixed_file_timestamp"],
            "resolved": False,
        }

    @staticmethod
    def _slack_reply_ts(root_ts: str, offset: int) -> str:
        seconds, fraction = root_ts.split(".", 1)
        return f"{seconds}.{int(fraction) + offset:06d}"

    def _slack_messages(self, asset: dict[str, Any]) -> list[dict[str, Any]]:
        """Render a seeded export as the human Slack thread it represents."""

        raw = self._asset_text(asset)
        payload: dict[str, Any] | None = None
        if PurePosixPath(asset["path"]).suffix.casefold() == ".json":
            try:
                candidate = json.loads(raw)
                payload = candidate if isinstance(candidate, dict) else None
            except json.JSONDecodeError:
                payload = None
        root_text = raw
        if payload is not None:
            root_text = "\n".join(
                value
                for value in (
                    f"*{payload.get('subject', asset['name'])}* — {payload.get('matter_number', '')}".rstrip(" —"),
                    str(payload.get("body") or ""),
                    f"Source: {payload.get('source_system', 'matter workspace')} · evidence {asset['evidence_id']}",
                )
                if value
            )
        root = {
            "type": "message",
            "user": f"U{int(asset['evidence_id'].split('-')[-1]):08d}",
            "text": root_text,
            "ts": asset["ts"],
            "thread_ts": asset["ts"],
            "metadata": {
                "event_type": "matter_evidence",
                "event_payload": {"evidence_id": asset["evidence_id"]},
            },
        }
        if payload is None:
            return [root]

        replies: list[str] = []
        for section in payload.get("sections") or []:
            if isinstance(section, dict):
                replies.append(
                    f"*{section.get('heading', 'Record detail')}*\n{section.get('text', '')}"
                )
        chronology = payload.get("chronology") or []
        if chronology:
            replies.append(
                "*Thread chronology*\n"
                + "\n".join(
                    f"• {row.get('date', '')} — {row.get('actor', '')}: "
                    f"{row.get('event', '')} ({row.get('reference', '')})"
                    for row in chronology
                    if isinstance(row, dict)
                )
            )
        rows = [row for row in payload.get("rows") or [] if isinstance(row, dict)]
        for start in range(0, len(rows), 6):
            batch = rows[start : start + 6]
            replies.append(
                f"*Approval-bot source rows {start + 1}–{start + len(batch)}*\n"
                + "\n".join(
                    f"• {row.get('line_id', '')} · {row.get('status', '')} · "
                    f"{row.get('effective_date', '')} · {row.get('metric', '')} — "
                    f"{row.get('note', '')}"
                    for row in batch
                )
            )
        return [
            root,
            *[
                {
                    "type": "message",
                    "user": f"U{int(asset['evidence_id'].split('-')[-1]) + index:08d}",
                    "text": text,
                    "ts": self._slack_reply_ts(asset["ts"], index),
                    "thread_ts": asset["ts"],
                }
                for index, text in enumerate(replies, start=1)
            ],
        ]

    def _slack_posted_message(self) -> dict[str, Any] | None:
        mutation = self._latest_mutation("slack.chat_postMessage")
        if not mutation:
            return None
        arguments = mutation["arguments"]
        return {
            "type": "message",
            "user": "UCOUNSEL",
            "text": arguments.get("text", ""),
            "ts": self.spec["state_contract"]["notification_id"],
            "thread_ts": arguments.get("thread_ts"),
        }

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        state = self.spec["state_contract"]
        if name == "clio_manage.matters.list":
            return tool_result({"data": [self._clio_matter()["data"]], "meta": {"paging": {}}})
        if name == "clio_manage.matters.get":
            if arguments.get("id") != state["matter_id"]:
                raise ToolFailure(f"Clio matter not found for id={arguments.get('id')!r}")
            return tool_result(self._clio_matter())
        if name == "clio_manage.matters.update":
            if arguments.get("id") != state["matter_id"]:
                raise ToolFailure("Clio matter update is outside the isolated matter scope")
            if not isinstance(arguments.get("data"), dict):
                raise ToolFailure("data must be an object")
            # The response is synthesized from this request before the mutation
            # is appended, so return the provider's patched representation here.
            data = self._merge_clio_matter_patch(
                self.spec["expected_matter"], arguments["data"]
            )
            data["etag"] = f'"matter-{state["matter_id"]}-v2"'
            return tool_result({"data": data})
        if name == "clio_manage.notes.list":
            if arguments.get("type") != "matter":
                return tool_result({"data": [], "meta": {"paging": {}}})
            values = [
                self._clio_note_summary(self._clio_seeded_note(asset)["data"])
                for asset in self.assets_by_provider["clio_manage"]
            ]
            created = self._clio_created_note()
            if created:
                values.append(self._clio_note_summary(created["data"]))
            return tool_result({"data": values, "meta": {"paging": {}}})
        if name == "clio_manage.notes.get":
            if arguments.get("id") == state["note_id"]:
                created = self._clio_created_note()
                if not created:
                    raise ToolFailure(f"Clio note not found for id={state['note_id']}")
                return tool_result(created)
            return tool_result(self._clio_seeded_note(self._find_asset("clio_manage", arguments.get("id"))))
        if name == "clio_manage.notes.create":
            data = arguments.get("data")
            regarding = data.get("regarding") if isinstance(data, dict) else None
            if not isinstance(data, dict) or not isinstance(regarding, dict):
                raise ToolFailure("data.regarding must be an object")
            if regarding.get("id") != state["matter_id"] or regarding.get("type") != "Matter":
                raise ToolFailure("Clio note is outside the isolated matter scope")
            response = deepcopy(data)
            response.update(
                {
                    "id": state["note_id"],
                    "etag": f'"note-{state["note_id"]}-v1"',
                    "created_at": self.spec["fixed_file_timestamp"],
                    "updated_at": self.spec["fixed_file_timestamp"],
                }
            )
            return tool_result({"data": response})
        if name == "gmail.messages.list":
            messages = [
                {"id": asset["resource_id"], "threadId": asset["thread_id"]}
                for asset in self.assets_by_provider["gmail"]
            ]
            sent = self._gmail_sent_message("minimal")
            if sent:
                messages.append({"id": sent["id"], "threadId": sent["threadId"]})
            return tool_result({"messages": messages, "resultSizeEstimate": len(messages)})
        if name == "gmail.messages.get":
            format_name = str(arguments.get("format") or "full")
            if str(arguments.get("id")) == str(state["notification_id"]):
                sent = self._gmail_sent_message(format_name)
                if sent:
                    return tool_result(sent)
            return tool_result(self._gmail_seeded_message(self._find_asset("gmail", arguments.get("id")), format_name))
        if name == "gmail.messages.send":
            if state["notification_provider"] != "gmail":
                raise ToolFailure("Gmail send is not authorized for this matter's completion channel")
            body = arguments.get("requestBody")
            if (
                arguments.get("userId") != "me"
                or not isinstance(body, dict)
                or not isinstance(body.get("raw"), str)
            ):
                raise ToolFailure(
                    "userId='me' and requestBody.raw RFC 2822 data are required"
                )
            try:
                _decode_base64url(body["raw"])
            except (ValueError, UnicodeError) as error:
                raise ToolFailure(
                    "requestBody.raw must be valid base64url RFC 2822 data"
                ) from error
            response = self._gmail_sent_message("minimal") or {
                "id": state["notification_id"],
                "threadId": body.get(
                    "threadId", f"sent-thread-{self.spec['task_id']}"
                ),
                "labelIds": ["SENT"],
            }
            return tool_result(response)
        if name == "google_drive.files.list":
            files = [self._drive_file(asset, media=False) for asset in self.assets_by_provider["google_drive"]]
            return tool_result({"kind": "drive#fileList", "files": files, "incompleteSearch": False})
        if name == "google_drive.files.get":
            asset = self._find_asset("google_drive", arguments.get("fileId"))
            return tool_result(self._drive_file(asset, media=arguments.get("alt") == "media"))
        if name == "google_drive.comments.list":
            self._find_asset("google_drive", arguments.get("fileId"))
            comment = self._drive_comment()
            comments = [comment] if comment else []
            return tool_result({"kind": "drive#commentList", "comments": comments})
        if name == "google_drive.comments.get":
            self._find_asset("google_drive", arguments.get("fileId"))
            comment = self._drive_comment()
            if not comment or str(arguments.get("commentId")) != str(comment["id"]):
                raise ToolFailure(f"Drive comment not found for id={arguments.get('commentId')!r}")
            return tool_result(comment)
        if name == "google_drive.comments.create":
            if state["notification_provider"] != "google_drive":
                raise ToolFailure("Drive comment is not authorized for this matter's completion channel")
            self._find_asset("google_drive", arguments.get("fileId"))
            body = arguments.get("requestBody")
            if not isinstance(body, dict) or not isinstance(body.get("content"), str):
                raise ToolFailure("requestBody.content must be a string")
            return tool_result(
                {
                    "kind": "drive#comment",
                    "id": state["notification_id"],
                    "content": body["content"],
                    "createdTime": self.spec["fixed_file_timestamp"],
                    "modifiedTime": self.spec["fixed_file_timestamp"],
                    "resolved": False,
                }
            )
        if name == "slack.search_messages":
            matches = [
                {
                    "iid": asset["evidence_id"],
                    "channel_id": asset["channel"],
                    "ts": asset["ts"],
                    "text": self._slack_messages(asset)[0]["text"][:280],
                }
                for asset in self.assets_by_provider["slack"]
            ]
            return tool_result({"ok": True, "query": arguments.get("query"), "messages": {"matches": matches, "total": len(matches)}})
        if name == "slack.conversations_history":
            channel = arguments.get("channel")
            values = [
                self._slack_messages(asset)[0]
                for asset in self.assets_by_provider["slack"]
                if asset["channel"] == channel
            ]
            return tool_result({"ok": True, "messages": values, "has_more": False})
        if name == "slack.conversations_replies":
            channel = arguments.get("channel")
            ts = arguments.get("ts")
            asset = next(
                (
                    item for item in self.assets_by_provider["slack"]
                    if item["channel"] == channel and item["ts"] == ts
                ),
                None,
            )
            if asset is None:
                raise ToolFailure(f"Slack thread not found for channel={channel!r}, ts={ts!r}")
            values = self._slack_messages(asset)
            posted = self._slack_posted_message()
            if posted and posted.get("thread_ts") == ts:
                values.append(posted)
            return tool_result({"ok": True, "messages": values, "has_more": False})
        if name == "slack.chat_postMessage":
            if state["notification_provider"] != "slack":
                raise ToolFailure("Slack post is not authorized for this matter's completion channel")
            channel = arguments.get("channel")
            thread_ts = arguments.get("thread_ts")
            if not any(asset["channel"] == channel and asset["ts"] == thread_ts for asset in self.assets_by_provider["slack"]):
                raise ToolFailure("Slack completion post is outside the isolated matter thread")
            if not isinstance(arguments.get("text"), str):
                raise ToolFailure("text must be a string")
            message = {
                "type": "message",
                "user": "UCOUNSEL",
                "text": arguments["text"],
                "ts": state["notification_id"],
                "thread_ts": thread_ts,
            }
            return tool_result({"ok": True, "channel": channel, "ts": message["ts"], "message": message})
        raise ToolFailure(f"Unknown tool: {name}")

    def _trace_entries(self) -> list[dict[str, Any]]:
        if not self.trace_path.exists():
            return []
        with self.trace_path.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def _mutation_scope_matches(
        self,
        name: str,
        arguments: dict[str, Any],
        expected: dict[str, Any],
    ) -> bool:
        """Validate the provider target and write surface, not oracle prose."""

        state = self.spec["state_contract"]
        if name == "clio_manage.matters.update":
            data = arguments.get("data")
            values = data.get("custom_field_values") if isinstance(data, dict) else None
            if (
                arguments.get("id") != state["matter_id"]
                or set(arguments) - {"id", "fields", "data"}
                or not isinstance(data, dict)
                or set(data) != {"custom_field_values"}
                or not isinstance(values, list)
                or len(values) != 1
                or not isinstance(values[0], dict)
            ):
                return False
            field = values[0]
            custom_field = field.get("custom_field")
            return bool(
                field.get("id") == state["custom_value_id"]
                and isinstance(field.get("value"), str)
                and set(field) <= {"id", "value", "custom_field"}
                and (
                    custom_field is None
                    or custom_field == {"id": state["custom_field_id"]}
                )
            )
        if name == "clio_manage.notes.create":
            data = arguments.get("data")
            regarding = data.get("regarding") if isinstance(data, dict) else None
            return bool(
                set(arguments) <= {"fields", "data"}
                and isinstance(data, dict)
                and set(data)
                <= {"subject", "detail", "detail_text_type", "regarding"}
                and isinstance(data.get("subject"), str)
                and isinstance(data.get("detail"), str)
                and regarding == {"id": state["matter_id"], "type": "Matter"}
            )
        if name == "slack.chat_postMessage":
            return bool(
                arguments.get("channel") == expected.get("channel")
                and arguments.get("thread_ts") == expected.get("thread_ts")
                and isinstance(arguments.get("text"), str)
                and set(arguments) <= {"channel", "thread_ts", "text"}
            )
        if name == "google_drive.comments.create":
            body = arguments.get("requestBody")
            return bool(
                arguments.get("fileId") == expected.get("fileId")
                and isinstance(body, dict)
                and isinstance(body.get("content"), str)
                and set(body) == {"content"}
                and set(arguments) <= {"fileId", "fields", "requestBody"}
            )
        if name == "gmail.messages.send":
            body = arguments.get("requestBody")
            expected_body = expected.get("requestBody") or {}
            if (
                arguments.get("userId") != expected.get("userId")
                or not isinstance(body, dict)
                or not isinstance(body.get("raw"), str)
                or set(body) - {"raw", "threadId"}
                or set(arguments) != {"userId", "requestBody"}
            ):
                return False
            try:
                actual_message = BytesParser(policy=policy.default).parsebytes(
                    _decode_base64url(body["raw"])
                )
                expected_message = BytesParser(policy=policy.default).parsebytes(
                    _decode_base64url(expected_body["raw"])
                )
            except (KeyError, TypeError, ValueError):
                return False
            return bool(
                actual_message.get("To") == expected_message.get("To")
                and actual_message.get("Subject") == expected_message.get("Subject")
                and body.get("threadId") == expected_body.get("threadId")
            )
        return False

    @staticmethod
    def _notification_text(name: str, arguments: dict[str, Any]) -> str:
        if name == "slack.chat_postMessage":
            return arguments.get("text") if isinstance(arguments.get("text"), str) else ""
        if name == "google_drive.comments.create":
            body = arguments.get("requestBody")
            return body.get("content") if isinstance(body, dict) and isinstance(body.get("content"), str) else ""
        if name == "gmail.messages.send":
            body = arguments.get("requestBody")
            try:
                message = BytesParser(policy=policy.default).parsebytes(
                    _decode_base64url(body["raw"])
                )
                content = message.get_body(preferencelist=("plain",))
                return content.get_content() if content is not None else message.get_content()
            except (AttributeError, KeyError, TypeError, ValueError):
                return ""
        return ""

    def _actual_state_values(
        self,
    ) -> tuple[Any, Any, str, str, bool, bool, bool, bool]:
        expected_by_tool = {call["name"]: call for call in self.spec["state_contract"]["writes"]}
        actual_by_tool: dict[str, list[dict[str, Any]]] = {}
        for mutation in self._mutations:
            actual_by_tool.setdefault(mutation["tool"], []).append(mutation)
        exact_set = (
            set(actual_by_tool) == set(expected_by_tool)
            and all(len(values) == 1 for values in actual_by_tool.values())
        )
        matter_mutation = (actual_by_tool.get("clio_manage.matters.update") or [{}])[-1]
        note_mutation = (actual_by_tool.get("clio_manage.notes.create") or [{}])[-1]
        notification_tool = next(
            call["name"]
            for call in self.spec["state_contract"]["writes"]
            if call["phase"] == "state-transition:notification"
        )
        notification_mutation = (actual_by_tool.get(notification_tool) or [{}])[-1]
        matter_exact = self._mutation_scope_matches(
            "clio_manage.matters.update",
            matter_mutation.get("arguments") or {},
            expected_by_tool["clio_manage.matters.update"]["arguments"],
        )
        note_exact = self._mutation_scope_matches(
            "clio_manage.notes.create",
            note_mutation.get("arguments") or {},
            expected_by_tool["clio_manage.notes.create"]["arguments"],
        )
        notification_exact = self._mutation_scope_matches(
            notification_tool,
            notification_mutation.get("arguments") or {},
            expected_by_tool[notification_tool]["arguments"],
        )

        register: Any = None
        decision: Any = None
        advice = ""
        notification = self._notification_text(
            notification_tool, notification_mutation.get("arguments") or {}
        )
        try:
            field_values = matter_mutation["arguments"]["data"]["custom_field_values"]
            register_text = field_values[0]["value"]
            try:
                parsed_register = json.loads(register_text)
                register = parsed_register if isinstance(parsed_register, dict) else register_text
            except json.JSONDecodeError:
                register = register_text
        except (KeyError, IndexError, TypeError):
            register = None
        try:
            detail = note_mutation["arguments"]["data"]["detail"]
            try:
                note = json.loads(detail)
            except json.JSONDecodeError:
                note = None
            if isinstance(note, dict) and isinstance(note.get("decision"), dict):
                decision = note["decision"]
                advice = note.get("advice_markdown") if isinstance(note.get("advice_markdown"), str) else detail
            else:
                decision = detail
                advice = detail
        except (KeyError, TypeError):
            decision = None
        return (
            decision,
            register,
            advice,
            notification,
            exact_set,
            matter_exact,
            note_exact,
            notification_exact,
        )

    @staticmethod
    def _decision_milestone(identifier: str) -> str:
        if identifier.startswith("choice.") or identifier.startswith("top_level.") or identifier == "decision_is_object":
            return "reasoning.options"
        if identifier in {
            "actions.exact_count",
            "holds.exact_count",
            "actions.exact_population",
            "holds.exact_population",
            "populations.disjoint",
        } or identifier.endswith(".present"):
            return "reasoning.branches"
        return "reasoning.actions"

    @staticmethod
    def _advice_milestone(identifier: str) -> str:
        if identifier.startswith("alternative.") or identifier.startswith("summary."):
            return "reasoning.options"
        if identifier.startswith("action."):
            return "reasoning.actions"
        if identifier.startswith("hold."):
            return "reasoning.branches"
        if identifier == "forbidden_claims_absent":
            return "containment.scope"
        return "state.legal_note"

    def verify(self, token: str | None) -> dict[str, Any]:
        """Return a complete deterministic report only to the verifier token holder."""

        if not token or sha256_text(token) != self.spec["verify_token_sha256"]:
            raise PermissionError("not found")
        trace = self._trace_entries()
        successful = [entry for entry in trace if entry.get("ok")]
        first_mutation = min((entry["index"] for entry in self._mutations), default=None)

        discovery_tools = {
            "clio_manage.matters.list",
            "clio_manage.notes.list",
            "gmail.messages.list",
            "google_drive.files.list",
            "slack.search_messages",
        }
        successful_tools = {entry["tool"] for entry in successful}
        discovery_complete = discovery_tools <= successful_tools
        evidence_results: list[tuple[dict[str, Any], bool, bool]] = []
        for asset in self.assets:
            if not asset["material"]:
                continue
            matching = [
                entry
                for entry in successful
                if (entry.get("evidence_proof") or {}).get("evidence_id")
                == asset["evidence_id"]
                and (entry.get("evidence_proof") or {}).get("sha256")
                == asset["sha256"]
            ]
            content_read = bool(matching)
            read_before_write = any(
                first_mutation is None or entry["index"] < first_mutation
                for entry in matching
            )
            evidence_results.append((asset, content_read, read_before_write))
        all_evidence = all(content_read for _, content_read, _ in evidence_results)
        all_evidence_prewrite = all(
            read_before_write for _, _, read_before_write in evidence_results
        )

        (
            decision,
            register,
            advice,
            notification,
            exact_mutation_set,
            matter_state_exact,
            note_state_exact,
            notification_exact,
        ) = self._actual_state_values()
        decision_scoring = score_decision(decision, self.spec)
        register_scoring = score_register(register, self.spec)
        advice_scoring = score_advice(advice, self.spec)
        notification_scoring = score_notification(notification, self.spec)
        write_scope_contained = (
            exact_mutation_set
            and matter_state_exact
            and note_state_exact
            and notification_exact
        )

        readback_checks: dict[str, bool] = {}
        after_tools = {
            "matter-register": "clio_manage.matters.update",
            "decision-note": "clio_manage.notes.create",
            "notification": next(
                call["name"]
                for call in self.spec["state_contract"]["writes"]
                if call["phase"] == "state-transition:notification"
            ),
        }
        for call in self.spec["state_contract"]["readbacks"]:
            label = call["phase"].split(":", 1)[1]
            mutation = self._latest_mutation(after_tools[label])
            if mutation is None:
                readback_checks[label] = False
                continue
            readback_checks[label] = any(
                entry["index"] > mutation["index"]
                and entry["tool"] == call["name"]
                and entry.get("state_readback") == label
                for entry in successful
            )

        procedure = {
            "minimum_successful_tool_calls": len(successful) >= self.spec["minimum_tool_calls"],
            "provider_discovery_complete": discovery_complete,
            "all_material_evidence_read": all_evidence,
            "all_material_evidence_precedes_first_mutation": all_evidence_prewrite,
            "exact_mutation_set": exact_mutation_set,
            "write_scope_contained": write_scope_contained,
            "core_provider_state_exact": matter_state_exact and note_state_exact,
            "notification_state_exact": (
                notification_exact and notification_scoring["passed"]
            ),
            "core_state_precedes_notification": False,
            "all_provider_readbacks_complete": all(readback_checks.values()),
            "no_rejected_mutation": not self._rejected_mutations,
        }
        notification_tool = next(
            call["name"]
            for call in self.spec["state_contract"]["writes"]
            if call["phase"] == "state-transition:notification"
        )
        core_mutations = [
            self._latest_mutation("clio_manage.matters.update"),
            self._latest_mutation("clio_manage.notes.create"),
        ]
        notification_mutation = self._latest_mutation(notification_tool)
        procedure["core_state_precedes_notification"] = bool(
            notification_mutation
            and all(core_mutations)
            and max(entry["index"] for entry in core_mutations if entry)
            < notification_mutation["index"]
        )

        atomic: list[dict[str, Any]] = []

        def add(identifier: str, passed: bool, milestone_id: str, evidence: Any = None) -> None:
            atomic.append(
                {
                    "id": identifier,
                    "passed": bool(passed),
                    "milestone_id": milestone_id,
                    "evidence": evidence,
                }
            )

        add("procedure.minimum_successful_tool_calls", procedure["minimum_successful_tool_calls"], "discovery.systems", {"actual": len(successful), "required": self.spec["minimum_tool_calls"]})
        add("procedure.provider_discovery_complete", discovery_complete, "discovery.systems", {"required_tools": sorted(discovery_tools)})
        add("procedure.all_material_evidence_read", all_evidence, "containment.scope")
        add("procedure.all_material_evidence_precedes_first_mutation", procedure["all_material_evidence_precedes_first_mutation"], "containment.scope")
        role_milestones = {
            "identity_crosswalk": "investigation.identity",
            "operative_authority": "investigation.authority",
            "current_operations": "investigation.operations",
            "approval_and_capacity": "investigation.approvals",
        }
        for asset, content_read, _ in evidence_results:
            add(
                f"evidence.{asset['evidence_id']}.content_read",
                content_read,
                role_milestones.get(asset["role"], "investigation.impact"),
                {"provider": asset["provider"], "role": asset["role"], "portfolio_key": asset["portfolio_key"]},
            )
        for identifier, passed in decision_scoring["criteria"].items():
            add(f"decision.{identifier}", passed, self._decision_milestone(identifier))
        for identifier, passed in register_scoring["criteria"].items():
            add(f"register.{identifier}", passed, "state.matter_register")
        for identifier, passed in advice_scoring["criteria"].items():
            add(f"advice.{identifier}", passed, self._advice_milestone(identifier))
        for identifier, passed in notification_scoring["criteria"].items():
            add(f"notification.{identifier}", passed, "state.collaboration")
        add("state.exact_mutation_set", exact_mutation_set, "containment.scope")
        add("state.write_scope_contained", write_scope_contained, "containment.scope")
        add("state.matter_register_exact", matter_state_exact and register_scoring["passed"], "state.matter_register")
        add("state.decision_note_exact", note_state_exact and decision_scoring["passed"] and advice_scoring["passed"], "state.legal_note")
        add(
            "state.notification_exact",
            notification_exact and notification_scoring["passed"],
            "state.collaboration",
        )
        add(
            "state.core_state_precedes_notification",
            procedure["core_state_precedes_notification"],
            "state.collaboration",
        )
        add("state.no_rejected_mutation", not self._rejected_mutations, "containment.scope", {"rejected": len(self._rejected_mutations)})
        for label, passed in readback_checks.items():
            add(f"readback.{label}", passed, "verification.readback")

        milestone_specs = self.spec["rubric_milestones"]
        if len(milestone_specs) != 14 or sum(float(row["weight"]) for row in milestone_specs) != 100:
            raise ValueError("invalid CounselScore milestone contract")
        known = {row["id"] for row in milestone_specs}
        unknown = sorted({row["milestone_id"] for row in atomic} - known)
        if unknown:
            raise ValueError(f"atomic checks reference unknown milestones: {unknown}")
        milestones: list[dict[str, Any]] = []
        total_score = 0.0
        for spec in milestone_specs:
            members = [row for row in atomic if row["milestone_id"] == spec["id"]]
            if not members:
                raise ValueError(f"semantic milestone has no atomic checks: {spec['id']}")
            ratio = sum(row["passed"] for row in members) / len(members)
            earned = float(spec["weight"]) * ratio
            total_score += earned
            milestones.append(
                {
                    "id": spec["id"],
                    "category": spec["category"],
                    "description": spec["description"],
                    "weight": spec["weight"],
                    "earned": round(earned, 6),
                    "passed": all(row["passed"] for row in members),
                    "atomic_passed": sum(row["passed"] for row in members),
                    "atomic_total": len(members),
                }
            )
        score = round(total_score, 6)
        passed = all(row["passed"] for row in atomic) and score == 100.0
        category_scores: dict[str, float] = {}
        for category in sorted({row["category"] for row in milestones}):
            rows = [row for row in milestones if row["category"] == category]
            category_scores[category] = round(sum(row["earned"] for row in rows), 6)

        report: dict[str, Any] = {
            "schema_version": "counselbench.verifier.v6",
            "task_id": self.spec["task_id"],
            "metric": "CounselScore",
            "score": score,
            "maximum_score": 100.0,
            "reward": round(score / 100.0, 6),
            "passed": passed,
            "checks": {row["id"]: row["passed"] for row in milestones},
            "milestones": milestones,
            "atomic_checks": atomic,
            "category_scores": category_scores,
            "criteria": {
                "procedure": {"criteria": procedure, "passed": all(procedure.values())},
                "decision": decision_scoring,
                "register": register_scoring,
                "advice": advice_scoring,
                "notification": notification_scoring,
            },
            "successful_tool_calls": len(successful),
            "required_tool_calls": self.spec["minimum_tool_calls"],
            "documents_read": sum(
                content_read for _, content_read, _ in evidence_results
            ),
            "required_documents": len(evidence_results),
            "provider_mutations": [entry["tool"] for entry in self._mutations],
            "rejected_mutations": len(self._rejected_mutations),
            "diagnostics": {
                "exact_decision_match": decision == self.spec["expected_decision"],
                "exact_register_match": register == self.spec["expected_register"],
                "exact_advice_match": advice == self.spec.get("expected_advice", ""),
                "semantic_notification_match": notification_scoring["passed"],
                "state_scope": {
                    "matter": matter_state_exact,
                    "note": note_state_exact,
                    "notification": notification_exact,
                },
                "readback_checks": readback_checks,
                "evidence": {
                    "required": len(evidence_results),
                    "content_reads": sum(
                        content_read for _, content_read, _ in evidence_results
                    ),
                    "prewrite_reads": sum(
                        read_before_write
                        for _, _, read_before_write in evidence_results
                    ),
                },
                "deterministic": True,
                "model_calls": 0,
                "network_calls": 0,
            },
        }
        report["report_sha256"] = sha256_text(canonical_json(report))
        return report
