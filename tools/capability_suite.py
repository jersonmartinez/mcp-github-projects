"""Backward-compatibility shim — canonical module is `tools.meta.capability_suite`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.capability_suite`) and `tools.meta.capability_suite` are the SAME object. New code MUST import from
`tools.meta.capability_suite`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.meta.capability_suite as _canonical

# Make `tools.capability_suite` an alias of `tools.meta.capability_suite`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
