"""Pydantic models for GitHub Project V2 metadata and discovery cache.

Contains models representing the project structure: fields, field options,
and the overall project metadata used for ID discovery and caching.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class FieldOption(BaseModel):
    """A selectable value within a single-select or iteration field.

    Example: "In Progress" option within the Status field.
    """

    id: str = Field(description="Node ID (e.g., 'PVTSSF_...')")
    name: str = Field(description="Display name (e.g., 'In Progress')")


class ProjectField(BaseModel):
    """A custom field defined in the GitHub Project V2.

    Represents fields like Status, Priority, Milestone, Due date, Estimate.
    """

    id: str = Field(description="Field node ID")
    name: str = Field(description="Field name (e.g., 'Status')")
    data_type: str = Field(
        description="Field type: SINGLE_SELECT, TEXT, DATE, NUMBER, ITERATION"
    )
    options: list[FieldOption] = Field(
        default_factory=list,
        description="Available options (only for SINGLE_SELECT/ITERATION fields)",
    )


class ProjectMetadata(BaseModel):
    """Cached metadata from the GitHub Project V2 discovery query.

    Contains all dynamic IDs needed to interact with the project:
    project node ID, field IDs, and option IDs.
    """

    project_id: str = Field(description="Project node ID (e.g., 'PVT_...')")
    owner: str = Field(description="Organization login")
    project_number: int = Field(description="Project number (e.g., 1)")
    fields: dict[str, ProjectField] = Field(
        description="Map of field_name -> ProjectField"
    )
    discovered_at: datetime = Field(description="Cache timestamp")
