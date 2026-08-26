"""Verify MCP setup: authentication, scopes, and target configuration."""

import asyncio
import sys

sys.path.insert(0, "/app")
import os

os.chdir("/app")

from auth import resolve_token, validate_scopes
from config import get_settings


async def main() -> None:
    print("▶ Resolving token...")
    token = await resolve_token()
    print("  ✓ Token found")

    print("▶ Validating scopes...")
    await validate_scopes(token)
    print("  ✓ Scopes valid")

    print("▶ Loading configuration...")
    settings = get_settings()
    print(f"  ✓ Target: {settings.org_name}/{settings.repo_name} #{settings.project_number}")
    print(f"  ✓ Owner type: {settings.owner_type}")

    print("")
    print("✅ MCP ready — all checks passed")


if __name__ == "__main__":
    asyncio.run(main())
