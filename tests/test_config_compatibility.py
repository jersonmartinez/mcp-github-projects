"""Tests for mandatory target configuration."""

import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from config import GitHubProjectSettings  # noqa: E402


@pytest.fixture
def configured_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a deterministic target for one test only."""
    monkeypatch.setenv("GH_PROJECT_ORG_NAME", "ExampleOrg")
    monkeypatch.setenv("GH_PROJECT_REPO_NAME", "ExampleRepo")
    monkeypatch.setenv("GH_PROJECT_PROJECT_NUMBER", "1")


def test_factib_profile_loads(configured_target: None) -> None:
    """Example target configuration produces expected settings."""
    settings = GitHubProjectSettings()
    assert settings.org_name == "ExampleOrg"
    assert settings.repo_name == "ExampleRepo"
    assert settings.project_number == 1


def test_missing_target_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server refuses to start without mandatory target fields."""
    for key in ("GH_PROJECT_ORG_NAME", "GH_PROJECT_REPO_NAME", "GH_PROJECT_PROJECT_NUMBER"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Missing required configuration"):
        GitHubProjectSettings()


def test_partial_target_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server rejects partial target configuration."""
    monkeypatch.setenv("GH_PROJECT_ORG_NAME", "some-org")
    monkeypatch.delenv("GH_PROJECT_REPO_NAME", raising=False)
    monkeypatch.delenv("GH_PROJECT_PROJECT_NUMBER", raising=False)

    with pytest.raises(ValueError) as exc_info:
        GitHubProjectSettings()
    assert "GH_PROJECT_REPO_NAME" in str(exc_info.value)
    assert "GH_PROJECT_PROJECT_NUMBER" in str(exc_info.value)
