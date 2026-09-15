"""Tests for exhaustive board pagination (ProjectService.list_all_items).

Regression for PR #20 review follow-up: reconciliation must reach items beyond
GH_PROJECT_MAX_ITEMS. `list_all_items` pages the whole board; `list_items` still
caps at max_items for interactive listing.

The GraphQL client is mocked to serve two pages, so no token or network is used.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("GH_PROJECT_ORG_NAME", "TestOrg")
os.environ.setdefault("GH_PROJECT_REPO_NAME", "TestRepo")
os.environ.setdefault("GH_PROJECT_PROJECT_NUMBER", "1")

from core.config import get_settings
from services.project_service import ProjectService


def _issue_node(node_id, number, status="🛠 In Progress", state="MERGED"):
    return {
        "id": node_id,
        "content": {
            "__typename": "Issue",
            "number": number,
            "title": f"Item {number}",
            "body": "",
            "url": f"https://x/{number}",
            "state": state,
            "assignees": {"nodes": []},
            "labels": {"nodes": []},
        },
        "fieldValues": {
            "nodes": [
                {
                    "name": status,
                    "field": {"name": "Status"},
                }
            ]
        },
    }


def _page(nodes, has_next, cursor):
    return {
        "data": {
            "organization": {
                "projectV2": {
                    "items": {
                        "nodes": nodes,
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    }
                }
            }
        }
    }


def _make_service(pages):
    """Build a ProjectService whose GraphQL client serves the given pages."""
    gql = MagicMock()
    gql.execute_with_retry = AsyncMock(side_effect=pages)
    svc = ProjectService(graphql_client=gql, gh_client=MagicMock())
    # Force organization owner type for deterministic query variables.
    svc._context = MagicMock()
    svc._context.target.owner_type = "organization"
    return svc, gql


def _metadata():
    md = MagicMock()
    md.owner = "TestOrg"
    md.project_number = 1
    return md


def test_list_all_items_pages_past_max_items():
    settings = get_settings()
    # Build 2 full pages of page_size each — total exceeds max_items only if
    # max_items < 2*page_size; regardless, exhaustive must return everything.
    ps = settings.page_size
    page1 = [_issue_node(f"PVTI_{i}", 1000 + i) for i in range(ps)]
    page2 = [_issue_node(f"PVTI_{ps + i}", 2000 + i) for i in range(5)]
    pages = [_page(page1, True, "c1"), _page(page2, False, None)]

    svc, gql = _make_service(pages)
    items = asyncio.run(svc.list_all_items(_metadata()))

    assert len(items) == ps + 5, f"expected {ps + 5}, got {len(items)}"
    # Two GraphQL fetches were made (followed the cursor).
    assert gql.execute_with_retry.await_count == 2
    print("✅ test_list_all_items_pages_past_max_items")


def test_list_items_still_caps_at_max_items():
    settings = get_settings()
    ps = settings.page_size
    # Enough nodes to exceed max_items across pages.
    total = settings.max_items + ps
    pages = []
    made = 0
    while made < total:
        chunk = [_issue_node(f"PVTI_{made + i}", 5000 + made + i) for i in range(ps)]
        made += ps
        pages.append(_page(chunk, made < total, f"c{made}"))
    svc, _ = _make_service(pages)
    items = asyncio.run(svc.list_items(metadata=_metadata()))
    assert len(items) <= settings.max_items
    print("✅ test_list_items_still_caps_at_max_items")


if __name__ == "__main__":
    test_list_all_items_pages_past_max_items()
    test_list_items_still_caps_at_max_items()
    print("All exhaustive-pagination tests passed")
