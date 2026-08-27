# Vendored: fleet-document-seeds (composer + legal seed subset)

Source: `packages/document-seeds/fleet_document_seeds` in
<https://github.com/blobfishai/blobfishai> (composer modules `skeleton.py`,
`entities.py`, `catalog.py`, `compose.py`, `recipe.py`; stdlib only). The
`catalog/` directory is a filtered subset of that package's bundled catalog
(legal practice areas, DOCX exemplars, 199 skeletons) written by
`fleet-document-seeds export`; `catalog/PROVENANCE.json` records the upstream
Harvey LAB commit and the subset filters, and `catalog/LICENSE-harvey-labs.txt`
is the MIT license the skeletons derive from.

The generator uses this to give `.md` and `.txt` evidence records the
structure of real legal documents (title block, recitals, articles, tables,
signature page) around the record-control block the verifier grades. Nothing
here runs at benchmark time: only `builder.py` / `generation.py` import it, and
generation stays deterministic with no network calls.

Refresh:

```bash
# from a blobfishai checkout
for m in __init__ skeleton entities catalog compose recipe; do
  cp packages/document-seeds/fleet_document_seeds/$m.py \
     ../legal-agent-simulation/benchmark/counselbench100/document_seeds/$m.py
done
PYTHONPATH=packages/document-seeds python3 -m fleet_document_seeds.cli export \
  --out ../legal-agent-simulation/benchmark/counselbench100/document_seeds/catalog \
  --kinds agreement,memo,letter,certificate,report,schedule,policy,minutes,resolution,checklist,notes,plan \
  --areas contracts,corporate-ma,corporate-governance,litigation-dispute-resolution,firm-knowledge,banking-finance,employment-labor,intellectual-property,real-estate,data-privacy-cybersecurity,white-collar-defense-investigations,antitrust-competition \
  --formats docx --max-total 220
```
