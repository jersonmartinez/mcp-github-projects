"""MCP tool for creating a new GitHub Project V2 item.

Exposes the `create_project_item` tool function that orchestrates:
1. Validate title/body length constraints
2. Create an issue via IssueService (gh issue create)
3. Add the issue to the project via ProjectService.add_item()
4. Set optional fields (status, priority, milestone, due_date) via
   ProjectService.update_field()
5. Return issue number, URL, and item node ID in a ToolSuccess envelope

Handles partial failures: if the issue is created but a subsequent
operation fails, returns an error with the created issue number and
which operation failed. If the API is unreachable or rate-limited
before issue creation, returns an error without creating anything.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from auth import resolve_token
from clients.cache_manager import CacheManager
from clients.gh_cli_client import GHCLIClient
from clients.graphql_client import GraphQLClient
from error_handling import build_error_response, handle_tool_error
from exceptions import (
    AuthenticationError,
    GraphQLError,
    RateLimitError,
    ValidationError,
)
from models.responses import ToolSuccess
from services.discovery_service import DiscoveryService
from services.issue_service import IssueService
from services.project_service import ProjectService

logger = logging.getLogger(__name__)


class CreateProjectItemInput(BaseModel):
    """Input schema for the create_project_item tool.

    Attributes:
        title: Issue title (1â€“256 characters).
        body: Issue body content (0â€“65536 characters).
        status: Optional Status field value to set on the project item.
        priority: Optional Priority field value to set on the project item.
        milestone: Optional milestone title for the issue.
        due_date: Optional due date in ISO 8601 format (YYYY-MM-DD).
        assignees: Optional list of GitHub usernames to assign.
        labels: Optional list of label names to apply.
    """

    title: str = Field(
        min_length=1,
        max_length=256,
        description="Issue title (1-256 characters)",
    )
    body: str = Field(
        default="",
        max_length=65536,
        description="Issue body content (0-65536 characters)",
    )
    status: str | None = Field(
        default=None, description="Status field value for the project item"
    )
    priority: str | None = Field(
        default=None, description="Priority field value for the project item"
    )
    milestone: str | None = Field(
        default=None, description="Milestone title for the issue"
    )
    due_date: str | None = Field(
        default=None, description="Due date in ISO 8601 format (YYYY-MM-DD)"
    )
    assignees: list[str] | None = Field(
        default=None, description="GitHub usernames to assign"
    )
    labels: list[str] | None = Field(
        default=None, description="Label names to apply"
    )


async def create_project_item(
    title: str,
    body: str = "",
    status: str | None = None,
    priority: str | None = None,
    milestone: str | None = None,
    due_date: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
) -> dict:
    """Create a new issue and add it to the GitHub Project board.

    Orchestrates the full creation flow: validates inputs, creates the
    issue via `gh issue create`, adds it to the project, and sets any
    optional fields (status, priority, due_date). Handles partial
    failures by reporting the created issue number alongside the error.

    Args:
        title: Issue title (1-256 characters).
        body: Issue body content (0-65536 characters).
        status: Optional Status field value to set on the project item.
        priority: Optional Priority field value to set on the project item.
        milestone: Optional milestone title for the issue.
        due_date: Optional due date in ISO 8601 format (YYYY-MM-DD).
        assignees: Optional list of GitHub usernames to assign.
        labels: Optional list of label names to apply.

    Returns:
        A dict conforming to ToolSuccess (ok=True, data with
        issue_number, issue_url, item_node_id) on success, or ToolError
        (ok=False, error_type, message, suggestion) on failure.
    """
    # â”€â”€ Step 1: Validate inputs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    title_len = len(title)
    if title_len < 1 or title_len > 256:
        return build_error_response(
            error_type="validation",
            message=(
                f"Title must be between 1 and 256 characters, "
                f"got {title_len}."
            ),
            suggestion="Provide a title with 1 to 256 characters.",
        )

    body_len = len(body)
    if body_len > 65536:
        return build_error_response(
            error_type="validation",
            message=(
                f"Body must be at most 65536 characters, "
                f"got {body_len}."
            ),
            suggestion="Shorten the body to 65536 characters or fewer.",
        )

    # â”€â”€ Step 2: Resolve token and initialize services â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        token = await resolve_token()
    except AuthenticationError as exc:
        logger.error("Authentication error in create_project_item: %s", exc)
        return handle_tool_error(exc, context="Create project item failed")

    graphql_client = GraphQLClient(token=token)
    cache_manager = CacheManager()
    gh_client = GHCLIClient()
    discovery_service = DiscoveryService(
        graphql_client=graphql_client,
        cache_manager=cache_manager,
    )
    project_service = ProjectService(
        graphql_client=graphql_client,
        gh_client=gh_client,
    )
    issue_service = IssueService(gh_client=gh_client)

    # â”€â”€ Step 3: Discover project metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        metadata = await discovery_service.get_cached_or_discover()
    except (RateLimitError, AuthenticationError, GraphQLError, Exception) as exc:
        logger.error("Discovery failed in create_project_item: %s", exc)
        return handle_tool_error(exc, context="Failed to discover project metadata")

    # â”€â”€ Step 4: Validate optional field values before creating issue â”€â”€â”€â”€â”€â”€
    # Pre-validate status and priority against known options to avoid
    # creating an issue that can't have its fields set.
    if status is not None:
        status_field = metadata.fields.get("Status")
        if status_field and status_field.options:
            valid_status_names = [opt.name for opt in status_field.options]
            if status not in valid_status_names:
                return build_error_response(
                    error_type="validation",
                    message=(
                        f"Invalid status value '{status}'. "
                        f"Valid options: {', '.join(valid_status_names)}"
                    ),
                    suggestion="Use one of the valid Status options listed above.",
                )

    if priority is not None:
        priority_field = metadata.fields.get("Priority")
        if priority_field and priority_field.options:
            valid_priority_names = [opt.name for opt in priority_field.options]
            if priority not in valid_priority_names:
                return build_error_response(
                    error_type="validation",
                    message=(
                        f"Invalid priority value '{priority}'. "
                        f"Valid options: {', '.join(valid_priority_names)}"
                    ),
                    suggestion="Use one of the valid Priority options listed above.",
                )

    # â”€â”€ Step 5: Create the issue â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        created_issue = await issue_service.create(
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
            milestone=milestone,
        )
    except RateLimitError as exc:
        logger.error(
            "Rate limit hit during issue creation: %s", exc
        )
        return ToolError(
            error_type="rate_limit",
            message=str(exc),
            suggestion=(
                f"Rate limit resets at {exc.reset_at}. "
                "Wait until the reset time or use a token with higher limits."
            ),
            request_id=exc.request_id,
        ).model_dump()
    except AuthenticationError as exc:
        logger.error(
            "Authentication error during issue creation: %s", exc
        )
        return ToolError(
            error_type="authentication",
            message=str(exc),
            suggestion=(
                "Verify that GITHUB_TOKEN or GH_TOKEN is set with "
                "repo, project, and read:org scopes."
            ),
            request_id=exc.request_id,
        ).model_dump()
    except Exception as exc:
        logger.error("Failed to create issue: %s", exc)
        return ToolError(
            error_type="internal",
            message=f"Failed to create issue: {exc}",
            suggestion=(
                "Check network connectivity and verify the token has "
                "permission to create issues in the repository."
            ),
            request_id=getattr(exc, "request_id", None),
        ).model_dump()

    issue_number = created_issue.number
    issue_url = created_issue.url

    # â”€â”€ Step 6: Add issue to the project â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        item_node_id = await project_service.add_item(
            metadata=metadata,
            issue_number=issue_number,
        )
    except Exception as exc:
        logger.error(
            "Failed to add issue #%d to project: %s", issue_number, exc
        )
        return ToolError(
            error_type="internal",
            message=(
                f"Issue #{issue_number} was created ({issue_url}) but "
                f"adding it to the project failed: {exc}"
            ),
            suggestion=(
                "The issue exists but is not on the project board. "
                "You can manually add it using discover_ids and retry, "
                "or use `gh project item-add`."
            ),
            request_id=getattr(exc, "request_id", None),
        ).model_dump()

    # â”€â”€ Step 7: Set optional fields on the project item â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    fields_to_set: list[tuple[str, str | float]] = []
    if status is not None:
        fields_to_set.append(("Status", status))
    if priority is not None:
        fields_to_set.append(("Priority", priority))
    if due_date is not None:
        fields_to_set.append(("Due date", due_date))

    for field_name, field_value in fields_to_set:
        try:
            await project_service.update_field(
                metadata=metadata,
                item_id=item_node_id,
                field_name=field_name,
                value=field_value,
            )
        except (ValidationError, GraphQLError, Exception) as exc:
            logger.error(
                "Failed to set field '%s' on issue #%d: %s",
                field_name,
                issue_number,
                exc,
            )
            return ToolError(
                error_type="internal",
                message=(
                    f"Issue #{issue_number} was created ({issue_url}) and "
                    f"added to the project (item ID: {item_node_id}), but "
                    f"setting field '{field_name}' failed: {exc}"
                ),
                suggestion=(
                    "The issue and project item exist. Retry setting the "
                    f"'{field_name}' field using update_project_item_fields "
                    f"with item ID '{item_node_id}'."
                ),
                request_id=getattr(exc, "request_id", None),
            ).model_dump()

    # â”€â”€ Step 8: Return success â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return ToolSuccess(
        data={
            "issue_number": issue_number,
            "issue_url": issue_url,
            "item_node_id": item_node_id,
            "message": (
                f"Issue #{issue_number} created and added to project "
                "successfully."
            ),
        },
    ).model_dump()
