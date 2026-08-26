"""GraphQL queries and mutations for GitHub Projects V2 API."""

from graphql.mutations import (
    ADD_ITEM_TO_PROJECT_MUTATION,
    ARCHIVE_ITEM_MUTATION,
    CREATE_FIELD_MUTATION,
    UPDATE_FIELD_MUTATION,
)
from graphql.queries import (
    DISCOVERY_QUERY,
    LIST_ITEMS_QUERY,
)

__all__ = [
    "ADD_ITEM_TO_PROJECT_MUTATION",
    "ARCHIVE_ITEM_MUTATION",
    "CREATE_FIELD_MUTATION",
    "DISCOVERY_QUERY",
    "LIST_ITEMS_QUERY",
    "UPDATE_FIELD_MUTATION",
]
