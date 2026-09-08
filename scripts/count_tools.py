"""Count registered MCP tools and verify minimum threshold."""

import asyncio
import sys

sys.path.insert(0, "/app")
import os

os.chdir("/app")

import core.auth as auth


async def noop(_: str) -> None:
    pass


# Bypass scope validation for structural check
auth.validate_scopes = noop

from server import mcp as server

MINIMUM_TOOLS = 100


async def main() -> None:
    tools = await server.list_tools()
    count = len(tools)
    print(f"Tools registered: {count}")

    if count >= MINIMUM_TOOLS:
        print(f"✅ Passed (>= {MINIMUM_TOOLS})")
    else:
        print(f"❌ Failed — expected >= {MINIMUM_TOOLS}, got {count}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
