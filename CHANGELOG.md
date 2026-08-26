# Changelog

All notable changes to the GitHub Project Management MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
