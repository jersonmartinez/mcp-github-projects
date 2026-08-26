"""Tests for scope hierarchy expansion in auth.py.

Validates that parent scopes correctly imply their children,
so tokens with admin:org pass validation that requires read:org.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import REQUIRED_SCOPES, _expand_scopes


def test_admin_org_implies_read_org():
    """admin:org should expand to include read:org and write:org."""
    granted = frozenset({"repo", "project", "admin:org"})
    effective = _expand_scopes(granted)

    assert "read:org" in effective
    assert "write:org" in effective
    # All required scopes should be covered
    missing = REQUIRED_SCOPES - effective
    assert len(missing) == 0, f"Missing: {missing}"


def test_explicit_read_org_still_works():
    """A token with read:org explicitly should still pass (no regression)."""
    granted = frozenset({"repo", "project", "read:org"})
    effective = _expand_scopes(granted)

    missing = REQUIRED_SCOPES - effective
    assert len(missing) == 0, f"Missing: {missing}"


def test_missing_org_scope_still_fails():
    """A token without admin:org or read:org should still be missing read:org."""
    granted = frozenset({"repo", "project"})
    effective = _expand_scopes(granted)

    missing = REQUIRED_SCOPES - effective
    assert "read:org" in missing


def test_write_org_implies_read_org():
    """write:org should expand to include read:org."""
    granted = frozenset({"repo", "project", "write:org"})
    effective = _expand_scopes(granted)

    assert "read:org" in effective
    missing = REQUIRED_SCOPES - effective
    assert len(missing) == 0, f"Missing: {missing}"


def test_multiple_hierarchies_expand():
    """Multiple parent scopes should all expand their children."""
    granted = frozenset({"admin:org", "admin:repo_hook", "write:discussion"})
    effective = _expand_scopes(granted)

    assert "read:org" in effective
    assert "write:org" in effective
    assert "read:repo_hook" in effective
    assert "write:repo_hook" in effective
    assert "read:discussion" in effective


def test_no_hierarchy_scopes_pass_through():
    """Scopes without hierarchy entries should remain unchanged."""
    granted = frozenset({"repo", "project", "gist", "notifications"})
    effective = _expand_scopes(granted)

    assert effective == granted


if __name__ == "__main__":
    test_admin_org_implies_read_org()
    print("✅ test_admin_org_implies_read_org")

    test_explicit_read_org_still_works()
    print("✅ test_explicit_read_org_still_works")

    test_missing_org_scope_still_fails()
    print("✅ test_missing_org_scope_still_fails")

    test_write_org_implies_read_org()
    print("✅ test_write_org_implies_read_org")

    test_multiple_hierarchies_expand()
    print("✅ test_multiple_hierarchies_expand")

    test_no_hierarchy_scopes_pass_through()
    print("✅ test_no_hierarchy_scopes_pass_through")

    print("\nAll scope hierarchy tests passed.")
