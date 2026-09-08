"""Backward-compatibility shim — canonical module is `core.profiles`.

This module aliases the canonical module in sys.modules so the historical
path (`profiles`) and `core.profiles` are the SAME object. New code MUST import from
`core.profiles`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.profiles as _canonical

# Make `profiles` an alias of `core.profiles`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
