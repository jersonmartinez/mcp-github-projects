"""MCP tool for discovering GitHub Project V2 IDs.

Exposes the `discover_ids` tool function that discovers project ID,
field IDs, and option IDs using the DiscoveryService. Returns cached
metadata when available and fresh, or queries the GraphQL API otherwise.
"""

from __future__ import annotations

import logging

from auth import resolve_token
from clients.cache_manager import CacheManager
from clients.graphql_client import GraphQLClient
from error_handling import handle_tool_error
from models.responses import ToolSuccess
from services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)


async def discover_ids(force: bool = False) -> dict:
    """Discover GitHub Project V2 IDs (project, fields, options).

    Queries the GitHub GraphQL API for the project's node ID, all custom
    field IDs, and all field option IDs. Results are cached locally with
    a 24-hour TTL to minimize API calls.

    Args:
        force: If True, bypass the cache and re-query the API regardless
               of cache freshness.

    Returns:
        A dict conforming to ToolSuccess (ok=True, data=metadata) on success,
        or ToolError (ok=False, error_type, message, suggestion) on failure.
    """
    try:
        token = await resolve_token()
        graphql_client = GraphQLClient(token=token)
        cache_manager = CacheManager()
        discovery_service = DiscoveryService(
            graphql_client=graphql_client,
            cache_manager=cache_manager,
        )

        if force:
            metadata = await discovery_service.discover(force=True)
        else:
            metadata = await discovery_service.get_cached_or_discover()

        return ToolSuccess(
            data=metadata.model_dump(mode="json"),
        ).model_dump()

    except Exception as exc:
        logger.error("Error during discovery: %s", exc)
        return handle_tool_error(exc, context="Discovery failed")
