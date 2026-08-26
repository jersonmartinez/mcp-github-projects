# Contributing to GitHub Project MCP Server

Thank you for your interest in contributing! This guide will help you get started.

## Development Environment

1. Docker (required — all code runs inside containers)
2. GitHub CLI (`gh`) authenticated
3. Python 3.12+ (for local syntax checks only)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jersonmartinez/github-project-mcp.git
cd github-project-mcp

# Copy a profile
cp profiles/example.env .env
# Edit .env with your target org/repo/project

# Build and verify
docker build -t github-project-mcp:latest .
docker run --rm -e GH_PROJECT_ORG_NAME=YourOrg -e GH_PROJECT_REPO_NAME=YourRepo \
  -e GH_PROJECT_PROJECT_NUMBER=1 github-project-mcp:latest \
  python3 tests/test_owner_type.py
```

## Branch Naming

```
<type>/<description-in-kebab-case>
```

| Type | When |
|------|------|
| `feat/` | New tool or functionality |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Maintenance, deps |
| `refactor/` | Code restructuring |

## Adding a New Tool

1. Create `tools/your_tool.py` with:
   - Pydantic input model
   - Async tool function with docstring
   - Error handling using `build_error_response` and `handle_tool_error`
2. Register in `server.py`: `mcp.tool()(your_tool_function)`
3. Add capability mapping in `capabilities.py`
4. Add tests in `tests/`
5. Verify: `python3 -c "import ast; ast.parse(open('tools/your_tool.py').read())"`

## Pull Request Requirements

- Title follows conventional commits: `feat(scope): description`
- Body includes `Closes #<issue_number>`
- All Python files pass `ast.parse` syntax check
- Docker image builds successfully
- New tools have at least one test

## Code Style

- Python 3.12, type hints on all public functions
- Docstrings on all public functions (Google style)
- No `any` type hints
- Error handling: never silent catches, always log or raise
- Security: never log tokens, never serialize credentials

## Reporting Issues

Use the issue templates in `.github/ISSUE_TEMPLATE/`:
- Bug reports: include reproduction steps and expected vs actual behavior
- Feature requests: describe the use case and proposed API

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
