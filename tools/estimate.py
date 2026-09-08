"""Backward-compatibility shim — canonical module is `tools.fields.estimate`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.estimate`) and `tools.fields.estimate` are the SAME object. New code MUST import from
`tools.fields.estimate`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.fields.estimate as _canonical

# Make `tools.estimate` an alias of `tools.fields.estimate`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
