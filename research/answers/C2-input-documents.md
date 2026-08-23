# C2 — What are the input documents, and what must the agent extract from them?

**Status:** answered from the eval corpus on disk.

**Evidence:** `research/repos/harveyai@harvey-labs` @ `7be41d57` (2026-08-11,
"firm-knowledge: add response.md output instruction + deliverable hooks"). Inventory extracted by
`research/extract-lab-corpus.mjs` into `research/answers/data/lab-corpus.json`;
the byte-level source identity is frozen in
`world/ingest/lab-source-lock.json`.

> **Count correction.** The repo's README badge says 1,671 tasks. At HEAD there
> are **2,010** `task.json` files. My first extraction found only 1,143 because
> it assumed tasks live at `tasks/<area>/<slug>/` — 867 sit one or two levels
> deeper. Both my first number and the badge are wrong; 2,010 is what is on
> disk.

---

## The corpus, measured

| | LAB | our world (`world-v6.json`) |
|---|---|---|
| tasks | 2,010 | 270 |
| task-local input documents | **51,683** | 311 |
| shared firm-knowledge DMS | **9,288** | separately hosted as C&H |
| document format | real `.docx` / `.xlsx` / `.eml` / `.pptx` | text rows in SQLite |
| grading units | 114,437 rubric criteria (mean **56.9**/task) | ~7 assertions/task |
| deliverable format | 1,247 `.docx`, 39 `.xlsx`, 261 `.md` | a row insert, or a document row |

Document formats, by count: `.docx` 33,954 · `.xlsx` 10,575 · `.eml` 5,169 ·
`.pptx` 1,091 · `.txt` 889.

The 51,683 figure is the sum of task-local `documents/` trees. LAB also has a
single 9,288-file `firm-knowledge/dms` tree referenced by 250 tasks via
`docs_dir`; it must be counted once, not omitted and not multiplied by 250.
The complete physical input boundary is therefore **60,971 files / 3.207 GB**.
Our `world/corpus/ch` index is that shared tree (9,288 parsed, zero failures),
while `world/corpus/lab` holds the task-local content-addressed store.

**The `.eml` and `.xlsx` counts are the interesting ones.** 5,169 emails and
10,575 spreadsheets means a large fraction of the evidence is *correspondence
and tabular data*, not prose contracts — the agent must read a thread and a
schedule, not just a clause.

## The data room is a folder tree, not a list

The diligence packs ship genuine data-room hierarchies:

```
tasks/diligence/aerospace-vertical-integration/documents/
  5.0 Commercial Contracts and Claims/
    5.2 Rhône-Aigle Commercial Program Agreements/
      amendment-no-8-to-ra-s450-2011-cfa-block-b-shipset-pricing-and-tooling.docx
      ra-s450-td-2024-021-saint-nazaire-barrel-join-tooling-calibration-data.eml
  9.0 Tax/
    9.2 State Apportionment Sales and Use Tax/
      trentwood-sba-m9-renton-tooling-and-spares-invoice-register-2023-h1.xlsx
```

Five diligence rooms exceed 3,500 documents each — `rail-horizontal-merger`
(4,061), `pharma-pipeline-acquisition` (3,858), `oil-gas-horizontal-merger`
(3,781), `enterprise-software-diversification` (3,633), `cybersecurity-tuck-in`
(3,513).

**This is the finding that matters for us.** Our world already anchors tasks to
`harvey_lab/diligence/aerospace-vertical-integration` by name. The real thing is
a 4,000-document numbered data room; our version is a handful of text rows in a
`matter_documents` table. The anchor names a shape we did not actually
reproduce. Retrieval-at-scale — finding the one invoice register that matters
among 4,061 files — is the core difficulty of the real task and is entirely
absent from ours.

## What the agent must produce

LAB's own `work_type` taxonomy over the 1,262 tasks that declare one:

| work_type | tasks |
|---|---|
| analyze | 488 |
| draft | 444 |
| review | 306 |
| research | 24 |

The remaining 748 are the **contracting** set, which uses a second schema
(`title` / `instructions` / `criteria`, no `work_type`) and is organised as a
negotiation lifecycle rather than by verb.

## The contracting lifecycle — 498 tasks, six stages, 14 domains

Each contract domain (banking, corporate-ma, ip-licensing, pe-funds,
real-estate, energy, healthcare, media, data-privacy-security,
employment-compensation, financing, disputes, commercial-vendor-customer,
commercial-channel-partnerships) ships the same six stages, each with 5–6
scenario variants:

1. `first-draft`
2. `counterparty-paper-review`
3. `first-turn-redline`
4. `subsequent-turn-redline`
5. `playbook-escalation`
6. `term-negotiation`

Title vocabulary across the set: *redline* 138, *negotiat\** 94, *first turn*
81, *subsequent turn* 56.

`subsequent-turn-redline` states the shape precisely: *"Using the prior redline
as your base, produce a tracked-changes redline that resolves agreed items as
clean text, advances compromise language in brackets on partially agreed items"*
(`tasks/contracts/financing/credit-lending-subsequent-turn-redline/scenario-02/task.json`).

This is **stateful multi-turn work**: the task's input includes the artifact
produced by the previous turn, and "done" is defined relative to it. It is the
industrial-scale version of the versioning/diff guard that 53 skills in the
automation corpus also require (see `C3-definition-of-done.md`), and our world
has no task of this shape — every one of our 270 starts from a state where the
deliverable does not exist.

## How LAB decides "done"

Each task carries rubric criteria with an `id`, a `title`, the `deliverables`
they bind to, and a `match_criteria` string beginning *"PASS if …"*. Example
from `contracts/financing/credit-lending-subsequent-turn-redline/scenario-02`:

> `C-001` — "Applicable Margin resolved at SOFR + 2.50%" — *PASS if the redline
> sets the Applicable Margin at SOFR + 2.50% per annum…*

Scoring is **all-pass over the rubric**, adjudicated by an LLM judge
(`docs/eval-strategies.md`). At 56.9 criteria per task, a LAB score is a
fine-grained rubric aggregate; our reward is a small set of deterministic
assertions with anti-hack vetoes.

Neither is strictly better, and the difference is the honest core of any
comparison we publish:

- LAB grades **prose quality against a rubric**, needing a judge, and can
  therefore score drafting work we can only grade structurally.
- We grade **executed state against a deterministic oracle**, needing no judge,
  and can therefore prove a task rejects a wrong answer — which is what our
  discrimination sweep does and what an LLM-judged rubric cannot do by
  construction.
