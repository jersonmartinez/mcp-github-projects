"""GitHub CLI client for executing `gh` commands asynchronously.

Provides a thin async wrapper around the `gh` CLI tool using
asyncio.create_subprocess_exec. Handles timeouts, non-zero exit codes,
and JSON output parsing.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from core.config import get_settings
from core.hardening import bounded_text, redact_sensitive
from models.context import GitHubContext


# ── Custom Exceptions ────────────────────────────────────────────────────────


class CLIError(Exception):
    """Raised when `gh` exits with a non-zero return code."""

    def __init__(self, message: str, return_code: int, stderr: str) -> None:
        self.return_code = return_code
        self.stderr = bounded_text(stderr)
        super().__init__(bounded_text(message))


class CLITimeoutError(Exception):
    """Raised when a `gh` command exceeds the configured timeout."""

    def __init__(self, message: str, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message)


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of a successful `gh` CLI command execution."""

    stdout: str
    stderr: str
    return_code: int


def _safe_command(args: list[str]) -> str:
    """Render a command without exposing tokens or unbounded user content."""
    secrets = [os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GH_TOKEN", "")]
    rendered = [bounded_text(redact_sensitive(arg, secrets), 200) for arg in args]
    return "gh " + " ".join(rendered)


# ── Client ───────────────────────────────────────────────────────────────────


class GHCLIClient:
    """Async client for executing GitHub CLI commands."""

    def __init__(self, context: GitHubContext | None = None) -> None:
        self._context = context

    async def run(self, args: list[str]) -> CommandResult:
        """Execute a `gh` command with the given arguments.
            args: List of arguments to pass to `gh`
                  (e.g., ["issue", "create", "--title", "Bug fix"]).

        Returns:
            CommandResult with stdout, stderr, and return_code (always 0).

        Raises:
            CLIError: If the command exits with a non-zero return code.
            CLITimeoutError: If the command exceeds the configured timeout.
        """
        settings = get_settings()
        timeout = settings.timeout_seconds
        environment = os.environ.copy()
        if self._context is not None:
            environment["GH_TOKEN"] = await self._context.resolve_token()

        process = await asyncio.create_subprocess_exec(
            "gh",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise CLITimeoutError(
                f"gh command timed out after {timeout} seconds: {_safe_command(args)}",
                timeout_seconds=timeout,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        return_code = process.returncode or 0
        if len(stdout) + len(stderr) > settings.max_cli_output_chars:
            raise CLIError(
                "gh command output exceeded the configured safety limit",
                return_code=return_code,
                stderr="Output truncated by MCP safety limit",
            )

        if return_code != 0:
            raise CLIError(
                f"gh command failed (exit {return_code}): {stderr.strip()}",
                return_code=return_code,
                stderr=stderr,
            )

        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
        )

    async def api_graphql(self, query: str, variables: dict[str, Any]) -> dict:
        """Execute a GraphQL query via `gh api graphql`.

        Constructs the `gh api graphql` command with the provided query
        and variables, parses the JSON output, and returns the result.

        Args:
            query: The GraphQL query string.
            variables: A dict of variable names to string values.
                       Each entry is passed as a `-f varName=value` flag.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            CLIError: If the command exits with a non-zero return code.
            CLITimeoutError: If the command exceeds the configured timeout.
            ValueError: If the command output is not valid JSON.
        """
        args: list[str] = ["api", "graphql", "-f", f"query={query}"]

        for var_name, value in variables.items():
            if isinstance(value, str):
                args.extend(["-f", f"{var_name}={value}"])
            else:
                encoded = json.dumps(value, separators=(",", ":"))
                args.extend(["-F", f"{var_name}={encoded}"])

        result = await self.run(args)

        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse JSON output from gh api graphql: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError("Expected an object from gh api graphql")
        return value
