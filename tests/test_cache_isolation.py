"""Tests for cache path isolation per target.

Verifies that different targets get different cache paths to prevent
cross-target pollution.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cache_path_includes_target_namespace():
    """Cache path must include org/repo/project to isolate targets."""
    os.environ["GH_PROJECT_ORG_NAME"] = "TestOrg"
    os.environ["GH_PROJECT_REPO_NAME"] = "TestRepo"
    os.environ["GH_PROJECT_PROJECT_NUMBER"] = "5"
    os.environ.pop("GH_PROJECT_CACHE_PATH", None)

    from config import _default_cache_path

    path = _default_cache_path()
    path_str = str(path)

    assert "TestOrg" in path_str, f"org not in path: {path_str}"
    assert "TestRepo" in path_str, f"repo not in path: {path_str}"
    assert "project-5" in path_str, f"project number not in path: {path_str}"
    assert path_str.endswith("metadata.json"), f"unexpected filename: {path_str}"


def test_different_targets_get_different_paths():
    """Two different targets must produce different cache paths."""
    os.environ.pop("GH_PROJECT_CACHE_PATH", None)

    os.environ["GH_PROJECT_ORG_NAME"] = "OrgA"
    os.environ["GH_PROJECT_REPO_NAME"] = "RepoA"
    os.environ["GH_PROJECT_PROJECT_NUMBER"] = "1"
    from config import _default_cache_path
    path_a = _default_cache_path()

    os.environ["GH_PROJECT_ORG_NAME"] = "OrgB"
    os.environ["GH_PROJECT_REPO_NAME"] = "RepoB"
    os.environ["GH_PROJECT_PROJECT_NUMBER"] = "2"
    path_b = _default_cache_path()

    assert path_a != path_b, f"Same path for different targets: {path_a}"


def test_explicit_cache_path_overrides_namespace():
    """GH_PROJECT_CACHE_PATH env var overrides the namespaced default."""
    custom = "/custom/path/cache.json"
    os.environ["GH_PROJECT_CACHE_PATH"] = custom
    os.environ["GH_PROJECT_ORG_NAME"] = "AnyOrg"
    os.environ["GH_PROJECT_REPO_NAME"] = "AnyRepo"
    os.environ["GH_PROJECT_PROJECT_NUMBER"] = "99"

    from config import _default_cache_path

    path = _default_cache_path()
    assert str(path) == custom

    os.environ.pop("GH_PROJECT_CACHE_PATH", None)


def test_cache_path_writable_in_tmp_fallback():
    """When HOME is not writable, /tmp fallback should be writable."""
    os.environ.pop("GH_PROJECT_CACHE_PATH", None)
    os.environ.pop("XDG_CACHE_HOME", None)
    os.environ["GH_PROJECT_ORG_NAME"] = "TestOrg"
    os.environ["GH_PROJECT_REPO_NAME"] = "TestRepo"
    os.environ["GH_PROJECT_PROJECT_NUMBER"] = "1"

    from config import _default_cache_path

    path = _default_cache_path()
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    assert os.access(parent, os.W_OK), f"Cache dir not writable: {parent}"


if __name__ == "__main__":
    test_cache_path_includes_target_namespace()
    print("✅ test_cache_path_includes_target_namespace")

    test_different_targets_get_different_paths()
    print("✅ test_different_targets_get_different_paths")

    test_explicit_cache_path_overrides_namespace()
    print("✅ test_explicit_cache_path_overrides_namespace")

    test_cache_path_writable_in_tmp_fallback()
    print("✅ test_cache_path_writable_in_tmp_fallback")

    print("\nAll cache isolation tests passed.")
