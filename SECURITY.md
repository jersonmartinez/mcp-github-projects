# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. Email: jersonmartinezsm@gmail.com with subject "SECURITY: github-project-mcp"
3. Include: description, reproduction steps, impact assessment
4. Expected response time: 48 hours

## Security Design Principles

- Tokens are NEVER logged, serialized, or included in responses
- Cache files use owner-only permissions (0600)
- Profile files must NOT contain token values
- Scope validation runs at startup before any operation
- All CLI output is bounded and redacted for token-like patterns
