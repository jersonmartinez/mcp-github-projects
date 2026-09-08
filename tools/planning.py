"""Backward-compatibility shim — canonical module is `tools.planning.planning`.

This module re-exports the canonical implementation so historical imports
(`tools.planning`) keep resolving. New code MUST import from `tools.planning.planning`.
See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import tools.planning.planning as _canon  # noqa: E402

# Re-export every module-level name (including non-__all__ symbols such as
# imported client classes that tests patch) so `patch('tools.planning.X')` resolves
# against the SAME object the canonical module uses.
globals().update(
    {k: v for k, v in vars(_canon).items() if not k.startswith('__')}
)
del _canon
