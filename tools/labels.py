"""Backward-compatibility shim.

Canonical module: `tools.fields.labels`.
Historical path `tools.labels` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`tools.fields.labels`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.fields.labels as _canonical

sys.modules[__name__] = _canonical
