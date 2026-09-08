"""Backward-compatibility shim.

Canonical module: `tools.pull_requests.pr_issue_lifecycle`.
Historical path `tools.pr_issue_lifecycle` is aliased to it via sys.modules so both resolve to
the SAME module object — attribute access and unittest.mock.patch on the old
path operate on the canonical module itself. New code MUST import from
`tools.pull_requests.pr_issue_lifecycle`.
See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.pull_requests.pr_issue_lifecycle as _canonical

sys.modules[__name__] = _canonical
