"""Backward-compatibility shim — canonical module is `core.config`.

This module aliases the canonical module in sys.modules so the historical
path (`config`) and `core.config` are the SAME object. New code MUST import from
`core.config`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.config as _canonical

# Make `config` an alias of `core.config`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
