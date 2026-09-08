"""Backward-compatibility shim — canonical module is `tools.discovery.discover`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.discover`) and `tools.discovery.discover` are the SAME object. New code MUST import from
`tools.discovery.discover`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.discovery.discover as _canonical

# Make `tools.discover` an alias of `tools.discovery.discover`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
