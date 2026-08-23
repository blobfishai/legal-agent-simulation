# Harvey LAB recovery fixture

This directory vendors the exact 15 input files needed by the one recovered
Harvey LAB task `labp_b50165c2a9cd39db`. The files are copied without mutation
from:

`harveyai/harvey-labs@7be41d57fd5a/tasks/contracts/commercial-vendor-customer/vendor-services-agreement-term-negotiation/scenario-03/documents`

The narrow vendoring boundary makes the canonical v20 overlay and v21 clean
rebuild self-contained; it does not replace the full 60,971-input local mirror
audited by `tools/audit_harvey_inputs.py`. Upstream is MIT licensed; the
applicable license is preserved in `LICENSE.harvey-labs`.

The five files under `sandbox/` are also copied byte-for-byte from the same
pinned commit. They are the minimal upstream source needed to rebuild the
LibreOffice/pandoc file-lane agent base in a clean checkout; the generator
prefers the complete local Harvey mirror when present and falls back to this
tracked recovery copy.

Likewise, `skills/` is the exact 29-file DOCX/XLSX/PPTX skill tree from
`harness/skills` at that commit. It makes authored legacy/recovery file lanes
self-contained without changing the skill manuals or helper scripts. The file
lane gate checks the combined 34-file sandbox/skill snapshot as 113,081 bytes
with tree SHA-256
`bbdcf02717bf2ad491bf5ebbe028ebd5d69f5427609fddb0aaca3ad8d4e88d5a`.
