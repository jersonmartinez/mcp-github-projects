#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# check_sync.sh — Verify that the backend-embedded MCP copy has not
# diverged from the canonical mcp/ source.
#
# Canonical source: mcp/
# Embedded copy:    app/backend/app/mcp/github_project/
#
# Exit codes:
#   0 — copies are in sync
#   1 — divergence detected (prints differing files)
#   2 — usage error (cannot find directories)
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CANONICAL="${REPO_ROOT}/mcp"
EMBEDDED="${REPO_ROOT}/app/backend/app/mcp/github_project"

if [[ ! -d "$CANONICAL" ]]; then
    echo "ERROR: Canonical source not found at $CANONICAL" >&2
    exit 2
fi
if [[ ! -d "$EMBEDDED" ]]; then
    echo "ERROR: Embedded copy not found at $EMBEDDED" >&2
    exit 2
fi

DIVERGED=0
CHECKED=0

# Compare shared Python files (those that exist in BOTH trees).
# Excludes: __init__.py (intentionally different), infra files, docs, tests, profiles, scripts.
while IFS= read -r -d '' rel_path; do
    embedded_file="${EMBEDDED}/${rel_path}"
    if [[ -f "$embedded_file" ]]; then
        CHECKED=$((CHECKED + 1))
        if ! diff -q "$CANONICAL/$rel_path" "$embedded_file" > /dev/null 2>&1; then
            echo "DIVERGED: $rel_path"
            diff --unified=3 "$CANONICAL/$rel_path" "$embedded_file" | head -20
            echo "---"
            DIVERGED=$((DIVERGED + 1))
        fi
    fi
done < <(find "$CANONICAL" \
    -path '*/__pycache__' -prune -o \
    -path '*/tests' -prune -o \
    -path '*/docs' -prune -o \
    -path '*/profiles' -prune -o \
    -path '*/scripts' -prune -o \
    -name '__init__.py' -prune -o \
    -name 'Dockerfile' -prune -o \
    -name '.dockerignore' -prune -o \
    -name 'requirements.txt' -prune -o \
    -name 'README.md' -prune -o \
    -name 'profiles.py' -prune -o \
    -name 'capabilities.py' -prune -o \
    -type f -name '*.py' -print0 \
    | sed -z "s|^${CANONICAL}/||")

echo "Checked $CHECKED files."

if [[ $DIVERGED -gt 0 ]]; then
    echo ""
    echo "❌ SYNC FAILURE: $DIVERGED file(s) have diverged."
    echo "   Fix: Apply changes in mcp/ (canonical), then copy to the embedded path."
    echo "   Run: cp mcp/<file> app/backend/app/mcp/github_project/<file>"
    exit 1
fi

echo "✅ All shared files are in sync between mcp/ and the backend embedded copy."
exit 0
