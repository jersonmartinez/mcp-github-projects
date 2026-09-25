"""MCP Server entry point for GitHub Project Management.

Creates a FastMCP server instance, registers all tools, validates
authentication on startup, and runs with stdio transport for MCP
communication.

Usage:
    python -m app.mcp.github_project.server
"""

from __future__ import annotations

import asyncio
import sys

from fastmcp import FastMCP

from core.auth import resolve_token, validate_scopes
from core.config import get_settings
from tools.projects.archive import (
    archive_project_item,
    move_to_done,
    move_to_trash,
)
from tools.projects.add_item import add_item_to_project
from tools.issues.close import close_issue
from tools.issues.comment_issue import comment_issue
from tools.issues.add_sub_issue import add_sub_issue
from tools.issues.edit_issue import edit_issue
from tools.issues.create_item import create_project_item
from tools.discovery.discover import discover_ids
from tools.fields.estimate import set_estimate
from tools.discovery.list_items import list_project_items
from tools.projects.update_fields import update_project_item_fields
from tools.fields.milestones import create_milestone, close_milestone, list_milestones
from tools.fields.labels import create_label, list_labels
from tools.bulk.bulk_operations import bulk_close_issues, search_issues
from tools.issues.advanced_operations import (
    move_to_status,
    bulk_update_items,
    get_issue_detail,
    list_sub_issues,
    remove_sub_issue,
    reopen_issue,
)
from tools.meta.nice_to_have import (
    get_project_stats,
    get_sprint_summary,
    link_pull_request,
    create_pull_request,
    bulk_assign,
)
from tools.repositories import create_repository
from tools.planning.planning import (
    sprint_planning,
    generate_release_notes,
)
from tools.planning.workflows import (
    complete_issue as complete_issue_workflow,
    daily_standup,
    sprint_review,
    triage_new_issues,
    escalate_overdue,
    handoff_issue,
    create_epic,
    close_sprint,
    blocked_report,
)
from tools.pull_requests.pr_issue_lifecycle import (
    verify_acceptance_criteria,
    get_pr_linked_issues,
    validate_issue_closure_readiness,
    close_issue_on_pr_merge,
    sync_closed_items_to_done,
)
from tools.meta import capability_suite
from tools.project_provisioning import (
    create_project,
    update_project,
    create_project_field,
    link_repository,
    list_projects,
)

# ── FastMCP Server Instance ──────────────────────────────────────────────────

mcp = FastMCP("github-project-management")

# ── Register Tools ───────────────────────────────────────────────────────────

# In FastMCP 2.14+, use mcp.tool() as a decorator wrapper for pre-defined functions
mcp.tool()(discover_ids)
mcp.tool()(list_project_items)
mcp.tool()(create_project_item)
mcp.tool()(update_project_item_fields)
mcp.tool()(add_item_to_project)
mcp.tool()(set_estimate)
mcp.tool()(archive_project_item)
mcp.tool()(move_to_done)
mcp.tool()(move_to_trash)
mcp.tool()(close_issue)
mcp.tool()(comment_issue)
mcp.tool()(add_sub_issue)
mcp.tool()(edit_issue)
mcp.tool()(create_milestone)
mcp.tool()(close_milestone)
mcp.tool()(list_milestones)
mcp.tool()(create_label)
mcp.tool()(list_labels)
mcp.tool()(bulk_close_issues)
mcp.tool()(search_issues)
mcp.tool()(move_to_status)
mcp.tool()(bulk_update_items)
mcp.tool()(get_issue_detail)
mcp.tool()(list_sub_issues)
mcp.tool()(remove_sub_issue)
mcp.tool()(reopen_issue)
mcp.tool()(get_project_stats)
mcp.tool()(get_sprint_summary)
mcp.tool()(link_pull_request)
mcp.tool()(create_pull_request)
mcp.tool()(create_repository)
mcp.tool()(bulk_assign)
mcp.tool()(sprint_planning)
mcp.tool()(generate_release_notes)
mcp.tool()(complete_issue_workflow)
mcp.tool()(daily_standup)
mcp.tool()(sprint_review)
mcp.tool()(triage_new_issues)
mcp.tool()(escalate_overdue)
mcp.tool()(handoff_issue)
mcp.tool()(create_epic)
mcp.tool()(close_sprint)
mcp.tool()(blocked_report)
mcp.tool()(verify_acceptance_criteria)
mcp.tool()(get_pr_linked_issues)
mcp.tool()(validate_issue_closure_readiness)
mcp.tool()(close_issue_on_pr_merge)
mcp.tool()(sync_closed_items_to_done)
mcp.tool()(create_project)
mcp.tool()(update_project)
mcp.tool()(create_project_field)
mcp.tool()(link_repository)
mcp.tool()(list_projects)

# Register the extended capability suite (60 additional tools).
for _tool_name in capability_suite.CAPABILITY_TOOL_NAMES:
    mcp.tool()(getattr(capability_suite, _tool_name))


# ── Startup Authentication ───────────────────────────────────────────────────


async def _validate_auth_on_startup() -> None:
    """Validate authentication within the configured timeout.

    Resolves the token and verifies it's valid by making a test API call.
    Scope validation is skipped for fine-grained tokens (github_pat_*)
    since they don't return X-OAuth-Scopes headers.
    """
    settings = get_settings()
    timeout = settings.timeout_seconds

    try:
        token = await asyncio.wait_for(
            resolve_token(),
            timeout=timeout,
        )
        # Skip scope validation for fine-grained PATs (github_pat_*)
        # They don't support X-OAuth-Scopes header but still have permissions
        if not token.startswith("github_pat_"):
            await asyncio.wait_for(
                validate_scopes(token),
                timeout=timeout,
            )
    except asyncio.TimeoutError:
        print(
            f"Error: Authentication validation timed out after "
            f"{timeout} seconds.\n"
            "Could not verify token and scopes within the time limit.",
            file=sys.stderr,
        )
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"Error: Authentication validation failed: {exc}\n"
            "Verify that GITHUB_TOKEN or GH_TOKEN is set with "
            "repo, project, and read:org scopes.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "github-project-management MCP server ready. "
        "Authentication validated successfully.",
        file=sys.stderr,
    )


# ── Main Entry Point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server with stdio transport.

    1. Validates authentication (token + scopes) within timeout.
    2. Starts the FastMCP server on stdio transport.
    """
    asyncio.run(_validate_auth_on_startup())
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
