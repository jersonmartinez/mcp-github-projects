# GitHub Project Management MCP Server

[![MCP CI](https://github.com/jersonmartinez/mcp-github-projects/actions/workflows/ci.yaml/badge.svg)](https://github.com/jersonmartinez/mcp-github-projects/actions/workflows/ci.yaml)

Custom MCP (Model Context Protocol) server that enables AI assistants to programmatically manage GitHub Project V2 boards via the Model Context Protocol. Built with Python 3.12 and FastMCP, communicates over stdio transport, and runs inside a standalone Docker container.

## Location

```
project/
├── mcp/                    ← This directory (root-level, independent of the app)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py           # FastMCP entry point
│   ├── config.py
│   ├── auth.py
│   ├── capabilities.py     # Tool → permission mapping
│   ├── profiles.py         # Multi-target profile system
│   ├── tools/              # MCP tool definitions
│   ├── services/           # Business logic
│   ├── clients/            # GraphQL + gh CLI clients
│   ├── models/             # Pydantic models
│   ├── graphql/            # Query/mutation strings
│   ├── tests/              # Unit + contract tests
│   ├── scripts/            # Validation, preflight, secret scanning
│   │   ├── validate.sh     # ← Run before every push
│   │   ├── preflight.sh    # Environment prerequisites
│   │   ├── scan_secrets.sh # Token pattern detection
│   │   └── smoke_build.sh  # Minimal build verification
│   ├── profiles/           # Target config (.env files, no secrets)
│   ├── docs/               # Detailed documentation
│   ├── LICENSE             # MIT
│   ├── CONTRIBUTING.md
│   └── SECURITY.md
```

> **Note**: This MCP server is a standalone component with its own Dockerfile, dependencies, and lifecycle.

## How It Works

```
MCP Client → docker run --rm -i github-project-mcp:latest → stdin/stdout JSON-RPC → GitHub API
```

1. El cliente MCP invoca una herramienta (ej: `create_project_item`)
2. Se ejecuta `docker run --rm -i github-project-mcp:latest python server.py`
3. El servidor valida autenticación y espera comandos por stdin
4. El cliente envía JSON-RPC via stdin, recibe respuestas por stdout
5. Al finalizar, el contenedor se destruye automáticamente (`--rm`)

## Docker — Construir y Gestionar

### Construir la imagen

```bash
# Desde la raíz del proyecto
docker build -t github-project-mcp:latest ./mcp
```

### Docker Compose (desarrollo local)

La forma más simple de configurar y correr el MCP localmente:

```bash
# 1. Crear tu configuración local (una sola vez)
cp mcp/.env.example mcp/.env
# Editar mcp/.env con tu GITHUB_TOKEN y target (org/repo/project)

# 2. Construir y verificar
cd mcp/
make build
make verify
```

### Makefile Targets

Todos los targets ejecutan dentro de Docker — sin dependencias del host.

```bash
cd mcp/
make help         # Mostrar todos los targets disponibles
make build        # Construir imagen Docker
make verify       # Validar auth + scopes + config
make test         # Ejecutar unit tests
make validate     # CI completo (build + syntax + tests + tools + secrets)
make tools        # Contar herramientas registradas (>= 100)
make syntax       # Verificar sintaxis Python
make secrets      # Escanear credenciales en código
make shell        # Shell interactivo dentro del contenedor
make clean        # Eliminar imágenes
```

> **Nota:** Si `make` no está disponible en el host, los targets pueden invocarse
> directamente con Docker. Ejemplo: `docker run --rm --env-file .env github-project-mcp:latest python3 scripts/verify_setup.py`

Cada contributor clona el repo, crea su `.env`, y el MCP funciona sin instalar nada más que Docker.

### Verificar que la imagen existe

```bash
docker images | grep github-project-mcp
```

### Probar manualmente (smoke test)

```bash
docker run --rm -i \
  -e GITHUB_TOKEN="<your_token>" \
  github-project-mcp:latest \
  python server.py
```

El servidor imprimirá en stderr: `github-project-management MCP server ready. Authentication validated successfully.`
Luego espera JSON-RPC por stdin. Presiona Ctrl+C para salir.

### Reconstruir después de cambios

```bash
docker build -t github-project-mcp:latest ./mcp --no-cache
```

## Script de gestión

El script `./scripts/dev/start.sh` soporta un argumento `mcp` para gestionar la imagen:

```bash
./scripts/dev/start.sh mcp build      # Construir/reconstruir la imagen
./scripts/dev/start.sh mcp test       # Ejecutar smoke test
./scripts/dev/start.sh mcp status     # Verificar si la imagen existe
```

> **Nota**: El MCP no es un servicio persistente. No necesita `up/down/restart`. Se lanza bajo demanda cada vez que el cliente usa una herramienta.

## IDE Integration

El MCP es compatible con cualquier cliente que soporte el protocolo MCP sobre stdio.
La configuración varía por IDE — el patrón general es:

```json
{
  "mcpServers": {
    "github-project-management": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GITHUB_TOKEN",
        "--env-file", "mcp/.env",
        "github-project-mcp:latest",
        "python", "server.py"
      ]
    }
  }
}
```

Para configuración específica por IDE, ver [docs/SETUP.md](docs/SETUP.md#ide-integration).

## Registered Tools (100)

### Core Operations
| Tool | Description |
|------|-------------|
| `discover_ids` | Discover project/field IDs |
| `list_project_items` | List items with filters |
| `create_project_item` | Create issue + add to project |
| `update_project_item_fields` | Update Status, Priority, Due date |
| `set_estimate` | Set story point estimate |
| `archive_project_item` | Archive item from board |

### Issue Management
| Tool | Description |
|------|-------------|
| `close_issue` | Close an issue |
| `reopen_issue` | Reopen a closed issue |
| `comment_issue` | Add comment to issue |
| `edit_issue` | Edit title, body, labels, milestone, assignees |
| `add_sub_issue` | Link as sub-issue |
| `remove_sub_issue` | Unlink sub-issue |
| `get_issue_detail` | Full issue detail |
| `search_issues` | Search by query |

### Board Operations
| Tool | Description |
|------|-------------|
| `move_to_status` | Move item to any status column |
| `move_to_done` | Mark as Done |
| `move_to_trash` | Move to Trash |
| `bulk_update_items` | Batch update multiple items |
| `bulk_close_issues` | Close multiple issues |
| `bulk_assign` | Assign multiple issues |

### Planning & Workflows
| Tool | Description |
|------|-------------|
| `sprint_planning` | Generate sprint plan |
| `generate_release_notes` | Auto-generate release notes |
| `complete_issue` | Full completion workflow |
| `daily_standup` | Generate standup report |
| `sprint_review` | Sprint review summary |
| `triage_new_issues` | Auto-triage proposals |
| `escalate_overdue` | Flag overdue items |
| `create_epic` | Create parent + children |
| `close_sprint` | Close sprint and move items |

### Metadata
| Tool | Description |
|------|-------------|
| `create_milestone` | Create GitHub milestone |
| `close_milestone` | Close milestone |
| `list_milestones` | List milestones |
| `create_label` | Create label |
| `list_labels` | List labels |
| `get_project_stats` | Board statistics |
| `get_sprint_summary` | Current sprint metrics |

## Architecture

```
Tool Layer (FastMCP tool definitions)
    ↓
Service Layer (business logic, orchestration)
    ↓
Client Layer (GraphQL + gh CLI + caching)
    ↓
GitHub APIs (GraphQL v4 + REST v3)
```

### Delegation Strategy

| Method | When Used |
|--------|-----------|
| **gh CLI** | Issue CRUD, comments, project item-add, close |
| **Custom GraphQL** | Field updates, archival, discovery, sub-issues |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub PAT (fine-grained or classic) |
| `GH_PROJECT_ORG_NAME` | **Yes** | GitHub owner (organization or user login) |
| `GH_PROJECT_REPO_NAME` | **Yes** | Repository name |
| `GH_PROJECT_PROJECT_NUMBER` | **Yes** | Project V2 board number (1–100000) |

## Troubleshooting

### MCP no conecta
```bash
# Verificar que la imagen existe
docker images | grep github-project-mcp

# Si no existe, construir
docker build -t github-project-mcp:latest ./mcp

# Verificar token
echo $GITHUB_TOKEN | head -c 20
```

### Reconectar MCP
Si el MCP se desconecta del IDE, usar la opción de reconexión del cliente MCP correspondiente.

### Error de autenticación
- Verificar que `GITHUB_TOKEN` está disponible en el entorno del contenedor
- Tokens `github_pat_*` (fine-grained) necesitan permisos: Issues (RW), Projects (RW), Metadata (R)
- Tokens clásicos necesitan scopes: `repo`, `project`, `read:org`

## Related Documentation

| Document | Purpose |
|----------|---------|
| [docs/SETUP.md](docs/SETUP.md) | Token setup and permissions |
| [docs/USAGE.md](docs/USAGE.md) | Tool input/output examples |
| [docs/PARAMETERS.md](docs/PARAMETERS.md) | Parameter reference |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors |

## Source locations and synchronization

This directory (`mcp/`) is the **canonical source of truth** for the MCP package.

The repository contains a synchronized copy at:
- `app/backend/app/mcp/github_project/` — embedded in the backend for Docker builds

### Sync workflow

1. **Make all changes here** in `mcp/` first.
2. Copy modified files to the embedded path:
   ```bash
   cp mcp/<file> app/backend/app/mcp/github_project/<file>
   ```
3. **Verify** with the automated check:
   ```bash
   ./mcp/scripts/check_sync.sh
   ```

The sync script compares all shared `.py` files (excluding `__init__.py` which is
intentionally different in the backend copy, and infra-only files like `Dockerfile`
and `requirements.txt`). CI runs this check on every push — divergence fails the build.

### Files intentionally different in the backend copy

| File | Reason |
|------|--------|
| `__init__.py` | Backend-specific imports + sync-source documentation |
| `README.md` | Points back here; documents the copy policy |

The backend test suite exercises the embedded copy; syntax validation must compile both trees.

## Hardened runtime behavior

All settings use the `GH_PROJECT_` prefix and are validated at startup:

| Setting | Default | Bounds / behavior |
|---------|---------|-------------------|
| `GH_PROJECT_TIMEOUT_SECONDS` | `10` | 1–120 seconds |
| `GH_PROJECT_RETRY_ATTEMPTS` | `1` | 0–5; reads only, mutations never retry |
| `GH_PROJECT_RETRY_DELAY_SECONDS` | `2.0` | 0–60 seconds, exponential backoff |
| `GH_PROJECT_CACHE_TTL_HOURS` | `24` | 1–720 hours |
| `GH_PROJECT_CACHE_PATH` | `.github_project_cache.json` | Configurable local path |
| `GH_PROJECT_PAGE_SIZE` | `100` | 1–100 |
| `GH_PROJECT_MAX_ITEMS` | `200` | 1–1,000 |
| `GH_PROJECT_MAX_CLI_OUTPUT_CHARS` | `1,000,000` | 10,000–10,000,000 |

The metadata cache is written atomically, uses owner-only permissions (`0600`), rejects future timestamps, and is not reused when organization or project number differs. CLI and GraphQL diagnostics redact token-like values and are bounded before returning to the MCP client.

## Docker-only validation

Run validation without host Python tooling:

```bash
# Compile both source copies through a Python container
tar -C . -cf - mcp app/backend/app/mcp \
  | docker run --rm -i python:3.12-slim sh -c \
    'mkdir -p /tmp/factib && tar -xf - -C /tmp/factib && \
     python -m compileall -q /tmp/factib/mcp /tmp/factib/app/backend/app/mcp'

# Run the backend MCP tests using the existing backend image
tar -C . -cf - app/backend/app app/backend/tests/mcp \
  | docker run --rm -i -e PYTHONPATH=/tmp/factib/app/backend backend:latest sh -c \
    'mkdir -p /tmp/factib && tar -xf - -C /tmp/factib && cd /tmp/factib/app/backend && \
     pytest -q --confcutdir=/tmp/factib/app/backend/tests/mcp tests/mcp'
```

## Local Validation (Pre-Push)

**Always run before creating a PR or pushing changes.** This mirrors the CI pipeline locally and catches issues before they reach GitHub Actions.

### Quick Start

```bash
# Full validation (builds image + runs all checks):
./mcp/scripts/validate.sh

# Quick mode (reuses cached image, skips rebuild):
./mcp/scripts/validate.sh --quick

# Auto-fix known issues (e.g., BOM characters):
./mcp/scripts/validate.sh --fix
```

### What It Checks

| Step | What | Same as CI step |
|------|------|-----------------|
| 1. BOM | Detects UTF-8 BOM bytes in Python files | N/A (prevents syntax errors) |
| 2. Build | `docker build -t github-project-mcp:validate ./mcp` | "Build MCP image" |
| 3. Syntax | `ast.parse` on all .py files inside the image | "Syntax check" |
| 4. Tests | Runs test modules in `tests/` | "Run unit tests" |
| 5. Tools | Counts registered tools (must be >= 100) | "Verify tool count" |
| 6. Secrets | Scans for token patterns in tracked files | N/A (pre-publication) |

### Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/validate.sh` | Full CI mirror | Before every push/PR |
| `scripts/preflight.sh` | Prerequisite check (Docker, token, config) | First setup or env changes |
| `scripts/scan_secrets.sh` | Secret pattern detection | Before publishing repo |
| `scripts/smoke_build.sh` | Minimal build + tool count | Quick sanity check |
| `scripts/run_contract_tests.sh` | Multi-target contract suite | After structural changes |

### Common Issues and Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| BOM characters | `SyntaxError: invalid non-printable character U+FEFF` | `./mcp/scripts/validate.sh --fix` |
| Image not built | "Image not found" in Docker commands | `docker build -t github-project-mcp:latest ./mcp` |
| Token not set | "No GitHub token found" in preflight | `export GITHUB_TOKEN=ghp_...` |
| Tool count < 100 | New tool not registered in server.py | Add `mcp.tool()(your_tool)` in server.py |

The complete 200-item register, including implemented and planned work, is in [`docs/HARDENING_200.md`](HARDENING_200.md).

## Extended capability suite: 60 additional tools

The server exposes 100+ tools in total: the original 40 operational tools plus 60 focused capabilities from `tools/capability_suite.py`.

| Group | Purpose | Examples |
|-------|---------|----------|
| Issue and Markdown quality | Validate, normalize, summarize, template, bundle and review issues | `validate_issue_markdown`, `build_issue_template`, `build_issue_review_checklist` |
| Comment system | Create progress, plan, blocker and resolution comments; list/search/edit comments | `comment_issue_progress`, `comment_issue_blocker`, `list_issue_comments` |
| Project reporting | Health, status, priority, assignee, due-date and field reports | `project_health_report`, `project_due_date_risk`, `project_field_options_report` |
| Project planning | Export/import Markdown, metadata synchronization plans and filtered bulk plans | `project_export_markdown`, `project_sync_issue_metadata`, `project_bulk_status_by_filter` |
| Strategic automation | Sprint plans, backlog ranking, risk/dependency reports and stakeholder updates | `plan_next_sprint`, `prioritize_backlog`, `generate_risk_register` |
| Roadmaps and decisions | Changelogs, release checklists, roadmaps, retrospectives and automation decisions | `generate_changelog_from_issues`, `build_roadmap_markdown`, `build_sprint_retrospective` |

Tools that could cause broad mutations return a `dry_run` plan by default. Direct comment tools perform one visible comment operation per invocation. The capability catalog asserts 60 unique additions at import time, and Docker validation confirms 100 registered FastMCP tools in both source copies.

## Distribution

### Docker Image

The MCP server is distributed as a standalone Docker image. Build locally:

```bash
docker build -t github-project-mcp:latest ./mcp
```

### CI/CD Pipeline

The `mcp-ci.yaml` workflow runs automatically on:
- Push to `main` when files under `mcp/` change
- Pull requests touching `mcp/` paths

Pipeline stages:
1. **Build** — Docker image build verification
2. **Syntax check** — AST parsing of all Python files
3. **Unit tests** — pytest suite execution
4. **Tool count verification** — Ensures ≥100 registered tools

### Versioning

This MCP server follows [Semantic Versioning](https://semver.org/). See [CHANGELOG.md](CHANGELOG.md) for release history.
