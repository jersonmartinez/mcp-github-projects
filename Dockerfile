# syntax=docker/dockerfile:1
# ── GitHub Project Management MCP Server ─────────────────────────────────────
# Generic MCP server for GitHub Projects V2 with gh CLI.

FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

LABEL org.opencontainers.image.title="GitHub Project MCP Server" \
      org.opencontainers.image.description="Generic MCP server for GitHub Projects V2 management" \
      org.opencontainers.image.source="https://github.com/jersonmartinez/github-project-mcp"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install gh CLI (required for project management operations)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gpg \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
       | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
       > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get purge -y curl gpg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/false --uid 1000 mcp \
    && mkdir -p /home/mcp/.cache/github-project-mcp \
    && chown -R mcp:mcp /home/mcp/.cache

WORKDIR /app

COPY requirements.txt .
COPY requirements-dev.txt .
ARG INSTALL_TEST_DEPS=false
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_TEST_DEPS" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY --chown=mcp:mcp . .

USER mcp

# The MCP server runs with stdio transport
CMD ["python", "server.py"]
