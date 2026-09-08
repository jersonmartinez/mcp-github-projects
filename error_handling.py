"""Backward-compatibility shim — canonical module is `core.error_handling`.

This module aliases the canonical module in sys.modules so the historical
path (`error_handling`) and `core.error_handling` are the SAME object. New code MUST import from
`core.error_handling`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.error_handling as _canonical

# Make `error_handling` an alias of `core.error_handling`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
