"""Diagnostics tool: server_info (issues #34 and #178).

Returns safe, credential-free server metadata so an MCP client can see the
effective access level, scope lock, and repository write-policy fences without
probing. Mirrors the
``server_info`` tool in mcp-monday-projects (which reports its write policy and
workspace scope); here it reports ``MCP_ACCESS_LEVEL`` and
``GH_PROJECT_SCOPE_LOCK`` plus the configured target and write policy.

No token, header, or secret is ever included in the response.
"""

from __future__ import annotations

import logging
import sys

from pydantic import BaseModel

from core.access import AccessLevel, level_counts, tools_for_level
from core.config import get_settings
from core.error_handling import handle_tool_error
from core.version import VERSION
from models.responses import ToolSuccess

logger = logging.getLogger(__name__)


class ServerInfoInput(BaseModel):
    """Input schema for server_info (no arguments)."""


async def server_info(params: ServerInfoInput) -> dict:
    """Return safe server metadata: access level, scope lock, write-policy fences, and target.

    The response includes:
      - access_level: the effective MCP_ACCESS_LEVEL (read | write | full).
      - access_level_meaning: a one-line gloss of what it exposes.
      - tool_exposure: classified/exposed/hidden counts, including how many
        permanent-delete tools are hidden at this level.
      - scope_lock: whether GH_PROJECT_SCOPE_LOCK confines the server, plus the
        variable name and the target it is (or would be) locked to.
      - write_policy: the effective branch/path fences for governed commits,
        including the exact workflow paths explicitly allowlisted.
      - target: the configured org / repo / project (no credentials).
    """
    try:
        settings = get_settings()
        level = AccessLevel.parse(settings.access_level)

        meaning = {
            AccessLevel.READ: "Only read-only tools are exposed.",
            AccessLevel.WRITE: (
                "Read + write tools (create/update/close/archive); no "
                "permanent-delete tools."
            ),
            AccessLevel.FULL: (
                "All tools, including permanent-delete tools (each requires "
                "confirm=true)."
            ),
        }[level]

        counts = level_counts(level)
        registered_names: list[str] | None = None
        server_module = sys.modules.get("server") or sys.modules.get("__main__")
        if server_module is not None and hasattr(server_module, "mcp"):
            registered_tools = await server_module.mcp.list_tools()
            allowed_at_level = set(tools_for_level(level))
            registered_names = sorted(
                tool.name for tool in registered_tools if tool.name in allowed_at_level
            )
            counts = {
                **counts,
                "exposed": len(registered_names),
                "hidden": max(int(counts.get("classified_total", 0)) - len(registered_names), 0),
                "source": "live_registry",
            }

        target = {
            "org_name": settings.org_name,
            "repo_name": settings.repo_name,
            "repository": f"{settings.org_name}/{settings.repo_name}",
            "project_number": settings.project_number,
            "project_numbers": list(settings.configured_project_numbers()),
            "owner_type": settings.owner_type,
        }

        scope_lock = {
            "enabled": bool(settings.scope_lock),
            "variable": "GH_PROJECT_SCOPE_LOCK",
            "confined_to": target if settings.scope_lock else None,
            "meaning": (
                "Every tool is confined to the configured org/repo/project "
                "allowlist; other targets are refused."
                if settings.scope_lock
                else "Off — the server is as wide as the token allows."
            ),
        }

        write_policy = {
            "branch_prefixes": list(settings.branch_prefixes()),
            "branch_prefixes_variable": "GH_PROJECT_WRITE_BRANCH_PREFIXES",
            "path_prefixes": list(settings.path_prefixes()),
            "path_prefixes_variable": "GH_PROJECT_WRITE_PATH_PREFIXES",
            "allowed_github_workflow_paths": list(settings.github_workflow_paths()),
            "allowed_github_workflow_paths_variable": (
                "GH_PROJECT_ALLOWED_GITHUB_WORKFLOW_PATHS"
            ),
            "default_branch_protected": True,
            "github_workflows_default_denied": True,
            "meaning": (
                "Governed commits must use an allowed branch and path. Files "
                "under .github/ remain denied unless an exact workflow path "
                "is explicitly allowlisted."
            ),
        }

        return ToolSuccess(
            data={
                "server": "github-project-management",
                "version": VERSION,
                "access_level": level.value,
                "access_level_variable": "MCP_ACCESS_LEVEL",
                "access_level_meaning": meaning,
                "tool_exposure": counts,
                "tool_profile": settings.tool_profile,
                "tool_profile_variable": "MCP_TOOL_PROFILE",
                "exposed_tools": registered_names if registered_names is not None else tools_for_level(level),
                "scope_lock": scope_lock,
                "write_policy": write_policy,
                "target": target,
            },
        ).model_dump()

    except Exception as exc:
        logger.error("Error in server_info: %s", exc)
        return handle_tool_error(exc, context="server_info failed")
