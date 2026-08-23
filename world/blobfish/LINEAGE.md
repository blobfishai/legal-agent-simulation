# World lineage — how the canonical world was built

Seven snapshots are kept: `world.json` (the original 156-task world as
generated), `world-v15.json` (the final synthesized-surface world),
`world-v16.json` (canonical product-only world), and `world-v17.json` (the
deterministic Harvey LAB superset), `world-v18.json` (the three new
product-state workflows), `world-v19.json` (checkpointed capstones and
native multi-turn evaluation), and `world-v20.json` (complete LAB adapter
coverage plus RetailGuard price-accuracy workflows). The intermediates were 11 files of
~7 MB each, ~80 MB of near-identical JSON, and every one is reproducible from
the step that made it — each pack is a *generator*, not static data.

| step | from → to | tasks | command |
|---|---|---|---|
| eval packs | `world.json` → `world-expanded.json` | 156 → 231 | `node world/expansion/assemble.mjs --in world/blobfish/world.json --out world/blobfish/world-expanded.json --packs-dir world/expansion/packs` |
| ERP purge | → `world-lawnative.json` | 231 → 230 | `node world/expansion/purge-domain.mjs` |
| v3 workflows | → `world-v3.json` | 230 → 245 | `node world/expansion/build-v3-tasks.mjs` |
| growth | → `world-v4.json` | 245 → 255 | `node sim/grow-tasks.mjs` |
| gap packs | → `world-v5.json` | 255 → 270 | `assemble.mjs --packs-dir world/expansion/packs-v3` |
| retire recipes | → `world-v5-pruned.json` | 270 → 232 | `node world/expansion/retire-recipe-tasks.mjs` |
| packs-v4 | → `world-v6.json` | 232 → 270 | `assemble.mjs --packs-dir world/expansion/packs-v4` |
| LAB pack | → `world-v7.json` | 270 → 274 | `node world/expansion/packs-lab/build-lab-pack.mjs` then `assemble.mjs` |
| gap disclosure | → `world-v8.json` | 274 → 277 | `packs-gap/build-gap-pack.mjs` then `assemble.mjs` |
| ethical wall | → `world-v9.json` | 277 → 280 | `packs-wall/build-wall-pack.mjs` then `assemble.mjs` |
| async queue | → `world-v10/11` | 280 → 284 | `packs-posture/build-posture-pack.mjs`, `add-analysis-queue.mjs` |
| async pack | → `world-v12.json` | 284 → 286 | `packs-async/build-async-pack.mjs` then `assemble.mjs` |
| growth pack | → `world-v13.json` | 286 → 288 | `packs-grow/build-grow-pack.mjs` then `assemble.mjs` |
| corpus tools | → `world-v14.json` | 288 | `node world/expansion/add-corpus-tools.mjs` |
| grounded drafting | → `world-v15.json` | 288 → 291 | `assemble.mjs --in world/blobfish/world-v14.json --out world/blobfish/world-v15.json --packs-dir world/expansion/packs-grounded` |
| v3 verifier revision 2 | `world-v15.json` → in place | 291 → 291 | `node world/expansion/build-v3-tasks.mjs --in world/blobfish/world-v15.json --out world/blobfish/world-v15.json --refresh-only` (same-row pin binding; tasks and seeds preserved) |
| product-surface migration | `world-v15.json` → `world-v16.json` | 291 → 291 | `python3 world/migrate/gen1_to_v16.py --write` (1,279 legacy rows reconciled; 276 verifiers grammar-regenerated; 99 synthesized tool specs removed) |
| LAB deterministic import | `world-v16.json` → `world-v17.json` | 291 → 2,274 | `python3 world/v17/build.py` after `python3 world/port/lab_determinize.py --check` (2,009/2,010 LAB tasks hosted; 65,614/111,814 practice criteria compiled; one source quarantined with reason) |
| product workflow admission | `world-v17.json` → `world-v18.json` | 2,274 → 2,289 | `python3 world/v18/build.py` (five CourtFile, five DeadlineRules, and five SealPoint workflows; all 15 oracle/discrimination gated) |
| long-horizon and interruption admission | `world-v18.json` → `world-v19.json` | 2,289 → 2,324 | `python3 world/v19/build.py` (five 50-call checkpointed capstones + 30 native multi-turn tasks; all 35 oracle/adversarial/pre-correction gated) |
| complete LAB + retail compliance | `world-v19.json` → `world-v20.json` | 2,324 → 2,331 | `python3 tools/build_retail_price_accuracy_pack.py && python3 world/v20/build.py` (one explicit output-contract adapter for the only upstream LAB omission + six RetailGuard workflows over 51 jurisdiction triage rows) |

After any rebuild: re-derive seeds and re-prove.

```bash
python3 world/migrate/gen1_to_v16.py --check
python3 tools/check_product_surface.py
python3 world/local/server.py --world world/blobfish/world-v16.json \
    --v2-contracts mcp/v3/contracts --port 8791          # explicit; same as the default
python3 world/local/oracle.py       --base http://localhost:8791 --world world/blobfish/world-v16.json
python3 world/local/discriminate.py --base http://localhost:8791 --world world/blobfish/world-v16.json \
    --out data/discrimination-v16.json --report-only
node world/expansion/discrimination-report.mjs \
    --sweep data/discrimination-v16.json --world world/blobfish/world-v16.json \
    --docs-out docs/DISCRIMINATION-v16.md \
    --data-out data/discrimination-v16-classified.json
node sim/compare-v16-boundary.mjs

# v17 compiler/import proof
python3 world/port/lab_determinize.py --check
python3 world/v17/build.py
python3 tools/check_v17_import.py
python3 tools/report_lab_determinization.py --check
python3 tools/sample_lab_determinization.py --check
python3 world/local/oracle.py --base http://localhost:8791 \
    --world world/blobfish/world-v17.json --out data/oracle-v17.json
python3 world/local/discriminate.py --base http://localhost:8791 \
    --world world/blobfish/world-v17.json --out data/discrimination-v17.json --report-only
node world/expansion/discrimination-report.mjs \
    --sweep data/discrimination-v17.json --world world/blobfish/world-v17.json \
    --docs-out docs/DISCRIMINATION-v17.md \
    --data-out data/discrimination-v17-classified.json

# v18 product workflow proof
python3 world/v18/build.py
python3 tools/check_v18_workflows.py

# v19 multi-step proof
python3 world/v19/build.py
python3 world/local/precorrection.py --world world/blobfish/world-v19.json
python3 tools/check_v19_multistep.py

# v20 complete-LAB and retail-compliance proof
python3 tools/build_retail_price_accuracy_pack.py
python3 tools/build_retail_price_accuracy_pack.py --check
python3 world/v20/build.py
python3 tools/check_v20_retail.py
python3 world/local/server.py --world world/blobfish/world-v20.json \
    --v2-contracts mcp/v4/contracts --port 8976
python3 world/local/oracle.py --base http://localhost:8976 \
    --world world/blobfish/world-v20.json \
    --tasks task_v20_retail_incident_audit,task_v20_retail_refund_exposure,task_v20_retail_51_jurisdiction_triage,task_v20_retail_receipt_redline,task_v20_retail_control_remediation,task_v20_retail_national_closeout
```
