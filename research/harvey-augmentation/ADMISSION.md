# Mutation asset admission status

This repository keeps generation research separate from benchmark admission so
that a reproducible document variant is never double-counted as an independently
graded task.

| Lane | Assets | Status | Counted in v21 task total? |
| --- | ---: | --- | --- |
| Strict Harvey derivatives | 4 recipe-bound task/document variants | Validated research candidates | No |
| Broad Harvey entity seeds | 35 byte-reproducible variants across 16 source tasks / 14 practice areas / 182 generated document instances | Validated mutation fixtures | No |
| v21 structure-matched packs | 117 packs / 351 DOCX-XLSX-PDF files | Release-admitted fixtures | Yes |
| v21 admitted mutations | 94 mutated packs, including 51 authority-mapped retail packs | Referenced by canonical tasks and native Harbor exports | Yes |

The four strict derivatives and thirty-five broad seeds are deliberately retained
as generator regression assets. They do not have stable release task IDs,
release-specific acceptance contracts, or independent Harbor packages, and are
therefore not presented as additional production tasks. This is an explicit
lifecycle boundary, not an unimplemented task-count claim.

A future release may admit one of these candidates only after it receives a
stable task ID, compiled deterministic acceptance contract, positive-oracle and
corruption discrimination evidence, an immutable input manifest, and a native
Harbor package. Until then, the v21 scale and mutation claims use only the 117
release-admitted packs and the tasks that actually reference them.
