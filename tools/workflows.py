"""MCP workflow tools for high-level project management operations.

These tools chain multiple operations into single calls for
efficient project management workflows.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from auth import resolve_token
from clients.gh_cli_client import CLIError, GHCLIClient
from config import get_settings
from error_handling import build_error_response, handle_tool_error
from models.responses import ToolSuccess

logger = logging.getLogger(__name__)


class CompleteIssueInput(BaseModel):
    """Input for complete_issue workflow."""
    issue_number: int = Field(description="Issue number to mark as complete")
    summary: Optional[str] = Field(default=None, description="Optional completion summary comment")


class DailyStandupInput(BaseModel):
    """Input for daily_standup workflow."""
    username: Optional[str] = Field(default=None, description="Filter by username (default: all team)")


class SprintReviewInput(BaseModel):
    """Input for sprint_review workflow."""
    milestone_title: str = Field(description="Sprint milestone to review")


class TriageNewIssuesInput(BaseModel):
    """Input for triage_new_issues workflow."""
    pass


class EscalateOverdueInput(BaseModel):
    """Input for escalate_overdue workflow."""
    pass


class HandoffIssueInput(BaseModel):
    """Input for handoff_issue workflow."""
    issue_number: int = Field(description="Issue to hand off")
    from_user: str = Field(description="Current assignee username")
    to_user: str = Field(description="New assignee username")
    context: Optional[str] = Field(default=None, description="Handoff context/notes")


class CreateEpicInput(BaseModel):
    """Input for create_epic workflow."""
    title: str = Field(description="Epic title")
    body: str = Field(description="Epic description")
    sub_tasks: list[str] = Field(
        max_length=20,
        description="List of sub-task titles to create (maximum 20)",
    )
    milestone: Optional[str] = Field(default=None, description="Milestone to assign")
    assignee: Optional[str] = Field(default=None, description="Default assignee for all")
    labels: Optional[list[str]] = Field(default=None, description="Labels for all issues")
    status: Optional[str] = Field(
        default="📢 Proposal",
        description="Project board status for created items (default: 📢 Proposal)",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Project board priority (Urgent, Important, Not urgent, Not important)",
    )


class CloseSprintInput(BaseModel):
    """Input for close_sprint workflow."""
    milestone_title: str = Field(description="Sprint milestone to close")
    next_milestone: Optional[str] = Field(default=None, description="Next sprint to move pending issues to")


class BlockedReportInput(BaseModel):
    """Input for blocked_report workflow."""
    pass


async def complete_issue(params: CompleteIssueInput) -> dict:
    """Complete an issue: comment summary, close it, project auto-moves to Done.

    Args:
        params: Issue number and optional summary.
    Returns:
        ToolSuccess with completion details.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        comment = params.summary or "✅ Issue completed."
        await gh.run(["issue", "comment", str(params.issue_number), "--repo", repo, "--body", comment])
        await gh.run(["issue", "close", str(params.issue_number), "--repo", repo, "--reason", "completed"])

        return ToolSuccess(data={
            "issue_number": params.issue_number, "status": "completed",
            "message": f"Issue #{params.issue_number} completed and closed.",
        }).model_dump()
    except CLIError as exc:
        return build_error_response("internal", f"Complete failed: {exc.stderr.strip()}", "Verify issue exists.")
    except Exception as exc:
        return handle_tool_error(exc, context="Complete issue workflow failed")


async def daily_standup(params: DailyStandupInput) -> dict:
    """Generate daily standup: done recently, in progress, blocked.

    Args:
        params: Optional username filter.
    Returns:
        ToolSuccess with standup data.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        closed_args = ["issue", "list", "--repo", repo, "--state", "closed",
                       "--limit", "20", "--json", "number,title,assignees,closedAt"]
        if params.username:
            closed_args.extend(["--assignee", params.username])
        closed_result = await gh.run(closed_args)
        all_closed = json.loads(closed_result.stdout)

        now = datetime.now(timezone.utc)
        recent_done = []
        for issue in all_closed:
            if issue.get("closedAt"):
                closed_at = datetime.fromisoformat(issue["closedAt"].replace("Z", "+00:00"))
                if (now - closed_at).total_seconds() < 172800:
                    recent_done.append({"number": issue["number"], "title": issue["title"],
                                        "assignees": [a["login"] for a in issue.get("assignees", [])]})

        open_args = ["issue", "list", "--repo", repo, "--state", "open",
                     "--limit", "50", "--json", "number,title,assignees,labels"]
        if params.username:
            open_args.extend(["--assignee", params.username])
        open_result = await gh.run(open_args)
        all_open = json.loads(open_result.stdout)

        in_progress = [{"number": i["number"], "title": i["title"],
                        "assignees": [a["login"] for a in i.get("assignees", [])]}
                       for i in all_open if i.get("assignees")]

        blocked = [{"number": i["number"], "title": i["title"]}
                   for i in all_open
                   if any("pending" in l.get("name", "").lower() or "blocked" in l.get("name", "").lower()
                          for l in i.get("labels", []))]

        return ToolSuccess(data={
            "date": now.strftime("%Y-%m-%d"),
            "done_recently": recent_done, "done_count": len(recent_done),
            "in_progress": in_progress[:15], "in_progress_count": len(in_progress),
            "blocked": blocked, "blocked_count": len(blocked),
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Daily standup failed")


async def sprint_review(params: SprintReviewInput) -> dict:
    """Sprint review: velocity, per-person stats, pending list.

    Args:
        params: Milestone title.
    Returns:
        ToolSuccess with review data.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        result = await gh.run(["issue", "list", "--repo", repo, "--milestone", params.milestone_title,
                               "--state", "all", "--limit", "100", "--json", "number,title,state,assignees,labels"])
        issues = json.loads(result.stdout)

        completed = [i for i in issues if i.get("state") == "CLOSED"]
        pending = [i for i in issues if i.get("state") == "OPEN"]

        person_stats: dict[str, dict] = {}
        for issue in issues:
            for assignee in issue.get("assignees", []):
                login = assignee.get("login", "unassigned")
                if login not in person_stats:
                    person_stats[login] = {"completed": 0, "pending": 0}
                if issue.get("state") == "CLOSED":
                    person_stats[login]["completed"] += 1
                else:
                    person_stats[login]["pending"] += 1

        total = len(issues)
        progress = round(len(completed) / max(total, 1) * 100)

        return ToolSuccess(data={
            "milestone": params.milestone_title, "total_issues": total,
            "completed": len(completed), "pending": len(pending),
            "progress_pct": progress, "velocity": len(completed),
            "per_person": person_stats,
            "pending_issues": [{"number": i["number"], "title": i["title"]} for i in pending],
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Sprint review failed")


async def triage_new_issues() -> dict:
    """Find untriaged issues (no milestone, no assignee, no labels).

    Returns:
        ToolSuccess with untriaged issues.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        result = await gh.run(["issue", "list", "--repo", repo, "--state", "open",
                               "--limit", "100", "--json", "number,title,labels,milestone,assignees"])
        issues = json.loads(result.stdout)

        untriaged = []
        for issue in issues:
            problems = []
            if not issue.get("milestone"):
                problems.append("no_milestone")
            if not issue.get("assignees"):
                problems.append("no_assignee")
            if not issue.get("labels"):
                problems.append("no_labels")
            if problems:
                untriaged.append({"number": issue["number"], "title": issue["title"], "problems": problems})

        return ToolSuccess(data={
            "untriaged_count": len(untriaged), "issues": untriaged[:30],
            "message": f"Found {len(untriaged)} issues needing triage.",
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Triage failed")


async def escalate_overdue() -> dict:
    """Find issues past their due date that are still open.

    Returns:
        ToolSuccess with overdue issues.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        ms_result = await gh.run(["api", f"repos/{repo}/milestones?state=open&per_page=50"])
        milestones = json.loads(ms_result.stdout)

        now = datetime.now(timezone.utc)
        overdue: list[dict] = []

        for ms in milestones:
            due_on = ms.get("due_on")
            if not due_on:
                continue
            due_date = datetime.fromisoformat(due_on.replace("Z", "+00:00"))
            if due_date < now and ms.get("open_issues", 0) > 0:
                issues_result = await gh.run(["issue", "list", "--repo", repo,
                                              "--milestone", ms["title"], "--state", "open",
                                              "--limit", "50", "--json", "number,title,assignees"])
                issues = json.loads(issues_result.stdout)
                days = (now - due_date).days
                for issue in issues:
                    overdue.append({
                        "number": issue["number"], "title": issue["title"],
                        "milestone": ms["title"], "days_overdue": days,
                        "assignees": [a["login"] for a in issue.get("assignees", [])],
                    })

        return ToolSuccess(data={
            "overdue_count": len(overdue), "issues": overdue,
            "message": f"Found {len(overdue)} overdue issues.",
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Escalate overdue failed")


async def handoff_issue(params: HandoffIssueInput) -> dict:
    """Hand off issue from one person to another with context comment.

    Args:
        params: Issue, from/to users, context.
    Returns:
        ToolSuccess on success.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        await gh.run(["issue", "edit", str(params.issue_number), "--repo", repo,
                      "--remove-assignee", params.from_user, "--add-assignee", params.to_user])

        context = params.context or "No additional context."
        comment = f"🔄 **Handoff:** @{params.from_user} → @{params.to_user}\n\n**Context:** {context}"
        await gh.run(["issue", "comment", str(params.issue_number), "--repo", repo, "--body", comment])

        return ToolSuccess(data={
            "issue_number": params.issue_number, "from": params.from_user, "to": params.to_user,
            "message": f"Issue #{params.issue_number} handed off to @{params.to_user}.",
        }).model_dump()
    except CLIError as exc:
        return build_error_response("internal", f"Handoff failed: {exc.stderr.strip()}", "Verify usernames.")
    except Exception as exc:
        return handle_tool_error(exc, context="Handoff failed")


# ── Project Board Field Defaults ─────────────────────────────────────────────

# Mapping of status names to project field option IDs.
_STATUS_OPTIONS: dict[str, str] = {
    "📢 Proposal": "f75ad846",
    "📌 To Do": "47fc9ee4",
    "🛠 In Progress": "98236657",
    "⏸ Pending": "6a7e9d0d",
    "✅ Done": "950b2fa1",
    "🗑️ Trash": "cb0f478a",
}

_PRIORITY_OPTIONS: dict[str, str] = {
    "Urgent": "631f13e6",
    "Important": "97ef5528",
    "Not urgent": "1d80676c",
    "Not important": "aa28dbfd",
}

# Project field IDs (configured via target).
_PROJECT_ID = "PVT_kwDOCg8zFs4A2iZ_"
_STATUS_FIELD_ID = "PVTSSF_lADOCg8zFs4A2iZ_zgr0_v4"
_PRIORITY_FIELD_ID = "PVTSSF_lADOCg8zFs4A2iZ_zgr0_wk"


async def _set_project_item_defaults(
    gh: GHCLIClient,
    item_id: str,
    *,
    status: str | None = "📢 Proposal",
    priority: str | None = None,
) -> None:
    """Set default project board fields on a newly-added item.

    Args:
        gh: Authenticated GH CLI client.
        item_id: Project item ID returned by 'gh project item-add --format json'.
        status: Status name to set (default: 📢 Proposal).
        priority: Priority name to set (optional).
    """
    if status and status in _STATUS_OPTIONS:
        try:
            await gh.run([
                "project", "item-edit",
                "--project-id", _PROJECT_ID,
                "--id", item_id,
                "--field-id", _STATUS_FIELD_ID,
                "--single-select-option-id", _STATUS_OPTIONS[status],
            ])
        except CLIError as exc:
            logger.warning("Failed to set status on item %s: %s", item_id, exc.stderr)

    if priority and priority in _PRIORITY_OPTIONS:
        try:
            await gh.run([
                "project", "item-edit",
                "--project-id", _PROJECT_ID,
                "--id", item_id,
                "--field-id", _PRIORITY_FIELD_ID,
                "--single-select-option-id", _PRIORITY_OPTIONS[priority],
            ])
        except CLIError as exc:
            logger.warning("Failed to set priority on item %s: %s", item_id, exc.stderr)


async def create_epic(params: CreateEpicInput) -> dict:
    """Create epic (parent) with sub-issues linked in one call.

    Args:
        params: Epic details and sub-task titles.
    Returns:
        ToolSuccess with created issue numbers.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        parent_args = ["issue", "create", "--repo", repo, "--title", params.title, "--body", params.body]
        if params.milestone:
            parent_args.extend(["--milestone", params.milestone])
        if params.assignee:
            parent_args.extend(["--assignee", params.assignee])
        if params.labels:
            for label in params.labels:
                parent_args.extend(["--label", label])

        parent_result = await gh.run(parent_args)
        parent_url = parent_result.stdout.strip()
        parent_number = int(parent_url.rstrip("/").split("/")[-1])

        parent_add_result = await gh.run([
            "project",
            "item-add",
            str(settings.project_number),
            "--owner",
            settings.org_name,
            "--url",
            parent_url,
            "--format",
            "json",
        ])
        parent_item_data = json.loads(parent_add_result.stdout.strip())
        parent_item_id = parent_item_data.get("id", "")

        if parent_item_id:
            await _set_project_item_defaults(gh, parent_item_id, params.status, params.priority)

        # Set project board fields on the parent epic.
        try:
            parent_item_result = await gh.run([
                "project", "item-list", str(settings.project_number),
                "--owner", settings.org_name,
                "--format", "json", "--limit", "200",
            ])
            parent_items = json.loads(parent_item_result.stdout)
            parent_item_id = None
            for item in parent_items.get("items", []):
                if item.get("content", {}).get("number") == parent_number:
                    parent_item_id = item.get("id")
                    break
            if parent_item_id:
                await _set_project_item_defaults(
                    gh, parent_item_id,
                    status=params.status,
                    priority=params.priority,
                )
        except (CLIError, json.JSONDecodeError) as exc:
            logger.warning("Could not set project fields on epic: %s", exc)

        parent_node = await gh.run(["api", f"repos/{repo}/issues/{parent_number}", "--jq", ".node_id"])
        parent_node_id = parent_node.stdout.strip()

        sub_issues: list[dict] = []
        for task_title in params.sub_tasks:
            sub_args = ["issue", "create", "--repo", repo, "--title", task_title,
                        "--body", f"Parent: #{parent_number}"]
            if params.milestone:
                sub_args.extend(["--milestone", params.milestone])
            if params.assignee:
                sub_args.extend(["--assignee", params.assignee])
            if params.labels:
                for label in params.labels:
                    sub_args.extend(["--label", label])

            sub_result = await gh.run(sub_args)
            sub_url = sub_result.stdout.strip()
            sub_number = int(sub_url.rstrip("/").split("/")[-1])

            sub_add_result = await gh.run([
                "project",
                "item-add",
                str(settings.project_number),
                "--owner",
                settings.org_name,
                "--url",
                sub_url,
                "--format",
                "json",
            ])
            sub_item_data = json.loads(sub_add_result.stdout.strip())
            sub_item_id = sub_item_data.get("id", "")

            if sub_item_id:
                await _set_project_item_defaults(gh, sub_item_id, params.status, params.priority)

            # Set project board fields on each sub-issue.
            try:
                sub_items_result = await gh.run([
                    "project", "item-list", str(settings.project_number),
                    "--owner", settings.org_name,
                    "--format", "json", "--limit", "200",
                ])
                sub_items_data = json.loads(sub_items_result.stdout)
                sub_item_id = None
                for item in sub_items_data.get("items", []):
                    if item.get("content", {}).get("number") == sub_number:
                        sub_item_id = item.get("id")
                        break
                if sub_item_id:
                    await _set_project_item_defaults(
                        gh, sub_item_id,
                        status=params.status,
                        priority=params.priority,
                    )
            except (CLIError, json.JSONDecodeError) as exc:
                logger.warning("Could not set project fields on sub-issue #%d: %s", sub_number, exc)

            sub_node = await gh.run(["api", f"repos/{repo}/issues/{sub_number}", "--jq", ".node_id"])
            sub_node_id = sub_node.stdout.strip()
            if parent_node_id and sub_node_id:
                try:
                    mutation = """
                    mutation AddSubIssue($issueId: ID!, $subIssueId: ID!) {
                      addSubIssue(input: {issueId: $issueId, subIssueId: $subIssueId}) {
                        issue { number }
                      }
                    }
                    """
                    await gh.api_graphql(
                        mutation,
                        {"issueId": parent_node_id, "subIssueId": sub_node_id},
                    )
                except Exception:
                    pass
            sub_issues.append({"number": sub_number, "title": task_title})

        return ToolSuccess(data={
            "parent_issue": parent_number, "parent_url": parent_url,
            "sub_issues": sub_issues, "sub_issues_count": len(sub_issues),
            "message": f"Epic #{parent_number} created with {len(sub_issues)} sub-tasks.",
        }).model_dump()
    except CLIError as exc:
        return build_error_response("internal", f"Create epic failed: {exc.stderr.strip()}", "Check inputs.")
    except Exception as exc:
        return handle_tool_error(exc, context="Create epic failed")


async def close_sprint(params: CloseSprintInput) -> dict:
    """Close sprint: close milestone, move pending to next, generate summary.

    Args:
        params: Sprint to close, optional next sprint.
    Returns:
        ToolSuccess with closure details.
    """
    try:
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        issues_result = await gh.run(["issue", "list", "--repo", repo, "--milestone", params.milestone_title,
                                      "--state", "all", "--limit", "100", "--json", "number,title,state"])
        issues = json.loads(issues_result.stdout)

        completed = [i for i in issues if i.get("state") == "CLOSED"]
        pending = [i for i in issues if i.get("state") == "OPEN"]

        moved: list[dict] = []
        if params.next_milestone and pending:
            for issue in pending:
                try:
                    await gh.run(["issue", "edit", str(issue["number"]), "--repo", repo,
                                  "--milestone", params.next_milestone])
                    moved.append({"number": issue["number"], "title": issue["title"]})
                except CLIError:
                    pass

        ms_result = await gh.run(["api", f"repos/{repo}/milestones?state=open&per_page=50"])
        for ms in json.loads(ms_result.stdout):
            if ms.get("title") == params.milestone_title:
                await gh.run(["api", f"repos/{repo}/milestones/{ms['number']}",
                              "--method", "PATCH", "-f", "state=closed"])
                break

        progress = round(len(completed) / max(len(issues), 1) * 100)
        return ToolSuccess(data={
            "milestone": params.milestone_title, "total": len(issues),
            "completed": len(completed), "pending_moved": len(moved),
            "moved_to": params.next_milestone, "completion_pct": progress,
            "moved_issues": moved,
            "message": f"Sprint closed. {len(completed)}/{len(issues)} done ({progress}%). {len(moved)} moved.",
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Close sprint failed")


async def blocked_report() -> dict:
    """Report blocked/pending issues with dependency info.

    Returns:
        ToolSuccess with blocked issues.
    """
    try:
        import re
        await resolve_token()
        settings = get_settings()
        repo = f"{settings.org_name}/{settings.repo_name}"
        gh = GHCLIClient()

        result = await gh.run(["issue", "list", "--repo", repo, "--state", "open",
                               "--limit", "100", "--json", "number,title,body,assignees,labels,milestone"])
        issues = json.loads(result.stdout)

        blocked: list[dict] = []
        for issue in issues:
            body = issue.get("body", "") or ""
            labels = [l.get("name", "") for l in issue.get("labels", [])]
            is_blocked = (any("blocked" in l.lower() or "pending" in l.lower() for l in labels)
                          or "depends on" in body.lower() or "blocked by" in body.lower())
            if is_blocked:
                dep = None
                match = re.search(r"(?:depends on|blocked by) #(\d+)", body, re.IGNORECASE)
                if match:
                    dep = int(match.group(1))
                blocked.append({
                    "number": issue["number"], "title": issue["title"],
                    "assignees": [a["login"] for a in issue.get("assignees", [])],
                    "milestone": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
                    "dependency": dep,
                })

        return ToolSuccess(data={
            "blocked_count": len(blocked), "issues": blocked,
            "message": f"Found {len(blocked)} blocked/pending issues.",
        }).model_dump()
    except Exception as exc:
        return handle_tool_error(exc, context="Blocked report failed")
