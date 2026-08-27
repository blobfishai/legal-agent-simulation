"""Seed-structured realistic document generation (vendored from blobfishai/packages/document-seeds).

Real professional documents are long, multi-page, and structured: a centered
title block, recitals, definitions with bold defined terms, numbered articles
and sections, bordered tables, signature blocks, exhibits, and running
headers/footers with page numbers. Template prose never reproduces that
shape. This package mines the *structure* of real exemplars (Harvey LAB,
MIT-licensed) into compact skeletons, then composes new documents that keep
the seed's structure while every fact — parties, people, dates, amounts, and
the operative provisions a task grades — is replaced or supplied by the
caller.

Heuristic-first: no network and no model is needed. ``compose`` is
deterministic for a given seed, content plan, and random seed.
"""

from importlib import import_module
from typing import Any

from .skeleton import Block, Skeleton

_LAZY = {
    "SeedCatalog": ".catalog",
    "load_catalog": ".catalog",
    "ComposedDocument": ".compose",
    "ContentPlan": ".compose",
    "compose_document": ".compose",
    "render_bytes": ".render",
}


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(name)
    return getattr(import_module(module, __name__), name)


__all__ = [
    "Block",
    "ComposedDocument",
    "ContentPlan",
    "SeedCatalog",
    "Skeleton",
    "compose_document",
    "load_catalog",
    "render_bytes",
]
