"""Cache manager for GitHub Project V2 metadata persistence.

Handles local JSON file storage for discovered project metadata,
providing read/write operations with TTL-based freshness checks.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from config import get_settings
from hardening import atomic_write_json
from models.metadata import ProjectMetadata

# Required top-level keys for a valid cache file.
_REQUIRED_KEYS = frozenset({"project_id", "fields", "owner", "project_number", "discovered_at"})


class CacheManager:
    """Manages local JSON cache for ProjectMetadata."""

    def read_cache(self, cache_path: Path) -> ProjectMetadata | None:
        """Load and validate cached metadata from a JSON file.

        Args:
            cache_path: Path to the JSON cache file.

        Returns:
            A ProjectMetadata instance if the file is valid, None otherwise.
            Returns None when:
            - The file does not exist
            - The file contains invalid JSON
            - The JSON is missing required keys
            - The JSON cannot be parsed into ProjectMetadata
        """
        if not cache_path.exists():
            return None

        try:
            raw = cache_path.read_text(encoding="utf-8")
        except OSError:
            return None

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        if not _REQUIRED_KEYS.issubset(data.keys()):
            return None

        try:
            return ProjectMetadata.model_validate(data)
        except (ValueError, TypeError):
            return None

    def write_cache(self, metadata: ProjectMetadata, cache_path: Path) -> None:
        """Serialize and write ProjectMetadata to a JSON cache file.

        Creates parent directories if they don't exist.

        Args:
            metadata: The ProjectMetadata to persist.
            cache_path: Destination file path.
        """
        payload = metadata.model_dump(mode="json")
        atomic_write_json(cache_path, payload)

    def is_fresh(self, metadata: ProjectMetadata) -> bool:
        """Check whether cached metadata is still within the TTL window.

        Compares metadata.discovered_at against the current UTC time
        using the configured cache_ttl_hours from settings.

        Args:
            metadata: The ProjectMetadata whose freshness to evaluate.

        Returns:
            True if the cache age is less than cache_ttl_hours, False otherwise.
        """
        settings = get_settings()
        now = datetime.now(timezone.utc)
        discovered = metadata.discovered_at

        # Ensure discovered_at is timezone-aware for comparison.
        if discovered.tzinfo is None:
            discovered = discovered.replace(tzinfo=timezone.utc)

        age_hours = (now - discovered).total_seconds() / 3600
        return 0 <= age_hours < settings.cache_ttl_hours
