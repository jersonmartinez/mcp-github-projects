"""Contracts for executable imports, project workflow visibility, and flow metrics."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.gh_cli_client import CommandResult  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.factory import use_service_factory  # noqa: E402
from models.metadata import FieldOption, ProjectField, ProjectMetadata  # noqa: E402
from tools.meta.capability_suite import MarkdownInput, project_import_markdown  # noqa: E402
from tools.projects.workflows_visibility import (  # noqa: E402
    DeleteProjectWorkflowInput,
    ListProjectWorkflowsInput,
    delete_project_workflow,
    list_project_workflows,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def configured_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("GH_PROJECT_ORG_NAME", "octo-org")
    monkeypatch.setenv("GH_PROJECT_REPO_NAME", "octo-repo")
    monkeypatch.setenv("GH_PROJECT_PROJECT_NUMBER", "7")
    monkeypatch.setenv("GH_PROJECT_OWNER_TYPE", "organization")
    monkeypatch.setenv("GH_PROJECT_CACHE_PATH", str(tmp_path / "metadata.json"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeGH:
    def __init__(self, stdout: str = "[]") -> None:
        self.stdout = stdout
        self.calls: list[list[str]] = []

    async def run(self, args: list[str]) -> CommandResult:
        self.calls.append(args)
        return CommandResult(stdout=self.stdout, stderr="", return_code=0)

    async def api_graphql(self, query: str, variables: dict) -> dict:
        return {}


class WorkflowGraphQL:
    def __init__(self) -> None:
        self.mutations: list[dict] = []

    async def execute(self, query: str, variables: dict | None = None) -> dict:
        if "deleteProjectV2Workflow" in query:
            self.mutations.append(variables or {})
            return {"deleteProjectV2Workflow": {"deletedWorkflowId": (variables or {})["workflowId"], "projectV2": {"id": "PVT_1", "title": "Board"}}}
        return {"node": {"title": "Board", "workflows": {"nodes": [{"id": "PVTW_1", "name": "Item closed", "number": 1, "enabled": True}]}}}

    async def execute_with_retry(self, query, variables=None, *, is_mutation=False) -> dict:
        return await self.execute(query, variables)


class MetadataCache:
    def read_cache(self, cache_path: Path):
        return ProjectMetadata(project_id="PVT_1", owner="octo-org", project_number=7, fields={}, discovered_at=datetime.now(timezone.utc))

    def write_cache(self, metadata, cache_path: Path) -> None:
        raise AssertionError("cache must already be fresh")

    def is_fresh(self, metadata) -> bool:
        return True


@pytest.mark.anyio
async def test_project_import_markdown_validates_all_rows_before_any_write() -> None:
    text = "| title | status | due_date |\n|---|---|---|\n| Alpha | Done | 2026-01-01 |\n| Alpha | Done | 2026-01-02 |\n"
    result = await project_import_markdown(MarkdownInput(text=text))
    assert result["ok"] is True
    assert result["data"]["valid"] is False
    assert result["data"]["dry_run"] is True
    assert any("duplicate title" in error for error in result["data"]["errors"])

    valid = await project_import_markdown(MarkdownInput(text="| title | status |\n|---|---|\n| Alpha | Done |\n"))
    assert valid["data"]["valid"] is True
    assert valid["data"]["rows"][0]["title"] == "Alpha"

    unconfirmed = await project_import_markdown(MarkdownInput(text="| title |\n|---|\n| Alpha |\n", dry_run=False, confirm=False))
    assert unconfirmed["ok"] is False
    assert "confirm=true" in unconfirmed["message"]


@pytest.mark.anyio
async def test_list_and_delete_project_workflows_are_explicit() -> None:
    graphql = WorkflowGraphQL()
    gh = FakeGH()
    with use_service_factory(graphql_client=graphql, gh_client=gh, cache_manager=MetadataCache()):
        listed = await list_project_workflows(ListProjectWorkflowsInput())
        refused = await delete_project_workflow(DeleteProjectWorkflowInput(workflow_id="PVTW_1", confirm=False))
        deleted = await delete_project_workflow(DeleteProjectWorkflowInput(workflow_id="PVTW_1", confirm=True))
    assert listed["data"]["workflows"][0]["name"] == "Item closed"
    assert "UI-only" in listed["data"]["api_limitations"][0] or "does not expose" in listed["data"]["api_limitations"][0]
    assert refused["ok"] is False
    assert deleted["data"]["deleted"] is True
    assert graphql.mutations == [{"workflowId": "PVTW_1"}]


@pytest.mark.anyio
async def test_project_import_revalidates_field_values_before_first_write() -> None:
    status_field = ProjectField(
        id="PVTSSF_status",
        name="Status",
        data_type="SINGLE_SELECT",
        options=[FieldOption(id="opt_done", name="Done")],
    )

    class ImportMetadataCache(MetadataCache):
        def read_cache(self, cache_path: Path):
            return ProjectMetadata(
                project_id="PVT_1",
                owner="octo-org",
                project_number=7,
                fields={"Status": status_field},
                discovered_at=datetime.now(timezone.utc),
            )

    gh = FakeGH()
    text = "| title | status |\n|---|---|\n| Alpha | Bogus |\n| Beta | Done |\n"
    with use_service_factory(graphql_client=WorkflowGraphQL(), gh_client=gh, cache_manager=ImportMetadataCache()):
        result = await project_import_markdown(MarkdownInput(text=text, dry_run=False, confirm=True))
    assert result["ok"] is True
    assert result["data"]["valid"] is False
    assert result["data"]["dry_run"] is True
    assert "Board field validation failed" in result["data"]["message"]
    assert not any(call[:2] == ["issue", "create"] for call in gh.calls)


@pytest.mark.anyio
async def test_delete_project_workflow_refuses_node_not_listed_on_project() -> None:
    class ForeignWorkflowGraphQL(WorkflowGraphQL):
        async def execute(self, query: str, variables: dict | None = None) -> dict:
            return {"node": {"id": "PVTW_foreign", "project": {"id": "PVT_other"}}}

    graphql = ForeignWorkflowGraphQL()
    with use_service_factory(graphql_client=graphql, gh_client=FakeGH(), cache_manager=MetadataCache()):
        result = await delete_project_workflow(DeleteProjectWorkflowInput(workflow_id="PVTW_foreign", confirm=True))
    assert result["ok"] is False
    assert "was not found on project" in result["message"]
    assert graphql.mutations == []
