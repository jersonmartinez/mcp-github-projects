"""Backward-compatibility shim — canonical module is `tools.projects.update_fields`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.update_fields`) and `tools.projects.update_fields` are the SAME object. New code MUST import from
`tools.projects.update_fields`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.projects.update_fields as _canonical

# Make `tools.update_fields` an alias of `tools.projects.update_fields`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
