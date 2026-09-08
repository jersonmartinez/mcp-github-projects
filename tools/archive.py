"""Backward-compatibility shim — canonical module is `tools.projects.archive`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.archive`) and `tools.projects.archive` are the SAME object. New code MUST import from
`tools.projects.archive`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.projects.archive as _canonical

# Make `tools.archive` an alias of `tools.projects.archive`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
