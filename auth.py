"""Backward-compatibility shim.

Canonical module: `core.auth`.
Historical path `auth` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`core.auth`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import core.auth as _canonical

sys.modules[__name__] = _canonical
