"""MCP tools for nice-to-have automation features.

Exposes tools for:
- Getting project statistics (items per status, velocity)
- Getting sprint summary (milestone progress, burndown data)
- Linking pull requests to issues
- Bulk assigning issues to users/milestones
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from auth import resolve_token
from clients.gh_cli_client import CLIError, GHCLIClient
from config import get_settings
from error_handling import build_error_response, handle_tool_error
from models.responses import ToolSuccess

logger = logging.getLogger(__name__)


class GetProjectStatsInput(BaseModel):
    """Input schema for the get_project_stats tool."""

    pass


class GetSprintSummaryInput(BaseModel):
    """Input schema for the get_sprint_summary tool."""

    milestone_title: str = Field(description="Milestone title to get summary for")


class LinkPullRequestInput(BaseModel):
    """Input schema for the link_pull_request tool."""

    issue_number: int = Field(description="Issue number to link the PR to")
    pr_number: int = Field(description="Pull request number to link")


class BulkAssignInput(BaseModel):
    """Input schema for the bulk_assign tool."""

    issue_numbers: list[int] = Field(description="List of issue numbers to assign")
    assignees: Optional[list[str]] = Field(default=None, description="GitHub usernames to assign")
    milestone: Optional[str] = Field(default=None, description="Milestone title to set on all issues")


async def get_project_stats() -> dict:
    """Get statistics for the GitHub Project board.

    Returns sprint progress, issue counts, and milestone data.

    Returns:
        ToolSuccess with project statistics.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh_client = GHCLIClient()

        # Get milestones for sprint tracking
        ms_result = await gh_client.run([
            "api", f"repos/{repo}/milestones?state=open&per_page=100&sort=due_on",
        ])
        milestones = json.loads(ms_result.stdout)

        sprint_stats = []
        total_open = 0
        total_closed = 0
        for ms in milestones:
            open_count = ms.get("open_issues", 0)
            closed_count = ms.get("closed_issues", 0)
            total = open_count + closed_count
            total_open += open_count
            total_closed += closed_count
            sprint_stats.append({
                "title": ms.get("title"),
                "open_issues": open_count,
                "closed_issues": closed_count,
                "total": total,
                "progress_pct": round(closed_count / max(total, 1) * 100),
                "due_on": ms.get("due_on"),
            })

        return ToolSuccess(
            data={
                "total_open_issues": total_open,
                "total_closed_issues": total_closed,
                "overall_progress_pct": round(total_closed / max(total_open + total_closed, 1) * 100),
                "sprints": sprint_stats,
                "sprint_count": len(sprint_stats),
            },
        ).model_dump()

    except Exception as exc:
        logger.error("Error in get_project_stats: %s", exc)
        return handle_tool_error(exc, context="Get project stats failed")


async def get_sprint_summary(params: GetSprintSummaryInput) -> dict:
    """Get summary of a specific sprint/milestone.

    Returns issues, completion percentage, assignee distribution, days remaining.

    Args:
        params: Input containing milestone title.

    Returns:
        ToolSuccess with sprint summary data.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh_client = GHCLIClient()

        ms_result = await gh_client.run([
            "api", f"repos/{repo}/milestones?state=open&per_page=100",
        ])
        milestones = json.loads(ms_result.stdout)

        target = None
        for ms in milestones:
            if ms.get("title") == params.milestone_title:
                target = ms
                break

        if not target:
            return build_error_response(
                error_type="not_found",
                message=f"Milestone '{params.milestone_title}' not found.",
                suggestion="Use list_milestones to see available milestones.",
            )

        issues_result = await gh_client.run([
            "issue", "list", "--repo", repo, "--milestone", params.milestone_title,
            "--state", "all", "--limit", "100",
            "--json", "number,title,state,assignees,labels",
        ])
        issues = json.loads(issues_result.stdout)

        open_issues = [i for i in issues if i.get("state") == "OPEN"]
        closed_issues = [i for i in issues if i.get("state") == "CLOSED"]

        assignee_counts: dict[str, int] = {}
        for issue in issues:
            for assignee in issue.get("assignees", []):
                login = assignee.get("login", "unassigned")
                assignee_counts[login] = assignee_counts.get(login, 0) + 1

        due_on = target.get("due_on")
        days_remaining = None
        if due_on:
            from datetime import datetime, timezone
            due_date = datetime.fromisoformat(due_on.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_remaining = max(0, (due_date - now).days)

        total = len(issues)
        progress_pct = round(len(closed_issues) / max(total, 1) * 100)

        return ToolSuccess(
            data={
                "milestone": params.milestone_title,
                "due_on": due_on,
                "days_remaining": days_remaining,
                "total_issues": total,
                "open": len(open_issues),
                "closed": len(closed_issues),
                "progress_pct": progress_pct,
                "assignee_distribution": assignee_counts,
                "open_issues": [{"number": i["number"], "title": i["title"]} for i in open_issues],
            },
        ).model_dump()

    except CLIError as exc:
        logger.error("CLI error in get_sprint_summary: %s", exc)
        return build_error_response(
            error_type="internal",
            message=f"Failed to get sprint summary: {exc.stderr.strip()}",
            suggestion="Verify the milestone title is correct.",
        )
    except Exception as exc:
        logger.error("Error in get_sprint_summary: %s", exc)
        return handle_tool_error(exc, context="Get sprint summary failed")


async def link_pull_request(params: LinkPullRequestInput) -> dict:
    """Link a pull request to an issue for traceability.

    Adds closing reference to PR body and comments on the issue.

    Args:
        params: Input containing issue and PR numbers.

    Returns:
        ToolSuccess on success.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh_client = GHCLIClient()

        pr_result = await gh_client.run([
            "pr", "view", str(params.pr_number), "--repo", repo,
            "--json", "title,url,body",
        ])
        pr_data = json.loads(pr_result.stdout)
        pr_url = pr_data.get("url", "")
        pr_body = pr_data.get("body", "")

        close_ref = f"Closes #{params.issue_number}"
        if close_ref.lower() not in pr_body.lower():
            new_body = f"{pr_body}\n\n{close_ref}" if pr_body else close_ref
            await gh_client.run([
                "pr", "edit", str(params.pr_number), "--repo", repo,
                "--body", new_body,
            ])

        comment = f"🔗 Linked to PR #{params.pr_number}: {pr_url}"
        await gh_client.run([
            "issue", "comment", str(params.issue_number),
            "--repo", repo, "--body", comment,
        ])

        return ToolSuccess(
            data={
                "issue_number": params.issue_number,
                "pr_number": params.pr_number,
                "pr_url": pr_url,
                "message": f"PR #{params.pr_number} linked to issue #{params.issue_number}.",
            },
        ).model_dump()

    except CLIError as exc:
        logger.error("CLI error in link_pull_request: %s", exc)
        return build_error_response(
            error_type="internal",
            message=f"Failed to link PR: {exc.stderr.strip()}",
            suggestion="Verify both issue and PR numbers exist.",
        )
    except Exception as exc:
        logger.error("Error in link_pull_request: %s", exc)
        return handle_tool_error(exc, context="Link pull request failed")


async def bulk_assign(params: BulkAssignInput) -> dict:
    """Assign multiple issues to users and/or milestone at once.

    Args:
        params: Input containing issue numbers, optional assignees and milestone.

    Returns:
        ToolSuccess with results per issue.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh_client = GHCLIClient()

        if not params.assignees and not params.milestone:
            return build_error_response(
                error_type="validation",
                message="Provide at least assignees or milestone to set.",
                suggestion="Include assignees list and/or milestone title.",
            )

        results: list[dict] = []

        for issue_num in params.issue_numbers:
            try:
                args = ["issue", "edit", str(issue_num), "--repo", repo]

                if params.assignees:
                    for assignee in params.assignees:
                        args.extend(["--add-assignee", assignee])

                if params.milestone:
                    args.extend(["--milestone", params.milestone])

                await gh_client.run(args)
                results.append({"issue": issue_num, "status": "updated"})
            except CLIError as exc:
                results.append({"issue": issue_num, "status": "failed", "error": exc.stderr.strip()})

        updated_count = sum(1 for r in results if r["status"] == "updated")

        return ToolSuccess(
            data={
                "results": results,
                "total": len(params.issue_numbers),
                "updated": updated_count,
                "message": f"Updated {updated_count}/{len(params.issue_numbers)} issues.",
            },
        ).model_dump()

    except Exception as exc:
        logger.error("Error in bulk_assign: %s", exc)
        return handle_tool_error(exc, context="Bulk assign failed")
