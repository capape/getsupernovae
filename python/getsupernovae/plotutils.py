"""Compatibility shim for plotutils.

Re-export the implementation from `app.reports.plotutils` so other modules
can continue importing `plotutils` while we migrate.
"""
try:
    from app.reports.plotutils import *  # noqa: F401,F403
except Exception:
    raise
