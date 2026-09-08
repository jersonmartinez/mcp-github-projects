"""Backward-compatibility shim — canonical module is `tools.planning.workflows`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.workflows`) and `tools.planning.workflows` are the SAME object. New code MUST import from
`tools.planning.workflows`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.planning.workflows as _canonical

# Make `tools.workflows` an alias of `tools.planning.workflows`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
