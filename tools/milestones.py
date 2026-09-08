"""Backward-compatibility shim — canonical module is `tools.fields.milestones`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.milestones`) and `tools.fields.milestones` are the SAME object. New code MUST import from
`tools.fields.milestones`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.fields.milestones as _canonical

# Make `tools.milestones` an alias of `tools.fields.milestones`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
