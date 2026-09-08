"""Backward-compatibility shim — canonical module is `tools.issues.close`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.close`) and `tools.issues.close` are the SAME object. New code MUST import from
`tools.issues.close`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.issues.close as _canonical

# Make `tools.close` an alias of `tools.issues.close`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
