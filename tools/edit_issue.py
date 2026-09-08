"""Backward-compatibility shim — canonical module is `tools.issues.edit_issue`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.edit_issue`) and `tools.issues.edit_issue` are the SAME object. New code MUST import from
`tools.issues.edit_issue`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.issues.edit_issue as _canonical

# Make `tools.edit_issue` an alias of `tools.issues.edit_issue`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
