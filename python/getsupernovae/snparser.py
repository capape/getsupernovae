"""Compatibility shim for `snparser`.

This module was migrated to `app.utils.snparser`. Keep a thin shim
here to preserve existing import paths while the refactor completes.
"""

try:
    from app.utils.snparser import *  # noqa: F401,F403
except Exception as _exc:  # pragma: no cover - fail early if migration incomplete
    raise
