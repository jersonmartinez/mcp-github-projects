"""Backward-compatibility shim — canonical module is `tools.discovery.list_items`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.list_items`) and `tools.discovery.list_items` are the SAME object. New code MUST import from
`tools.discovery.list_items`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.discovery.list_items as _canonical

# Make `tools.list_items` an alias of `tools.discovery.list_items`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
