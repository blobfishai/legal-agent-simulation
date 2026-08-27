"""Recipes: reproduce a composed document from a few hundred bytes.

A world stores each document's canonical ``text`` plus a recipe — the seed
id, the content plan, and the RNG seed — instead of a rendered layout. Any
consumer with the same bundled catalog recomposes the identical document
(the text is re-derived and compared byte for byte) and renders it natively.
If the catalog drifted, ``compose_from_recipe`` reports the mismatch so the
caller can fall back to text-only rendering rather than ship a document
whose bytes disagree with its extraction.
"""

from __future__ import annotations

from collections.abc import Mapping
from random import Random
from typing import Any

from .catalog import SeedCatalog, default_catalog
from .compose import ComposedDocument, CompositionError, ContentPlan, compose_document

RECIPE_SCHEMA = "blobfish.document-seed-recipe.v1"


class RecipeMismatch(ValueError):
    """The recipe no longer reproduces the stored text (catalog drift)."""


def build_recipe(
    seed_id: str,
    plan: ContentPlan,
    rng_seed: int,
    *,
    catalog: SeedCatalog | None = None,
) -> dict[str, Any]:
    catalog = catalog or default_catalog()
    ref = catalog.by_id(seed_id)
    return {
        "schema": RECIPE_SCHEMA,
        "seed": seed_id,
        "seed_source": ref.source,
        "seed_kind": ref.kind,
        "rng": int(rng_seed),
        "plan": plan.to_json(),
    }


def compose_from_recipe(
    recipe: Mapping[str, Any],
    *,
    catalog: SeedCatalog | None = None,
    expected_text: str | None = None,
) -> ComposedDocument:
    """Recompose; raise ``RecipeMismatch`` when the text no longer matches."""

    if recipe.get("schema") != RECIPE_SCHEMA:
        raise RecipeMismatch(f"unknown recipe schema {recipe.get('schema')!r}")
    catalog = catalog or default_catalog()
    try:
        skeleton = catalog.load(str(recipe["seed"]))
    except KeyError as exc:
        raise RecipeMismatch(
            f"seed {recipe.get('seed')!r} is not in the catalog"
        ) from exc
    plan = ContentPlan.from_json(recipe.get("plan") or {})
    try:
        document = compose_document(skeleton, plan, Random(int(recipe.get("rng", 0))))
    except CompositionError as exc:
        raise RecipeMismatch(str(exc)) from exc
    if expected_text is not None and document.to_text() != expected_text:
        raise RecipeMismatch(
            f"seed {recipe['seed']} no longer reproduces the stored text"
        )
    return document


__all__ = ["RECIPE_SCHEMA", "RecipeMismatch", "build_recipe", "compose_from_recipe"]
