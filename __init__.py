"""GitHub Project Management MCP Server.

Enables AI assistants to programmatically manage
GitHub Project V2 board (project number 1). Exposes tools for listing,
creating, updating, archiving, and managing project items with full
field control (Status, Priority, Milestone, Due date, Estimate,
Assignees, Labels).
"""

from config import GitHubProjectSettings, get_settings

__all__ = ["GitHubProjectSettings", "get_settings"]
