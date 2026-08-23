#!/usr/bin/env python3
"""Pure fixture checks for systematic-failure triage auditing."""

from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "audit_triage_suspects", ROOT / "tools/audit_triage_suspects.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


def verdict(passed: bool, assertion_passed: bool):
    return {
        "passed": passed,
        "failed_conditions": [] if assertion_passed else ["required_path"],
        "assertions": [{"name": "required_path", "passed": assertion_passed}],
    }


fixture = {
    "episodes": {
        "oracle": {"verdict": verdict(True, True)},
        "noop": {"verdict": verdict(False, False)},
        "text_only": {"verdict": verdict(False, False)},
        "blind_write": {"verdict": verdict(False, False)},
        "wrong_value": {"verdict": verdict(False, False)},
    }
}
triage = {"systematic_failed_assertions": ["required_path"]}
cleared = module.audit_task("fixture", triage, fixture)
assert cleared["decision"] == "harness_cleared_model_boundary"

missing = module.audit_task("fixture", triage, None)
assert missing["decision"] == "unresolved_missing_fixture"

not_discriminated = {**fixture, "episodes": {
    **fixture["episodes"],
    "noop": {"verdict": {"passed": False, "failed_conditions": ["different"],
                           "assertions": [{"name": "different", "passed": False}]}},
    "text_only": {"verdict": {"passed": False, "failed_conditions": ["different"],
                                "assertions": [{"name": "different", "passed": False}]}},
    "blind_write": {"verdict": {"passed": False, "failed_conditions": ["different"],
                                  "assertions": [{"name": "different", "passed": False}]}},
    "wrong_value": {"verdict": {"passed": False, "failed_conditions": ["different"],
                                  "assertions": [{"name": "different", "passed": False}]}},
}}
unresolved = module.audit_task("fixture", triage, not_discriminated)
assert unresolved["decision"] == "unresolved_assertion_not_discriminated"

print("triage suspect audit gate: cleared, missing-fixture, and undiscriminated branches pass")
