"""Backward-compatibility shim — canonical module is `tools.issues.create_item`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.create_item`) and `tools.issues.create_item` are the SAME object. New code MUST import from
`tools.issues.create_item`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.issues.create_item as _canonical

# Make `tools.create_item` an alias of `tools.issues.create_item`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
