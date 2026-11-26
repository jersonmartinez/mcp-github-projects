"""Read-only validation of GitHub Project V2 field values.

The tool resolves friendly field names and values against live project metadata
and returns the exact GraphQL payloads a write would use, without mutating the
board. It is the pre-write contract companion of update_project_item_fields and
bulk_update_items.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from core.error_handling import handle_tool_error
from core.factory import get_service_factory
from core.project_scope import project_context
from models.responses import ToolSuccess

logger = logging.getLogger(__name__)


class ValidateProjectFieldValuesInput(BaseModel):
    """Input schema for validate_project_field_values."""

    fields: dict[str, Any] = Field(
        min_length=1,
        max_length=25,
        description="Board field names to friendly values: single-select option names, YYYY-MM-DD dates, numbers, or text.",
    )
    project_number: int | None = Field(
        default=None,
        gt=0,
        le=100_000,
        description="Project V2 board number; defaults to the configured board.",
    )


async def validate_project_field_values(params: ValidateProjectFieldValuesInput) -> dict:
    """Validate project field values against discovered board metadata.

    Returns canonical field names, field types, exact mutation payloads, valid
    options for select fields, and per-field errors. No GitHub mutation is made.
    """
    try:
        context = project_context(params.project_number)
        graphql_client = await get_service_factory().graphql()
        gh_client = get_service_factory().gh(context=context)
        discovery = await get_service_factory().discovery_service(
            graphql_client,
            context=context,
        )
        project_service = await get_service_factory().project_service(
            graphql_client,
            gh_client,
            context=context,
        )
        metadata = await discovery.get_cached_or_discover()

        rows: list[dict[str, Any]] = []
        valid = True
        for requested_name, value in params.fields.items():
            try:
                field, payload = project_service.plan_field_value(metadata, requested_name, value)
                rows.append({
                    "requested_field": requested_name,
                    "field": field.name,
                    "field_id": field.id,
                    "data_type": field.data_type,
                    "input": value,
                    "payload": payload,
                    "valid": True,
                    "valid_options": [option.name for option in field.options] if field.options else [],
                })
            except Exception as exc:
                valid = False
                rows.append({
                    "requested_field": requested_name,
                    "input": value,
                    "valid": False,
                    "error": str(exc),
                })

        return ToolSuccess(
            data={
                "valid": valid,
                "fields": rows,
                "available_fields": sorted(metadata.fields),
                "message": "Validation complete; no project item was mutated.",
            }
        ).model_dump()
    except Exception as exc:
        logger.error("Error in validate_project_field_values: %s", exc)
        return handle_tool_error(exc, context="Validate project field values failed")
