# Changelog

All notable changes to the GitHub Project Management MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `sync_closed_items_to_done` — board-reconciliation tool that moves items whose
  linked issue/PR is CLOSED or MERGED to the Done column (skips items already in a
  terminal column). Supports `dry_run` preview and `issue_or_pr_number` scoping.
  GitHub does not auto-advance a card to Done when its PR merges, so cards
  otherwise linger in *In Progress*; this tool reconciles them in bulk.
  Tool count 104 → 105.

### Changed

- `sync_closed_items_to_done` now scans the board **exhaustively** — it pages the
  entire board past `GH_PROJECT_MAX_ITEMS` (via the new
  `ProjectService.list_all_items`), so boards with more than 200 cards are fully
  reconciled in a single call, including the `issue_or_pr_number` scope. The
  previous `scan_capped`/`max_items` response fields are removed (no longer
  meaningful). `_fetch_all_items` gains an `exhaustive` flag with a large safety
  ceiling.
- `_ITEMS_FRAGMENT` (list-items GraphQL) now selects the content `state` and a
  `PullRequest` block, and `ProjectItem` gains a `content_state` field
  (OPEN/CLOSED/MERGED). PR-typed items are now parsed instead of skipped.

## [1.0.0] - 2026-08-20

### Added

- Initial stable release with 100 registered FastMCP tools
- 40 core operational tools for GitHub Project V2 management
- 60 capability suite tools (issue quality, comments, reporting, planning, strategy, roadmaps)
- Standalone Docker image with Python 3.12 and stdio transport
- CI/CD pipeline (`mcp-ci.yaml`) with build, syntax check, tests, and tool count verification
- Comprehensive documentation in `mcp/docs/`
- Support for environment-based configuration (`GH_PROJECT_ORG_NAME`, `GH_PROJECT_REPO_NAME`, `GH_PROJECT_PROJECT_NUMBER`)
- Dry-run mode for mutation-capable tools
- GraphQL and `gh` CLI dual-client architecture
