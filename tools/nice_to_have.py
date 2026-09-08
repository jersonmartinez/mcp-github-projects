"""Backward-compatibility shim.

Canonical module: `tools.meta.nice_to_have`.
Historical path `tools.nice_to_have` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`tools.meta.nice_to_have`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.meta.nice_to_have as _canonical

sys.modules[__name__] = _canonical
