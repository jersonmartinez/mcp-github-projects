# Setup Guide

## Prerequisites

| Requirement | Purpose | Install |
|-------------|---------|---------|
| Docker 20+ | Container runtime for the MCP server | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| GitHub Token | API authentication (PAT classic or fine-grained) | See [Token Generation](#token-generation) |
| GitHub CLI (optional) | Alternative auth + host utilities | [cli.github.com](https://cli.github.com/) |

Run the preflight check to validate all prerequisites:

```bash
./mcp/scripts/preflight.sh
# Or with automatic resolution:
./mcp/scripts/preflight.sh --fix
```

---

## Authentication Architecture

The MCP resolves credentials in a strict priority chain. The first valid token wins:

```
┌─────────────────────────────────────────────────────────┐
│  1. GITHUB_TOKEN env var (highest priority)             │
│  2. GH_TOKEN env var (fallback)                         │
│  3. gh auth token (CLI-based, requires gh installed)    │
└─────────────────────────────────────────────────────────┘
```

**Design invariants:**
- Tokens are NEVER persisted in files tracked by git
- Tokens are NEVER printed to stdout, logs, or diagnostics
- The MCP validates scopes at startup and fails fast with actionable messages
- Scope hierarchy is honored (`admin:org` implies `read:org`)

### Local Development

Set your token as an environment variable:

```bash
# Option A: Export in shell session
export GITHUB_TOKEN=ghp_your_token_here

# Option B: Add to shell profile (~/.bashrc, ~/.zshrc)
echo 'export GITHUB_TOKEN=ghp_...' >> ~/.bashrc

# Option C: Use .env file (auto-loaded by Docker --env-file)
echo 'GITHUB_TOKEN=ghp_...' > mcp/.env
# ⚠️ .env is in .gitignore — never commit it
```

### CI/CD (GitHub Actions)

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
  GH_PROJECT_ORG_NAME: your-org
  GH_PROJECT_REPO_NAME: your-repo
  GH_PROJECT_PROJECT_NUMBER: "1"
```

Store the token in **Settings → Secrets and variables → Actions** as `GH_TOKEN`.

### gh CLI Authentication (Alternative)

If you prefer not to manage tokens manually:

```bash
gh auth login --scopes "repo,project,read:org"
gh auth status  # Verify
```

The MCP container includes `gh` internally. When no `GITHUB_TOKEN` env var is set, it falls back to `gh auth token` — but this requires the host's gh session to be mounted or the token exported.

---

## Token Generation

### Classic Personal Access Token

1. Navigate to [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token (classic)**
3. Configure:
   - Name: `github-project-mcp`
   - Expiration: 90 days
   - Scopes:

| Scope | Purpose |
|-------|---------|
| `repo` | Issue CRUD, PR operations, repository access |
| `project` | Project board read/write (items, fields, status) |
| `read:org` | Organization membership resolution |

4. Copy the token immediately (shown only once)

### Fine-Grained Personal Access Token

1. Navigate to [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)
2. **Generate new token**
3. Configure:
   - Name: `github-project-mcp`
   - Resource owner: Your target organization
   - Repository access: Select target repository
   - Permissions:

| Permission | Level | Purpose |
|------------|-------|---------|
| Issues | Read & Write | Create, edit, close issues |
| Projects | Read & Write | Board management |
| Metadata | Read | Repository metadata |
| Organization → Projects | Read & Write | Org-level project access |
| Organization → Members | Read | Resolve assignees |

> **Note:** Fine-grained tokens do not report scopes via `X-OAuth-Scopes` header. The MCP detects this and skips scope validation for `github_pat_*` tokens.

---

## Token Rotation

Rotate credentials periodically (recommended: every 90 days) or immediately if compromised.

### Rotation Procedure

```bash
# 1. Generate a new token (see Token Generation above)
#    Copy the new token value

# 2. Update your local environment
export GITHUB_TOKEN=ghp_new_token_here
# Or update .env file:
echo 'GITHUB_TOKEN=ghp_new_token_here' > mcp/.env

# 3. Verify the new token works
./mcp/scripts/preflight.sh

# 4. Revoke the old token
#    Go to: github.com/settings/tokens
#    Find the old token → Delete

# 5. If using CI/CD, update the secret
#    Settings → Secrets → Actions → GH_TOKEN → Update
```

### Post-Rotation Checklist

- [ ] New token has required scopes (`repo`, `project`, `read:org`)
- [ ] MCP server starts successfully with `./mcp/scripts/preflight.sh`
- [ ] Old token is revoked (not just unused)
- [ ] CI/CD secret is updated if applicable
- [ ] No residual references to old token in shell history

### Emergency Rotation (Token Compromised)

```bash
# 1. IMMEDIATELY revoke at github.com/settings/tokens
# 2. Check audit log: github.com/settings/security-log
# 3. Generate replacement with same scopes
# 4. Scan for unauthorized access in the audit log
# 5. Run secret scanner to verify no persistence:
./mcp/scripts/scan_secrets.sh --history
```

---

## Target Configuration

The MCP requires three mandatory fields identifying the GitHub Project:

| Variable | Description | Example |
|----------|-------------|---------|
| `GH_PROJECT_ORG_NAME` | GitHub owner (org or user login) | `my-org` |
| `GH_PROJECT_REPO_NAME` | Repository name | `my-repo` |
| `GH_PROJECT_PROJECT_NUMBER` | Project V2 board number | `1` |
| `GH_PROJECT_OWNER_TYPE` | `organization` or `user` (default: organization) | `organization` |

### Using Profiles

Pre-built profiles live in `profiles/`:

```bash
# Example:
cp profiles/factib.env .env

# For a personal project:
cp profiles/example.env .env
# Edit with your values
```

### Using Environment Variables

```bash
export GH_PROJECT_ORG_NAME=my-org
export GH_PROJECT_REPO_NAME=my-repo
export GH_PROJECT_PROJECT_NUMBER=1
export GH_PROJECT_OWNER_TYPE=organization
```

---

## Building and Running the Container

### Build

```bash
docker build -t github-project-mcp:latest ./mcp
```

The image is ~150MB, based on `python:3.12-slim`, includes `gh` CLI, and runs as non-root user `mcp` (uid 1000).

### Run (stdio transport)

The MCP communicates via JSON-RPC over stdin/stdout. It is not a long-running daemon — it starts, processes requests, and exits.

```bash
# Minimal (env vars set in shell):
docker run --rm -i \
  -e GITHUB_TOKEN \
  -e GH_PROJECT_ORG_NAME \
  -e GH_PROJECT_REPO_NAME \
  -e GH_PROJECT_PROJECT_NUMBER \
  github-project-mcp:latest

# With .env file:
docker run --rm -i \
  -e GITHUB_TOKEN \
  --env-file mcp/.env \
  github-project-mcp:latest

# With profile:
docker run --rm -i \
  -e GITHUB_TOKEN \
  --env-file mcp/profiles/factib.env \
  github-project-mcp:latest
```

### IDE Integration (Kiro / VS Code)

The MCP is configured in `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "github-project-management": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--name", "factib_mcp",
        "-e", "GITHUB_TOKEN",
        "github-project-mcp:latest",
        "python", "server.py"
      ],
      "disabled": false
    }
  }
}
```

The `-e GITHUB_TOKEN` flag passes the variable name (not value) — Docker reads it from the host environment at runtime.

### Verify

```bash
# Quick smoke test:
echo '{}' | docker run --rm -i \
  -e GITHUB_TOKEN \
  --env-file mcp/.env \
  github-project-mcp:latest

# Full preflight:
./mcp/scripts/preflight.sh

# Secret scan:
./mcp/scripts/scan_secrets.sh
```

---

## Security Practices

### What is safe to commit

- `.kiro/settings/mcp.json` — contains command structure, NOT token values
- `mcp/profiles/*.env` — contains target config (org/repo/project), NOT tokens
- `mcp/docs/SETUP.md` — this file

### What must NEVER be committed

- `.env` files with `GITHUB_TOKEN=ghp_...` values
- Shell history containing token values
- Docker run commands with inline token values in CI logs

### Secret Scanning

Run before publishing or sharing the repository:

```bash
# Scan working tree
./mcp/scripts/scan_secrets.sh

# Scan git history (pre-publication)
./mcp/scripts/scan_secrets.sh --history
```

### Cache Isolation

Each target gets its own cache directory:
```
~/.cache/github-project-mcp/{org}/{repo}/project-{N}/metadata.json
```

Cache files have `0600` permissions and are never shared between targets.

---

## Troubleshooting

| Problem | Diagnostic | Fix |
|---------|-----------|-----|
| "Missing required configuration" | Missing env vars | Set `GH_PROJECT_ORG_NAME`, `REPO_NAME`, `PROJECT_NUMBER` |
| "No GitHub token found" | No token in any source | Set `GITHUB_TOKEN` or run `gh auth login` |
| "Insufficient token scopes" | Token missing permissions | Regenerate with `repo`, `project`, `read:org` |
| "Permission denied" on cache | Container user issue | Image uses `/home/mcp/.cache` (writable) |
| Token works locally but not in CI | Secret not set | Check Settings → Secrets → `GH_TOKEN` |
| Fine-grained token "scope error" | FG tokens don't report scopes | MCP auto-detects and skips validation |
