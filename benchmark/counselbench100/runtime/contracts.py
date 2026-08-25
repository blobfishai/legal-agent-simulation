"""Pinned MCP tool contracts used by the benchmark world.

These definitions mirror the tools exposed by
``@modelcontextprotocol/server-filesystem@2026.7.10`` at the npm-recorded
upstream commit 9a96ea6e5913736f92b88345bf51caeaaa8e719f.
``tests/conformance.py``
launches that package and compares its live ``tools/list`` response with this
allowlisted subset.  Keeping the JSON here makes every generated task runnable
without network access.
"""

from __future__ import annotations

from copy import deepcopy


MCP_PIN = {
    "repository": "https://github.com/modelcontextprotocol/servers",
    "commit": "9a96ea6e5913736f92b88345bf51caeaaa8e719f",
    "package": "@modelcontextprotocol/server-filesystem",
    "version": "2026.7.10",
    "server_name": "io.github.modelcontextprotocol/server-filesystem",
    "runtime_server_name": "secure-filesystem-server",
    "runtime_server_version": "0.2.0",
    "protocol_version": "2025-06-18",
    "license": "Apache-2.0/MIT transition notice",
}


def _object(
    properties: dict,
    required: list[str] | None = None,
    *,
    additional_properties: bool | None = None,
) -> dict:
    schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    if additional_properties is not None:
        schema["additionalProperties"] = additional_properties
    return schema


_TEXT_OUTPUT = _object(
    {"content": {"type": "string"}}, ["content"], additional_properties=False
)


TOOLS: list[dict] = [
    {
        "name": "read_text_file",
        "title": "Read Text File",
        "description": (
            "Read the complete contents of a file from the file system as text. "
            "Handles various text encodings and provides detailed error messages "
            "if the file cannot be read. Use this tool when you need to examine "
            "the contents of a single file. Use the 'head' parameter to read only "
            "the first N lines of a file, or the 'tail' parameter to read only "
            "the last N lines of a file. Operates on the file as text regardless "
            "of extension. Only works within allowed directories."
        ),
        "inputSchema": _object(
            {
                "path": {"type": "string"},
                "tail": {
                    "type": "number",
                    "description": "If provided, returns only the last N lines of the file",
                },
                "head": {
                    "type": "number",
                    "description": "If provided, returns only the first N lines of the file",
                },
            },
            ["path"],
        ),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "write_file",
        "title": "Write File",
        "description": (
            "Create a new file or completely overwrite an existing file with new content. "
            "Use with caution as it will overwrite existing files without warning. "
            "Handles text content with proper encoding. Only works within allowed directories."
        ),
        "inputSchema": _object(
            {"path": {"type": "string"}, "content": {"type": "string"}},
            ["path", "content"],
        ),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "directory_tree",
        "title": "Directory Tree",
        "description": (
            "Get a recursive tree view of files and directories as a JSON structure. "
            "Each entry includes 'name', 'type' (file/directory), and 'children' for directories. "
            "Files have no children array, while directories always have a children array "
            "(which may be empty). The output is formatted with 2-space indentation for "
            "readability. Only works within allowed directories."
        ),
        "inputSchema": _object(
            {
                "path": {"type": "string"},
                "excludePatterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
            ["path"],
        ),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "search_files",
        "title": "Search Files",
        "description": (
            "Recursively search for files and directories matching a pattern. "
            "The patterns should be glob-style patterns that match paths relative to the "
            "working directory. Use pattern like '*.ext' to match files in current directory, "
            "and '**/*.ext' to match files in all subdirectories. Returns full paths to all "
            "matching items. Great for finding files when you don't know their exact location. "
            "Only searches within allowed directories."
        ),
        "inputSchema": _object(
            {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "excludePatterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
            ["path", "pattern"],
        ),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_file_info",
        "title": "Get File Info",
        "description": (
            "Retrieve detailed metadata about a file or directory. Returns comprehensive "
            "information including size, creation time, last modified time, permissions, "
            "and type. This tool is perfect for understanding file characteristics without "
            "reading the actual content. Only works within allowed directories."
        ),
        "inputSchema": _object({"path": {"type": "string"}}, ["path"]),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "list_allowed_directories",
        "title": "List Allowed Directories",
        "description": (
            "Returns the list of directories that this server is allowed to access. "
            "Subdirectories within these allowed directories are also accessible. "
            "Use this to understand which directories and their nested paths are available "
            "before trying to access files."
        ),
        "inputSchema": _object({}),
        "outputSchema": _TEXT_OUTPUT,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]

for _tool in TOOLS:
    _tool["execution"] = {"taskSupport": "forbidden"}


def tool_definitions() -> list[dict]:
    """Return an isolated copy so callers cannot mutate the contract snapshot."""

    return deepcopy(TOOLS)


TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}
