"""Skeleton IR: the structure of one exemplar document, without its owner.

A skeleton keeps everything that makes a document *look* real — page
geometry, fonts, running header/footer with page-number fields, the block
sequence with per-paragraph formatting, table shapes — plus the seed prose
so heuristic composition can re-skin it. It is plain JSON so it can be
bundled, diffed, and consumed from other languages.

Formatting units follow OOXML: sizes in half-points, distances in twips.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "blobfish.document-seed-skeleton.v1"

# Block roles, inferred at extraction time. Composition keys off these.
ROLE_TITLE = "title"
ROLE_PARTY = "party"  # centered title-block lines: parties, "by and between", dates
ROLE_HEADING = "heading"  # ARTICLE / top-level heading
ROLE_SUBHEADING = "subheading"  # Section N.N / second level
ROLE_RECITAL = "recital"
ROLE_DEFINITION = "definition"
ROLE_BODY = "body"
ROLE_LIST = "list"
ROLE_SIGNATURE = "signature"
ROLE_EXHIBIT = "exhibit"
ROLE_TOC = "toc"
ROLE_BLANK = "blank"
ROLE_META = "meta"  # memo/letter header lines: TO/FROM/DATE/RE, addresses

# Block types.
TYPE_PARAGRAPH = "p"
TYPE_TABLE = "tbl"
TYPE_PAGE_BREAK = "pb"

FIELD_PAGE = "{PAGE}"
FIELD_NUMPAGES = "{NUMPAGES}"


@dataclass
class Block:
    """One paragraph, table, or page break."""

    type: str = TYPE_PARAGRAPH
    text: str = ""
    role: str = ROLE_BODY
    # Compact style: b/i/u/caps (0|1), sz (half-points), al (left|center|right|both),
    # il (left indent twips), fl (first-line indent twips), sb/sa (space before/after
    # twips), kn (keep with next), num (list level, -1 = none).
    style: dict[str, Any] = field(default_factory=dict)
    # Mixed-formatting paragraphs keep their runs: [[text, style], ...].
    runs: list[list[Any]] | None = None
    # Tables.
    rows: list[list[str]] | None = None
    header_row: bool = False
    widths: list[int] | None = None  # twips per column
    borders: str = "single"  # single|none
    align: str = "center"
    # Tight blocks render without a blank separator line in the text IR, so a
    # caller's operative lines keep their original line count.
    tight: bool = False

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"t": self.type}
        if self.tight:
            payload["tight"] = 1
        if self.type == TYPE_PARAGRAPH:
            payload["x"] = self.text
            payload["r"] = self.role
            if self.style:
                payload["s"] = self.style
            if self.runs:
                payload["runs"] = self.runs
        elif self.type == TYPE_TABLE:
            payload["rows"] = self.rows or []
            payload["hdr"] = 1 if self.header_row else 0
            if self.widths:
                payload["w"] = self.widths
            payload["bd"] = self.borders
            payload["al"] = self.align
            if self.role != ROLE_BODY:
                payload["r"] = self.role
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Block":
        kind = payload.get("t", TYPE_PARAGRAPH)
        tight = bool(payload.get("tight", 0))
        if kind == TYPE_TABLE:
            return cls(
                type=TYPE_TABLE,
                rows=[list(map(str, row)) for row in payload.get("rows", [])],
                header_row=bool(payload.get("hdr", 0)),
                widths=list(payload.get("w") or []) or None,
                borders=str(payload.get("bd", "single")),
                align=str(payload.get("al", "center")),
                role=str(payload.get("r", ROLE_BODY)),
                tight=tight,
            )
        if kind == TYPE_PAGE_BREAK:
            return cls(type=TYPE_PAGE_BREAK)
        return cls(
            type=TYPE_PARAGRAPH,
            text=str(payload.get("x", "")),
            role=str(payload.get("r", ROLE_BODY)),
            style=dict(payload.get("s") or {}),
            runs=[list(run) for run in payload.get("runs") or []] or None,
            tight=tight,
        )

    @property
    def plain_text(self) -> str:
        if self.type == TYPE_TABLE:
            return "\n".join("\t".join(row) for row in (self.rows or []))
        return self.text

    def word_count(self) -> int:
        return len(self.plain_text.split())


@dataclass
class Furniture:
    """A running header or footer: paragraphs with page-field tokens."""

    paragraphs: list[Block] = field(default_factory=list)

    def to_json(self) -> list[dict[str, Any]]:
        return [block.to_json() for block in self.paragraphs]

    @classmethod
    def from_json(cls, payload: list[dict[str, Any]] | None) -> "Furniture":
        return cls([Block.from_json(item) for item in payload or []])

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.paragraphs if block.text)


@dataclass
class Sheet:
    name: str
    rows: list[list[str]]
    header_index: int = 0  # row index of the column-header row
    widths: list[float] | None = None
    total_rows: int | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "n": self.name,
            "rows": self.rows,
            "h": self.header_index,
        }
        if self.widths:
            payload["w"] = self.widths
        if self.total_rows is not None:
            payload["nrows"] = self.total_rows
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Sheet":
        return cls(
            name=str(payload.get("n", "Sheet1")),
            rows=[list(map(str, row)) for row in payload.get("rows", [])],
            header_index=int(payload.get("h", 0)),
            widths=list(payload.get("w") or []) or None,
            total_rows=payload.get("nrows"),
        )


@dataclass
class Message:
    """One message of an email thread (the first is the outermost)."""

    headers: dict[str, str]
    body: list[str]  # paragraphs

    def to_json(self) -> dict[str, Any]:
        return {"h": self.headers, "b": self.body}

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Message":
        return cls(
            headers={str(k): str(v) for k, v in (payload.get("h") or {}).items()},
            body=[str(line) for line in payload.get("b") or []],
        )


@dataclass
class Slide:
    title: str
    body: list[str]
    tables: list[list[list[str]]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": self.title, "body": self.body}
        if self.tables:
            payload["tables"] = self.tables
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Slide":
        return cls(
            title=str(payload.get("title", "")),
            body=[str(line) for line in payload.get("body") or []],
            tables=[
                [list(map(str, row)) for row in table]
                for table in payload.get("tables") or []
            ],
        )


@dataclass
class Skeleton:
    id: str
    source: str  # path relative to the exemplar corpus root
    practice_area: str
    format: str  # docx|xlsx|eml|pptx|txt|md
    kind: str
    title: str
    subkind: str = ""
    tags: list[str] = field(default_factory=list)
    words: int = 0
    tables: int = 0
    page_breaks: int = 0
    est_pages: int = 1
    page: dict[str, int] = field(default_factory=dict)
    font: dict[str, Any] = field(default_factory=dict)
    header: Furniture = field(default_factory=Furniture)
    footer: Furniture = field(default_factory=Furniture)
    blocks: list[Block] = field(default_factory=list)
    sheets: list[Sheet] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    slides: list[Slide] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)
    license: str = "MIT © 2026 Harvey AI (harveyai/harvey-labs)"

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "id": self.id,
            "src": self.source,
            "area": self.practice_area,
            "fmt": self.format,
            "kind": self.kind,
            "subkind": self.subkind,
            "title": self.title,
            "tags": self.tags,
            "words": self.words,
            "tables": self.tables,
            "breaks": self.page_breaks,
            "pages": self.est_pages,
            "license": self.license,
        }
        if self.page:
            payload["page"] = self.page
        if self.font:
            payload["font"] = self.font
        if self.header.paragraphs:
            payload["header"] = self.header.to_json()
        if self.footer.paragraphs:
            payload["footer"] = self.footer.to_json()
        if self.blocks:
            payload["blocks"] = [block.to_json() for block in self.blocks]
        if self.sheets:
            payload["sheets"] = [sheet.to_json() for sheet in self.sheets]
        if self.messages:
            payload["messages"] = [message.to_json() for message in self.messages]
        if self.slides:
            payload["slides"] = [slide.to_json() for slide in self.slides]
        if self.entities:
            payload["ents"] = self.entities
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Skeleton":
        return cls(
            id=str(payload["id"]),
            source=str(payload.get("src", "")),
            practice_area=str(payload.get("area", "")),
            format=str(payload.get("fmt", "docx")),
            kind=str(payload.get("kind", "document")),
            subkind=str(payload.get("subkind", "")),
            title=str(payload.get("title", "")),
            tags=[str(tag) for tag in payload.get("tags") or []],
            words=int(payload.get("words", 0)),
            tables=int(payload.get("tables", 0)),
            page_breaks=int(payload.get("breaks", 0)),
            est_pages=int(payload.get("pages", 1)),
            page={str(k): int(v) for k, v in (payload.get("page") or {}).items()},
            font=dict(payload.get("font") or {}),
            header=Furniture.from_json(payload.get("header")),
            footer=Furniture.from_json(payload.get("footer")),
            blocks=[Block.from_json(item) for item in payload.get("blocks") or []],
            sheets=[Sheet.from_json(item) for item in payload.get("sheets") or []],
            messages=[
                Message.from_json(item) for item in payload.get("messages") or []
            ],
            slides=[Slide.from_json(item) for item in payload.get("slides") or []],
            entities={
                str(k): [str(x) for x in v]
                for k, v in (payload.get("ents") or {}).items()
            },
            license=str(payload.get("license", "")),
        )

    def dumps(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def loads(cls, payload: str) -> "Skeleton":
        return cls.from_json(json.loads(payload))

    def summary(self) -> dict[str, Any]:
        """Index row: everything selection needs, no prose."""
        return {
            "id": self.id,
            "src": self.source,
            "area": self.practice_area,
            "fmt": self.format,
            "kind": self.kind,
            "subkind": self.subkind,
            "title": self.title,
            "tags": self.tags,
            "words": self.words,
            "tables": self.tables,
            "pages": self.est_pages,
            "hf": int(bool(self.header.paragraphs or self.footer.paragraphs)),
        }


__all__ = [
    "Block",
    "Furniture",
    "Message",
    "SCHEMA_VERSION",
    "Sheet",
    "Skeleton",
    "Slide",
    "asdict",
]
