"""Backward-compatibility shim — canonical module is `core.hardening`.

This module aliases the canonical module in sys.modules so the historical
path (`hardening`) and `core.hardening` are the SAME object. New code MUST import from
`core.hardening`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.hardening as _canonical

# Make `hardening` an alias of `core.hardening`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
