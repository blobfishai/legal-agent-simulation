#!/usr/bin/env bash
# Clone the domain corpus that grounds every downstream artifact.
#
# Rule 1 of the creation workflow: every eval, workflow and MCP tool we host
# must be mocked and runnable in the world. Rule 2: new tasks/tools/mock data
# must be judged against evidence from a repo that is actually on disk. Both
# rules require the corpus to be LOCAL, not a list of URLs — the previous
# registry (data/research/domain-registry.json, 101 items) was web-sourced and
# nothing was ever downloaded, so no claim in it could be checked against code.
#
# Shallow, detached checkouts of the exact revisions in repos-commits.json; we
# want source and fixtures, not history, and "latest main" is not provenance.
# Failures are RECORDED, never silently skipped — an unavailable repo is a fact
# about the domain, not a gap to paper over.
#
# Usage: bash research/clone-repos.sh
set -u
DEST="$(cd "$(dirname "$0")" && pwd)/repos"
LOCKS="$(cd "$(dirname "$0")" && pwd)/repos-commits.json"
mkdir -p "$DEST"
MANIFEST="$DEST/../repos-manifest.tsv"
: > "$MANIFEST"
printf 'status\tcategory\trepo\tsize\tnote\n' >> "$MANIFEST"

clone() {  # clone <category> <owner/name>
  local cat="$1" repo="$2"
  local name="${repo//\//@}"
  local dir="$DEST/$name"
  local locked
  locked="$(python3 - "$LOCKS" "$name" <<'PY'
import json, sys
print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))
PY
)"
  if [ -z "$locked" ]; then
    printf 'FAIL\t%s\t%s\t-\tmissing revision in repos-commits.json\n' "$cat" "$repo" >> "$MANIFEST"
    echo "FAIL  $repo — no pinned revision"; return
  fi
  if [ -d "$dir/.git" ]; then
    local actual; actual="$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)"
    if [[ "$actual" == "$locked"* ]]; then
      if ! git -C "$dir" update-ref refs/remotes/origin/pinned "$actual"; then
        printf 'FAIL\t%s\t%s\t-\tcannot persist origin/pinned at %s\n' "$cat" "$repo" "$actual" >> "$MANIFEST"
        echo "FAIL  $repo — cannot persist origin/pinned"; return
      fi
      printf 'OK\t%s\t%s\t%s\tpresent@%s\n' "$cat" "$repo" "$(du -sh "$dir" | cut -f1 | tr -d ' ')" "$locked" >> "$MANIFEST"
      echo "SKIP  $repo@$locked"; return
    fi
  fi
  rm -rf "$dir"
  mkdir -p "$dir"
  git -C "$dir" init --quiet
  git -C "$dir" remote add origin "https://github.com/$repo.git"
  # Git upload-pack generally does not accept abbreviated, unreachable SHAs.
  # Resolve our human-auditable 12-char lock through GitHub's commit endpoint,
  # then fetch that exact full object even after the default branch moves.
  local resolved
  resolved="$(curl -fsSL "https://api.github.com/repos/$repo/commits/$locked" 2>/tmp/clone_err \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("sha", ""))' 2>>/tmp/clone_err || true)"
  if [ -z "$resolved" ] || [[ "$resolved" != "$locked"* ]]; then
    printf 'FAIL\t%s\t%s\t-\tcannot resolve pinned revision %s\n' "$cat" "$repo" "$locked" >> "$MANIFEST"
    echo "FAIL  $repo — cannot resolve $locked"; return
  fi
  # Persist the resolved object under a stable ref; FETCH_HEAD alone is not a
  # reproducible provenance boundary after a fresh hydration.
  if timeout 900 git -C "$dir" fetch --depth 1 --quiet origin \
      "$resolved:refs/remotes/origin/pinned" 2>/tmp/clone_err \
      && git -C "$dir" checkout --detach --quiet refs/remotes/origin/pinned; then
    local actual; actual="$(git -C "$dir" rev-parse HEAD)"
    if [[ "$actual" != "$locked"* ]]; then
      printf 'FAIL\t%s\t%s\t-\trevision mismatch: got %s expected %s\n' "$cat" "$repo" "$actual" "$locked" >> "$MANIFEST"
      echo "FAIL  $repo — revision mismatch"; return
    fi
    printf 'OK\t%s\t%s\t%s\t%s\n' "$cat" "$repo" "$(du -sh "$dir" | cut -f1 | tr -d ' ')" "$actual" >> "$MANIFEST"
    echo "OK    $repo@$actual"
  else
    local err; err=$(tr '\n' ' ' < /tmp/clone_err | head -c 140)
    printf 'FAIL\t%s\t%s\t-\t%s\n' "$cat" "$repo" "$err" >> "$MANIFEST"
    echo "FAIL  $repo — $err"
  fi
}

# ---- 0. evaluation framework source ---------------------------------------
clone framework harbor-framework/harbor

# ---- 1. domain evals / benchmarks (what tasks are likely) -----------------
clone eval harveyai/harvey-labs
clone eval HazyResearch/legalbench
clone eval TheAtticusProject/cuad
clone eval TheAtticusProject/maud
clone eval TheAtticusProject/acord
clone eval RegNLP/ObliQADataset
clone eval minnesotanlp/LawFlow
clone eval olivialiu121/ContractEval
clone eval Exploration-Lab/CJPE
clone eval thunlp/jec-qa
clone eval lbox-kr/lbox-open
clone eval SgfdDttt/sara-ie
clone eval hoorangyee/LRAGE

# ---- 2. domain automation / agent skills (how the work is actually done) --
clone automation CSlawyer1985/claude-for-legal-ZH
clone automation lawve-ai/awesome-legal-skills
clone automation armanaydemir/openprobono
clone automation SuffolkLITLab/ALKiln
clone automation jhpyle/docassemble

# ---- 3. domain MCP / tool surfaces (what the agent calls) -----------------
clone mcp agentic-ops/legal-mcp
clone mcp grafana/mcp-grafana
clone mcp modelcontextprotocol/servers

# ---- 4. real services we mirror (ground truth for API shape) -------------
clone service freelawproject/courtlistener
clone service freelawproject/juriscraper
clone service freelawproject/eyecite
clone service LexPredict/lexpredict-lexnlp
clone service eugene-yang/tarexp
clone service shmsoft/FreeEed

# ---- 5. domain surveys (find what we have not thought of) ----------------
clone survey maastrichtlawtech/awesome-legal-nlp

echo
echo "=== manifest ==="
column -t -s $'\t' "$MANIFEST" 2>/dev/null || cat "$MANIFEST"
echo
echo "OK:   $(grep -c '^OK' "$MANIFEST")"
echo "FAIL: $(grep -c '^FAIL' "$MANIFEST")"
