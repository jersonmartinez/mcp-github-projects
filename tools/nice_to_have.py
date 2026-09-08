"""Backward-compatibility shim — canonical module is `tools.meta.nice_to_have`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.nice_to_have`) and `tools.meta.nice_to_have` are the SAME object. New code MUST import from
`tools.meta.nice_to_have`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.meta.nice_to_have as _canonical

# Make `tools.nice_to_have` an alias of `tools.meta.nice_to_have`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
