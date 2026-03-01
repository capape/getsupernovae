"""Preferences Coordinator

This module coordinates preferences loading, saving, and UI synchronization.
Handles persisting user preferences and applying them to UI components.
"""

import tkinter as tk
from typing import Any, Callable, Dict, Optional

from app.config.snconfig import load_user_prefs
from app.i18n import set_language
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class PreferencesCoordinator:
    """Coordinates preferences persistence and UI synchronization.

    This coordinator handles:
    - Saving current UI state to disk
    - Loading saved preferences and applying to UI
    - Migrating legacy preferences format
    - Updating visibility UI based on window selection

    Follows Single Responsibility Principle by focusing on preferences orchestration.
    Uses callbacks to avoid tight coupling with the main application.
    """

    def __init__(
        self,
        state_manager: Any,
        preferences_manager: Any,
        get_initializing_flag: Callable[[], bool],
        get_tk_variables: Callable[[], Dict[str, tk.Variable]],
        get_sites: Callable[[], Dict[str, Any]],
        get_visibility_windows: Callable[[], Dict[str, Any]],
        get_filter_panel_manager: Callable[[], Optional[Any]],
        get_language_coordinator: Callable[[], Optional[Any]],
        get_theme_coordinator: Callable[[], Optional[Any]],
    ):
        """Initialize the preferences coordinator.

        Args:
            state_manager: Application state manager
            preferences_manager: Preferences persistence manager
            get_initializing_flag: Callback to check if app is initializing
            get_tk_variables: Callback to get dict of Tk variables
            get_sites: Callback to get sites dictionary
            get_visibility_windows: Callback to get visibility windows dictionary
            get_filter_panel_manager: Callback to get filter panel manager
            get_language_coordinator: Callback to get language coordinator
            get_theme_coordinator: Callback to get theme coordinator
        """
        self.state_manager = state_manager
        self.preferences_manager = preferences_manager
        self.get_initializing_flag = get_initializing_flag
        self.get_tk_variables = get_tk_variables
        self.get_sites = get_sites
        self.get_visibility_windows = get_visibility_windows
        self.get_filter_panel_manager = get_filter_panel_manager
        self.get_language_coordinator = get_language_coordinator
        self.get_theme_coordinator = get_theme_coordinator

    def update_visibility_ui(self):
        """Enable/disable minLatitude entry depending on visibility window selection.

        If a named visibility window is selected (present in `visibility_windows`),
        disable the `minLatitude` entry and show its numeric values in
        `visibilityValuesLabel`. If no valid window is selected, enable the
        `minLatitude` entry and clear the label.
        """
        try:
            tk_vars = self.get_tk_variables()
            visibility_window_var = tk_vars.get("visibilityWindow")

            sel = ""
            if visibility_window_var:
                try:
                    sel = visibility_window_var.get() or ""
                except (AttributeError, tk.TclError):
                    log_exception(logger, "Failed to read selected visibility window")
                    sel = ""

            visibility_windows = self.get_visibility_windows()
            filter_panel_manager = self.get_filter_panel_manager()

            if not filter_panel_manager:
                return

            if sel and sel in visibility_windows:
                cfg = visibility_windows.get(sel, {})
                min_alt = cfg.get("min_alt", 0.0)
                max_alt = cfg.get("max_alt", 90.0)
                min_az = cfg.get("min_az", 0.0)
                max_az = cfg.get("max_az", 360.0)
                txt = (
                    f"min_alt: {min_alt:.1f}°  max_alt: {max_alt:.1f}°  "
                    f"min_az: {min_az:.1f}°  max_az: {max_az:.1f}°"
                )

                filter_panel_manager.update_visibility_values_label(txt)
                filter_panel_manager.set_min_latitude_state("disabled")
            else:
                filter_panel_manager.update_visibility_values_label("")
                filter_panel_manager.set_min_latitude_state("normal")

        except (AttributeError, TypeError, KeyError):
            log_exception(logger, "Failed to update visibility UI")

    def persist_prefs(self, *_args):
        """Collect current tracked UI values and persist them to disk."""
        # Don't persist during initialization (before prefs are loaded)
        if self.get_initializing_flag():
            return

        try:
            tk_vars = self.get_tk_variables()

            # Update state manager with current UI values (store names, not computed values)
            self.state_manager.update_search_state(
                magnitude=self._get_var_value(tk_vars, "magnitude", ""),
                days_to_search=self._get_var_value(tk_vars, "days_to_search", "30"),
                observation_date=self._get_var_value(tk_vars, "observation_date", ""),
                observation_time=self._get_var_value(tk_vars, "observation_time", ""),
                observation_duration=self._get_var_value(tk_vars, "observation_duration", ""),
                site=self._get_var_value(tk_vars, "site", None),
                visibility_window=self._get_var_value(tk_vars, "visibility_window", None),
                min_latitude=self._get_var_value(tk_vars, "min_latitud", ""),
            )

            self.state_manager.update_ui_state(
                language=self._get_var_value(tk_vars, "lang_var", "en"),
                dark_mode=self._get_var_value(tk_vars, "dark_mode", False),
            )

            # Save to disk using preferences manager
            try:
                self.preferences_manager.save_preferences(self.state_manager.state)
            except (OSError, IOError, AttributeError, TypeError):
                log_exception(logger, "Failed to save preferences to disk")
        except (AttributeError, TypeError, KeyError):
            log_exception(logger, "Failed to persist preferences")

    def load_and_apply_prefs(self):
        """Load persisted prefs and apply to UI variables where valid."""
        try:
            # Try to load new format first
            loaded_state = self.preferences_manager.load_preferences()

            # If no new format exists, try to migrate from old format
            if loaded_state is None:
                loaded_state = self._migrate_legacy_preferences()

            if loaded_state is None:
                return

            # Update state manager with loaded state
            self.state_manager.state = loaded_state

            # Apply loaded state to UI
            self._apply_search_state(loaded_state)
            self._apply_ui_state(loaded_state)

            # Update visibility UI
            try:
                self.update_visibility_ui()
            except (AttributeError, TypeError, KeyError):
                log_exception(
                    logger,
                    "Failed to refresh visibility UI after restoring preferences",
                )
        except (OSError, IOError, AttributeError, TypeError, KeyError):
            log_exception(logger, "Failed to load and apply preferences")

    def _get_var_value(self, tk_vars: Dict[str, tk.Variable], key: str, default: Any) -> Any:
        """Safely get value from Tk variable."""
        var = tk_vars.get(key)
        if var:
            try:
                return var.get()
            except (AttributeError, tk.TclError):
                return default
        return default

    def _migrate_legacy_preferences(self) -> Optional[Any]:
        """Migrate old flat dict format to new state structure."""
        try:
            old_prefs = load_user_prefs()
            if old_prefs and isinstance(old_prefs, dict):
                # Migrate old flat dict format to new state structure
                # pylint: disable=import-outside-toplevel  # Avoid circular dependency
                from app.state.app_state import AppState

                loaded_state = AppState()

                # Map old keys to new state
                if "magnitude" in old_prefs:
                    loaded_state.search.magnitude = old_prefs["magnitude"]
                if "daysToSearch" in old_prefs:
                    loaded_state.search.days_to_search = old_prefs["daysToSearch"]
                if "observationTime" in old_prefs:
                    loaded_state.search.observation_time = old_prefs["observationTime"]
                if "observationHours" in old_prefs:
                    loaded_state.search.observation_duration = old_prefs["observationHours"]
                if "minLatitude" in old_prefs:
                    loaded_state.search.min_latitude = old_prefs["minLatitude"]
                if "site" in old_prefs:
                    loaded_state.search.site = old_prefs["site"]
                if "visibilityWindow" in old_prefs:
                    loaded_state.search.visibility_window = old_prefs["visibilityWindow"]
                if "language" in old_prefs:
                    loaded_state.ui.language = old_prefs["language"]

                # Save in new format for next time
                self.preferences_manager.save_preferences(loaded_state)
                return loaded_state
        except (OSError, IOError, AttributeError, TypeError, KeyError):
            log_exception(logger, "Failed to migrate legacy preferences")

        return None

    def _apply_search_state(self, loaded_state: Any):
        """Apply search state to UI variables."""
        tk_vars = self.get_tk_variables()

        # Apply magnitude
        try:
            if loaded_state.search.magnitude:
                var = tk_vars.get("magnitude")
                if var:
                    var.set(str(loaded_state.search.magnitude))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore magnitude preference")

        # Apply days to search
        try:
            if loaded_state.search.days_to_search:
                var = tk_vars.get("days_to_search")
                if var:
                    var.set(str(loaded_state.search.days_to_search))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore days_to_search preference")

        # Apply observation date
        try:
            if loaded_state.search.observation_date:
                var = tk_vars.get("observation_date")
                if var:
                    var.set(str(loaded_state.search.observation_date))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore observation_date preference")

        # Apply observation time
        try:
            if loaded_state.search.observation_time:
                var = tk_vars.get("observation_time")
                if var:
                    var.set(str(loaded_state.search.observation_time))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore observation_time preference")

        # Apply observation duration
        try:
            if loaded_state.search.observation_duration:
                var = tk_vars.get("observation_duration")
                if var:
                    var.set(str(loaded_state.search.observation_duration))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore observation_duration preference")

        # Apply min latitude
        try:
            if loaded_state.search.min_latitude:
                var = tk_vars.get("min_latitud")
                if var:
                    var.set(str(loaded_state.search.min_latitude))
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore min_latitude preference")

        # Apply site
        try:
            site = loaded_state.search.site
            sites = self.get_sites()
            if site and site in list(sites.keys()):
                var = tk_vars.get("site")
                if var:
                    var.set(site)
        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, "Failed to restore site preference")

        # Apply visibility window
        try:
            vw = loaded_state.search.visibility_window
            visibility_windows = self.get_visibility_windows()
            if vw and vw in visibility_windows:
                var = tk_vars.get("visibility_window")
                if var:
                    var.set(vw)
        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, "Failed to restore visibility window preference")

    def _apply_ui_state(self, loaded_state: Any):
        """Apply UI state (language, theme) to UI."""
        tk_vars = self.get_tk_variables()

        # Apply language
        try:
            lang = loaded_state.ui.language
            if lang:
                try:
                    set_language(lang)
                    langvar = tk_vars.get("lang_var")
                    if langvar:
                        langvar.set(lang)

                    # Refresh UI after language restoration
                    try:
                        lang_coordinator = self.get_language_coordinator()
                        if lang_coordinator:
                            lang_coordinator.on_language_change()
                    except (AttributeError, TypeError, ImportError):
                        log_exception(logger, "Failed to refresh UI after language restoration")
                except (AttributeError, tk.TclError, TypeError, ImportError):
                    log_exception(logger, "Failed to apply restored language")
        except (AttributeError, TypeError):
            log_exception(logger, "Failed while restoring language preference")

        # Apply dark mode theme
        try:
            dark_mode = loaded_state.ui.dark_mode
            if dark_mode is not None:
                dark_mode_var = tk_vars.get("dark_mode")
                if dark_mode_var:
                    dark_mode_var.set(dark_mode)

                    # Apply theme
                    try:
                        theme_coordinator = self.get_theme_coordinator()
                        if theme_coordinator:
                            theme_coordinator.apply_theme()
                    except (AttributeError, TypeError, tk.TclError):
                        log_exception(logger, "Failed to apply restored dark mode theme")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to restore dark mode preference")
