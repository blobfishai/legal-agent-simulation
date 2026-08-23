# Harvey LAB `v1.0` release audit — versus the pinned mirror `7be41d5`

Audited 2026-08-22 against the live remote `https://github.com/harveyai/harvey-labs`.
Companion machine-readable delta: `research/harvey-v1.0-delta.json`.
Deep input audit report: `reports/harvey-v1.0-input-audit.json` (allowlist:
`reports/harvey-v1.0-known-defects.json`).

## Executive verdict

**Our pinned source `7be41d5` is a strict content superset of the public v1.0
release, and is newer.** The v1.0 tag adds **zero** tasks, documents, or harness
features that the pin lacks. Everything the new-lineage commit messages
advertise — the 409 contract-negotiation tasks (#81), the `tasks/diligence`
area (#109–#111), DOCX-redline criteria (#76), Gemini/OpenAI/Mistral judges
(#55), Fireworks/Baseten adapters (#83/#84), Windows/UTF-8 fixes, offline CI
(#113) — is already present, bit-identical, in the `7be41d5` tree. **No ingest
gap exists. The pin stands.**

Three genuine findings:

1. `7be41d5` additionally carries the entire **firm-knowledge lane** (250 tasks
   + the shared 9,288-file DMS = 9,538 files) that the public v1.0 release does
   not ship, plus **post-v1.0 content fixes** to 50 files (6 task rubrics, 44
   documents) matching the public fix PRs #122/#125/#127/#128.
2. The v1.0 tag ships one **release defect**: a stray zero-byte artifact
   `tasks/contracts/financing/credit-lending-subsequent-turn-redline/scenario-03/documents/.!33830!commitment-schedule.xlsx`
   (a partial-transfer temp name; the real `commitment-schedule.xlsx` is intact
   beside it, and no task references the stray file).
3. One upstream feature exists on **no** line we host: the *reasoning-first LAB
   judge* at the tip of `calvin/reasoning-first-lab-judge` (4 files; see §5).

## 1. Server truth and the three lineages

| Ref | Commit | Date | Lineage |
|---|---|---|---|
| `HEAD` = `refs/heads/main` (our pin) | `7be41d57fd5a` | 2026-08-11 | internal-superset line; tip commit is public-numbered PR #142 (“firm-knowledge: add response.md output instruction + deliverable hooks”) |
| `refs/tags/v1.0` (annotated, tagger Calvin Qi, 2026-07-24) | `1da4750171bc` | 2026-07-24 | public line, rooted at squashed `initial commit` `81330519` (2026-05-06); 25 commits, PRs #44–#113 |
| `taxonomy-alignment` / `entity-cleanup` / `entity-cleanup-v2` | tips `708e842a` / `e325abae` / `c001902e` | 2026-05-05/06 | third, pre-publication line (internal PRs #19–#24 + cleanup batches); disjoint from both others |

The three lines share **no git history** (every `merge-base` query fails;
`git log --cherry` marks no patch-equivalents), yet §2 shows their **content**
converged: the 2026-05-06 public squash `81330519` captured the cleanup line’s
work (fictional-name replacement, taxonomy alignment, removal of
`detailed_instructions`, rewritten docx/pptx/xlsx skills), the public line then
advanced through PR #113/v1.0, and the internal `main` kept absorbing the same
public PRs (its tip is #142) while retaining firm-knowledge. History diverged;
content did not. **Tree comparison, not commit ancestry, is the only valid
lens for this repository**, and all deltas below are tree-level.

## 2. Content delta (tree-level, `v1.0` → `7be41d5`)

Totals: v1.0 has **1,760 tasks / 111,826 criteria / 53,445 files /
2,737,470,668 bytes** under `tasks/` (33,954 docx · 10,576 xlsx · 5,169 eml ·
1,766 json · 1,091 pptx · 889 txt · rest misc). The pin has 2,010 tasks /
114,437 criteria / 62,982 files, matching the committed baseline in
`world/ingest/README.md` exactly.

| Delta class | Count | Content |
|---|---|---|
| Tasks only at v1.0 | **0** | — |
| Tasks only at pin | **250** | the entire `firm-knowledge` area |
| Files only at pin | **9,538** | firm-knowledge: 250 `task.json` + 9,288 shared-DMS files — exactly the documented lane |
| Files only at v1.0 | **1** | the zero-byte `.!33830!commitment-schedule.xlsx` stray (finding 2) |
| Same path, different bytes | **50** | 6 `task.json` + 44 documents; every inspected diff shows the **pin side is the fix** |
| Identical tasks | **1,754** of 1,754 shared − 6 | includes all 498 `contracts` and all 11 `diligence` tasks, bit-identical |

Per-area task counts are identical on both sides for all 26 shared areas
(contracts 498, corporate-ma 161, intellectual-property 147, corporate-governance 97,
funds-asset-management 66, litigation-dispute-resolution 52, …); the pin adds
firm-knowledge (250) as the 27th area. Full lists: `research/harvey-v1.0-delta.json`.

**The 6 modified rubrics** (v1.0 → pin direction, matching public fix PRs):

- `corporate-governance/compare-document-production-against-discovery-request-specifications` — full rubric overhaul + retitle (#127: “restore matching rubric + strip answer-giving notes”).
- `immigration/draft-perm-recruitment-report`, `immigration/extract-filing-requirements-from-regulatory-guidance`, `tax/identify-issues-in-annual-tax-compliance-report` — stale real-entity names replaced (Cromdale Consulting→Mercer, Venkatesh→Subramanian; #125 “stale entity names in three task rubrics”).
- `intellectual-property/compare-asserted-patent-claims-against-accused-product` — drops a criterion referencing prior art absent from the documents, renumbers C-031…(rubric/document desync class).
- `litigation-dispute-resolution/build-litigation-case-timeline` — drops two deposition criteria unsupported by the record.

Net effect: v1.0 carries **12 more criteria** (111,826) than the pin’s practice
lane (111,814) — all 12 are criteria the fixes deliberately **removed** as
undischargeable. The pin’s rubric set is the corrected one. The 44 differing
documents concentrate in `diligence/*` (good-standing certificates, FAA/AS9100
records, the CMA provisional-findings letter deduplicated by #128) plus two
`corporate-ma` cloudmesh schedules and one `corporate-governance` production log
— the #122 “Fixes for diligence documents” batch.

## 3. Deep input audit of the v1.0 tree

Method: second read-only worktree at `research/repos/harveyai@harvey-labs-v1.0`
(detached at the tag), then `tools/audit_harvey_inputs.py` — every task’s
document set resolved, every byte hashed, every OOXML container decompressed
with ZIP CRCs checked and every XML part parsed —
`--expected-commit 1da4750…`, report at `reports/harvey-v1.0-input-audit.json`.

The nine known upstream OOXML defects (raw ampersands in XML text nodes) carry
over verbatim: all nine files are **bit-identical** at v1.0 (none is among the
50 differing paths), so `reports/harvey-v1.0-known-defects.json` re-pins the
same nine `(path, part, sha256, occurrences)` rows to commit `1da4750…`. No new
allowlist entry was needed or added.

**Result: PASS except one upstream release defect (exit 1).** 1,760 tasks /
1,760 document sets resolved; **51,684 physical inputs, 2,685,895,182 bytes,
51,253 unique blobs** — exactly the pin’s 51,683 task-local documents plus the
one stray (the pin’s corpus byte total differs only through the 44 fixed
documents, net +247,187 bytes on the pin side). Worktree clean, commit matches
the expected pin. Format exercise: **45,620 OOXML containers** fully
decompressed with CRCs verified and **948,922 XML parts parsed**; zero LFS
pointers, zero legacy-Office containers, zero PDFs in the corpus. The **9**
failed XML parts are precisely the nine allowlisted raw-ampersand defects
(`known_source_defects.matched: true`). The **single validation error** is the
finding-2 stray: `…/.!33830!commitment-schedule.xlsx: ValueError: zero-byte
input` (`zero_byte_inputs: 1`). By extension: docx 33,954 / 2,213,266,091 B ·
xlsx 10,575 / 270,192,197 B · eml 5,169 / 46,982,834 B · pptx 1,091 /
99,745,377 B · txt 889 / 55,575,066 B · json 5 / 133,617 B. Evidence-tree
SHA-256 recorded in the report (`physical_input_tree_sha256`).

## 4. Harness delta

**Shared by both lines (already mirrored at the pin).** DOCX-redline criteria
(#76): a criterion may set `evaluation_options.include_docx_redlines`, and
`evaluation/scoring.py` then extracts deliverable text with
`DocxTrackChanges.ALL` so the judge sees insertions/deletions rather than the
flattened accepted text; the agent-side `harness/skills/docx/scripts/redline.py`
generates tracked-changes files (PyPI `redlines` with a pure-OOXML fallback).
Multi-judge (#55): `evaluation/judge.py` detects the provider from the model
name (anthropic / gemini→google / gpt→openai / mistral) behind one `Judge`
class. Doc-coverage (#95): `harness/tools.py` emits `total_documents` and
`run_eval` reports `documents_read/total_documents` (fixing the always-zero
denominator). Adapters: anthropic, google, openai, mistral, fireworks, baseten.
Offline CI (#113): `.github/workflows/build-sandbox-image.yml` +
`validate-task-schema.yml`.

**Only at the pin (post-v1.0, 11 files: `evaluation/{run_eval,compare,report,charts}.py`,
`harness/run.py`, 2 tests, README + 3 docs).** Standard **dual-judge**
evaluation (#120): `evaluate_run_dual` scores every criterion independently
with `JUDGE_MODELS = ("claude-sonnet-4-6", "gpt-5.5")`, preserves per-judge
artifacts, and averages into `scores_dual.json`; comparison/report/chart
support on top. And `docs_dir` support in `harness/run.py`, which is what lets
the 250 firm-knowledge tasks share one DMS tree (`"../../dms"`) instead of
duplicating it 250 times.

**On neither hosted line.** The reasoning-first LAB judge —
`calvin/reasoning-first-lab-judge` tip `8f741ae8` — modifies
`evaluation/judge.py`, `evaluation/prompts/rubric_criterion.txt`,
`harness/run.py` and adds `tests/test_judge.py` to request the judge’s
reasoning **before** its verdict. The other 7 commits on that branch beyond
v1.0 (#118 bibtex, #120 dual-judge, #122/#125/#127/#128 content fixes) are all
already reflected in the pin’s content.

## 5. Unmerged-branch inventory (2026-08-22)

- `calvin/reasoning-first-lab-judge` (tip 2026-08-07; contains the v1.0 tag; 8 commits past it) — everything past v1.0 is in the pin’s content **except** the tip’s reasoning-first judge (4 files, §4). The one branch worth re-checking on the next sync.
- `sihan/benchmark-recommendations` (2026-05-07; 1 commit past the squash+readme) — adds a `finish` tool, `finish_reason` capture, sandbox-path echoes, and chunked rubric judging. Experimental; unmerged anywhere.
- `mblau/self-summarization` (2026-06-12; 2 commits past its #81 base) — optional agent self-summarization / context compaction in the harness, tool-free summarize contract. Unmerged.
- `bchen/fireworks-provider-draft-v2` (2026-05-23) — Fireworks draft; superseded by the merged #83 adapter already at the pin.
- `jerry-cursor/baseten-adapter-thinking-fix-8c2d` (2026-05-20; 3 commits past its base) — Baseten streaming fixes for reasoning models: keep qwen3 thinking, replay via a `reasoning` key, retry when a stream yields only reasoning, recover Hermes-style tool calls client-side. Relevant if we ever run Baseten-hosted reasoning models through Harvey’s harness; unmerged.
- `taxonomy-alignment` (96 commits, tip 2026-05-05) — the pre-publication line: 2026-04-08 practice-area taxonomy, fictional-name replacement across all task documents, `detailed_instructions` removal, CMA managed-agents runners, rewritten office skills. **Not** pending future changes: its content shipped via the 2026-05-06 squash — the pin has zero `detailed_instructions` keys and the fictional names throughout.
- `entity-cleanup` / `entity-cleanup-v2` (87/118 commits, 2026-05-05/06) — the real-entity scrub batches (md-rebuilds + byte-fixes of ~170 documents) that fed the same squash. Historical.
- `specter/polin924harvey/optimize-spectre-image-builds-…` (2026-05-13) — parallelized sandbox image builds; infra only.

## 6. Schema drift

**None.** v1.0 `task.json` keys: `title`/`instructions`/`criteria` on all 1,760;
`work_type`/`tags`/`deliverables` on the same 1,262 (contracts tasks carry no
`deliverables` key on either line). The pin’s only extra keys are `id` and
`docs_dir`, both exclusively on the 250 firm-knowledge tasks. No key exists at
v1.0 that the pin lacks; `detailed_instructions` exists on neither.
`world/ingest/lab_ingest.py` and the extractor lane apply to v1.0 content
unchanged — which is moot, because every shared blob is already ingested.

## 7. Recommendation

1. **Keep `7be41d5` as the world’s single pinned source.** It is a strict
   superset (firm-knowledge exists only there), strictly newer (corrected
   rubrics, fixed diligence documents), and world-v19 plus the entire
   ingest/audit chain already stand on it. Re-pinning to v1.0 would *lose*
   content and *reintroduce* 12 known-bad criteria and 44 stale documents.
2. **Cite v1.0 as the public compatibility point.** When describing LAB
   coverage externally, “v1.0 (1,760 tasks, 111,826 criteria) ⊂ pinned
   `7be41d5` (2,010 tasks, 114,437 criteria)” is now a proven statement; keep
   the v1.0 worktree for provenance.
3. **Nothing to ingest.** The only v1.0-unique object is the zero-byte stray
   artifact — worth reporting upstream, never worth hosting. Watch
   `calvin/reasoning-first-lab-judge` (reasoning-first judging could change
   upstream score semantics if merged) and any future `v1.0.x`/`v1.1` tag; the
   6 rubric fixes in the pin should be assumed to appear in the next public tag.
4. On the next pin advance, rerun: this delta pipeline, then
   `tools/audit_harvey_inputs.py`, `world/ingest/lab_ingest.py --check --deep`,
   and `tools/check_lab_extractor_parity.py --check`.

## Reproduce

```bash
cd research/repos/harveyai@harvey-labs
git fetch origin && git ls-remote origin HEAD main refs/tags/v1.0
git worktree add --detach ../harveyai@harvey-labs-v1.0 v1.0
# tree-level delta (disjoint roots — do NOT trust ancestry):
git ls-tree -r main tasks/ ; git ls-tree -r 'v1.0^{commit}' tasks/   # → set-compare OIDs
python3 tools/audit_harvey_inputs.py \
  --source research/repos/harveyai@harvey-labs-v1.0 \
  --expected-commit 1da4750171bc5a534960b3d82d15ba7fd2cf653f \
  --known-defects reports/harvey-v1.0-known-defects.json \
  --report reports/harvey-v1.0-input-audit.json
```
