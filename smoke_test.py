"""Smoke test verification script for the GitHub Project Management MCP Server.

Validates token validity, scopes, project access, and item listing
in sequence. Reports pass/fail per step with remediation suggestions.
Continues all steps regardless of failures and reports a summary.

Exits 0 if all steps pass, non-zero if any fail.

Security: The token value is NEVER printed, logged, or included in any output.

Usage:
    python -m app.mcp.github_project.smoke_test
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass

import httpx

from auth import REQUIRED_SCOPES, resolve_token
from config import get_settings

logger = logging.getLogger("mcp.github_project.smoke_test")

_GITHUB_API_URL = "https://api.github.com"
_GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

_DISCOVER_PROJECT_QUERY = """
query DiscoverProject($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      title
    }
  }
}
""".strip()

_LIST_IN_PROGRESS_QUERY = """
query ListInProgressItems($org: String!, $number: Int!, $first: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      items(first: $first) {
        nodes {
          content {
            ... on Issue {
              number
              title
            }
            ... on DraftIssue {
              title
            }
            __typename
          }
          fieldValues(first: 10) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2SingleSelectField {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
""".strip()


@dataclass
class StepResult:
    """Result of a single smoke test step."""

    name: str
    passed: bool
    message: str
    suggestion: str | None = None


def _print_step_result(step_number: int, result: StepResult) -> None:
    """Print a formatted step result to stdout.

    Args:
        step_number: The step number (1-based).
        result: The StepResult to display.
    """
    tag = "[PASS]" if result.passed else "[FAIL]"
    print(f"  {tag} Step {step_number}: {result.name}")
    print(f"        {result.message}")
    if result.suggestion and not result.passed:
        print(f"        Suggestion: {result.suggestion}")


async def _graphql_request(
    token: str, query: str, variables: dict, timeout: float
) -> dict:
    """Execute a GraphQL request against the GitHub API.

    Args:
        token: GitHub token for authorization.
        query: GraphQL query string.
        variables: Query variables.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response body.

    Raises:
        httpx.TimeoutException: If request exceeds timeout.
        httpx.HTTPError: On network errors.
        ValueError: On non-200 status or GraphQL errors.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            _GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code == 401:
        raise ValueError("Authentication failed (HTTP 401)")
    if response.status_code == 403:
        raise ValueError("Access denied (HTTP 403) — insufficient permissions")
    if response.status_code != 200:
        raise ValueError(f"Unexpected HTTP status: {response.status_code}")

    body = response.json()
    if "errors" in body:
        error_msg = body["errors"][0].get("message", "Unknown GraphQL error")
        raise ValueError(f"GraphQL error: {error_msg}")

    return body


async def check_token_validity(token: str) -> StepResult:
    """Verify token validity by querying the GitHub authenticated user endpoint.

    Args:
        token: The resolved GitHub token.

    Returns:
        StepResult indicating pass or fail with cause and remediation.
    """
    settings = get_settings()
    logger.debug("Checking token validity against %s/user", _GITHUB_API_URL)

    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.get(
                f"{_GITHUB_API_URL}/user",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.TimeoutException:
        return StepResult(
            name="Token Validity",
            passed=False,
            message="Request timed out after 10 seconds.",
            suggestion="Check your network connection and retry.",
        )
    except httpx.HTTPError as exc:
        return StepResult(
            name="Token Validity",
            passed=False,
            message=f"HTTP error: {type(exc).__name__}",
            suggestion="Check your network connection and try again.",
        )

    if response.status_code == 401:
        return StepResult(
            name="Token Validity",
            passed=False,
            message="Token is invalid or expired (HTTP 401).",
            suggestion=(
                "Generate a new personal access token with required scopes: "
                "repo, project, read:org."
            ),
        )

    if response.status_code != 200:
        return StepResult(
            name="Token Validity",
            passed=False,
            message=f"Unexpected response status: {response.status_code}.",
            suggestion="Verify your token and network access to api.github.com.",
        )

    return StepResult(
        name="Token Validity",
        passed=True,
        message="Token is valid. Authenticated successfully.",
    )


async def check_scopes(token: str) -> StepResult:
    """Confirm the token has repo, project, and read:org scopes.

    Args:
        token: The resolved GitHub token.

    Returns:
        StepResult indicating pass or fail with missing scopes listed.
    """
    settings = get_settings()
    logger.debug("Verifying token scopes against %s", _GITHUB_API_URL)

    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.get(
                _GITHUB_API_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.TimeoutException:
        return StepResult(
            name="Scope Verification",
            passed=False,
            message="Request timed out after 10 seconds.",
            suggestion="Check your network connection and retry.",
        )
    except httpx.HTTPError as exc:
        return StepResult(
            name="Scope Verification",
            passed=False,
            message=f"HTTP error: {type(exc).__name__}",
            suggestion="Check your network connection and try again.",
        )

    if response.status_code == 401:
        return StepResult(
            name="Scope Verification",
            passed=False,
            message="Token is invalid or expired (HTTP 401).",
            suggestion="Generate a new token with scopes: repo, project, read:org.",
        )

    scopes_header = response.headers.get("X-OAuth-Scopes", "")
    granted_scopes = frozenset(
        scope.strip() for scope in scopes_header.split(",") if scope.strip()
    )

    missing_scopes = REQUIRED_SCOPES - granted_scopes
    if missing_scopes:
        return StepResult(
            name="Scope Verification",
            passed=False,
            message=f"Missing scopes: {', '.join(sorted(missing_scopes))}.",
            suggestion=(
                f"Regenerate the token with all required scopes: "
                f"{', '.join(sorted(REQUIRED_SCOPES))}."
            ),
        )

    return StepResult(
        name="Scope Verification",
        passed=True,
        message=f"All required scopes present: {', '.join(sorted(REQUIRED_SCOPES))}.",
    )


async def check_project_access(token: str) -> StepResult:
    """Query the GitHub Project and confirm it returns project metadata.

    Args:
        token: The resolved GitHub token.

    Returns:
        StepResult indicating pass or fail with cause and remediation.
    """
    settings = get_settings()
    logger.debug(
        "Querying project #%d in org '%s'",
        settings.project_number,
        settings.org_name,
    )

    try:
        body = await _graphql_request(
            token=token,
            query=_DISCOVER_PROJECT_QUERY,
            variables={
                "org": settings.org_name,
                "number": settings.project_number,
            },
            timeout=settings.timeout_seconds,
        )
    except httpx.TimeoutException:
        return StepResult(
            name="Project Access",
            passed=False,
            message="Request timed out after 10 seconds.",
            suggestion="Check your network connection and retry.",
        )
    except httpx.HTTPError as exc:
        return StepResult(
            name="Project Access",
            passed=False,
            message=f"HTTP error: {type(exc).__name__}",
            suggestion="Check your network connection and try again.",
        )
    except ValueError as exc:
        return StepResult(
            name="Project Access",
            passed=False,
            message=str(exc),
            suggestion=(
                f"Verify that org '{settings.org_name}' has project "
                f"#{settings.project_number} and the token has access."
            ),
        )

    data = body.get("data", {})
    org = data.get("organization")
    if not org:
        return StepResult(
            name="Project Access",
            passed=False,
            message=f"Organization '{settings.org_name}' not found or inaccessible.",
            suggestion=(
                f"Confirm the org name '{settings.org_name}' is correct and "
                "the token has read:org scope."
            ),
        )

    project = org.get("projectV2")
    if not project:
        return StepResult(
            name="Project Access",
            passed=False,
            message=(
                f"Project #{settings.project_number} not found in "
                f"org '{settings.org_name}'."
            ),
            suggestion=(
                f"Verify that project #{settings.project_number} exists in "
                f"'{settings.org_name}' and the token has project scope."
            ),
        )

    project_id = project.get("id", "unknown")
    project_title = project.get("title", "Untitled")
    return StepResult(
        name="Project Access",
        passed=True,
        message=(
            f"Project #{settings.project_number} accessible. "
            f"Title: '{project_title}', ID: {project_id}."
        ),
    )


async def check_list_in_progress(token: str) -> StepResult:
    """List Project Items with Status 'In Progress' and display title/number.

    Args:
        token: The resolved GitHub token.

    Returns:
        StepResult indicating pass or fail with item details in the message.
    """
    settings = get_settings()
    max_items = 50
    logger.debug(
        "Listing 'In Progress' items from project #%d (max %d)",
        settings.project_number,
        max_items,
    )

    try:
        body = await _graphql_request(
            token=token,
            query=_LIST_IN_PROGRESS_QUERY,
            variables={
                "org": settings.org_name,
                "number": settings.project_number,
                "first": max_items,
            },
            timeout=settings.timeout_seconds,
        )
    except httpx.TimeoutException:
        return StepResult(
            name="List In Progress Items",
            passed=False,
            message="Request timed out after 10 seconds.",
            suggestion="Check your network connection and retry.",
        )
    except httpx.HTTPError as exc:
        return StepResult(
            name="List In Progress Items",
            passed=False,
            message=f"HTTP error: {type(exc).__name__}",
            suggestion="Check your network connection and try again.",
        )
    except ValueError as exc:
        return StepResult(
            name="List In Progress Items",
            passed=False,
            message=str(exc),
            suggestion="Check project access and token permissions.",
        )

    data = body.get("data", {})
    items_nodes = (
        data.get("organization", {})
        .get("projectV2", {})
        .get("items", {})
        .get("nodes", [])
    )

    in_progress_items: list[dict[str, str | int | None]] = []
    for item in items_nodes:
        status = _extract_status(item)
        if status == "In Progress":
            content = item.get("content") or {}
            title = content.get("title", "Untitled")
            number = content.get("number")
            in_progress_items.append({"title": title, "number": number})

    if not in_progress_items:
        return StepResult(
            name="List In Progress Items",
            passed=True,
            message="No items with Status 'In Progress' found.",
        )

    lines = [f"Found {len(in_progress_items)} item(s) In Progress:"]
    for item in in_progress_items:
        number_str = f"#{item['number']}" if item["number"] else "(draft)"
        lines.append(f"    - {number_str} {item['title']}")

    return StepResult(
        name="List In Progress Items",
        passed=True,
        message="\n".join(lines),
    )


def _extract_status(item: dict) -> str | None:
    """Extract the Status field value from a project item.

    Args:
        item: A project item node from the GraphQL response.

    Returns:
        The status string or None if not found.
    """
    field_values = item.get("fieldValues", {}).get("nodes", [])
    for field_value in field_values:
        field_info = field_value.get("field") or {}
        if field_info.get("name") == "Status":
            return field_value.get("name")
    return None


def _is_token_available() -> bool:
    """Check if a token environment variable is set and non-empty.

    Returns:
        True if GITHUB_TOKEN or GH_TOKEN is set and non-empty.
    """
    return bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))


async def run_smoke_test() -> int:
    """Run all smoke test steps and return exit code.

    Programmatic entry point for tests. Resolves the token, executes all
    verification steps, and returns 0 on success, 1 on any failure.

    Returns:
        0 if all steps pass, 1 if any step fails.
    """
    return await main()


async def main() -> int:
    """Entry point for the smoke test.

    Checks for token availability, resolves it, runs all verification
    steps, and reports results. Returns exit code 0 on success, 1 on
    any failure.

    Returns:
        0 if all steps pass, 1 if any step fails.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    print("=" * 60)
    print("  GitHub Project MCP — Smoke Test")
    print("=" * 60)
    print()

    # Check token env var immediately — exit if not set
    if not _is_token_available():
        print(
            "[FAIL] Token environment variable is not set or empty.\n"
            "       Set GITHUB_TOKEN or GH_TOKEN before running the smoke test."
        )
        logger.error("No token environment variable found. Exiting.")
        return 1

    # Resolve token (uses env vars checked above)
    token = await resolve_token()

    steps = [
        check_token_validity,
        check_scopes,
        check_project_access,
        check_list_in_progress,
    ]

    results: list[StepResult] = []
    for i, step_fn in enumerate(steps, start=1):
        result = await step_fn(token)
        results.append(result)
        _print_step_result(i, result)
        print()

    # Summary
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)

    print("-" * 60)
    if passed_count == total:
        print(f"  All {total} steps passed. The MCP server is ready.")
    else:
        failed_count = total - passed_count
        print(f"  {passed_count}/{total} steps passed, {failed_count} failed.")
        print()
        print("  Failed steps:")
        for r in results:
            if not r.passed:
                print(f"    - {r.name}: {r.message}")
    print("-" * 60)

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
