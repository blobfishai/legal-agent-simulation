"""v20 verifier compiler.

The v19 declarative compiler is generic (required_path, new_row/absent_new_row/
changed_row/tool_observation_contains/tool_min_calls assertions, allowed-table
collateral guard) and its emitted VCode is self-contained at grade time, so v20
reuses it verbatim rather than forking a second dialect.
"""
from __future__ import annotations

from world.v19.verifiers import compile_vcode

__all__ = ["compile_vcode"]
