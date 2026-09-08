"""Backward-compatibility shim — canonical module is `core.auth`.

This module aliases the canonical module in sys.modules so the historical
path (`auth`) and `core.auth` are the SAME object. New code MUST import from
`core.auth`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.auth as _canonical

# Make `auth` an alias of `core.auth`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
