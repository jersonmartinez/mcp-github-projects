"""MCP tool definitions for GitHub Project Management."""

from tools.archive import (
    archive_project_item,
    move_to_done,
    move_to_trash,
)
from tools.close import close_issue
from tools.create_item import create_project_item
from tools.discover import discover_ids
from tools.estimate import set_estimate
from tools.list_items import list_project_items
from tools.update_fields import update_project_item_fields

__all__ = [
    "archive_project_item",
    "close_issue",
    "create_project_item",
    "discover_ids",
    "list_project_items",
    "move_to_done",
    "move_to_trash",
    "set_estimate",
    "update_project_item_fields",
]
