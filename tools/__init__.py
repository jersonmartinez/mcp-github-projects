"""MCP tool definitions for GitHub Project Management."""

from tools.projects.archive import (
    archive_project_item,
    move_to_done,
    move_to_trash,
)
from tools.issues.close import close_issue
from tools.issues.create_item import create_project_item
from tools.discovery.discover import discover_ids
from tools.fields.estimate import set_estimate
from tools.discovery.list_items import list_project_items
from tools.projects.update_fields import update_project_item_fields

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
