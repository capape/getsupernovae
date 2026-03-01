"""Filter Panel Manager

This module manages the left filter panel UI components for the supernova application.
Follows SOLID principles by isolating UI creation, event handling, and state management
for the filter controls.
"""

import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from app.config.ui_constants import (
    THEME_COLORS,
    UI_CONSTANTS,
    UI_STRINGS,
)
from app.i18n import _, get_language, set_language
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


@dataclass
class FilterPanelCallbacks:
    """Callbacks for filter panel interactions."""

    on_clear_results: Callable[[], None]
    on_persist_prefs: Callable[[], None]
    on_update_visibility_ui: Callable[[], None]
    on_language_change: Callable[[], None]
    on_add_site: Callable[[], None]
    on_add_visibility_window: Callable[[], None]


class FilterPanelManager:
    """Manages the filter panel UI components and their interactions.

    This class is responsible for:
    - Creating all filter panel widgets (labels, entries, comboboxes)
    - Setting up event bindings
    - Managing widget state (enable/disable)
    - Coordinating with callbacks for business logic

    Follows Single Responsibility Principle by focusing only on UI management.
    """

    def __init__(
        self,
        parent: tk.Widget,
        variables: Dict[str, tk.StringVar],
        sites: Dict[str, Any],
        visibility_windows: Dict[str, Dict[str, float]],
        callbacks: FilterPanelCallbacks,
        dark_mode: Optional[tk.BooleanVar] = None,
    ):
        """Initialize the filter panel manager.

        Args:
            parent: Parent widget to contain the filter panel
            variables: Dictionary of tk.StringVar objects for form fields
            sites: Dictionary of available observation sites
            visibility_windows: Dictionary of visibility window configurations
            callbacks: FilterPanelCallbacks object with event handlers
            dark_mode: Optional BooleanVar for dark mode state
        """
        self.parent = parent
        self.variables = variables
        self.sites = sites
        self.visibility_windows = visibility_windows
        self.callbacks = callbacks
        self.dark_mode = dark_mode

        # Widget references
        self.frame: Optional[ttk.Frame] = None
        self.widgets: Dict[str, tk.Widget] = {}

    def build(self) -> ttk.Frame:
        """Build and return the filter panel frame with all widgets.

        Returns:
            ttk.Frame containing all filter panel widgets
        """
        self.frame = ttk.Frame(self.parent)
        self.frame.grid(column=0, row=1, rowspan=11, columnspan=3, sticky="nw", padx=5, pady=5)

        # Configure columns
        try:
            self.frame.grid_columnconfigure(0, weight=0)
            self.frame.grid_columnconfigure(1, weight=0)
            self.frame.grid_columnconfigure(2, weight=0)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to configure filter panel grid columns")

        # Build all filter controls
        self._build_magnitude_control(row=0)
        self._build_days_to_search_control(row=1)
        self._build_observation_date_control(row=2)
        self._build_init_time_control(row=3)
        self._build_duration_control(row=4)
        self._build_site_control(row=5)
        self._build_visibility_window_control(row=6)
        self._build_min_latitude_control(row=7)
        self._build_visibility_values_label(row=8)
        self._build_language_control(row=9)
        self._build_rochester_attribution(row=10)

        # Set up change callbacks
        self._setup_variable_traces()

        return self.frame

    def _build_magnitude_control(self, row: int) -> None:
        """Build magnitude input control."""
        label = ttk.Label(self.frame, text=_("Max. magnitude: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_magnitude"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["magnitude"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_magnitude"] = entry

    def _build_days_to_search_control(self, row: int) -> None:
        """Build days to search input control."""
        label = ttk.Label(self.frame, text=_("Find the n previous days: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_days_to_search"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["days_to_search"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_days_to_search"] = entry

    def _build_observation_date_control(self, row: int) -> None:
        """Build observation date input control."""
        label = ttk.Label(self.frame, text=_("Observation date: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_observation_date"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["observation_date"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_observation_date"] = entry

    def _build_init_time_control(self, row: int) -> None:
        """Build init time input control."""
        label = ttk.Label(self.frame, text=_("Init time in observation date: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_init_time"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["observation_time"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_init_time"] = entry

    def _build_duration_control(self, row: int) -> None:
        """Build observation duration input control."""
        label = ttk.Label(self.frame, text=_("Hours of observation: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_duration"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["observation_duration"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_duration"] = entry

    def _build_site_control(self, row: int) -> None:
        """Build site selection control with edit button."""
        label = ttk.Label(self.frame, text=_("Site: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_site"] = label

        site_values = sorted(list(self.sites.keys()))
        combobox = ttk.Combobox(self.frame, values=site_values, textvariable=self.variables["site"])
        combobox.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["combobox_site"] = combobox

        button = ttk.Button(
            self.frame,
            text=UI_STRINGS.EDIT_ICON,
            width=UI_CONSTANTS.EDIT_BUTTON_WIDTH,
            command=self.callbacks.on_add_site,
        )
        button.grid(column=2, row=row, padx=(2, 10), pady=5, sticky=tk.W)
        self.widgets["button_add_site"] = button

    def _build_visibility_window_control(self, row: int) -> None:
        """Build visibility window selection control with edit button."""
        label = ttk.Label(self.frame, text=_("Visibility window:"))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_visibility"] = label

        vis_values = [""] + sorted(list(self.visibility_windows.keys()))
        combobox = ttk.Combobox(
            self.frame, values=vis_values, textvariable=self.variables["visibility_window"]
        )
        combobox.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["combobox_visibility"] = combobox

        # Bind selection event
        try:
            combobox.bind(
                "<<ComboboxSelected>>", lambda ev: self.callbacks.on_update_visibility_ui()
            )
        except (AttributeError, tk.TclError):
            try:
                self.variables["visibility_window"].trace_add(
                    "write", lambda *a: self.callbacks.on_update_visibility_ui()
                )
            except (AttributeError, tk.TclError, TypeError):
                log_exception(logger, "Failed to bind visibility window updates")

        button = ttk.Button(
            self.frame,
            text=UI_STRINGS.EDIT_ICON,
            width=UI_CONSTANTS.EDIT_BUTTON_WIDTH,
            command=self.callbacks.on_add_visibility_window,
        )
        button.grid(column=2, row=row, padx=(2, 10), pady=5, sticky=tk.W)
        self.widgets["button_add_visibility"] = button

    def _build_min_latitude_control(self, row: int) -> None:
        """Build minimum latitude input control."""
        label = ttk.Label(self.frame, text=_("Min latitude: "))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_min_latitude"] = label

        entry = ttk.Entry(self.frame, textvariable=self.variables["min_latitude"])
        entry.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["entry_min_latitude"] = entry

    def _build_visibility_values_label(self, row: int) -> None:
        """Build label to display visibility window values."""
        label = ttk.Label(self.frame, text="", justify=tk.LEFT)
        label.grid(column=0, row=row, padx=5, columnspan=3, pady=(0, 6), sticky=tk.W)
        self.widgets["label_visibility_values"] = label

    def _build_language_control(self, row: int) -> None:
        """Build language selection control."""
        label = ttk.Label(self.frame, text=_("Language:"))
        label.grid(column=0, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["label_language"] = label

        # Get available languages
        try:
            locales_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "locales"
            )
            lang_values = [
                d for d in os.listdir(locales_dir) if os.path.isdir(os.path.join(locales_dir, d))
            ]
        except (OSError, IOError, AttributeError):
            lang_values = ["en", "es"]

        if "en" not in lang_values:
            lang_values.append("en")

        current_lang = get_language()
        if not current_lang:
            try:
                set_language("en")
                current_lang = "en"
            except (ImportError, AttributeError, ValueError):
                current_lang = "en"

        lang_var = tk.StringVar(value=current_lang)
        self.variables["language"] = lang_var

        try:
            combobox = ttk.Combobox(
                self.frame, values=sorted(lang_values), textvariable=lang_var, width=6
            )
        except (AttributeError, tk.TclError, TypeError):
            combobox = ttk.Combobox(self.frame, values=sorted(lang_values))

        combobox.grid(column=1, row=row, padx=5, pady=5, sticky=tk.W)
        self.widgets["combobox_language"] = combobox

        try:
            combobox.set(lang_var.get() or "en")
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to set language combobox initial value")

        try:
            combobox.bind("<<ComboboxSelected>>", lambda ev: self.callbacks.on_language_change())
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to bind language change callback")

    def _build_rochester_attribution(self, row: int) -> None:
        """Build Rochester attribution text."""
        try:
            rochester_text = _(
                "All data is obtained from https://www.rochesterastronomy.org/snimages/ . "
                "Please collaborate with Latest Supernovae Site."
            )
            text_widget = tk.Text(
                self.frame,
                wrap="word",
                height=UI_CONSTANTS.ROCHESTER_TEXT_HEIGHT,
                width=UI_CONSTANTS.ROCHESTER_TEXT_WIDTH,
                borderwidth=0,
                relief=tk.FLAT,
            )
            text_widget.insert("1.0", rochester_text)

            # Apply theme color
            bg_color = (
                THEME_COLORS.DARK_ROCHESTER_BG
                if self.dark_mode and self.dark_mode.get()
                else THEME_COLORS.LIGHT_ROCHESTER_BG
            )
            text_widget.config(state="disabled", background=bg_color)

            text_widget.grid(column=0, row=row, columnspan=3, padx=5, pady=(2, 6), sticky=tk.W)
            self.widgets["text_rochester"] = text_widget
        except (AttributeError, tk.TclError, TypeError, ImportError):
            log_exception(logger, "Failed to build Rochester attribution text")

    def _setup_variable_traces(self) -> None:
        """Set up traces on variables to trigger callbacks."""
        try:
            # Callback that clears results and persists prefs
            # Note: tkinter trace callbacks receive (var, index, mode) arguments
            def clear_and_persist(*_a):
                self.callbacks.on_clear_results(*_a)
                self.callbacks.on_persist_prefs(*_a)

            # Trace key variables
            self._safe_trace_add(self.variables["magnitude"], clear_and_persist)
            self._safe_trace_add(self.variables["days_to_search"], clear_and_persist)
            self._safe_trace_add(self.variables["observation_date"], clear_and_persist)
            self._safe_trace_add(self.variables["observation_time"], clear_and_persist)
            self._safe_trace_add(self.variables["observation_duration"], clear_and_persist)
            self._safe_trace_add(self.variables["site"], clear_and_persist)
            self._safe_trace_add(self.variables["min_latitude"], clear_and_persist)

            # Visibility window needs extra update
            def vis_callback(*_a):
                self.callbacks.on_clear_results(*_a)
                self.callbacks.on_persist_prefs(*_a)
                self.callbacks.on_update_visibility_ui()

            self._safe_trace_add(self.variables["visibility_window"], vis_callback)

            # Language only persists
            try:
                if "language" in self.variables:
                    self._safe_trace_add(
                        self.variables["language"], self.callbacks.on_persist_prefs
                    )
            except (AttributeError, TypeError):
                log_exception(logger, "Failed to add language trace callback")
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to setup filter panel variable traces")

    def _safe_trace_add(self, var: tk.StringVar, callback: Callable) -> None:
        """Safely add a trace to a variable, handling exceptions."""
        try:
            var.trace_add("write", callback)
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to add variable trace callback")

    def update_visibility_values_label(self, text: str) -> None:
        """Update the visibility values label text.

        Args:
            text: Text to display in the visibility values label
        """
        try:
            if "label_visibility_values" in self.widgets:
                widget = self.widgets["label_visibility_values"]
                widget.config(text=text)  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to update visibility values label")

    def set_min_latitude_state(self, state: str) -> None:
        """Enable or disable the min latitude entry.

        Args:
            state: "normal" to enable, "disabled" to disable
        """
        try:
            if "entry_min_latitude" in self.widgets:
                self.widgets["entry_min_latitude"].config(state=state)  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to update min latitude entry state")

    def update_site_values(self, site_values: list) -> None:
        """Update the site combobox values.

        Args:
            site_values: List of site names
        """
        try:
            if "combobox_site" in self.widgets:
                self.widgets["combobox_site"]["values"] = site_values
        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, "Failed to update site combobox values")

    def update_visibility_window_values(self, vis_values: list) -> None:
        """Update the visibility window combobox values.

        Args:
            vis_values: List of visibility window names
        """
        try:
            if "combobox_visibility" in self.widgets:
                self.widgets["combobox_visibility"]["values"] = vis_values
        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, "Failed to update visibility combobox values")

    def refresh_labels(self) -> None:
        """Refresh all label texts after language change."""
        try:
            if "label_magnitude" in self.widgets:
                widget = self.widgets["label_magnitude"]
                widget.config(text=_("Max. magnitude: "))  # type: ignore[attr-defined]
            if "label_days_to_search" in self.widgets:
                widget = self.widgets["label_days_to_search"]
                widget.config(text=_("Find the n previous days: "))  # type: ignore[attr-defined]
            if "label_observation_date" in self.widgets:
                widget = self.widgets["label_observation_date"]
                widget.config(text=_("Observation date: "))  # type: ignore[attr-defined]
            if "label_init_time" in self.widgets:
                widget = self.widgets["label_init_time"]
                text = _("Init time in observation date: ")
                widget.config(text=text)  # type: ignore[attr-defined]
            if "label_duration" in self.widgets:
                widget = self.widgets["label_duration"]
                widget.config(text=_("Hours of observation: "))  # type: ignore[attr-defined]
            if "label_site" in self.widgets:
                self.widgets["label_site"].config(text=_("Site: "))  # type: ignore[attr-defined]
            if "label_visibility" in self.widgets:
                widget = self.widgets["label_visibility"]
                widget.config(text=_("Visibility window:"))  # type: ignore[attr-defined]
            if "label_min_latitude" in self.widgets:
                widget = self.widgets["label_min_latitude"]
                widget.config(text=_("Min latitude: "))  # type: ignore[attr-defined]
            if "label_language" in self.widgets:
                widget = self.widgets["label_language"]
                widget.config(text=_("Language:"))  # type: ignore[attr-defined]

            # Update Rochester attribution text
            if "text_rochester" in self.widgets:
                rochester_text = _(
                    "All data is obtained from https://www.rochesterastronomy.org/snimages/ . "
                    "Please collaborate with Latest Supernovae Site."
                )
                text_widget = self.widgets["text_rochester"]
                text_widget.config(state="normal")  # type: ignore[attr-defined]
                text_widget.delete("1.0", tk.END)  # type: ignore[attr-defined]
                text_widget.insert("1.0", rochester_text)  # type: ignore[attr-defined]
                text_widget.config(state="disabled")  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError, ImportError):
            log_exception(logger, "Failed to refresh filter panel labels")

    def apply_theme(self, dark_mode: bool) -> None:
        """Apply theme to widgets.

        Args:
            dark_mode: True for dark mode, False for light mode
        """
        try:
            if "text_rochester" in self.widgets:
                bg_color = (
                    THEME_COLORS.DARK_ROCHESTER_BG if dark_mode else THEME_COLORS.LIGHT_ROCHESTER_BG
                )
                widget = self.widgets["text_rochester"]
                widget.config(background=bg_color)  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to apply filter panel theme")
