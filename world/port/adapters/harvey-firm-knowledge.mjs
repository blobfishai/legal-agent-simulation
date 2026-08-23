/**
 * Harvey LAB — Calderwood & Harkness firm knowledge.
 *
 * tasks       250 retrieval/reasoning questions over the whole firm corpus
 * seeded data 9,288 files / ~133M chars, hosted out-of-band at world/corpus/ch
 * tools       the DMS surface: corpus_matters_list/files_list/search/read
 * verifier    DETERMINISTIC for 2,515 of 2,623 criteria — the rubric text names
 *             matter ids ("Identifies matter 1001-00004 ..."), so the key is a
 *             set of ids and needs no judge. The other 108 are prose and are
 *             reported ungraded.
 * workflow    none declared; the corpus is too large to walk exhaustively,
 *             which is the point of the environment
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { gitCommit, has } from "../lib.mjs";

export const meta = { id: "harvey-firm-knowledge", repo: "harveyai@harvey-labs", license: "MIT" };
const MATTER = /\b(\d{4}-\d{5})\b/g;

export function port(repoDir) {
  const src = join(repoDir, "tasks", "firm-knowledge", "tasks");
  const tasks = [];
  let ungraded = 0;
  for (const dir of readdirSync(src).sort()) {
    const p = join(src, dir, "task.json");
    if (!has(p)) continue;
    const t = JSON.parse(readFileSync(p, "utf8"));
    const criteria = (t.criteria ?? []).map((c) => {
      const ids = [...new Set([...`${c.match_criteria ?? ""} ${c.title ?? ""}`.matchAll(MATTER)]
        .map((m) => m[1]))];
      return { id: c.id, title: c.title, match_criteria: c.match_criteria,
               matter_ids: ids, judge_required: ids.length === 0 };
    });
    const keyed = criteria.filter((c) => !c.judge_required);
    ungraded += criteria.length - keyed.length;
    tasks.push({
      id: `fk_${t.id}`, prompt: t.instructions, title: t.title,
      deliverables: Object.keys(t.deliverables ?? {}),
      expected: [...new Set(keyed.flatMap((c) => c.matter_ids))].sort(),
      criteria,
      grading: keyed.length && keyed.length === criteria.length ? "deterministic"
        : keyed.length ? "mixed" : "judge_only",
      provenance: { path: `tasks/firm-knowledge/tasks/${dir}/task.json` },
    });
  }
  return {
    source: { repo: meta.repo, commit: gitCommit(repoDir),
              path: "tasks/firm-knowledge", license: meta.license, adaptations: [] },
    tasks,
    documents: { external_store: "world/corpus/ch",
                 source_lock: "world/ingest/lab-source-lock.json#shared_document_sets[ch]",
                 note: "9,288 files ingested by world/corpus/build-corpus-index.py; the world "
                     + "document holds only the catalogue" },
    tools: ["corpus_matters_list", "corpus_files_list", "corpus_search", "corpus_read"],
    grading: { kind: "mixed", key: "matter ids named in the source rubric", ungraded },
    gaps: [],
  };
}
