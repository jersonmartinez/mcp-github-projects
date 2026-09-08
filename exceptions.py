"""Backward-compatibility shim — canonical module is `core.exceptions`.

This module aliases the canonical module in sys.modules so the historical
path (`exceptions`) and `core.exceptions` are the SAME object. New code MUST import from
`core.exceptions`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.exceptions as _canonical

# Make `exceptions` an alias of `core.exceptions`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
