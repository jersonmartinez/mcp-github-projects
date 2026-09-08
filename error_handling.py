"""Backward-compatibility shim.

Canonical module: `core.error_handling`.
Historical path `error_handling` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`core.error_handling`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.error_handling as _canonical

sys.modules[__name__] = _canonical
