#!/bin/bash
# ── Contract Tests Runner ────────────────────────────────────────────────────
# Builds the MCP Docker image and runs contract tests inside a container.
# No live GitHub token required — tests validate structure only.
#
# Usage:
#   ./mcp/scripts/run_contract_tests.sh
#   ./mcp/scripts/run_contract_tests.sh -k "test_all_tools"
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🔨 Building MCP Docker image..."
docker build -t github-project-mcp:latest "${MCP_DIR}"

echo "🧪 Running contract tests..."
docker run --rm \
  -e GH_PROJECT_ORG_NAME=ContractTestOrg \
  -e GH_PROJECT_REPO_NAME=ContractTestRepo \
  -e GH_PROJECT_PROJECT_NUMBER=1 \
  -e GITHUB_TOKEN=ghp_contract_test_placeholder \
  github-project-mcp:latest \
  bash -c "pip install --quiet pytest && python3 -m pytest tests/test_contracts.py -v $*"

echo "✅ Contract tests passed!"
