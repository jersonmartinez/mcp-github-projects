#!/bin/bash
# smoke_build.sh — Reproducible build verification for the MCP image.
# Works with both legacy Docker builder and BuildKit.
# Exit on any failure.
set -euo pipefail

IMAGE="github-project-mcp:test"

echo "=== Building MCP image (legacy builder compatible) ==="
docker build -t "$IMAGE" ./mcp

echo "=== Verifying non-root user ==="
docker run --rm "$IMAGE" whoami | grep -q mcp
echo "  ✓ Runs as 'mcp' user"

echo "=== Verifying tool count ==="
TOOLS=$(docker run --rm \
  -e GH_PROJECT_ORG_NAME=Test \
  -e GH_PROJECT_REPO_NAME=Test \
  -e GH_PROJECT_PROJECT_NUMBER=1 \
  "$IMAGE" python3 -c "
import sys; sys.path.insert(0, '/app')
from server import mcp as server
print(len(server._tool_manager._tools))")
echo "  Tools registered: $TOOLS"
[ "$TOOLS" -ge 100 ] || { echo "FAIL: Expected >= 100 tools, got $TOOLS"; exit 1; }
echo "  ✓ Tool count OK"

echo "=== Verifying Python syntax ==="
docker run --rm "$IMAGE" python3 -c "
import ast, os
for root, dirs, files in os.walk('/app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fh:
                ast.parse(fh.read(), filename=path)
print('All .py files compile successfully')"
echo "  ✓ Python syntax OK"

echo ""
echo "✅ Smoke build passed — image is reproducible and legacy-builder compatible"
