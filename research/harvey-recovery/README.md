# Harvey LAB recovery fixture

This directory vendors the exact 15 input files needed by the one recovered
Harvey LAB task `labp_b50165c2a9cd39db`. The files are copied without mutation
from:

`harveyai/harvey-labs@7be41d57fd5a/tasks/contracts/commercial-vendor-customer/vendor-services-agreement-term-negotiation/scenario-03/documents`

The narrow vendoring boundary makes the canonical v20 overlay and v21 clean
rebuild self-contained; it does not replace the full 60,971-input local mirror
audited by `tools/audit_harvey_inputs.py`. Upstream is MIT licensed; the
applicable license is preserved in `LICENSE.harvey-labs`.
