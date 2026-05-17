"""State management package.

Provides centralized state management with:
- Type-safe state classes using dataclasses
- Observer pattern for reactive updates
- State persistence support
"""

from app.state.app_state import (
    AppState,
    AppStateManager,
    ResultsState,
    SearchState,
    UIState,
)
from app.state.preferences_manager import (
    PreferencesManager,
    load_user_prefs,
    migrate_legacy_prefs,
    save_user_prefs,
)

__all__ = [
    "SearchState",
    "ResultsState",
    "UIState",
    "AppState",
    "AppStateManager",
    "PreferencesManager",
    "save_user_prefs",
    "load_user_prefs",
    "migrate_legacy_prefs",
]
