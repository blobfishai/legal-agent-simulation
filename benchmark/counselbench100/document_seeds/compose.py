"""Compose a new document on a seed's structure.

The seed supplies the shape — title block, recitals, definitions, articles,
tables, signature page, running header/footer, page geometry. The caller
supplies the facts: the organization and parties, an optional title and
furniture, and the *operative* lines the task will grade. Every entity in the
seed prose is re-skinned deterministically and anything on the ``avoid``
list is scrubbed, so the composed document reads like a real matter file
without ever answering the task by accident.

Heuristic-first: ``compose_document`` needs no model. A ``writer`` callback
can rewrite seed paragraphs (outline mode) when one is available.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from random import Random
from typing import Any

from .entities import Reskin, generate_person, parties_of
from .skeleton import (
    FIELD_NUMPAGES,
    FIELD_PAGE,
    ROLE_BLANK,
    ROLE_BODY,
    ROLE_DEFINITION,
    ROLE_EXHIBIT,
    ROLE_HEADING,
    ROLE_LIST,
    ROLE_META,
    ROLE_PARTY,
    ROLE_RECITAL,
    ROLE_SIGNATURE,
    ROLE_SUBHEADING,
    ROLE_TITLE,
    ROLE_TOC,
    TYPE_PAGE_BREAK,
    TYPE_PARAGRAPH,
    TYPE_TABLE,
    Block,
    Message,
    Sheet,
    Skeleton,
    Slide,
)

LAYOUT_SCHEMA = "blobfish.document-layout.v1"
OPERATIVE_START = "operative_start"

ANCHOR_TOP = "top"
ANCHOR_AFTER_FRONT_MATTER = "after_front_matter"
ANCHOR_OPERATIVE = "operative"
ANCHOR_END = "end"
ANCHOR_REPLACE_BODY = "replace_body"

_FRONT_ROLES = {ROLE_TITLE, ROLE_PARTY, ROLE_META, ROLE_TOC, ROLE_BLANK}
_BACK_ROLES = {ROLE_SIGNATURE, ROLE_EXHIBIT}


class CompositionError(ValueError):
    """The seed could not be composed safely (e.g. an avoided literal survived)."""


@dataclass
class ContentPlan:
    """What the caller knows about the document to produce."""

    title: str | None = None
    organization: str | None = None
    parties: Sequence[str] = ()
    people: Mapping[str, str] = field(default_factory=dict)
    header: str | None = None
    footer: str | None = None
    operative: Sequence[str] = ()
    operative_heading: str | None = None
    anchor: str | int = ANCHOR_OPERATIVE
    target_words: int | None = None
    avoid: Sequence[str] = ()
    date_offset_days: int | None = None
    writer: Callable[[Block, "ContentPlan"], str | None] | None = None
    # Email-specific: who writes/receives the newest message.
    sender: str | None = None
    recipients: Sequence[str] = ()
    subject: str | None = None
    # Spreadsheet-specific: operative sheets first (parsed from ``operative``).
    operative_sheet_name: str | None = None
    # Keep operative lines contiguous (no blank separators) so their count in
    # the text is exactly the caller's; and never trim seed sections that
    # precede the operative block, so its line offset is decided by the anchor.
    tight_operative: bool = False
    trim_head: bool = True
    # Verbatim: operative lines are inserted exactly as given (no heading /
    # list / table parsing), so a pre-rendered record survives byte for byte.
    verbatim_operative: bool = False
    # Fraction of the seed prose that trimming must keep (0.35 keeps a document
    # substantive; size-gated consumers may go lower).
    keep_fraction: float = 0.35

    def to_json(self) -> dict[str, Any]:
        """JSON recipe (``writer`` is not serializable and is dropped)."""

        return {
            "title": self.title,
            "organization": self.organization,
            "parties": list(self.parties),
            "people": dict(self.people),
            "header": self.header,
            "footer": self.footer,
            "operative": list(self.operative),
            "operative_heading": self.operative_heading,
            "anchor": self.anchor,
            "target_words": self.target_words,
            "avoid": list(self.avoid),
            "date_offset_days": self.date_offset_days,
            "sender": self.sender,
            "recipients": list(self.recipients),
            "subject": self.subject,
            "operative_sheet_name": self.operative_sheet_name,
            "tight_operative": self.tight_operative,
            "trim_head": self.trim_head,
            "verbatim_operative": self.verbatim_operative,
            "keep_fraction": self.keep_fraction,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ContentPlan":
        anchor = payload.get("anchor", ANCHOR_OPERATIVE)
        return cls(
            title=payload.get("title"),
            organization=payload.get("organization"),
            parties=[str(item) for item in payload.get("parties") or []],
            people={str(k): str(v) for k, v in (payload.get("people") or {}).items()},
            header=payload.get("header"),
            footer=payload.get("footer"),
            operative=[str(item) for item in payload.get("operative") or []],
            operative_heading=payload.get("operative_heading"),
            anchor=int(anchor)
            if isinstance(anchor, int) or (isinstance(anchor, str) and anchor.isdigit())
            else str(anchor),
            target_words=payload.get("target_words"),
            avoid=[str(item) for item in payload.get("avoid") or []],
            date_offset_days=payload.get("date_offset_days"),
            sender=payload.get("sender"),
            recipients=[str(item) for item in payload.get("recipients") or []],
            subject=payload.get("subject"),
            operative_sheet_name=payload.get("operative_sheet_name"),
            tight_operative=bool(payload.get("tight_operative", False)),
            trim_head=bool(payload.get("trim_head", True)),
            verbatim_operative=bool(payload.get("verbatim_operative", False)),
            keep_fraction=float(payload.get("keep_fraction", 0.35)),
        )


@dataclass
class ComposedDocument:
    seed_id: str
    source: str
    format: str
    kind: str
    title: str
    page: dict[str, int] = field(default_factory=dict)
    font: dict[str, Any] = field(default_factory=dict)
    header: list[Block] = field(default_factory=list)
    footer: list[Block] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    sheets: list[Sheet] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    slides: list[Slide] = field(default_factory=list)
    operative_span: tuple[int, int] | None = None
    receipt: dict[str, Any] = field(default_factory=dict)

    # ---- the text contract every existing consumer already understands
    def to_text(self) -> str:
        if self.format == "xlsx":
            return "\n".join(_sheet_text(sheet) for sheet in self.sheets) + "\n"
        if self.format == "eml":
            return _thread_text(self.messages)
        if self.format == "pptx":
            return "\n".join(_slide_text(slide) for slide in self.slides) + "\n"
        return "\n".join(_block_lines(self.blocks)) + "\n"

    def to_markdown(self) -> str:
        """Markdown rendering: pipe tables, ``##`` headings, blank-line paragraphs."""

        if self.format not in ("docx", "txt", "md"):
            return self.to_text()
        lines: list[str] = []
        for block in self.blocks:
            if block.type == TYPE_TABLE and block.rows:
                width = max(len(row) for row in block.rows)
                rows = [row + [""] * (width - len(row)) for row in block.rows]

                def cells(row: Sequence[str]) -> str:
                    return (
                        "| "
                        + " | ".join(
                            cell.replace("|", "/").replace("\n", " ") for cell in row
                        )
                        + " |"
                    )

                lines.append(cells(rows[0]))
                lines.append("|" + "---|" * width)
                lines.extend(cells(row) for row in rows[1:])
                lines.append("")
                continue
            if block.type == TYPE_PAGE_BREAK:
                continue
            if block.role == ROLE_BLANK or not block.text:
                if block.tight:
                    lines.append("")
                continue
            text = block.text
            if block.role == ROLE_TITLE:
                lines.append(f"# {text}")
            elif block.role in (ROLE_HEADING, ROLE_EXHIBIT):
                lines.append(f"## {text}")
            elif block.role == ROLE_SUBHEADING:
                lines.append(f"### {text}")
            elif block.role == ROLE_LIST and not re.match(
                r"^(\(?[a-z0-9ivx]{1,3}[\).]|[•\-–▪])\s", text
            ):
                lines.append(f"- {text}")
            elif block.role == ROLE_DEFINITION and not block.runs:
                lines.append(re.sub(r'^("[^"]+"|“[^”]+”)', r"**\1**", text, count=1))
            else:
                lines.append(text)
            if not block.tight:
                lines.append("")
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"

    def to_plain(self) -> str:
        """Plain-text rendering: upper-case headings, ``|``-separated table rows."""

        if self.format not in ("docx", "txt", "md"):
            return self.to_text()
        lines: list[str] = []
        for block in self.blocks:
            if block.type == TYPE_TABLE and block.rows:
                lines.extend(
                    " | ".join(cell.replace("\n", " ") for cell in row)
                    for row in block.rows
                )
                lines.append("")
                continue
            if block.type == TYPE_PAGE_BREAK:
                continue
            if block.role == ROLE_BLANK or not block.text:
                if block.tight:
                    lines.append("")
                continue
            text = block.text
            if block.role in (ROLE_TITLE, ROLE_HEADING, ROLE_EXHIBIT):
                lines.append(text.upper())
            else:
                lines.append(text)
            if not block.tight:
                lines.append("")
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"

    def operative_lines(self) -> tuple[int, int] | None:
        """(first line, line count) of the operative block inside ``to_text()``."""

        if self.operative_span is None or self.format not in (
            "docx",
            "pdf",
            "txt",
            "md",
        ):
            return None
        start, end = self.operative_span
        before = _block_lines(self.blocks[:start])
        inside = _block_lines(self.blocks[start:end])
        # Blocks are separated by one blank line in ``to_text()``.
        return len(before) + (1 if before else 0), len(inside)

    @staticmethod
    def line_offset(blocks: Sequence[Block], index: int) -> int:
        """Text line at which block ``index`` would start in ``to_text()``."""

        before = _block_lines(blocks[:index])
        return len(before) + (1 if before else 0)

    def word_count(self) -> int:
        return len(self.to_text().split())

    def layout(self) -> dict[str, Any]:
        """Renderer sidecar: structure + formatting, no consumer-facing semantics."""

        payload: dict[str, Any] = {
            "schema": LAYOUT_SCHEMA,
            "seed": self.seed_id,
            "source": self.source,
            "format": self.format,
            "kind": self.kind,
            "title": self.title,
            "page": self.page,
            "font": self.font,
            "header": [block.to_json() for block in self.header],
            "footer": [block.to_json() for block in self.footer],
        }
        if self.blocks:
            payload["blocks"] = [block.to_json() for block in self.blocks]
        if self.sheets:
            payload["sheets"] = [sheet.to_json() for sheet in self.sheets]
        if self.messages:
            payload["messages"] = [message.to_json() for message in self.messages]
        if self.slides:
            payload["slides"] = [slide.to_json() for slide in self.slides]
        if self.operative_span:
            payload["operative_span"] = list(self.operative_span)
        return payload


# --------------------------------------------------------------------------- text helpers
def _block_lines(blocks: Sequence[Block]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        if block.type == TYPE_TABLE:
            for row in block.rows or []:
                lines.append(
                    "\t".join(
                        cell.replace("\t", " ").replace("\n", " ") for cell in row
                    )
                )
            if not block.tight:
                lines.append("")
            continue
        if block.type == TYPE_PAGE_BREAK:
            continue
        if block.role == ROLE_BLANK or not block.text:
            if block.tight:
                lines.append("")
            continue
        text = block.text.replace("\t", " ")
        if block.role == ROLE_TITLE:
            lines.append(f"# {text}")
        elif block.role in (ROLE_HEADING, ROLE_EXHIBIT):
            lines.append(f"## {text}")
        elif block.role == ROLE_SUBHEADING:
            lines.append(f"### {text}")
        elif block.role == ROLE_LIST and not re.match(
            r"^(\(?[a-z0-9ivx]{1,3}[\).]|[•\-–▪])\s", text
        ):
            lines.append(f"- {text}")
        else:
            lines.append(text)
        if not block.tight:
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _sheet_text(sheet: Sheet) -> str:
    rows = "\n".join(
        "\t".join(cell.replace("\t", " ") for cell in row)
        for row in sheet.rows
        if any(row)
    )
    return f"=== SHEET: {sheet.name} ===\n{rows}"


def _thread_text(messages: Sequence[Message]) -> str:
    parts: list[str] = []
    for index, message in enumerate(messages):
        if index:
            parts.append("-----Original Message-----")
        for key in (
            "From",
            "Sent",
            "Date",
            "To",
            "Cc",
            "Subject",
            "Message-ID",
            "In-Reply-To",
        ):
            if key in message.headers and not (
                key == "Sent" and "Date" in message.headers
            ):
                parts.append(f"{key}: {message.headers[key]}")
        parts.append("")
        parts.extend(paragraph + "\n" for paragraph in message.body)
    return "\n".join(parts).rstrip() + "\n"


def _slide_text(slide: Slide) -> str:
    lines = [f"# {slide.title}"] + list(slide.body)
    for table in slide.tables:
        lines.extend("\t".join(row) for row in table)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- operative parsing
def _style_bank(blocks: Sequence[Block]) -> dict[str, dict[str, Any]]:
    """The seed's own styles for each role, so inserted content matches."""

    bank: dict[str, dict[str, Any]] = {}
    by_role: dict[str, list[dict[str, Any]]] = {}
    for block in blocks:
        if block.type != TYPE_PARAGRAPH or not block.text:
            continue
        by_role.setdefault(block.role, []).append(dict(block.style))
    for role, styles in by_role.items():
        # The majority style for the role (ARTICLE headings outnumber "RECITALS").
        seen: dict[str, int] = {}
        for style in styles:
            key = repr(sorted(style.items()))
            seen[key] = seen.get(key, 0) + 1
        best = max(seen, key=lambda key: (seen[key], -list(seen).index(key)))
        bank[role] = next(
            style for style in styles if repr(sorted(style.items())) == best
        )
    bank.setdefault(ROLE_BODY, {"al": "both", "sa": 120})
    bank.setdefault(
        ROLE_HEADING,
        {
            **{k: v for k, v in bank[ROLE_BODY].items() if k in ("sz",)},
            "b": 1,
            "kn": 1,
            "sb": 240,
            "sa": 120,
        },
    )
    bank.setdefault(
        ROLE_SUBHEADING,
        {
            **{k: v for k, v in bank[ROLE_BODY].items() if k in ("sz",)},
            "b": 1,
            "kn": 1,
            "sb": 160,
            "sa": 80,
        },
    )
    bank.setdefault(ROLE_LIST, {**bank[ROLE_BODY], "il": 720, "fl": -360})
    return bank


def _table_template(blocks: Sequence[Block]) -> Block | None:
    for block in blocks:
        if block.type == TYPE_TABLE:
            return block
    return None


def parse_operative(
    lines: Sequence[str],
    bank: Mapping[str, dict[str, Any]],
    table_template: Block | None,
    tight: bool = False,
    verbatim: bool = False,
) -> list[Block]:
    """Turn line-IR content (``# ``, ``## ``, ``### ``, ``- ``, tab rows) into seed-styled blocks."""

    blocks: list[Block] = []
    if verbatim:
        for raw in lines:
            line = raw.rstrip("\n")
            if line.strip():
                blocks.append(
                    Block(
                        text=line,
                        role=ROLE_BODY,
                        style=dict(bank[ROLE_BODY]),
                        tight=True,
                    )
                )
            else:
                blocks.append(Block(text="", role=ROLE_BLANK, tight=True))
        return blocks
    rows: list[list[str]] = []

    def flush() -> None:
        nonlocal rows
        if rows:
            width = max(len(row) for row in rows)
            rows = [row + [""] * (width - len(row)) for row in rows]
            block = Block(type=TYPE_TABLE, rows=rows, header_row=True)
            if table_template is not None:
                block.borders = table_template.borders
                block.align = table_template.align
            blocks.append(block)
        rows = []

    for raw in lines:
        line = raw.rstrip("\n")
        if "\t" in line:
            rows.append([cell.strip() for cell in line.split("\t")])
            continue
        flush()
        stripped = line.strip()
        if not stripped:
            if tight:
                # Tight mode preserves the caller's blank lines one-for-one.
                blocks.append(Block(text="", role=ROLE_BLANK, tight=True))
            continue
        if stripped.startswith("### "):
            blocks.append(
                Block(
                    text=stripped[4:],
                    role=ROLE_SUBHEADING,
                    style=dict(bank[ROLE_SUBHEADING]),
                )
            )
        elif stripped.startswith("## "):
            blocks.append(
                Block(
                    text=stripped[3:], role=ROLE_HEADING, style=dict(bank[ROLE_HEADING])
                )
            )
        elif stripped.startswith("# "):
            blocks.append(
                Block(
                    text=stripped[2:], role=ROLE_HEADING, style=dict(bank[ROLE_HEADING])
                )
            )
        elif stripped.startswith("- "):
            blocks.append(
                Block(text=stripped[2:], role=ROLE_LIST, style=dict(bank[ROLE_LIST]))
            )
        elif re.match(r"^\d+[.)]\s+", stripped):
            blocks.append(
                Block(text=stripped, role=ROLE_LIST, style=dict(bank[ROLE_LIST]))
            )
        else:
            blocks.append(
                Block(text=stripped, role=ROLE_BODY, style=dict(bank[ROLE_BODY]))
            )
    flush()
    if tight:
        for block in blocks:
            block.tight = True
    return blocks


_MBOX_HEADER = re.compile(
    r"^(From|To|Cc|Subject|Date|Sent|Message-ID|In-Reply-To):\s*(.*)$"
)


def parse_mbox(lines: Sequence[str]) -> list[Message]:
    """Parse a pseudo-mbox thread (``From:``/``To:``/``Subject:`` blocks) in the order given."""

    messages: list[Message] = []
    headers: dict[str, str] | None = None
    body: list[str] = []
    in_headers = False
    for raw in lines:
        line = raw.rstrip("\n").strip()
        match = _MBOX_HEADER.match(line)
        if match and (in_headers or line.startswith("From:")):
            if line.startswith("From:") and headers is not None and not in_headers:
                messages.append(Message(headers=headers, body=body))
                headers, body = None, []
            if headers is None:
                headers = {}
            headers[match.group(1)] = match.group(2).strip()
            in_headers = True
            continue
        if not line:
            in_headers = False
            continue
        in_headers = False
        if headers is None:
            headers = {}
        body.append(line)
    if headers is not None or body:
        messages.append(Message(headers=headers or {}, body=body))
    return messages


def parse_sheets(lines: Sequence[str], default_name: str = "Data") -> list[Sheet]:
    sheets: list[Sheet] = []
    name = default_name
    rows: list[list[str]] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith("=== SHEET: ") and line.endswith(" ==="):
            if rows:
                sheets.append(Sheet(name=name, rows=rows, header_index=0))
            name = line[11:-4].strip()[:31] or default_name
            rows = []
        elif line.strip():
            rows.append([cell.strip() for cell in line.split("\t")])
    if rows:
        sheets.append(Sheet(name=name, rows=rows, header_index=0))
    return sheets


# --------------------------------------------------------------------------- anchors
def _index_of_front_matter_end(blocks: Sequence[Block]) -> int:
    """First block after the title block / memo header lines."""

    for index, block in enumerate(blocks):
        if block.type == TYPE_PAGE_BREAK:
            continue
        if block.type == TYPE_TABLE:
            return index
        if block.role not in _FRONT_ROLES:
            return index
    return len(blocks)


def _index_after_definitions(blocks: Sequence[Block]) -> int | None:
    """End of the first recitals/definitions cluster (exhibit definitions do not count)."""

    first = None
    for index, block in enumerate(blocks):
        if block.type == TYPE_PARAGRAPH and block.role in (
            ROLE_DEFINITION,
            ROLE_RECITAL,
        ):
            first = index
            break
    if first is None:
        return None
    last = first
    gap = 0
    for index in range(first + 1, len(blocks)):
        block = blocks[index]
        if block.type == TYPE_PARAGRAPH and block.role in (
            ROLE_DEFINITION,
            ROLE_RECITAL,
        ):
            last = index
            gap = 0
            continue
        if block.type == TYPE_PARAGRAPH and block.role in (
            ROLE_BODY,
            ROLE_LIST,
            ROLE_BLANK,
            ROLE_SUBHEADING,
        ):
            gap += 1
            if gap > 4:
                break
            continue
        if (
            block.type == TYPE_PARAGRAPH
            and block.role in (ROLE_HEADING, ROLE_EXHIBIT)
            and "definition" not in block.text.lower()
        ):
            break
    # Skip to the next heading so the insertion starts a fresh article.
    for index in range(last + 1, len(blocks)):
        block = blocks[index]
        if block.type == TYPE_PARAGRAPH and block.role in (
            ROLE_HEADING,
            ROLE_SUBHEADING,
            ROLE_EXHIBIT,
        ):
            return index
        if block.type == TYPE_PAGE_BREAK and index > last + 1:
            return index
    return last + 1


def _index_of_back_matter(blocks: Sequence[Block]) -> int:
    """Where the signature page (or trailing exhibits) begins.

    Exhibit headings only count once the body is behind us: a document that
    *is* an exhibit ("EXHIBIT D — FORM OF COMPLIANCE CERTIFICATE") opens with
    one, and treating that as back matter would leave no body at all.
    """

    def rewind(index: int) -> int:
        while index > 0 and (
            blocks[index - 1].type == TYPE_PAGE_BREAK
            or blocks[index - 1].role == ROLE_BLANK
        ):
            index -= 1
        return index

    halfway = len(blocks) // 2
    for index, block in enumerate(blocks):
        if block.type != TYPE_PARAGRAPH:
            continue
        upper = block.text.upper()
        if (
            block.role == ROLE_SIGNATURE
            or "IN WITNESS WHEREOF" in upper
            or upper.startswith("SIGNATURE PAGE")
        ):
            return rewind(index)
        if block.role == ROLE_EXHIBIT and index >= halfway:
            return rewind(index)
    return len(blocks)


def _heading_boundary_near(blocks: Sequence[Block], fraction: float) -> int:
    target = int(len(blocks) * fraction)
    for index in range(target, len(blocks)):
        block = blocks[index]
        if block.type == TYPE_PARAGRAPH and block.role in (ROLE_HEADING, ROLE_EXHIBIT):
            return index
    return min(target, _index_of_back_matter(blocks))


def resolve_anchor(blocks: Sequence[Block], anchor: str | int) -> int:
    if isinstance(anchor, int):
        return max(0, min(anchor, len(blocks)))
    if anchor == ANCHOR_TOP:
        return _index_of_front_matter_end(blocks)
    if anchor == ANCHOR_END:
        return _index_of_back_matter(blocks)
    if anchor in (ANCHOR_AFTER_FRONT_MATTER, ANCHOR_OPERATIVE):
        after = _index_after_definitions(blocks)
        if after is not None:
            return min(after, _index_of_back_matter(blocks))
        if anchor == ANCHOR_AFTER_FRONT_MATTER:
            return _index_of_front_matter_end(blocks)
        return min(_heading_boundary_near(blocks, 0.3), _index_of_back_matter(blocks))
    raise ValueError(f"unknown anchor {anchor!r}")


# --------------------------------------------------------------------------- length control
def _sections(blocks: Sequence[Block], start: int, end: int) -> list[tuple[int, int]]:
    """Heading-delimited spans inside [start, end)."""

    spans: list[tuple[int, int]] = []
    current = start
    for index in range(start, end):
        block = blocks[index]
        if (
            block.type == TYPE_PARAGRAPH
            and block.role in (ROLE_HEADING, ROLE_EXHIBIT)
            and index > current
        ):
            spans.append((current, index))
            current = index
    if current < end:
        spans.append((current, end))
    return spans


def trim_to_target(
    blocks: list[Block],
    target_words: int,
    protected: tuple[int, int] | None,
    trim_head: bool = True,
    keep_fraction: float = 0.35,
) -> tuple[list[Block], tuple[int, int] | None]:
    """Drop whole trailing sections (and exhibits) until the seed prose fits the target."""

    def words_of(items: Sequence[Block]) -> int:
        return sum(block.word_count() for block in items)

    total = words_of(blocks)
    if total <= target_words:
        return blocks, protected
    back = _index_of_back_matter(blocks)
    front = _index_of_front_matter_end(blocks)
    op_start, op_end = protected if protected else (back, back)
    # Candidate spans: sections between the operative block and the back matter first,
    # then sections between front matter and the operative block.
    tail = [span for span in _sections(blocks, op_end, back)]
    head = [span for span in _sections(blocks, front, op_start)]
    # The opening section (parties, recitals, or the memo's first paragraphs)
    # always survives; so does at least 35% of the seed prose.
    removable = list(reversed(tail)) + (list(reversed(head[1:])) if trim_head else [])
    floor_words = max(target_words, int(total * keep_fraction))
    # Exhibits after the signature page are the cheapest to drop.
    exhibit_start = None
    for index in range(back, len(blocks)):
        block = blocks[index]
        if block.type == TYPE_PARAGRAPH and block.role == ROLE_EXHIBIT:
            exhibit_start = index
            break
    keep = [True] * len(blocks)
    if exhibit_start is not None and total > target_words:
        for index in range(exhibit_start, len(blocks)):
            keep[index] = False
        total = words_of([b for b, k in zip(blocks, keep, strict=True) if k])
    for start, end in removable:
        if total <= target_words:
            break
        span_words = words_of(blocks[start:end])
        if total - span_words < floor_words * 0.8:
            continue
        for index in range(start, end):
            keep[index] = False
        total = words_of([b for b, k in zip(blocks, keep, strict=True) if k])
    kept: list[Block] = []
    new_span: tuple[int, int] | None = None
    for index, (block, flag) in enumerate(zip(blocks, keep, strict=True)):
        if protected and index == protected[0]:
            new_span = (len(kept), len(kept) + (protected[1] - protected[0]))
        if flag:
            kept.append(block)
    return kept, new_span


# --------------------------------------------------------------------------- composition
def _reskin_blocks(
    blocks: Sequence[Block],
    reskin: Reskin,
    writer: Callable[[Block, ContentPlan], str | None] | None,
    plan: ContentPlan,
) -> list[Block]:
    out: list[Block] = []
    for block in blocks:
        clone = copy.deepcopy(block)
        if clone.type == TYPE_TABLE:
            clone.rows = [
                [reskin.apply(cell) for cell in row] for row in (clone.rows or [])
            ]
            out.append(clone)
            continue
        if clone.type == TYPE_PARAGRAPH and clone.text:
            rewritten = (
                writer(clone, plan)
                if writer and clone.role in (ROLE_BODY, ROLE_RECITAL, ROLE_LIST)
                else None
            )
            if rewritten:
                clone.text = reskin.scrub(rewritten)
                clone.runs = None
            else:
                clone.text = reskin.apply(clone.text)
                if clone.runs:
                    clone.runs = [
                        [reskin.apply(text), style] for text, style in clone.runs
                    ]
        out.append(clone)
    return out


def _set_paragraph_text(block: Block, text: str) -> None:
    block.text = text
    block.runs = None


def _retitle(blocks: list[Block], title: str) -> None:
    """Install the caller's title verbatim; a shouted seed title keeps its look via ``caps``."""

    for block in blocks:
        if block.type == TYPE_PARAGRAPH and block.role == ROLE_TITLE:
            if block.text.isupper() and not title.isupper():
                block.style = {**block.style, "caps": 1}
            _set_paragraph_text(block, title)
            return
    style = {"al": "center", "b": 1, "sa": 240, "kn": 1}
    blocks.insert(0, Block(text=title, role=ROLE_TITLE, style=style))


def _furniture(
    seed: Sequence[Block],
    override: str | None,
    reskin: Reskin,
    old_title: str,
    new_title: str,
    keep_fields: bool,
) -> list[Block]:
    paragraphs = [copy.deepcopy(block) for block in seed]
    for block in paragraphs:
        text = block.text
        if old_title and new_title and old_title.casefold() in text.casefold():
            text = re.sub(re.escape(old_title), new_title, text, flags=re.I)
        block.text = reskin.apply(text)
        block.runs = None
    if override is None:
        return paragraphs
    style = dict(paragraphs[0].style) if paragraphs else {"al": "center", "sz": 18}
    result = [Block(text=override, role=ROLE_META, style=style)]
    if keep_fields and not any(
        token in override for token in (FIELD_PAGE, FIELD_NUMPAGES)
    ):
        field_block = next(
            (block for block in paragraphs if FIELD_PAGE in block.text), None
        )
        result.append(
            field_block
            or Block(
                text=f"Page {FIELD_PAGE} of {FIELD_NUMPAGES}",
                role=ROLE_META,
                style={"al": "center", "sz": 16},
            )
        )
    return result


def compose_document(
    skeleton: Skeleton, plan: ContentPlan, rng: Random | None = None
) -> ComposedDocument:
    """Compose one document from a seed skeleton and a content plan."""

    rng = rng or Random(skeleton.id)
    fmt = skeleton.format
    parties = list(plan.parties) or ([plan.organization] if plan.organization else [])
    reskin = Reskin(
        rng,
        people=plan.people,
        date_offset_days=plan.date_offset_days,
        avoid=plan.avoid,
    )

    if fmt in ("docx", "txt", "md"):
        return _compose_paged(skeleton, plan, rng, reskin, parties)
    if fmt == "xlsx":
        return _compose_sheets(skeleton, plan, rng, reskin, parties)
    if fmt == "eml":
        return _compose_thread(skeleton, plan, rng, reskin, parties)
    if fmt == "pptx":
        return _compose_deck(skeleton, plan, rng, reskin, parties)
    raise CompositionError(f"unsupported seed format {fmt!r}")


def _finish(
    document: ComposedDocument, reskin: Reskin, plan: ContentPlan
) -> ComposedDocument:
    text = document.to_text()
    leaks = reskin.contains_avoided(text)
    # Operative content is the caller's and may legitimately carry graded values;
    # only seed-derived text is checked.
    if (
        leaks
        and document.operative_span is not None
        and document.format in ("docx", "txt", "md")
    ):
        start, end = document.operative_span
        seed_text = "\n".join(
            _block_lines(document.blocks[:start] + document.blocks[end:])
        )
        seed_text += "\n" + "\n".join(
            block.text for block in document.header + document.footer
        )
        leaks = reskin.contains_avoided(seed_text)
    elif leaks and plan.operative:
        operative_text = "\n".join(plan.operative).casefold()
        leaks = [needle for needle in leaks if needle not in operative_text]
    if leaks:
        # Text the caller supplied (title, furniture, parties, subject) is not
        # a leak even when it names an avoided literal such as the company.
        supplied = " ".join(
            str(value)
            for value in (
                plan.title,
                plan.header,
                plan.footer,
                plan.subject,
                plan.operative_heading,
                plan.organization,
                *plan.parties,
            )
            if value
        ).casefold()
        leaks = [needle for needle in leaks if needle not in supplied]
    if leaks:
        raise CompositionError(f"avoided literal survived composition: {leaks[:3]}")
    document.receipt.update(
        {
            "organizations_replaced": len(reskin.organizations),
            "people_replaced": len(reskin.people),
            "avoid_checked": len(reskin.avoid),
            "words": len(text.split()),
        }
    )
    return document


def _compose_paged(
    skeleton: Skeleton,
    plan: ContentPlan,
    rng: Random,
    reskin: Reskin,
    parties: list[str],
) -> ComposedDocument:
    blocks = [copy.deepcopy(block) for block in skeleton.blocks]
    trusted = "\n".join(
        [skeleton.header.text, skeleton.footer.text]
        + [
            b.text
            for b in blocks
            if b.type == TYPE_PARAGRAPH
            and b.role in (ROLE_TITLE, ROLE_PARTY, ROLE_META)
        ]
    )
    body_text = "\n".join(b.text for b in blocks if b.type == TYPE_PARAGRAPH and b.text)
    cell_text = "\n".join(
        cell
        for b in blocks
        if b.type == TYPE_TABLE
        for row in (b.rows or [])
        for cell in row
    )
    # Body first so the caller's parties bind to the organizations the prose
    # names; header/footer names follow, sharing stems where they overlap.
    reskin.learn(body_text + "\n" + cell_text, roles=parties, trusted=trusted)
    reskin.learn(trusted, trusted=trusted)

    old_title = skeleton.title
    blocks = _reskin_blocks(blocks, reskin, plan.writer, plan)
    new_title = plan.title or reskin.apply(old_title)
    if plan.title:
        _retitle(blocks, plan.title)
        display_title = plan.title.title() if plan.title.isupper() else plan.title
        for block in blocks:
            if (
                block.type == TYPE_PARAGRAPH
                and block.role == ROLE_META
                and re.match(r"^(RE|Re|SUBJECT|Subject)\s*:", block.text)
            ):
                _set_paragraph_text(
                    block, f"{block.text.split(':', 1)[0]}: {display_title}"
                )

    header = _furniture(
        skeleton.header.paragraphs,
        plan.header,
        reskin,
        old_title,
        new_title,
        keep_fields=False,
    )
    if plan.header is None and parties and header:
        # A seed header that names an organization outside the caller's
        # parties (some exemplars are internally inconsistent) is rebuilt.
        mentioned = parties_of([block.text for block in header])
        if any(name not in " ".join(parties) for name in mentioned) or not mentioned:
            style = dict(header[0].style)
            names = " / ".join(
                re.sub(
                    r",?\s*(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|L\.P\.|LP|LLP|PLC|Co\.)\s*$",
                    "",
                    party.strip(),
                )
                for party in parties[:2]
            )
            header = [
                Block(
                    text=f"{new_title.title() if new_title.isupper() else new_title} — {names} — Confidential",
                    role=ROLE_META,
                    style=style,
                )
            ]
    footer = _furniture(
        skeleton.footer.paragraphs,
        plan.footer,
        reskin,
        old_title,
        new_title,
        keep_fields=True,
    )
    if plan.title and plan.footer is None:
        # A footer that restates the seed's subject follows the new title; a
        # bare "Page" label without its field is a seed artifact and goes.
        generic = (
            "confidential",
            "privileged",
            "©",
            "all rights",
            "draft",
            "attorney",
            "internal use",
            "do not",
        )
        kept: list[Block] = []
        for block in footer:
            lowered = block.text.casefold()
            if lowered.strip() in {"page", "page:"}:
                continue
            if (
                FIELD_PAGE not in block.text
                and FIELD_NUMPAGES not in block.text
                and not any(marker in lowered for marker in generic)
            ):
                _set_paragraph_text(
                    block, plan.title.title() if plan.title.isupper() else plan.title
                )
            kept.append(block)
        footer = kept
    if not footer:
        footer = [
            Block(
                text=f"Page {FIELD_PAGE} of {FIELD_NUMPAGES}",
                role=ROLE_META,
                style={"al": "center", "sz": 16},
            )
        ]
    if not header and (plan.organization or parties):
        names = " / ".join(
            re.sub(
                r",?\s*(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|L\.P\.|LP|LLP|PLC|Co\.)\s*$",
                "",
                party.strip(),
            )
            for party in (list(parties) or [str(plan.organization)])[:2]
        )
        header = [
            Block(
                text=f"{new_title.title() if new_title.isupper() else new_title} — {names} — Confidential",
                role=ROLE_META,
                style={"al": "center", "sz": 18},
            )
        ]

    span: tuple[int, int] | None = None
    if plan.operative:
        bank = _style_bank(blocks)
        inserted = parse_operative(
            plan.operative,
            bank,
            _table_template(blocks),
            tight=plan.tight_operative or plan.verbatim_operative,
            verbatim=plan.verbatim_operative,
        )
        if plan.operative_heading:
            inserted.insert(
                0,
                Block(
                    text=plan.operative_heading,
                    role=ROLE_HEADING,
                    style=dict(bank[ROLE_HEADING]),
                ),
            )
        if plan.anchor == ANCHOR_REPLACE_BODY:
            start = _index_of_front_matter_end(blocks)
            after = _index_after_definitions(blocks)
            if after is not None:
                start = min(after, _index_of_back_matter(blocks))
            end = _index_of_back_matter(blocks)
            blocks = blocks[:start] + inserted + blocks[end:]
            span = (start, start + len(inserted))
        else:
            start = resolve_anchor(blocks, plan.anchor)
            blocks = blocks[:start] + inserted + blocks[start:]
            span = (start, start + len(inserted))

    if plan.target_words:
        blocks, span = trim_to_target(
            blocks,
            plan.target_words,
            span,
            trim_head=plan.trim_head,
            keep_fraction=plan.keep_fraction,
        )

    document = ComposedDocument(
        seed_id=skeleton.id,
        source=skeleton.source,
        format=skeleton.format,
        kind=skeleton.kind,
        title=new_title,
        page=dict(skeleton.page),
        font=dict(skeleton.font),
        header=header,
        footer=footer,
        blocks=blocks,
        operative_span=span,
        receipt={
            "seed": skeleton.id,
            "seed_source": skeleton.source,
            "seed_kind": skeleton.kind,
            "anchor": str(plan.anchor),
        },
    )
    return _finish(document, reskin, plan)


_NUMBER_CELL = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^[+-]?\d+(?:\.\d+)?$")


def _jitter_number(cell: str, factor: float) -> str:
    if not _NUMBER_CELL.match(cell.strip()) or cell.strip() in ("0", "1"):
        return cell
    raw = cell.strip().replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return cell
    if abs(value) < 10 and "." not in raw:
        return cell
    scaled = value * factor
    if "." in raw:
        decimals = len(raw.split(".")[1])
        text = f"{scaled:,.{decimals}f}" if "," in cell else f"{scaled:.{decimals}f}"
    else:
        text = f"{int(round(scaled)):,}" if "," in cell else str(int(round(scaled)))
    return text


def _compose_sheets(
    skeleton: Skeleton,
    plan: ContentPlan,
    rng: Random,
    reskin: Reskin,
    parties: list[str],
) -> ComposedDocument:
    all_text = "\n".join(
        cell for sheet in skeleton.sheets for row in sheet.rows for cell in row
    )
    reskin.learn(
        all_text,
        roles=parties,
        trusted="\n".join(
            cell for sheet in skeleton.sheets for row in sheet.rows[:3] for cell in row
        ),
    )
    factor = rng.choice((0.7, 0.82, 0.9, 1.1, 1.24, 1.37))
    sheets: list[Sheet] = []
    for sheet in skeleton.sheets:
        rows = [
            [_jitter_number(reskin.apply(cell), factor) for cell in row]
            for row in sheet.rows
        ]
        sheets.append(
            Sheet(
                name=sheet.name,
                rows=rows,
                header_index=sheet.header_index,
                widths=sheet.widths,
                total_rows=None,
            )
        )
    if plan.operative:
        operative = parse_sheets(plan.operative, plan.operative_sheet_name or "Data")
        names = {sheet.name.casefold() for sheet in operative}
        sheets = operative + [
            sheet for sheet in sheets if sheet.name.casefold() not in names
        ]
    title = plan.title or reskin.apply(skeleton.title)
    document = ComposedDocument(
        seed_id=skeleton.id,
        source=skeleton.source,
        format="xlsx",
        kind=skeleton.kind,
        title=title,
        sheets=sheets,
        receipt={
            "seed": skeleton.id,
            "seed_source": skeleton.source,
            "seed_kind": skeleton.kind,
        },
    )
    return _finish(document, reskin, plan)


def _compose_thread(
    skeleton: Skeleton,
    plan: ContentPlan,
    rng: Random,
    reskin: Reskin,
    parties: list[str],
) -> ComposedDocument:
    seed_text = "\n".join("\n".join(message.body) for message in skeleton.messages)
    header_text = "\n".join(
        f"{k}: {v}" for message in skeleton.messages for k, v in message.headers.items()
    )
    reskin.learn(header_text + "\n" + seed_text, roles=parties, trusted=header_text)
    history: list[Message] = []
    for message in skeleton.messages:
        headers = {key: reskin.apply(value) for key, value in message.headers.items()}
        history.append(
            Message(
                headers=headers,
                body=[reskin.apply(paragraph) for paragraph in message.body],
            )
        )
    subject = (
        plan.subject
        or plan.title
        or (history[0].headers.get("Subject") if history else "")
        or "Matter update"
    )
    if plan.operative and any(line.startswith("From:") for line in plan.operative):
        # A thread of the caller's own messages (chronological): newest on top,
        # then the seed's re-skinned history as the older quoted messages.
        own = parse_mbox(plan.operative)
        own.reverse()
        for message in own:
            message.headers.setdefault("Subject", subject)
        if own and plan.subject:
            own[0].headers["Subject"] = plan.subject
        messages = own + history
    elif plan.operative:
        sender = plan.sender or generate_person(rng)
        recipients = (
            list(plan.recipients)
            or [history[0].headers.get("From", generate_person(rng))]
            if history
            else [generate_person(rng)]
        )
        newest = Message(
            headers={
                "From": sender,
                "To": "; ".join(recipients),
                "Subject": subject
                if subject.lower().startswith("re:") or not history
                else f"RE: {subject}",
                "Date": history[0].headers.get("Date", "") if history else "",
            },
            body=[line for line in plan.operative if line.strip()],
        )
        messages = [newest] + history
    else:
        messages = history
        if messages and plan.subject:
            messages[0].headers["Subject"] = plan.subject
    document = ComposedDocument(
        seed_id=skeleton.id,
        source=skeleton.source,
        format="eml",
        kind=skeleton.kind,
        title=subject,
        messages=messages,
        receipt={
            "seed": skeleton.id,
            "seed_source": skeleton.source,
            "seed_kind": skeleton.kind,
        },
    )
    return _finish(document, reskin, plan)


def _compose_deck(
    skeleton: Skeleton,
    plan: ContentPlan,
    rng: Random,
    reskin: Reskin,
    parties: list[str],
) -> ComposedDocument:
    seed_text = "\n".join(
        slide.title + "\n" + "\n".join(slide.body) for slide in skeleton.slides
    )
    trusted = (
        "\n".join(slide.title for slide in skeleton.slides[:2])
        + "\n"
        + "\n".join(skeleton.slides[0].body if skeleton.slides else [])
    )
    reskin.learn(seed_text, roles=parties, trusted=trusted)
    slides = [
        Slide(
            title=reskin.apply(slide.title),
            body=[reskin.apply(line) for line in slide.body],
            tables=[
                [[reskin.apply(cell) for cell in row] for row in table]
                for table in slide.tables
            ],
        )
        for slide in skeleton.slides
    ]
    if plan.title and slides:
        slides[0].title = plan.title
    if plan.operative:
        extra: list[Slide] = []
        current: Slide | None = None
        rows: list[list[str]] = []
        for raw in plan.operative:
            line = raw.rstrip("\n")
            if "\t" in line:
                rows.append([cell.strip() for cell in line.split("\t")])
                continue
            if rows and current is not None:
                current.tables.append(rows)
                rows = []
            if line.startswith("# ") or line.startswith("## "):
                current = Slide(title=line.lstrip("# ").strip(), body=[])
                extra.append(current)
            elif line.strip():
                if current is None:
                    current = Slide(title=plan.title or "Summary", body=[])
                    extra.append(current)
                current.body.append(line.strip().lstrip("- ").strip())
        if rows and current is not None:
            current.tables.append(rows)
        insert_at = min(len(slides), 2)
        slides = slides[:insert_at] + extra + slides[insert_at:]
    document = ComposedDocument(
        seed_id=skeleton.id,
        source=skeleton.source,
        format="pptx",
        kind=skeleton.kind,
        title=plan.title or (slides[0].title if slides else skeleton.title),
        slides=slides,
        receipt={
            "seed": skeleton.id,
            "seed_source": skeleton.source,
            "seed_kind": skeleton.kind,
        },
    )
    return _finish(document, reskin, plan)


__all__ = [
    "ANCHOR_AFTER_FRONT_MATTER",
    "ANCHOR_END",
    "ANCHOR_OPERATIVE",
    "ANCHOR_REPLACE_BODY",
    "ANCHOR_TOP",
    "ComposedDocument",
    "CompositionError",
    "ContentPlan",
    "LAYOUT_SCHEMA",
    "compose_document",
    "parse_mbox",
    "parse_operative",
    "parse_sheets",
    "resolve_anchor",
    "trim_to_target",
]
