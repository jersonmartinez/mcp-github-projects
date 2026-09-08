"""Backward-compatibility shim — canonical module is `core.capabilities`.

This module aliases the canonical module in sys.modules so the historical
path (`capabilities`) and `core.capabilities` are the SAME object. New code MUST import from
`core.capabilities`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.capabilities as _canonical

# Make `capabilities` an alias of `core.capabilities`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
