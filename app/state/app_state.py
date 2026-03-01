"""Application state management.

This module provides centralized state management for the application using
dataclasses and the observer pattern for reactive updates.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class SearchState:
    """State for search/filter parameters."""

    magnitude: str = "17.5"
    days_to_search: str = "30"
    observation_date: str = ""
    observation_time: str = ""
    observation_duration: str = "6"
    site: Optional[str] = None  # Site name (e.g., "Home", "Sabadell")
    visibility_window: Optional[str] = None  # Visibility window name (e.g., "Default", "Evening")
    min_latitude: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SearchState":
        """Create SearchState from dictionary."""
        # Filter out unknown keys to handle missing/extra fields gracefully
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class ResultsState:
    """State for search results and related data."""

    supernovas_found: int = 0
    cached_dto_list: List[Any] = field(default_factory=list)
    refreshing: bool = False
    last_error: Optional[str] = None
    sort_column: int = 0
    sort_reverse: bool = False
    selected_items: List[str] = field(default_factory=list)

    def clear_results(self) -> None:
        """Clear all result data."""
        self.supernovas_found = 0
        self.cached_dto_list = []
        self.last_error = None
        self.selected_items = []

    def has_results(self) -> bool:
        """Check if results exist."""
        return self.supernovas_found > 0

    def has_cached_data(self) -> bool:
        """Check if cached data exists for re-filtering."""
        return len(self.cached_dto_list) > 0


@dataclass
class UIState:
    """State for UI preferences and window configuration."""

    language: str = "en"
    dark_mode: bool = False
    window_width: Optional[int] = None
    window_height: Optional[int] = None
    window_x: Optional[int] = None
    window_y: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UIState":
        """Create UIState from dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class AppState:
    """Top-level application state containing all sub-states."""

    search: SearchState = field(default_factory=SearchState)
    results: ResultsState = field(default_factory=ResultsState)
    ui: UIState = field(default_factory=UIState)

    def to_dict(self) -> dict:
        """Convert to dictionary. Note: results are not persisted."""
        return {
            "search": self.search.to_dict(),
            "ui": self.ui.to_dict(),
            # Don't persist results - they're transient
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppState":
        """Create AppState from dictionary."""
        state = cls()

        if "search" in data and isinstance(data["search"], dict):
            state.search = SearchState.from_dict(data["search"])

        if "ui" in data and isinstance(data["ui"], dict):
            state.ui = UIState.from_dict(data["ui"])

        # results are not loaded from persistence
        return state


class AppStateManager:
    """Manages application state with observer pattern for change notifications.

    Usage:
        state_mgr = AppStateManager()

        # Listen to search state changes
        def on_search_changed(search_state):
            print(f"Search state changed: {search_state}")

        state_mgr.add_listener('search', on_search_changed)

        # Update state (triggers listeners)
        state_mgr.update_search_state(magnitude="15", site="TestSite")
    """

    VALID_CATEGORIES = {"search", "results", "ui", "all"}

    def __init__(self, initial_state: Optional[AppState] = None):
        """Initialize state manager.

        Args:
            initial_state: Optional initial state. If None, uses default state.
        """
        self.state = initial_state or AppState()
        self._listeners = {
            "search": [],
            "results": [],
            "ui": [],
            "all": [],
        }

    def add_listener(self, category: str, callback: Callable) -> None:
        """Add a listener for state changes.

        Args:
            category: Category to listen to ('search', 'results', 'ui', 'all')
            callback: Function to call when state changes.
                     For specific categories: callback(state_obj)
                     For 'all' category: callback(category_name, state_obj)

        Raises:
            ValueError: If category is invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}"
            )

        if callback not in self._listeners[category]:
            self._listeners[category].append(callback)

    def remove_listener(self, category: str, callback: Callable) -> None:
        """Remove a listener.

        Args:
            category: Category the listener is registered for
            callback: The callback function to remove
        """
        if category in self._listeners and callback in self._listeners[category]:
            self._listeners[category].remove(callback)

    def notify_listeners(self, category: str) -> None:
        """Notify all listeners of a state change.

        Args:
            category: Category that changed ('search', 'results', 'ui')

        Raises:
            ValueError: If category is invalid
        """
        if category not in self.VALID_CATEGORIES or category == "all":
            raise ValueError(f"Invalid category for notification: {category}")

        # Get the specific state object
        if category == "search":
            state_obj = self.state.search
        elif category == "results":
            state_obj = self.state.results
        elif category == "ui":
            state_obj = self.state.ui
        else:
            state_obj = None

        # Notify category-specific listeners with the state object
        for callback in self._listeners[category]:
            try:
                callback(state_obj)
            except Exception:
                # Don't let listener errors stop other listeners
                pass

        # Notify 'all' listeners with category name and state object
        for callback in self._listeners["all"]:
            try:
                callback(category, state_obj)
            except Exception:
                pass

    def update_search_state(self, **kwargs) -> None:
        """Update search state fields and notify listeners.

        Args:
            **kwargs: Field names and values to update in SearchState
        """
        for key, value in kwargs.items():
            if hasattr(self.state.search, key):
                setattr(self.state.search, key, value)

        self.notify_listeners("search")

    def update_results_state(self, **kwargs) -> None:
        """Update results state fields and notify listeners.

        Args:
            **kwargs: Field names and values to update in ResultsState
        """
        for key, value in kwargs.items():
            if hasattr(self.state.results, key):
                setattr(self.state.results, key, value)

        self.notify_listeners("results")

    def update_ui_state(self, **kwargs) -> None:
        """Update UI state fields and notify listeners.

        Args:
            **kwargs: Field names and values to update in UIState
        """
        for key, value in kwargs.items():
            if hasattr(self.state.ui, key):
                setattr(self.state.ui, key, value)

        self.notify_listeners("ui")

    def clear_results(self) -> None:
        """Clear results state and notify listeners."""
        self.state.results.clear_results()
        self.notify_listeners("results")

    def reset_to_defaults(self) -> None:
        """Reset all state to defaults and notify all listeners."""
        self.state = AppState()

        # Notify all categories individually (not 'all' which would raise ValueError)
        for category in ["search", "results", "ui"]:
            for callback in self._listeners["all"]:
                try:
                    callback(category)
                except Exception:
                    pass
