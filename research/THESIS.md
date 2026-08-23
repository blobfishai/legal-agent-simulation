# Thesis — what this world is for, and what the evidence says it should be

**Version:** v1, drawn from the 28-repo corpus on disk
(`research/repos-manifest.tsv`, 6.6 GB, 0 clone failures). Sections A, B and E
of `research/QUESTIONS.md` are still open; this thesis covers what C and D
support and is explicit about what it is not yet entitled to claim.

---

## 1. The finding that reframes the project

There are **two incompatible architectures** for evaluating legal agents, and we
built one of them without having read the other.

| | Harvey LAB | legal-agent-simulation |
|---|---|---|
| agent surface | 6 filesystem tools (`bash`, `read`, `write`, `edit`, `glob`, `grep`) in a Docker sandbox | 91 domain tools + 88 vendor-API-mirrored tools over SQLite |
| the "legal system" is | a read-only folder of `.docx`/`.xlsx`/`.eml` | a database of matters, dockets, invoices, documents |
| the deliverable | a `.docx` written to `output/` | a row committed to a table |
| grading | 114,437 rubric criteria, mean 56.9/task, adjudicated by an LLM judge, all-pass | ~7 deterministic assertions/task, graded reward, anti-hack vetoes |
| scale | 2,010 tasks · 51,683 documents | 270 tasks · 311 documents |

*(LAB figures from `research/answers/data/lab-corpus.json`, extracted at commit
`7be41d57`. Note the repo's own README badge says 1,671 tasks; there are 2,010
`task.json` files at HEAD, and my first extraction said 1,143 before I fixed a
fixed-depth scan. All three numbers were wrong at some point today; 2,010 is
what is on disk.)*

Neither architecture dominates. They measure genuinely different things:

- **LAB can grade prose.** With 57 rubric criteria per task and a judge, it
  scores whether a drafted consent decree identifies a supply gap. We cannot;
  our 110 prose-deliverable tasks grade structure and evidence-chain, never
  content (`docs/DISCRIMINATION.md`).
- **We can prove a task discriminates.** Our discrimination sweep runs four
  adversarial episodes per task and asserts the verifier rejects each. An
  LLM-judged rubric cannot do this by construction — you cannot prove a judge
  rejects a wrong answer without asking the judge, which is the thing under
  test.
- **We can grade side effects.** LAB's agent writes files; it has no notion of
  "the agent also mutated a record it should not have". Our anti-hack vetoes —
  `no_offtask_table_changes`, `no_undeclared_rows_created`,
  `audit_logs_append_only` — grade the blast radius of an action. That is the
  half of agent safety a filesystem benchmark structurally cannot see.

**The honest positioning is therefore not "deeper than LAB".** It is: *LAB
measures work product; we measure execution against a system of record.* Any
claim we publish that we are "the most in-depth law-firm world" is false on the
axis that LAB owns — 51,683 real documents against our 311 — and defensible only
on the axis we own.

## 2. What the domain says the work actually is

From `CSlawyer1985/claude-for-legal-ZH` (175 skills, 14 practice areas, 10
standing watcher agents) and LAB's own taxonomy:

- LAB's verbs, over the 1,262 tasks that declare one: **analyze 488, draft 444,
  review 306, research 24**. Drafting and analysis dominate; pure research is
  2%.
- LAB's contracting set is **498 tasks in a six-stage lifecycle** —
  first-draft → counterparty-paper-review → first-turn-redline →
  subsequent-turn-redline → playbook-escalation → term-negotiation — across 14
  contract domains. This is *stateful multi-turn* work: the input includes the
  previous turn's artifact.
- The automation corpus independently requires the same statefulness: **53 of
  175 skills** version their output and present a diff against the prior run.

Our world has **no task of this shape at all**. Every one of our 270 begins
from a state where the deliverable does not exist.

## 3. The domain's own guardrails validate our grading model

The practitioner corpus writes down guardrails that map almost one-to-one onto
assertions we already ship — which is the strongest external validation the
verifier design has received:

| Practitioner guard | Skills | Our equivalent |
|---|---|---|
| source attribution | 28 | `required_documents_read`, fabrication traps |
| confidentiality gate | 17 | *(none — procedural abstention is ungraded)* |
| gap disclosure | 55 | **none** |
| versioning + diff | 53 | **none** |
| human confirmation | 51 | structural gap (multi-party) |

`litigation-legal/chronology` requires every entry to carry its source and
untraceable entries to carry a non-removable tag (web-retrieved / model
knowledge / user-provided). `corporate-legal/diligence-issue-extraction:103`
states the fabrication policy outright: when a cited statute cannot be
retrieved, do not describe it from memory — tag it *[not retrieved — needs
verification]* and retrieve, ask, or refer out, because *"a confident but wrong
description of a real statute is worse than 'unclear'."*

**Gap disclosure is the single most common guard in the corpus and we grade
nothing like it.** Our tasks grade what the agent found; the domain grades
whether the agent declared what it could not reach.

## 4. Where the evidence says we are actually thin

1. **Retrieval at scale.** LAB's diligence rooms run to **4,061 documents** in a
   numbered data-room tree. We anchor tasks to
   `harvey_lab/diligence/aerospace-vertical-integration` by name while hosting a
   handful of text rows. The anchor names a shape we did not reproduce, and
   finding the one invoice register that matters among 4,061 files *is* the
   task.
2. **Workflow length.** 41% of practitioner skills run ≥8 steps (deepest 40).
   We have **3 of 270** at ≥8, mean 3.5.
3. **Party posture.** 14 skills make the answer depend on which side the firm
   acts for — the same event rates differently for the claiming and defending
   party. Same documents, different correct answer. We have nothing of this
   shape, and it is the cheapest real difficulty available: it multiplies tasks
   without adding a document and cannot be pattern-matched.
4. **One product per category.** We mirror Clio, CourtListener, Relativity,
   iManage, Google Workspace and LEDES — one each. No intra-category
   disagreement is expressible, and whole categories (CLM, contract-AI, IP
   management, entity management, firm financials) are absent.

## 5. A claim I had to withdraw

I listed the competitor products per category (Litify, NetDocuments, Everlaw,
Ironclad, Kira…) and then ran a corpus-wide census to confirm them. It refuted
the list: `disco` collapsed from 2,184 file hits to 8 once word-bounded (the
rest was "discovery"), `ironclad`'s 76 hits are the case name *Kenai Ironclad v.
CP Marine Services* in PACER fixtures, and only **one** of `clio`'s hits is the
product.

The reason is structural: this corpus is open-source legal tooling, and
open-source legal tooling is built on **free public court data**. The commercial
SaaS a firm runs on is absent from it by construction. So the competitor list
stands as *category knowledge, asserted and uncorroborated*, and mocking those
surfaces requires each vendor's published API documentation — a separate
evidence source the repo corpus cannot supply.

## 6. What this thesis licenses us to build next

In priority order, each traceable to a finding above:

1. **Gap-disclosure family** (§3) — a referenced document is deliberately
   unreachable; the deliverable must name the gap. Hostable today with the
   outcome grammar we have.
2. **Posture-flip family** (§4.3) — identical documents, the posture is the
   operative variable, the answer is determinate given it.
3. **Prior-state / second-turn family** (§2) — the artifact exists; done means
   an incremented version plus a stated diff.
4. **Retrieval-at-scale** (§4.1) — raise a diligence room from a handful of rows
   to hundreds of documents with one operative fact, so finding it is the work.
5. **A second product inside one category** (§4.4) — the minimum needed to make
   "these two systems disagree; which governs?" expressible.

Items 1–3 need no new tool surface. Item 4 needs bulk document generation. Item
5 needs vendor API documentation, not the repo corpus.

## 7. What this thesis does NOT yet claim

Sections A (domain value, billable weight, asymmetry of error), B (stakeholders
and authority) and E (chaos scenarios, forbidden answers) of
`research/QUESTIONS.md` are unanswered. Until they are, this thesis says nothing
evidence-backed about *who* in the firm does which task, what a handoff carries,
or which questions require reconciling systems to answer at all — and the task
families in §6 are shaped by document and workflow evidence only, not by
stakeholder evidence.
