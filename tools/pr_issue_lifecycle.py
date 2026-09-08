"""Backward-compatibility shim — canonical module is `tools.pull_requests.pr_issue_lifecycle`.

This module aliases the canonical module in sys.modules so the historical
path (`tools.pr_issue_lifecycle`) and `tools.pull_requests.pr_issue_lifecycle` are the SAME object. New code MUST import from
`tools.pull_requests.pr_issue_lifecycle`. See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import sys

import tools.pull_requests.pr_issue_lifecycle as _canonical

# Make `tools.pr_issue_lifecycle` an alias of `tools.pull_requests.pr_issue_lifecycle`: attribute access and mock.patch on the
# old path operate on the canonical module object itself.
sys.modules[__name__] = _canonical
