"""Backward-compatibility shim — canonical module is `tools.fields.labels`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.labels`) and `tools.fields.labels` are the SAME object. New code MUST import from
`tools.fields.labels`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.fields.labels as _canonical

# Make `tools.labels` an alias of `tools.fields.labels`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
