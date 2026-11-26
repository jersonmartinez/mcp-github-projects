"""Visibility and narrowly-scoped lifecycle support for Projects V2 workflows."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from core.error_handling import build_error_response, handle_tool_error
from core.factory import get_service_factory
from core.project_scope import project_context
from models.responses import ToolSuccess

logger = logging.getLogger(__name__)


class ListProjectWorkflowsInput(BaseModel):
    """Input schema for list_project_workflows."""

    project_number: int | None = Field(default=None, gt=0, le=100_000, description="Project V2 board number; defaults to configured board.")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum workflows returned.")


class DeleteProjectWorkflowInput(BaseModel):
    """Input schema for delete_project_workflow."""

    workflow_id: str = Field(..., min_length=4, max_length=200, description="Workflow node id returned by list_project_workflows; never guess it.")
    project_number: int | None = Field(default=None, gt=0, le=100_000, description="Project V2 board number; defaults to configured board.")
    confirm: bool = Field(default=False, description="Required true: workflow deletion is permanent and cannot be recreated through the public API.")


def _summary(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": workflow.get("id"),
        "name": workflow.get("name"),
        "number": workflow.get("number"),
        "enabled": workflow.get("enabled"),
        "created_at": workflow.get("createdAt"),
        "updated_at": workflow.get("updatedAt"),
    }


async def list_project_workflows(params: ListProjectWorkflowsInput) -> dict:
    """List native GitHub Projects V2 workflows and their enabled state.

    GitHub exposes workflow configuration as read-only through GraphQL. Creation
    and rule editing are UI-only; this tool intentionally does not pretend those
    operations are automatable.
    """
    try:
        context = project_context(params.project_number)
        factory = get_service_factory()
        graphql = await factory.graphql()
        discovery = await factory.discovery_service(graphql, context=context)
        project = await discovery.get_cached_or_discover()
        query = """
        query($projectId: ID!, $limit: Int!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              id
              title
              workflows(first: $limit) {
                nodes { id name number enabled createdAt updatedAt }
              }
            }
          }
        }
        """
        data = await graphql.execute(query, {"projectId": project.project_id, "limit": params.limit})
        node = (data or {}).get("node") or {}
        nodes = ((node.get("workflows") or {}).get("nodes") or [])
        workflows = [_summary(item) for item in nodes if isinstance(item, dict)]
        return ToolSuccess(data={
            "project_id": project.project_id,
            "project_title": node.get("title"),
            "total": len(workflows),
            "workflows": workflows,
            "api_limitations": [
                "GitHub does not expose mutations to create, edit, enable, or disable built-in project workflows.",
                "Only deleteProjectV2Workflow is exposed; deletion is permanent and gated behind confirm=true.",
                "Use deterministic MCP workflow tools for executable automation that the API can perform safely.",
            ],
        }).model_dump()
    except Exception as exc:
        logger.error("Error in list_project_workflows: %s", exc)
        return handle_tool_error(exc, context="List project workflows failed")


async def delete_project_workflow(params: DeleteProjectWorkflowInput) -> dict:
    """Delete a native Projects V2 workflow after explicit confirmation.

    This is the only native workflow lifecycle mutation exposed by GitHub. It is
    destructive because there is no public mutation capable of recreating the
    workflow or its exact rule configuration.
    """
    try:
        if not params.confirm:
            return build_error_response(
                error_type="validation",
                message="Deleting a project workflow is permanent; pass confirm=true.",
                suggestion="Run list_project_workflows first and preserve the workflow name/number in your change record.",
            )
        context = project_context(params.project_number)
        factory = get_service_factory()
        graphql = await factory.graphql()
        discovery = await factory.discovery_service(graphql, context=context)
        project = await discovery.get_cached_or_discover()
        ownership_query = """
        query($projectId: ID!, $limit: Int!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              workflows(first: $limit) { nodes { id name number enabled } }
            }
          }
        }
        """
        ownership_data = await graphql.execute(ownership_query, {"projectId": project.project_id, "limit": 100})
        workflows = ((((ownership_data or {}).get("node") or {}).get("workflows") or {}).get("nodes") or [])
        if not any(isinstance(item, dict) and item.get("id") == params.workflow_id for item in workflows):
            return build_error_response(
                error_type="validation",
                message=f"Workflow {params.workflow_id} was not found on project {project.project_number}.",
                suggestion="Run list_project_workflows for the same project_number and never guess workflow node ids.",
            )
        mutation = """
        mutation($workflowId: ID!) {
          deleteProjectV2Workflow(input: {workflowId: $workflowId}) {
            deletedWorkflowId
            projectV2 { id title }
          }
        }
        """
        data = await graphql.execute(mutation, {"workflowId": params.workflow_id})
        payload = (data or {}).get("deleteProjectV2Workflow") or {}
        if not payload.get("deletedWorkflowId"):
            return build_error_response(
                error_type="internal",
                message="GitHub returned an incomplete workflow deletion response.",
                suggestion="Re-run list_project_workflows before attempting any retry.",
            )
        return ToolSuccess(data={
            "deleted": True,
            "workflow_id": payload.get("deletedWorkflowId"),
            "project": payload.get("projectV2") or {},
        }).model_dump()
    except Exception as exc:
        logger.error("Error in delete_project_workflow: %s", exc)
        return handle_tool_error(exc, context="Delete project workflow failed")
