"""Test that the example profile loads correctly.

Validates that the profile-based configuration still works through
the profile mechanism after removing hardcoded defaults.
"""

import os
import sys

# Simulate an example profile environment
os.environ["GH_PROJECT_ORG_NAME"] = "ExampleOrg"
os.environ["GH_PROJECT_REPO_NAME"] = "ExampleRepo"
os.environ["GH_PROJECT_PROJECT_NUMBER"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GitHubProjectSettings


def test_factib_profile_loads():
    """Example profile produces the expected settings."""
    settings = GitHubProjectSettings()
    assert settings.org_name == "ExampleOrg"
    assert settings.repo_name == "ExampleRepo"
    assert settings.project_number == 1


def test_missing_target_raises():
    """Server refuses to start without mandatory target fields."""
    # Clear the env vars
    for key in ("GH_PROJECT_ORG_NAME", "GH_PROJECT_REPO_NAME", "GH_PROJECT_PROJECT_NUMBER"):
        os.environ.pop(key, None)

    try:
        GitHubProjectSettings()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Missing required configuration" in str(e)


def test_partial_target_raises():
    """Server rejects partial target configuration."""
    os.environ["GH_PROJECT_ORG_NAME"] = "some-org"
    os.environ.pop("GH_PROJECT_REPO_NAME", None)
    os.environ.pop("GH_PROJECT_PROJECT_NUMBER", None)

    try:
        GitHubProjectSettings()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "GH_PROJECT_REPO_NAME" in str(e)
        assert "GH_PROJECT_PROJECT_NUMBER" in str(e)


if __name__ == "__main__":
    # Reset lru_cache between tests
    from config import get_settings
    get_settings.cache_clear()

    test_factib_profile_loads()
    print("✅ test_factib_profile_loads passed")

    get_settings.cache_clear()
    test_missing_target_raises()
    print("✅ test_missing_target_raises passed")

    get_settings.cache_clear()
    test_partial_target_raises()
    print("✅ test_partial_target_raises passed")

    print("\nAll compatibility tests passed.")
