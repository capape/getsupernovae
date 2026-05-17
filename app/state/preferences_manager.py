"""Preferences persistence manager.

Handles saving and loading application preferences to/from JSON files,
with legacy compatibility for existing preference format.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.config.snconfig import get_user_config_dir
from app.state.app_state import AppState


class PreferencesManager:
    """Manages application preferences persistence."""

    DEFAULT_PREFS_DIR = Path(get_user_config_dir())
    DEFAULT_PREFS_FILE = "preferences.json"

    def __init__(self, prefs_dir: Optional[Path] = None, prefs_file: str = DEFAULT_PREFS_FILE):
        """Initialize preferences manager.

        Args:
            prefs_dir: Directory for preferences file (default: from get_user_config_dir())
            prefs_file: Preferences filename (default: preferences.json)
        """
        self.prefs_dir = prefs_dir or self.DEFAULT_PREFS_DIR
        self.prefs_file = prefs_file
        self.prefs_path = self.prefs_dir / self.prefs_file

    def _ensure_prefs_dir(self) -> bool:
        """Ensure preferences directory exists.

        Returns:
            True if directory exists or was created successfully, False otherwise
        """
        try:
            self.prefs_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            print(f"Error creating preferences directory: {e}")
            return False

    def save_preferences(self, state: AppState) -> bool:
        """Save application state to preferences file.

        Args:
            state: Application state to save

        Returns:
            True if successful, False otherwise
        """
        # Ensure preferences directory exists before saving
        if not self._ensure_prefs_dir():
            return False

        try:
            prefs_data = state.to_dict()
            with open(self.prefs_path, "w", encoding="utf-8") as f:
                json.dump(prefs_data, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, IOError, TypeError) as e:
            print(f"Error saving preferences: {e}")
            return False

    def load_preferences(self) -> Optional[AppState]:
        """Load application state from preferences file.

        Returns:
            AppState if successful, None if file doesn't exist or error
        """
        if not self.prefs_path.exists():
            return None

        try:
            with open(self.prefs_path, "r", encoding="utf-8") as f:
                prefs_data = json.load(f)
            return AppState.from_dict(prefs_data)
        except (
            OSError,
            IOError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            KeyError,
            AttributeError,
            TypeError,
        ) as e:
            print(f"Error loading preferences: {e}")
            return None

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a single preference value.

        Args:
            key: Dot-separated key path (e.g., 'search.magnitude', 'ui.language')
            default: Default value if key not found

        Returns:
            Preference value or default
        """
        state = self.load_preferences()
        if state is None:
            return default

        try:
            keys = key.split(".")
            obj = state
            for k in keys:
                if hasattr(obj, k):
                    obj = getattr(obj, k)
                else:
                    return default
            return obj
        except (KeyError, AttributeError, TypeError, IndexError):
            return default

    def set_preference(self, key: str, value: Any) -> bool:
        """Set a single preference value.

        Args:
            key: Dot-separated key path (e.g., 'search.magnitude', 'ui.language')
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        state = self.load_preferences() or AppState()

        try:
            keys = key.split(".")
            if len(keys) != 2:
                return False

            category, attr = keys
            if category == "search" and hasattr(state.search, attr):
                setattr(state.search, attr, value)
            elif category == "ui" and hasattr(state.ui, attr):
                setattr(state.ui, attr, value)
            elif category == "results" and hasattr(state.results, attr):
                setattr(state.results, attr, value)
            else:
                return False

            return self.save_preferences(state)
        except (AttributeError, TypeError, ValueError, OSError, IOError) as e:
            print(f"Error setting preference: {e}")
            return False

    def clear_preferences(self) -> bool:
        """Delete preferences file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.prefs_path.exists():
                self.prefs_path.unlink()
            return True
        except (OSError, IOError, PermissionError) as e:
            print(f"Error clearing preferences: {e}")
            return False

    def preferences_exist(self) -> bool:
        """Check if preferences file exists.

        Returns:
            True if preferences file exists
        """
        return self.prefs_path.exists()


# Legacy compatibility functions for existing code


def save_user_prefs(
    site: Optional[str],
    _latitude: Optional[float],
    _longitude: Optional[float],
    magnitude: str,
    days: str,
    duration: str,
    language: str,
    min_latitude: str = "",
) -> bool:
    """Save user preferences (legacy compatibility function).

    Args:
        site: Observatory site name
        _latitude: Site latitude (ignored - kept for backward compatibility)
        _longitude: Site longitude (ignored - kept for backward compatibility)
        magnitude: Magnitude limit
        days: Days to search
        duration: Observation duration
        language: UI language
        min_latitude: Minimum latitude filter

    Returns:
        True if successful, False otherwise
    """
    manager = PreferencesManager()

    # Load existing state or create new one
    state = manager.load_preferences() or AppState()

    # Update search state (latitude/longitude ignored - site name is sufficient)
    state.search.site = site
    state.search.magnitude = magnitude
    state.search.days_to_search = days
    state.search.observation_duration = duration
    state.search.min_latitude = min_latitude

    # Update UI state
    state.ui.language = language

    return manager.save_preferences(state)


def load_user_prefs() -> Optional[Dict[str, Any]]:
    """Load user preferences (legacy compatibility function).

    Returns:
        Dictionary with preferences in legacy format, or None if not found
    """
    manager = PreferencesManager()
    state = manager.load_preferences()

    if state is None:
        return None

    # Convert to legacy format (latitude/longitude always None now)
    return {
        "site": state.search.site,
        "latitude": None,
        "longitude": None,
        "magnitude": state.search.magnitude,
        "days": state.search.days_to_search,
        "duration": state.search.observation_duration,
        "language": state.ui.language,
        "min_latitude": state.search.min_latitude,
    }


def migrate_legacy_prefs(legacy_path: Optional[Path] = None) -> bool:
    """Migrate preferences from old format to new format.

    Args:
        legacy_path: Path to legacy preferences file (if different from default)

    Returns:
        True if migration successful or not needed, False on error
    """
    if legacy_path is None:
        legacy_path = PreferencesManager.DEFAULT_PREFS_DIR / "config.json"

    if not legacy_path.exists():
        return True  # No legacy file to migrate

    try:
        with open(legacy_path, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)

        # Create new state from legacy data
        state = AppState()

        # Map legacy fields to new state
        if "site" in legacy_data:
            state.search.site = legacy_data["site"]
        # latitude/longitude ignored - site name is sufficient
        if "magnitude" in legacy_data:
            state.search.magnitude = legacy_data["magnitude"]
        if "days" in legacy_data:
            state.search.days_to_search = legacy_data["days"]
        if "duration" in legacy_data:
            state.search.observation_duration = legacy_data["duration"]
        if "min_latitude" in legacy_data:
            state.search.min_latitude = legacy_data["min_latitude"]
        if "language" in legacy_data:
            state.ui.language = legacy_data["language"]

        # Save to new format
        manager = PreferencesManager()
        return manager.save_preferences(state)

    except (
        OSError,
        IOError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
        AttributeError,
        TypeError,
        ValueError,
    ) as e:
        print(f"Error migrating legacy preferences: {e}")
        return False
