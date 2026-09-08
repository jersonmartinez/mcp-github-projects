"""Backward-compatibility shim — canonical module is `tools.bulk.bulk_operations`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.bulk_operations`) and `tools.bulk.bulk_operations` are the SAME object. New code MUST import from
`tools.bulk.bulk_operations`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.bulk.bulk_operations as _canonical

# Make `tools.bulk_operations` an alias of `tools.bulk.bulk_operations`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
