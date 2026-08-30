"""Documented provider-operation contracts for the CounselBench sandbox.

CounselBench owns the deterministic synthetic state, but it does not invent
business-level tools such as ``decide_matter`` or ``approve_finding``. Each
agent-facing tool maps to one published provider operation. Schemas are a
task-relevant subset of the upstream request surface; resource names, methods,
paths, and request nesting follow the provider.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


Json = dict[str, Any]

CLIO = "https://docs.developers.clio.com/clio-manage/api-reference"
CLIO_FIELDS = "https://docs.developers.clio.com/api-docs/clio-manage/fields/"
GMAIL = "https://developers.google.com/workspace/gmail/api/reference/rest/v1/users"
DRIVE = "https://developers.google.com/workspace/drive/api/reference/rest/v3"
SLACK = "https://api.slack.com/methods"

MCP_PIN = {
    "schema_version": "counselbench.provider-contracts.v1",
    "runtime_server_name": "counselbench-enterprise-sandbox",
    "runtime_server_version": "3.2.1",
    "protocol_version": "2025-06-18",
    "providers": {
        "clio_manage": {"api": "v4", "source": CLIO},
        "gmail": {"api": "v1", "source": GMAIL},
        "google_drive": {"api": "v3", "source": DRIVE},
        "slack": {"api": "Web API", "source": SLACK},
    },
    "contract_mode": "documented-operation-allowlist",
}


def _object(properties: Json | None = None, required: list[str] | None = None) -> Json:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _string() -> Json:
    return {"type": "string"}


def _integer() -> Json:
    return {"type": "integer"}


def _boolean() -> Json:
    return {"type": "boolean"}


def _contract(
    name: str,
    *,
    provider: str,
    method: str,
    path: str,
    source: str,
    description: str,
    input_schema: Json,
    read_only: bool,
    idempotent: bool | None = None,
) -> Json:
    return {
        "name": name,
        "title": name,
        "description": description,
        "inputSchema": input_schema,
        "annotations": {
            "readOnlyHint": read_only,
            "destructiveHint": not read_only,
            "idempotentHint": read_only if idempotent is None else idempotent,
            "openWorldHint": False,
        },
        "execution": {"taskSupport": "forbidden"},
        "_meta": {
            "counselbench": {
                "provider": provider,
                "implementation": "closed deterministic sandbox",
                "contractMode": "documented-operation",
                "upstream": {"method": method, "path": path, "source": source},
            }
        },
    }


def _clio_contracts() -> list[Json]:
    custom_field_value = _object(
        {
            "id": _string(),
            "value": _string(),
            "custom_field": _object({"id": _integer()}, ["id"]),
            "_destroy": _boolean(),
        }
    )
    return [
        _contract(
            "clio_manage.matters.list",
            provider="clio_manage",
            method="GET",
            path="/api/v4/matters.json",
            source=f"{CLIO}/#tag/Matters/operation/Matter#index",
            description="List Clio Manage matters using supported fields and filters.",
            input_schema=_object(
                {
                    "fields": _string(),
                    "query": _string(),
                    "status": _string(),
                    "limit": _integer(),
                    "page_token": _string(),
                }
            ),
            read_only=True,
        ),
        _contract(
            "clio_manage.matters.get",
            provider="clio_manage",
            method="GET",
            path="/api/v4/matters/{id}.json",
            source=f"{CLIO}/#tag/Matters/operation/Matter#show",
            description="Get one Clio Manage matter and requested nested fields.",
            input_schema=_object({"id": _integer(), "fields": _string()}, ["id"]),
            read_only=True,
        ),
        _contract(
            "clio_manage.matters.update",
            provider="clio_manage",
            method="PATCH",
            path="/api/v4/matters/{id}.json",
            source=CLIO_FIELDS,
            description="Patch one Clio Manage matter, including documented custom_field_values.",
            input_schema=_object(
                {
                    "id": _integer(),
                    "fields": _string(),
                    "data": _object(
                        {
                            "description": _string(),
                            "custom_field_values": {
                                "type": "array",
                                "items": custom_field_value,
                            },
                        }
                    ),
                },
                ["id", "data"],
            ),
            read_only=False,
            idempotent=True,
        ),
        _contract(
            "clio_manage.notes.list",
            provider="clio_manage",
            method="GET",
            path="/api/v4/notes.json",
            source=f"{CLIO}/#tag/Notes/operation/Note#index",
            description="List matter or contact notes in Clio Manage.",
            input_schema=_object(
                {
                    "type": {"type": "string", "enum": ["matter", "contact"]},
                    "fields": _string(),
                    "query": _string(),
                    "limit": _integer(),
                    "page_token": _string(),
                },
                ["type"],
            ),
            read_only=True,
        ),
        _contract(
            "clio_manage.notes.get",
            provider="clio_manage",
            method="GET",
            path="/api/v4/notes/{id}.json",
            source=f"{CLIO}/#tag/Notes/operation/Note#show",
            description="Get one Clio Manage matter or contact note.",
            input_schema=_object({"id": _integer(), "fields": _string()}, ["id"]),
            read_only=True,
        ),
        _contract(
            "clio_manage.notes.create",
            provider="clio_manage",
            method="POST",
            path="/api/v4/notes.json",
            source=f"{CLIO}/#tag/Notes/operation/Note#create",
            description="Create a Clio Manage note regarding an existing matter or contact.",
            input_schema=_object(
                {
                    "fields": _string(),
                    "data": _object(
                        {
                            "subject": _string(),
                            "detail": _string(),
                            "detail_text_type": {
                                "type": "string",
                                "enum": ["plain_text", "rich_text"],
                            },
                            "regarding": _object(
                                {
                                    "id": _integer(),
                                    "type": {"type": "string", "enum": ["Matter", "Contact"]},
                                },
                                ["id", "type"],
                            ),
                        },
                        ["subject", "detail", "regarding"],
                    ),
                },
                ["data"],
            ),
            read_only=False,
            idempotent=False,
        ),
    ]


def _workspace_contracts() -> list[Json]:
    return [
        _contract(
            "gmail.messages.list",
            provider="gmail",
            method="GET",
            path="/gmail/v1/users/{userId}/messages",
            source=f"{GMAIL}.messages/list",
            description="Search Gmail messages using Gmail's q grammar.",
            input_schema=_object(
                {
                    "userId": _string(),
                    "q": _string(),
                    "labelIds": {"type": "array", "items": _string()},
                    "maxResults": _integer(),
                    "pageToken": _string(),
                    "includeSpamTrash": _boolean(),
                },
                ["userId"],
            ),
            read_only=True,
        ),
        _contract(
            "gmail.messages.get",
            provider="gmail",
            method="GET",
            path="/gmail/v1/users/{userId}/messages/{id}",
            source=f"{GMAIL}.messages/get",
            description="Get one Gmail message in minimal, full, raw, or metadata format.",
            input_schema=_object(
                {
                    "userId": _string(),
                    "id": _string(),
                    "format": {"type": "string", "enum": ["minimal", "full", "raw", "metadata"]},
                    "metadataHeaders": {"type": "array", "items": _string()},
                },
                ["userId", "id"],
            ),
            read_only=True,
        ),
        _contract(
            "gmail.messages.send",
            provider="gmail",
            method="POST",
            path="/gmail/v1/users/{userId}/messages/send",
            source=f"{GMAIL}.messages/send",
            description="Send a base64url RFC 2822 message through Gmail.",
            input_schema=_object(
                {
                    "userId": _string(),
                    "requestBody": _object(
                        {"raw": _string(), "threadId": _string()}, ["raw"]
                    ),
                },
                ["userId", "requestBody"],
            ),
            read_only=False,
            idempotent=False,
        ),
        _contract(
            "google_drive.files.list",
            provider="google_drive",
            method="GET",
            path="/drive/v3/files",
            source=f"{DRIVE}/files/list",
            description="Search Drive files using the q grammar.",
            input_schema=_object(
                {
                    "q": _string(),
                    "spaces": _string(),
                    "orderBy": _string(),
                    "pageSize": _integer(),
                    "pageToken": _string(),
                    "fields": _string(),
                }
            ),
            read_only=True,
        ),
        _contract(
            "google_drive.files.get",
            provider="google_drive",
            method="GET",
            path="/drive/v3/files/{fileId}",
            source=f"{DRIVE}/files/get",
            description="Get Drive file metadata or media.",
            input_schema=_object(
                {"fileId": _string(), "alt": _string(), "fields": _string(), "acknowledgeAbuse": _boolean()},
                ["fileId"],
            ),
            read_only=True,
        ),
        _contract(
            "google_drive.comments.list",
            provider="google_drive",
            method="GET",
            path="/drive/v3/files/{fileId}/comments",
            source=f"{DRIVE}/comments/list",
            description="List comments on a Drive file.",
            input_schema=_object(
                {"fileId": _string(), "pageSize": _integer(), "pageToken": _string(), "includeDeleted": _boolean(), "fields": _string()},
                ["fileId"],
            ),
            read_only=True,
        ),
        _contract(
            "google_drive.comments.get",
            provider="google_drive",
            method="GET",
            path="/drive/v3/files/{fileId}/comments/{commentId}",
            source=f"{DRIVE}/comments/get",
            description="Get one Drive comment by ID.",
            input_schema=_object(
                {"fileId": _string(), "commentId": _string(), "includeDeleted": _boolean(), "fields": _string()},
                ["fileId", "commentId"],
            ),
            read_only=True,
        ),
        _contract(
            "google_drive.comments.create",
            provider="google_drive",
            method="POST",
            path="/drive/v3/files/{fileId}/comments",
            source=f"{DRIVE}/comments/create",
            description="Create a plain-text comment on a Drive file.",
            input_schema=_object(
                {"fileId": _string(), "requestBody": _object({"content": _string()}, ["content"])},
                ["fileId", "requestBody"],
            ),
            read_only=False,
            idempotent=False,
        ),
        _contract(
            "slack.search_messages",
            provider="slack",
            method="GET",
            path="/api/search.messages",
            source=f"{SLACK}/search.messages",
            description="Search messages visible to the Slack caller.",
            input_schema=_object(
                {"query": _string(), "count": _integer(), "page": _integer(), "sort": _string(), "sort_dir": _string()},
                ["query"],
            ),
            read_only=True,
        ),
        _contract(
            "slack.conversations_history",
            provider="slack",
            method="GET",
            path="/api/conversations.history",
            source=f"{SLACK}/conversations.history",
            description="Get top-level messages in a Slack conversation.",
            input_schema=_object(
                {"channel": _string(), "cursor": _string(), "inclusive": _boolean(), "latest": _string(), "oldest": _string(), "limit": _integer()},
                ["channel"],
            ),
            read_only=True,
        ),
        _contract(
            "slack.conversations_replies",
            provider="slack",
            method="GET",
            path="/api/conversations.replies",
            source=f"{SLACK}/conversations.replies",
            description="Get a Slack thread, parent message first.",
            input_schema=_object(
                {"channel": _string(), "ts": _string(), "cursor": _string(), "limit": _integer()},
                ["channel", "ts"],
            ),
            read_only=True,
        ),
        _contract(
            "slack.chat_postMessage",
            provider="slack",
            method="POST",
            path="/api/chat.postMessage",
            source=f"{SLACK}/chat.postMessage",
            description="Post a Slack channel message or thread reply.",
            input_schema=_object(
                {"channel": _string(), "text": _string(), "thread_ts": _string()},
                ["channel", "text"],
            ),
            read_only=False,
            idempotent=False,
        ),
    ]


TOOLS: list[Json] = [*_clio_contracts(), *_workspace_contracts()]
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
MUTATION_TOOLS = {
    tool["name"] for tool in TOOLS if not tool["annotations"]["readOnlyHint"]
}


def tool_definitions() -> list[Json]:
    """Return an isolated copy so callers cannot mutate the contract snapshot."""

    return deepcopy(TOOLS)
