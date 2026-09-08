"""Backward-compatibility shim — canonical module is `tools.planning.planning`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.planning`) and `tools.planning.planning` are the SAME object. New code MUST import from
`tools.planning.planning`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.planning.planning as _canonical

# Make `tools.planning` an alias of `tools.planning.planning`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
