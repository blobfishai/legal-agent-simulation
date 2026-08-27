"""Load the bundled seed catalog and pick the closest exemplar.

Selection is deterministic: candidates are scored on format, kind, practice
area, title overlap, and length fit; ties are broken by a seeded RNG so
different worlds draw different exemplars from the same bucket.
"""

from __future__ import annotations

import gzip
import json
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from random import Random
from typing import Any

from .skeleton import Skeleton

ENV_CATALOG = "BLOBFISH_DOCUMENT_SEEDS"
BUNDLED_DIR = Path(__file__).resolve().parent / "catalog"
INDEX_FILENAME = "index.json"

# Families: a requested kind matches its own bucket first, then its family.
KIND_FAMILIES: dict[str, tuple[str, ...]] = {
    "agreement": ("agreement", "term_sheet", "redline"),
    "memo": ("memo", "report", "letter", "notes"),
    "letter": ("letter", "memo", "email"),
    "minutes": ("minutes", "resolution", "notes", "memo"),
    "resolution": ("resolution", "minutes", "certificate"),
    "certificate": ("certificate", "resolution", "letter"),
    "policy": ("policy", "checklist", "report", "memo"),
    "checklist": ("checklist", "policy", "schedule"),
    "report": ("report", "memo", "plan"),
    "schedule": ("schedule", "spreadsheet", "report"),
    "plan": ("plan", "report", "memo"),
    "pleading": ("pleading", "letter", "memo"),
    "filing": ("filing", "report", "certificate"),
    "notes": ("notes", "memo", "email"),
    "term_sheet": ("term_sheet", "agreement", "memo"),
    "redline": ("redline", "agreement"),
    "template": ("template", "agreement", "policy"),
    "spreadsheet": ("spreadsheet",),
    "email": ("email",),
    "deck": ("deck",),
    "document": ("document", "memo", "report"),
}

_WORD = re.compile(r"[a-z0-9]{3,}")
_STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "this",
    "that",
    "draft",
    "final",
    "v1",
    "v2",
    "copy",
    "file",
}


def _tokens(text: str) -> set[str]:
    return {token for token in _WORD.findall(text.casefold()) if token not in _STOP}


@dataclass(frozen=True)
class SeedRef:
    """One index row: what selection sees."""

    id: str
    source: str
    practice_area: str
    format: str
    kind: str
    subkind: str
    title: str
    tags: tuple[str, ...]
    words: int
    tables: int
    pages: int
    furnished: bool
    file: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SeedRef":
        return cls(
            id=str(row["id"]),
            source=str(row.get("src", "")),
            practice_area=str(row.get("area", "")),
            format=str(row.get("fmt", "docx")),
            kind=str(row.get("kind", "document")),
            subkind=str(row.get("subkind", "")),
            title=str(row.get("title", "")),
            tags=tuple(str(tag) for tag in row.get("tags") or ()),
            words=int(row.get("words", 0)),
            tables=int(row.get("tables", 0)),
            pages=int(row.get("pages", 1)),
            furnished=bool(row.get("hf", 0)),
            file=str(row.get("file", "")),
        )


@dataclass
class SeedCatalog:
    root: Path
    refs: list[SeedRef]
    _cache: dict[str, Skeleton] = field(default_factory=dict, repr=False)
    _loaded_files: set[str] = field(default_factory=set, repr=False)

    def __len__(self) -> int:
        return len(self.refs)

    @property
    def practice_areas(self) -> list[str]:
        return sorted({ref.practice_area for ref in self.refs})

    @property
    def kinds(self) -> list[str]:
        return sorted({ref.kind for ref in self.refs})

    def by_id(self, seed_id: str) -> SeedRef:
        for ref in self.refs:
            if ref.id == seed_id:
                return ref
        raise KeyError(seed_id)

    def load(self, ref: SeedRef | str) -> Skeleton:
        """Load the full skeleton (prose included) for one index row."""

        if isinstance(ref, str):
            ref = self.by_id(ref)
        if ref.id in self._cache:
            return self._cache[ref.id]
        if ref.file not in self._loaded_files:
            path = self.root / ref.file
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        payload = json.loads(line)
                        self._cache[str(payload["id"])] = Skeleton.from_json(payload)
            self._loaded_files.add(ref.file)
        if ref.id not in self._cache:
            raise KeyError(f"seed {ref.id} missing from {ref.file}")
        return self._cache[ref.id]

    # ---- selection
    def candidates(
        self,
        *,
        format: str | None = None,
        kind: str | None = None,
        practice_area: str | Sequence[str] | None = None,
        exclude: Iterable[str] = (),
        max_words: int | None = None,
    ) -> list[SeedRef]:
        excluded = set(exclude)
        rows = [ref for ref in self.refs if ref.id not in excluded]
        if format:
            rows = [ref for ref in rows if ref.format == format.lstrip(".").lower()]
        if max_words:
            # A hard length cap (size-gated consumers); ignored if nothing fits.
            bounded = [ref for ref in rows if ref.words <= max_words]
            if bounded:
                rows = bounded
        if kind:
            family = KIND_FAMILIES.get(kind, (kind,))
            rows = [ref for ref in rows if ref.kind in family]
        if practice_area:
            # A single area, or an ordered list of preferred areas: the first
            # area (or prefix of areas) holding at least three candidates wins,
            # so a thin practice area never drags in exemplars from an
            # unrelated one when a neighbouring area could serve.
            areas = (
                [practice_area]
                if isinstance(practice_area, str)
                else list(practice_area)
            )
            for depth in range(1, len(areas) + 1):
                preferred = [ref for ref in rows if ref.practice_area in areas[:depth]]
                if len(preferred) >= 3:
                    rows = preferred
                    break
        return rows

    def score(
        self,
        ref: SeedRef,
        *,
        kind: str | None,
        subkind: str | None,
        practice_area: str | Sequence[str] | None,
        title: str | None,
        tags: Sequence[str],
        target_words: int | None,
        want_tables: bool | None,
    ) -> float:
        score = 0.0
        if kind:
            family = KIND_FAMILIES.get(kind, (kind,))
            if ref.kind == kind:
                score += 6
            elif ref.kind in family:
                score += 6 - 1.5 * family.index(ref.kind)
        if subkind and ref.subkind == subkind:
            score += 4
        if practice_area:
            areas = (
                [practice_area]
                if isinstance(practice_area, str)
                else list(practice_area)
            )
            if ref.practice_area in areas:
                score += 3 - 0.5 * min(4, areas.index(ref.practice_area))
        if title:
            wanted = _tokens(title)
            have = _tokens(ref.title) | _tokens(Path(ref.source).stem.replace("-", " "))
            if wanted and have:
                score += 5 * len(wanted & have) / len(wanted | have) + 1.5 * len(
                    wanted & have
                )
        if tags:
            wanted_tags = {tag.casefold() for tag in tags}
            score += 0.75 * len(wanted_tags & {tag.casefold() for tag in ref.tags})
        if target_words and ref.words:
            ratio = min(ref.words, target_words) / max(ref.words, target_words)
            score += 2 * ratio
        if want_tables is True:
            score += 1.5 if ref.tables else -1
        if ref.format == "docx" and ref.furnished:
            score += 1
        return score

    def select(
        self,
        *,
        format: str = "docx",
        kind: str | None = None,
        subkind: str | None = None,
        practice_area: str | Sequence[str] | None = None,
        title: str | None = None,
        tags: Sequence[str] = (),
        target_words: int | None = None,
        want_tables: bool | None = None,
        exclude: Iterable[str] = (),
        rng: Random | None = None,
        top: int = 4,
        max_words: int | None = None,
    ) -> SeedRef:
        """The closest exemplar; among the ``top`` scorers a seeded draw adds variety."""

        rows = self.candidates(
            format=format,
            kind=kind,
            practice_area=practice_area,
            exclude=exclude,
            max_words=max_words,
        )
        if not rows:
            rows = self.candidates(format=format, exclude=exclude, max_words=max_words)
        if not rows:
            raise LookupError(f"no seed available for format={format!r} kind={kind!r}")
        ranked = sorted(
            rows,
            key=lambda ref: (
                -self.score(
                    ref,
                    kind=kind,
                    subkind=subkind,
                    practice_area=practice_area,
                    title=title,
                    tags=tags,
                    target_words=target_words,
                    want_tables=want_tables,
                ),
                ref.id,
            ),
        )
        pool = ranked[: max(1, top)]
        if rng is None or len(pool) == 1:
            return pool[0]
        return pool[rng.randrange(len(pool))]

    def summary(self) -> dict[str, Any]:
        counts: dict[str, dict[str, int]] = {"formats": {}, "kinds": {}, "areas": {}}
        for ref in self.refs:
            counts["formats"][ref.format] = counts["formats"].get(ref.format, 0) + 1
            counts["kinds"][ref.kind] = counts["kinds"].get(ref.kind, 0) + 1
            counts["areas"][ref.practice_area] = (
                counts["areas"].get(ref.practice_area, 0) + 1
            )
        return {
            "seeds": len(self.refs),
            **{key: dict(sorted(value.items())) for key, value in counts.items()},
        }


def load_catalog(path: str | Path | None = None) -> SeedCatalog:
    """Load a catalog directory (default: the bundled one, or ``$BLOBFISH_DOCUMENT_SEEDS``)."""

    root = Path(path) if path else Path(os.environ.get(ENV_CATALOG) or BUNDLED_DIR)
    index_path = root / INDEX_FILENAME
    if not index_path.is_file():
        raise FileNotFoundError(f"seed catalog index missing: {index_path}")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    refs = [SeedRef.from_row(row) for row in payload.get("seeds", [])]
    return SeedCatalog(root=root, refs=refs)


@lru_cache(maxsize=4)
def default_catalog(path: str | None = None) -> SeedCatalog:
    """Process-wide cached catalog."""

    return load_catalog(path)


__all__ = [
    "BUNDLED_DIR",
    "ENV_CATALOG",
    "KIND_FAMILIES",
    "SeedCatalog",
    "SeedRef",
    "default_catalog",
    "load_catalog",
]
