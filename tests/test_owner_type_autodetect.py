"""Tests for runtime owner-type auto-detection (issue #8).

Verifies that owner_type='auto' resolves to 'user' or 'organization' by
querying GitHub, that explicit values short-circuit detection, that the
result is cached, and that detection failures fall back safely.
"""

import asyncio
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("GH_PROJECT_ORG_NAME", "TestOrg")
os.environ.setdefault("GH_PROJECT_REPO_NAME", "TestRepo")
os.environ.setdefault("GH_PROJECT_PROJECT_NUMBER", "1")

from services import owner_type_resolver as otr  # noqa: E402


def _fake_completed(returncode: int, stdout: str) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def setup_function() -> None:
    otr.clear_cache()


def test_typename_mapping():
    assert otr._typename_to_owner_type("User") == "user"
    assert otr._typename_to_owner_type("Organization") == "organization"
    assert otr._typename_to_owner_type("Bot") is None
    assert otr._typename_to_owner_type("") is None


def test_sync_detects_user(monkeypatch):
    """A login GitHub reports as User resolves to 'user'."""
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _fake_completed(0, "User\n"),
    )
    assert otr.resolve_owner_type_sync("jersonmartinez") == "user"


def test_sync_detects_organization(monkeypatch):
    """A login GitHub reports as Organization resolves to 'organization'."""
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _fake_completed(0, "Organization\n"),
    )
    assert otr.resolve_owner_type_sync("github") == "organization"


def test_sync_caches_result(monkeypatch):
    """Detection runs once per login; subsequent calls hit the cache."""
    calls = {"n": 0}

    def _run(*a, **k):
        calls["n"] += 1
        return _fake_completed(0, "User\n")

    monkeypatch.setattr(subprocess, "run", _run)
    assert otr.resolve_owner_type_sync("octocat") == "user"
    assert otr.resolve_owner_type_sync("octocat") == "user"
    assert calls["n"] == 1


def test_sync_falls_back_when_gh_missing(monkeypatch):
    """No gh binary → safe default (backward compatible)."""
    def _raise(*a, **k):
        raise FileNotFoundError("gh not found")

    monkeypatch.setattr(subprocess, "run", _raise)
    assert otr.resolve_owner_type_sync("whoever") == "organization"


def test_sync_falls_back_on_nonzero_exit(monkeypatch):
    """gh error (unauth / rate limit) → safe default."""
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _fake_completed(1, ""),
    )
    assert otr.resolve_owner_type_sync("whoever") == "organization"


def test_sync_custom_default(monkeypatch):
    def _raise(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", _raise)
    assert otr.resolve_owner_type_sync("x", default="user") == "user"


def test_sync_empty_login_returns_default():
    assert otr.resolve_owner_type_sync("") == "organization"


class _FakeGraphQL:
    def __init__(self, typename):
        self._typename = typename
        self.calls = 0

    async def execute(self, query, variables):
        self.calls += 1
        return {"data": {"repositoryOwner": {"__typename": self._typename}}}


def test_async_detects_user():
    client = _FakeGraphQL("User")
    result = asyncio.run(
        otr.resolve_owner_type_via_graphql("octocat", client)
    )
    assert result == "user"


def test_async_detects_org_and_caches():
    client = _FakeGraphQL("Organization")
    r1 = asyncio.run(otr.resolve_owner_type_via_graphql("acme", client))
    r2 = asyncio.run(otr.resolve_owner_type_via_graphql("acme", client))
    assert r1 == r2 == "organization"
    assert client.calls == 1  # second call served from cache


def test_async_falls_back_on_error():
    class _Boom:
        async def execute(self, *a, **k):
            raise RuntimeError("network down")

    result = asyncio.run(
        otr.resolve_owner_type_via_graphql("acme", _Boom())
    )
    assert result == "organization"


def test_async_null_owner_falls_back():
    class _Null:
        async def execute(self, *a, **k):
            return {"data": {"repositoryOwner": None}}

    result = asyncio.run(
        otr.resolve_owner_type_via_graphql("ghost", _Null())
    )
    assert result == "organization"


def test_from_settings_auto_resolves(monkeypatch):
    """GitHubContext.from_settings with owner_type='auto' detects at runtime."""
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _fake_completed(0, "User\n"),
    )
    otr.clear_cache()
    from config import GitHubProjectSettings
    from models.context import GitHubContext

    settings = GitHubProjectSettings(
        org_name="jersonmartinez",
        repo_name="mcp-github-projects",
        project_number=11,
        owner_type="auto",
    )
    context = GitHubContext.from_settings(
        settings=settings,
        token_provider=lambda: "fake-token",
    )
    assert context.target.owner_type == "user"


def test_from_settings_explicit_short_circuits(monkeypatch):
    """Explicit owner_type never triggers detection."""
    def _fail(*a, **k):
        raise AssertionError("detection must not run for explicit owner_type")

    monkeypatch.setattr(subprocess, "run", _fail)
    from config import GitHubProjectSettings
    from models.context import GitHubContext

    settings = GitHubProjectSettings(
        org_name="acme",
        repo_name="repo",
        project_number=2,
        owner_type="organization",
    )
    context = GitHubContext.from_settings(
        settings=settings,
        token_provider=lambda: "fake-token",
    )
    assert context.target.owner_type == "organization"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
