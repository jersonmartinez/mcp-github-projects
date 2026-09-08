"""Backward-compatibility shim — canonical module is `core.error_handling`.

This module re-exports the canonical implementation so historical imports
(`error_handling`) keep resolving. New code MUST import from `core.error_handling`.
See docs/architecture/PROJECT_STRUCTURE.md §1 (compatibility layer).
"""
import core.error_handling as _canon  # noqa: E402

# Re-export every module-level name (including non-__all__ symbols such as
# imported client classes that tests patch) so `patch('error_handling.X')` resolves
# against the SAME object the canonical module uses.
globals().update(
    {k: v for k, v in vars(_canon).items() if not k.startswith('__')}
)
del _canon
