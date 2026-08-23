#!/usr/bin/env node
/**
 * packs-lab — Harvey LAB tasks, hosted in this world.
 *
 * Requirement: "all the automation, tools, and tasks from the github should be
 * able to run in the world." LAB tasks cannot be copied across as-is — LAB
 * grades a .docx deliverable against ~57 prose rubric criteria with an LLM
 * judge, and this world grades committed state with a deterministic verifier
 * (research/THESIS.md §1). So the bridge is:
 *
 *   1. LAB's REAL DOCUMENTS come across verbatim. `research/lab_extract.py`
 *      reads the actual .docx/.xlsx/.eml bytes — no paraphrase, no synthesis.
 *      A lawyer reading these rows is reading Harvey's corpus.
 *   2. The QUESTIONS are re-cut to the determinate decisions those documents
 *      already settle. The source task asks for an escalation memorandum; the
 *      memo's own rubric asserts, among its 57 criteria, that the CAP
 *      escalation chain runs CPO -> GC -> Board Compensation Committee at
 *      stated thresholds. Those thresholds have exactly one right answer given
 *      the facts, so they are gradeable without a judge.
 *
 * What is honestly lost: prose quality. LAB scores whether the memo is
 * well-argued; we score whether the agent reached the right conclusion from
 * the right documents. What is honestly gained: the answer key is checkable,
 * and the discrimination sweep can prove a wrong answer is rejected.
 *
 * Source: research/repos/harveyai@harvey-labs at the commit pinned in
 *   research/repos-commits.json, task
 *   tasks/contracts/employment-compensation/
 *     employment-agreement-playbook-escalation/scenario-01
 *   (10 documents, 57 criteria, MIT licensed)
 *
 * Run: node world/expansion/packs-lab/build-lab-pack.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..");
const SOURCE_COMMIT = JSON.parse(
  readFileSync(join(ROOT, "research", "repos-commits.json"), "utf8"),
)["harveyai@harvey-labs"];
const LAB_TASK = join(ROOT, "research/repos/harveyai@harvey-labs/tasks/contracts",
  "employment-compensation/employment-agreement-playbook-escalation/scenario-01");

if (!existsSync(LAB_TASK)) {
  console.error("LAB corpus missing — run bash research/clone-repos.sh");
  process.exit(1);
}

// ---- 1. bring the real documents across ---------------------------------
const raw = execFileSync("python3",
  [join(ROOT, "research/lab_extract.py"), LAB_TASK, "--json"],
  { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
const extracted = JSON.parse(raw);
const parsed = extracted.filter((r) => r.ok && r.text.trim());
if (parsed.length < 8) {
  console.error(`only ${parsed.length}/${extracted.length} documents parsed — refusing to ship a partial corpus`);
  process.exit(1);
}

const TITLES = {
  "verdana-compensation-authority-policy-v3-2.docx": "Verdana — Compensation Authority Policy v3.2",
  "chen-velasco-employment-agreement-counterproposal.docx": "Chen-Velasco — Employment agreement counterproposal",
  "chen-velasco-employment-agreement-redline.docx": "Chen-Velasco — Employment agreement redline",
  "ashworth-kane-candidate-assessment.docx": "Ashworth Kane — Confidential candidate assessment",
  "cap-deviation-analysis-summary.xlsx": "CAP deviation analysis summary",
  "whitfield-greer-peer-benchmarking-report.xlsx": "Whitfield Greer — Peer benchmarking report",
  "ikeda-escalation-request-email.eml": "Ikeda — Escalation request (email)",
  "otieno-counterproposal-transmittal.eml": "Otieno — Counterproposal transmittal (email)",
  "ramanathan-response-to-ikeda.eml": "Ramanathan — Response to Ikeda (email)",
  "verdana-svp-employment-agreement-template.docx": "Verdana — SVP employment agreement template",
};
const DOC_TYPES = {
  ".docx": "agreement_document", ".xlsx": "analysis_workbook", ".eml": "correspondence",
};

const BODY_CAP = 24000; // keep rows readable; the operative provisions sit well inside this
const documents = parsed.map((r) => ({
  title: TITLES[r.file] ?? r.file,
  doc_type: DOC_TYPES[r.ext] ?? "input_materials",
  body: `[Source: Harvey LAB, ${r.file} — extracted verbatim]\n\n` + r.text.slice(0, BODY_CAP),
}));

const POLICY = "Verdana — Compensation Authority Policy v3.2";
const COUNTER = "Chen-Velasco — Employment agreement counterproposal";
const ASSESS = "Ashworth Kane — Confidential candidate assessment";
const mid = (n) => `legal_matters_${String(n).padStart(3, "0")}`;

// ---- 2. re-cut the determinate decisions --------------------------------
const tasks = [
  {
    slug: "cap-approval-authority",
    difficulty: "high",
    prompt:
      "Compensation approval review for the Chen-Velasco SVP offer. Read the Verdana " +
      "Compensation Authority Policy and the candidate's counterproposal in the matter folder " +
      "in full. Apply the Policy's tiered approval framework to the proposed terms and record " +
      "which approval authority must authorize this arrangement by calling " +
      `legal_matters_review_create against ${mid(1)} with reviewer_role exactly ` +
      '"compensation-counsel" and outcome set to exactly one of "cpo", "gc_co_approval" or ' +
      '"board_compensation_committee". Where more than one tier is triggered, the Policy states ' +
      "which one governs.",
    reads: [POLICY, COUNTER],
    creates: [{
      tool: "legal_matters_review_create",
      args: {
        legal_matters_id: mid(1),
        reviewer_role: "compensation-counsel",
        outcome: "board_compensation_committee",
        rationale:
          "The counterproposal includes a Guaranteed Bonus Floor, which the Policy prohibits " +
          "categorically and reserves to the Committee regardless of amount, and a CIC Severance " +
          "Multiplier of 2.0x against an SVP CAP Limit of 1.0x — 100% above the limit, far beyond " +
          "the CPO's 25% Tier 1 authority. Where multiple tiers are triggered the highest governs.",
      },
      pinned: { outcome: "board_compensation_committee", reviewer_role: "compensation-counsel" },
    }],
    // The CPO tier is the trap: each individual element looks negotiable, and the
    // deviation analysis workbook invites a Tier 1 reading.
    forbidden: [{ table: "legal_matters_reviews", field: "outcome", value: "cpo" }],
  },
  {
    slug: "cap-timing-authorization-path",
    difficulty: "high",
    prompt:
      "Sequencing review for the Chen-Velasco SVP offer. Read the Verdana Compensation Authority " +
      "Policy and the Ashworth Kane candidate assessment in the matter folder in full. Compare the " +
      "candidate's stated deadline for a fully authorized offer against the next regularly " +
      "scheduled Board Compensation Committee meeting, then record the authorization route the " +
      `Policy provides by calling legal_matters_remediation_create against ${mid(2)} with ` +
      'owner_role exactly "committee-chair" if the regular meeting cannot deliver a fully ' +
      'authorized offer in time, or exactly "board-secretary" if it can, and status exactly "open".',
    reads: [POLICY, ASSESS],
    creates: [{
      tool: "legal_matters_remediation_create",
      args: {
        legal_matters_id: mid(2),
        owner_role: "committee-chair",
        action_required:
          "The candidate's deadline for a fully authorized offer is 13 June 2025; the next " +
          "regularly scheduled Committee meeting is 19 June 2025, six days later, and the " +
          "competing retention offer expires 16 June 2025. The Policy permits the Chair to " +
          "authorize interim telephonic or written approval where the next scheduled meeting " +
          "falls after a documented offer deadline, subject to communication to the full " +
          "Committee within two business days and ratification at the next meeting.",
        due_at: "2025-06-13T17:00:00Z",
        status: "open",
      },
      pinned: { owner_role: "committee-chair", status: "open" },
    }],
    forbidden: [{ table: "legal_matters_remediations", field: "owner_role", value: "board-secretary" }],
  },
  {
    slug: "cap-guaranteed-bonus-floor-classification",
    difficulty: "medium",
    prompt:
      "Policy classification for the Chen-Velasco counterproposal. Read the Verdana Compensation " +
      "Authority Policy and the counterproposal in the matter folder in full and classify the " +
      "requested Guaranteed Bonus Floor by calling legal_matters_evidence_create against " +
      `${mid(3)} with evidence_type set to exactly "categorical_prohibition" if the Policy bars ` +
      'the term outright, or exactly "quantitative_deviation" if it merely exceeds a numeric CAP ' +
      'Limit, owner_role exactly "compensation-counsel" and status exactly "confirmed". The ' +
      "distinction determines whether any officer can approve it.",
    reads: [POLICY, COUNTER],
    creates: [{
      tool: "legal_matters_evidence_create",
      args: {
        legal_matters_id: mid(3),
        evidence_type: "categorical_prohibition",
        source_uri: "matter://verdana/cap/guaranteed-bonus-floor",
        content_digest: "cap-v3-2-guaranteed-bonus-floor-prohibited",
        owner_role: "compensation-counsel",
        status: "confirmed",
      },
      pinned: { evidence_type: "categorical_prohibition", owner_role: "compensation-counsel" },
    }],
    forbidden: [{ table: "legal_matters_evidence_records", field: "evidence_type", value: "quantitative_deviation" }],
  },
  {
    slug: "cap-cic-multiplier-deviation-magnitude",
    difficulty: "high",
    prompt:
      "Quantify the deviation for the Chen-Velasco counterproposal. Read the Verdana Compensation " +
      "Authority Policy and the counterproposal in the matter folder in full. Compute how far the " +
      "requested Change-in-Control Severance Multiplier sits above the applicable SVP CAP Limit, " +
      "expressed as a percentage of that CAP Limit as the Policy directs, and record it by calling " +
      `legal_matters_amount_history_create against ${mid(4)} with fee_budget set to that ` +
      'percentage as a number and changed_by_role exactly "compensation-counsel". The Policy ' +
      "states the percentage is calculated on the CAP Limit, not on the proposed term.",
    reads: [POLICY, COUNTER],
    creates: [{
      tool: "legal_matters_amount_history_create",
      args: {
        legal_matters_id: mid(4),
        fee_budget: 100,
        changed_by_role: "compensation-counsel",
        change_reason:
          "SVP CAP Limit for the CIC Severance Multiplier is 1.0x base plus target bonus; the " +
          "counterproposal requests 2.0x. The excess is 1.0x on a 1.0x limit = 100% above the " +
          "CAP Limit, which exceeds the CPO's 25% Tier 1 authority.",
      },
      pinned: { fee_budget: 100, changed_by_role: "compensation-counsel" },
    }],
    // 50 is the answer you get by dividing the excess by the PROPOSED term (1.0/2.0)
    // instead of by the CAP Limit — the error the Policy explicitly warns against.
    forbidden: [{ table: "legal_matters_amount_history", field: "fee_budget", value: 50 }],
  },
];

const pack = {
  family: "lab-employment-compensation-escalation",
  anchor: "harvey_lab",
  provenance: {
    repo: "harveyai/harvey-labs",
    commit: SOURCE_COMMIT,
    task: "tasks/contracts/employment-compensation/employment-agreement-playbook-escalation/scenario-01",
    license: "MIT",
    documents_verbatim: true,
    source_criteria: 57,
    note: "Documents extracted verbatim by research/lab_extract.py. Questions re-cut to the " +
      "determinate decisions the source rubric already asserts, so they grade without a judge.",
  },
  documents,
  tasks,
};

mkdirSync(HERE, { recursive: true });
writeFileSync(join(HERE, "lab-employment-compensation-escalation.json"), JSON.stringify(pack, null, 1));
console.log(`packs-lab: ${tasks.length} tasks · ${documents.length} documents extracted verbatim from LAB`);
for (const d of documents) console.log(`   ${String(d.body.length).padStart(6)} chars  ${d.title}`);
