"""Backward-compatibility shim — canonical module is `tools.issues.advanced_operations`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.advanced_operations`) and `tools.issues.advanced_operations` are the SAME object. New code MUST import from
`tools.issues.advanced_operations`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.issues.advanced_operations as _canonical

# Make `tools.advanced_operations` an alias of `tools.issues.advanced_operations`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
