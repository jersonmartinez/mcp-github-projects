"""Backward-compatibility shim.

Canonical module: `tools.meta.capability_suite`.
Historical path `tools.capability_suite` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`tools.meta.capability_suite`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.meta.capability_suite as _canonical

sys.modules[__name__] = _canonical
