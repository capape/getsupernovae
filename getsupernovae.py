#!/usr/bin/python
"""Get Supernovae - Desktop application for tracking supernova discoveries.

This is the main entry point for the Get Supernovae application, a tkinter-based
desktop application that fetches and displays supernova data from online sources,
calculates visibility windows, and generates observation reports.
"""

# Check supernova data
#

import os
import sys
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, List

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time

# ensure local modules in this directory can be imported when script run directly
sys.path.insert(0, os.path.dirname(__file__))

from app.config.snconfig import (
    bootstrap_config,
    load_old_supernovae,
    load_sites,
    load_visibility_windows,
)
from app.config.ui_constants import DEFAULT_VALUES, UI_STRINGS
from app.coordinators.results_tree_coordinator import ResultsTreeCoordinator
from app.i18n import _
from app.models.dto import SupernovaDTO
from app.services.observation_time_service import ObservationTimeService
from app.services.provider import NetworkRochesterProvider
from app.services.supernova_filter_service import SupernovaFilterService
from app.services.supernova_selection_service import SupernovaSelectionService
from app.ui.filter_panel_manager import FilterPanelCallbacks, FilterPanelManager
from app.ui.results_panel_manager import ResultsPanelCallbacks, ResultsPanelManager
from app.ui.snvisibility import VisibilityWindow
from app.ui.toolbar_manager import ToolbarCallbacks, ToolbarManager
from app.utils.logger import get_logger, log_exception

if TYPE_CHECKING:
    from app.coordinators.report_coordinator import ReportCoordinator
    from app.coordinators.search_coordinator import SearchCoordinator
    from app.ui.results_presenter import ResultsPresenter

bootstrap_config()
old = load_old_supernovae()
sites = load_sites()
visibility_windows = load_visibility_windows()
logger = get_logger(__name__)


class SupernovaCallBackData:  # pylint: disable=too-few-public-methods
    """Data container for supernova observation search parameters.

    This class holds the search criteria and observation parameters
    needed for supernova queries and visibility calculations.
    """

    def __init__(
        self,
        magnitude,
        observation_date,
        observation_time,
        observation_hours,
        days_to_search,
        site,
        min_latitude,
        visibility_window_name=None,
    ):
        self.magnitude = magnitude
        self.observation_date = observation_date
        self.observation_time = ObservationTimeService.normalize_time(observation_time)
        self.observation_hours = observation_hours
        self.days_to_search = days_to_search
        self.site = site
        self.min_latitude = min_latitude
        self.observation_start = Time(observation_date + "T" + self.observation_time + "Z")
        self.from_date_time = self.observation_start - timedelta(days=int(days_to_search))
        self.from_date = self.from_date_time.strftime("%Y-%m-%d")
        self.visibility_window_name = visibility_window_name


class RochesterSupernova:
    """Main class for fetching and selecting supernovae from Rochester catalog."""

    def __init__(
        self,
        visibility_factory=None,
        provider_factory=None,
        reporter=None,
        filter_service=None,
        selection_service=None,
    ):
        # visibility_factory should be a callable/class that creates a
        # visibility window instance with signature
        # VisibilityWindow(min_alt, max_alt, min_az, max_az)
        self.visibility_factory = (
            visibility_factory if visibility_factory is not None else VisibilityWindow
        )
        # provider_factory constructs a provider used to fetch Rochester data
        self.provider_factory = (
            provider_factory if provider_factory is not None else NetworkRochesterProvider
        )
        # reporter is optional; selection logic does not require it but keep for DI consistency
        self.reporter = reporter
        # filter_service handles all filtering logic
        self.filter_service = (
            filter_service
            if filter_service is not None
            else SupernovaFilterService(visibility_factory=self.visibility_factory)
        )
        # selection_service coordinates selection and sorting
        self.selection_service = (
            selection_service
            if selection_service is not None
            else SupernovaSelectionService(
                filter_service=self.filter_service, visibility_windows=visibility_windows
            )
        )

    def select_and_sort_supernovae(
        self, e: SupernovaCallBackData, supernovae_list: List[SupernovaDTO]
    ):
        """Select and sort supernovae using the selection service.

        This method now delegates to SupernovaSelectionService for all
        selection, filtering, and sorting logic.
        """
        # Convert magnitude to float
        try:
            max_magnitude = float(e.magnitude)
        except (ValueError, TypeError):
            max_magnitude = float(str(e.magnitude))

        # Use selection service to coordinate the entire selection process
        supernovas = self.selection_service.select_and_sort_supernovae(
            supernova_list=supernovae_list,
            max_magnitude=max_magnitude,
            observation_start=e.observation_start,
            observation_hours=int(e.observation_hours),
            from_date=e.from_date,
            site=e.site,
            exclusion_list=set(old) if old else set(),
            visibility_window_name=getattr(e, "visibility_window_name", None),
            min_latitude=float(e.min_latitude),
            visibility_factory=self.visibility_factory,
        )

        return supernovas

    def select_supernovae(
        self,
        supernovae_list: List[SupernovaDTO],
        max_mag: str,
        observation_day: datetime,
        local_start_time: str,
        hours_observation: int,
        from_date: str,
        site: EarthLocation,
        min_alt: float = 0,
        max_alt: float = 90,
        min_az: float = 0,
        max_az: float = 360,
    ):
        """Select supernovae using the filter service.

        Legacy method kept for backward compatibility. Delegates to filter service.
        For new code, prefer using select_and_sort_supernovae with SupernovaCallBackData.
        """
        observation_start = observation_day.strftime("%Y-%m-%d") + "T" + local_start_time + "Z"

        time1 = Time(observation_start)
        time2 = time1 + timedelta(hours=hours_observation)

        # Convert maxMag to float
        try:
            max_mag_threshold = float(max_mag)
        except (ValueError, TypeError):
            max_mag_threshold = float(str(max_mag))

        # Use filter service to apply all filters and get results
        filtered_results = self.filter_service.apply_all_filters(
            supernovae=supernovae_list,
            max_magnitude=max_mag_threshold,
            from_date=from_date,
            exclusion_list=set(old) if old else set(),
            site=site,
            observation_start=time1,
            observation_end=time2,
            min_altitude=min_alt,
            max_altitude=max_alt,
            min_azimuth=min_az,
            max_azimuth=max_az,
            visibility_factory=self.visibility_factory,
        )

        # Convert to domain models
        supernovas = self.filter_service.convert_to_domain_models(filtered_results)

        return supernovas


# Note: domain model dataclasses live in `app.models.snmodels` and are imported
# at the top of this module. Do not redefine them here to avoid drift.


class SearchFilters:  # pylint: disable=too-few-public-methods
    """Data class to hold supernova search filter parameters."""

    def __init__(
        self,
        magnitude: str,
        days_to_search: int,
        observation_date: datetime,
        observation_time: str,
        observation_hours: int,
        site: str,
        min_latitude: float,
        visibility_window_name: str | None = None,
    ):
        self.magnitude = magnitude
        self.days_to_search = days_to_search
        self.observation_date = observation_date
        self.observation_time = observation_time
        self.observation_hours = observation_hours
        self.site = site
        self.min_latitude = min_latitude
        self.visibility_window_name = visibility_window_name


class SupernovasApp(tk.Tk):
    """Main application class for Get Supernovae.

    Many attributes are initialized by InitializationBuilder.build().
    """

    # Type hints for attributes set by InitializationBuilder
    presenter: "ResultsPresenter"
    report_coordinator: "ReportCoordinator"
    search_coordinator: "SearchCoordinator"
    site: tk.StringVar
    visibility_window: tk.StringVar

    # State management
    _initializing: bool
    refreshing: bool
    supernova_data: dict
    supernovas_found: list | None

    # Tk variables
    dark_mode: tk.BooleanVar
    days_to_search: tk.StringVar
    lang_var: tk.StringVar
    magnitude: tk.StringVar
    min_latitud: tk.StringVar
    observation_date: tk.StringVar
    observation_duration: tk.StringVar
    observation_time: tk.StringVar
    results: tk.StringVar

    # UI managers
    filter_panel_manager: "FilterPanelManager"
    results_panel_manager: "ResultsPanelManager"
    toolbar_manager: "ToolbarManager"

    # Coordinators (in addition to report_coordinator and search_coordinator above)
    dialog_coordinator: "DialogCoordinator"
    language_coordinator: "LanguageCoordinator"
    preferences_coordinator: "PreferencesCoordinator"
    theme_coordinator: "ThemeCoordinator"
    tree_coordinator: "ResultsTreeCoordinator"

    # Widget references from FilterPanelManager
    cb_lang: Any
    cb_site: Any
    cb_visibility: Any
    entry_latitud: Any
    label_days_to_Search: Any
    label_duration: Any
    label_init_time: Any
    label_lang: Any
    label_latitud: Any
    label_magnitude: Any
    label_observation_date: Any
    label_site: Any
    label_visibility: Any
    rochester_text: Any
    visibility_values_label: Any

    # Widget references from ResultsPanelManager
    exit_button: Any
    label_results: Any
    pdf_button: Any
    progress_bar: Any
    results_tree: Any
    search_button: Any
    txt_button: Any

    # Widget references from ToolbarManager
    dark_toggle: Any
    edit_old_button: Any
    find_stars_button: Any
    ignore_selected_button: Any

    #
    # Create object with filters to search
    #
    def _safe_trace_add(self, var, callback):
        """Add a trace callback to a Tk variable, with fallbacks for
        environments with different `trace_add` signatures.
        """
        try:
            var.trace_add(["write", "unset"], callback)
            return
        except (TypeError, AttributeError, RuntimeError):
            log_exception(logger, "Failed to add combined trace callback")
        try:
            var.trace_add("write", callback)
            return
        except (TypeError, AttributeError, RuntimeError):
            log_exception(logger, "Failed to add write trace callback")
        try:
            var.trace_add("unset", callback)
        except (TypeError, AttributeError, RuntimeError):
            log_exception(logger, "Failed to add unset trace callback")

    def get_data_to_search(self):
        """Retrieve current search filter parameters from UI variables."""
        try:
            callback_data = SupernovaCallBackData(
                self.magnitude.get(),
                self.observation_date.get(),
                self.observation_time.get(),
                self.observation_duration.get(),
                self.days_to_search.get(),
                sites[self.site.get()],
                self.min_latitud.get(),
                getattr(self, "visibility_window", None) and self.visibility_window.get(),
            )
            return callback_data
        except (ValueError, AttributeError, TypeError) as ex:
            messagebox.showerror(
                _("Invalid input"),
                _(
                    "Invalid observation time. Use HH, HH:MM or HH:MM:SS.\n\nDetails: {error}"
                ).format(error=str(ex)),
            )
            return None

    #
    # Check if there is already a search done with current filters
    #
    def has_results(self):
        """Check if there are search results available."""
        if self.supernovas_found is None:
            return False
        return True

    #
    # PDF button callback
    #
    def on_pdf_export_clicked(self, e: SupernovaCallBackData):
        """Generate PDF report using report coordinator."""
        self.report_coordinator.generate_pdf_report(e)

    #
    # TXT button callback
    #
    def on_text_export_clicked(self, e: SupernovaCallBackData):
        """Generate TXT report using report coordinator."""
        self.report_coordinator.generate_txt_report(e)

    #
    #  Refresh button callback
    #
    def on_refresh_clicked(self, e: SupernovaCallBackData):
        """Refresh search results using the search coordinator."""
        if e is None:
            return
        self.search_coordinator.refresh_search(e)

    #
    # Do a async search
    #
    def on_search_async(self, e: SupernovaCallBackData, source="SEARCH"):
        """Execute async search using the search coordinator."""
        self.search_coordinator.search_async(e, source)

    def _handle_search_results(self, results, error_text):
        """Handle search results from coordinator.

        Args:
            results: List of supernovae or None if error
            error_text: Error message if any, or empty string
        """
        try:
            self.supernovas_found = results

            # Update results display
            if error_text:
                self.set_results_text(error_text)
            elif results:
                self.set_results_text("")
            else:
                self.set_results_text("ERROR: No results")
        except (AttributeError, TypeError, KeyError):
            log_exception(logger, "Failed to handle search results")

    def _set_button_state(self, button_name: str, state: str):
        """Set button state from coordinator.

        Args:
            button_name: Button identifier ("pdf", "txt", "refresh")
            state: Button state ("normal", "disabled")
        """
        try:
            tk_state = tk.NORMAL if state == "normal" else tk.DISABLED
            if button_name == "pdf" and hasattr(self, "pdfButton"):
                self.pdf_button["state"] = tk_state
            elif button_name == "txt" and hasattr(self, "txtButton"):
                self.txt_button["state"] = tk_state
            elif button_name == "refresh" and hasattr(self, "searchButton"):
                self.search_button["state"] = tk_state
        except (AttributeError, KeyError, tk.TclError):
            log_exception(logger, f"Failed to set {button_name} button state to {state}")

    def start_progress_bar(self):
        """Start the progress bar animation."""
        self.results_panel_manager.start_progress_bar()

    def end_progress_bar(self):
        """Stop the progress bar animation."""
        self.results_panel_manager.stop_progress_bar()

    def _show_yes_no_dialog(self, title: str, message: str, icon_type: str = "question") -> bool:
        """Show a yes/no dialog and return the user's choice.

        Args:
            title: Dialog title
            message: Dialog message
            icon_type: Icon type for the dialog

        Returns:
            True if user clicked Yes, False otherwise
        """
        return messagebox.askyesno(title, message, icon=icon_type)

    def _show_warning_dialog(self, title: str, message: str):
        """Show a warning dialog.

        Args:
            title: Dialog title
            message: Dialog message
        """
        messagebox.showwarning(title, message)

    def _show_info_dialog(self, title: str, message: str):
        """Show an info dialog.

        Args:
            title: Dialog title
            message: Dialog message
        """
        messagebox.showinfo(title, message)

    def _show_error_dialog(self, title: str, message: str):
        """Show an error dialog.

        Args:
            title: Dialog title
            message: Dialog message
        """
        messagebox.showerror(title, message)

    def _get_selected_supernova(self):
        """Get the currently selected supernova from the results tree.

        Returns:
            Supernova object if one is selected, None otherwise
        """
        try:
            selection = self.results_tree.selection()
            if not selection:
                return None

            item = selection[0]
            if item not in self.supernova_data:
                return None

            return self.supernova_data[item]
        except (KeyError, AttributeError):
            return None

    def _update_sites_combobox(self, values: list, selected: str | None = None):
        """Update site combobox with new values.

        Args:
            values: List of site names
            selected: Site name to select
        """
        try:
            self.filter_panel_manager.update_site_values(values)
            if selected:
                self.site.set(selected)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to update sites combobox")

    def _update_visibility_windows_combobox(self, values: list, selected: str | None = None):
        """Update visibility window combobox with new values.

        Args:
            values: List of visibility window names
            selected: Visibility window name to select
        """
        try:
            self.filter_panel_manager.update_visibility_window_values(values)
            if selected:
                self.visibility_window.set(selected)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to update visibility windows combobox")

    def _enable_find_stars_button(self, _button_name: str):
        """Enable the find stars button.

        Args:
            _button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, "find_stars_button") and self.find_stars_button:
                self.find_stars_button.config(state=tk.NORMAL)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to enable find stars button")

    def _disable_find_stars_button(self, _button_name: str):
        """Disable the find stars button.

        Args:
            _button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, "find_stars_button") and self.find_stars_button:
                self.find_stars_button.config(state=tk.DISABLED)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to disable find stars button")

    def on_clear_results(self, _var, _index, _mode):
        """Clear results when any filter variable changes.

        Args:
            _var: Variable that changed (unused, required by trace callback)
            _index: Index (unused, required by trace callback)
            _mode: Mode (unused, required by trace callback)
        """
        self.supernovas_found = None

    def set_results_text(self, datatxt: str):
        """Helper to update the results table from supernova data."""
        # Clear existing tree entries
        try:
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.supernova_data.clear()
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to clear existing results tree entries")

        # If datatxt is an error message, show it
        if datatxt and (datatxt.startswith("ERROR") or self.supernovas_found is None):
            try:
                # Insert error as a single row
                self.results_tree.insert(
                    "", "end", values=(datatxt, "", "", "", "", "", "", "", "", "", "")
                )
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to render error row in results tree")
            return

        # Populate tree from self.supernovas_found
        try:
            if self.supernovas_found:
                for idx, sn in enumerate(self.supernovas_found):
                    presenter = self.presenter
                    try:
                        row = presenter.present(sn)
                    except (AttributeError, TypeError, ValueError):
                        # Fallback to minimal row on presenter error
                        row = (
                            getattr(sn, "name", ""),
                            getattr(sn, "type", ""),
                            getattr(sn, "mag", "") or "",
                            getattr(sn, "date", "") or "",
                            "",
                            getattr(sn, "host", ""),
                            getattr(sn, "constellation", ""),
                            "",
                            "",
                            "🔗",
                            "🔗",
                        )

                    # Determine brightness tag based on numeric magnitude
                    mag_val = None
                    try:
                        mag_attr = getattr(sn, "mag", None)
                        if mag_attr is not None:
                            mag_val = float(mag_attr)
                    except (ValueError, TypeError):
                        mag_val = None

                    is_bright = (
                        mag_val is not None and mag_val < DEFAULT_VALUES.BRIGHT_MAGNITUDE_THRESHOLD
                    )
                    tag = (
                        (
                            UI_STRINGS.TAG_EVEN_ROW_BRIGHT
                            if idx % 2 == 0
                            else UI_STRINGS.TAG_ODD_ROW_BRIGHT
                        )
                        if is_bright
                        else (UI_STRINGS.TAG_EVEN_ROW if idx % 2 == 0 else UI_STRINGS.TAG_ODD_ROW)
                    )

                    item_id = self.results_tree.insert("", "end", values=row, tags=(tag,))
                    self.supernova_data[item_id] = sn
        except (AttributeError, TypeError, KeyError, tk.TclError) as e:
            # If population fails, show error
            try:
                self.results_tree.insert(
                    "", "end", values=(f"Error: {str(e)}", "", "", "", "", "", "", "", "", "", "")
                )
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to render exception row in results tree")

    def build_left_panel(self):
        """Build the left-side filter controls using FilterPanelManager."""
        try:
            # Prepare variables dictionary for the filter panel
            filter_variables = {
                "magnitude": self.magnitude,
                "days_to_search": self.days_to_search,
                "observation_date": self.observation_date,
                "observation_time": self.observation_time,
                "observation_duration": self.observation_duration,
                "site": self.site,
                "visibility_window": self.visibility_window,
                "min_latitude": self.min_latitud,
            }

            # Create callbacks for the filter panel
            callbacks = FilterPanelCallbacks(
                on_clear_results=self.on_clear_results,
                on_persist_prefs=self.preferences_coordinator.persist_prefs,
                on_update_visibility_ui=self.preferences_coordinator.update_visibility_ui,
                on_language_change=self.language_coordinator.on_language_change,
                on_add_site=self.on_add_site,
                on_add_visibility_window=self.on_add_visibility_window,
            )

            # Create and build the filter panel manager
            self.filter_panel_manager = FilterPanelManager(
                parent=self,
                variables=filter_variables,
                sites=sites,
                visibility_windows=visibility_windows,
                callbacks=callbacks,
                dark_mode=self.dark_mode,
            )

            self.filter_panel_manager.build()

            # Store references to commonly accessed widgets for backward compatibility
            self.cb_site = self.filter_panel_manager.widgets.get("combobox_site")
            self.cb_visibility = self.filter_panel_manager.widgets.get("combobox_visibility")
            self.entry_latitud = self.filter_panel_manager.widgets.get("entry_min_latitude")
            self.visibility_values_label = self.filter_panel_manager.widgets.get(
                "label_visibility_values"
            )

            # Store widget references for language change updates
            self.label_magnitude = self.filter_panel_manager.widgets.get("label_magnitude")
            self.label_days_to_Search = self.filter_panel_manager.widgets.get("label_days_to_search")
            self.label_observation_date = self.filter_panel_manager.widgets.get(
                "label_observation_date"
            )
            self.label_init_time = self.filter_panel_manager.widgets.get("label_init_time")
            self.label_duration = self.filter_panel_manager.widgets.get("label_duration")
            self.label_site = self.filter_panel_manager.widgets.get("label_site")
            self.label_lang = self.filter_panel_manager.widgets.get("label_language")
            self.label_visibility = self.filter_panel_manager.widgets.get("label_visibility")
            self.label_latitud = self.filter_panel_manager.widgets.get("label_min_latitude")
            self.rochester_text = self.filter_panel_manager.widgets.get("text_rochester")
            self.cb_lang = self.filter_panel_manager.widgets.get("combobox_language")

            # Get lang_var from filter panel manager
            if "language" in filter_variables:
                self.lang_var = filter_variables["language"]

            # Apply persisted prefs if present (best-effort)
            try:
                self.preferences_coordinator.load_and_apply_prefs()
            except (OSError, ValueError, KeyError, AttributeError):
                log_exception(
                    logger, "Failed to load and apply preferences while building left panel"
                )

            # Initialization complete, enable preference persistence
            self._initializing = False
        except (AttributeError, TypeError, tk.TclError):
            log_exception(logger, "Failed to build left panel")

    def build_results_panel(self):
        """Build the results panel using ResultsPanelManager."""
        try:
            # Store references first (needed for coordinator initialization)
            # These will be properly set after building the panel
            self.supernova_data = {}

            # Placeholder callbacks - will be replaced with coordinator methods
            callbacks = ResultsPanelCallbacks(
                on_sort_column=lambda col, is_numeric: None,
                on_double_click=lambda e: None,
                on_motion=lambda e: None,
                on_leave=lambda e: None,
                on_selection_change=lambda e: None,
                on_pdf=lambda: self.on_pdf_export_clicked(self.get_data_to_search()),
                on_txt=lambda: self.on_text_export_clicked(self.get_data_to_search()),
                on_refresh=lambda: self.on_refresh_clicked(self.get_data_to_search()),
                on_exit=self.quit,
            )

            # Create and build the results panel manager
            self.results_panel_manager = ResultsPanelManager(
                parent=self, callbacks=callbacks, dark_mode=self.dark_mode
            )

            self.results_panel_manager.build()

            # Store references to commonly accessed widgets for backward compatibility
            self.results_tree = self.results_panel_manager.get_tree()
            self.label_results = self.results_panel_manager.widgets.get("label_results")
            self.pdf_button = self.results_panel_manager.widgets.get("button_pdf")
            self.txt_button = self.results_panel_manager.widgets.get("button_txt")
            self.search_button = self.results_panel_manager.widgets.get("button_refresh")
            self.exit_button = self.results_panel_manager.widgets.get("button_exit")
            self.progress_bar = self.results_panel_manager.widgets.get("progress_bar")

            # Use manager's data storage
            self.supernova_data = self.results_panel_manager.supernova_data

            # Initialize ResultsTreeCoordinator to handle all tree interactions
            self.tree_coordinator = ResultsTreeCoordinator(
                tree_widget=self.results_tree,
                supernova_data=self.supernova_data,
                get_dark_mode=lambda: self.dark_mode.get() if hasattr(self, "dark_mode") else False,
                on_enable_button=self._enable_find_stars_button,
                on_disable_button=self._disable_find_stars_button,
                on_show_error=self._show_error_dialog,
            )

            # Update callbacks to use coordinator
            updated_callbacks = ResultsPanelCallbacks(
                on_sort_column=self.tree_coordinator.sort_column,
                on_double_click=self.tree_coordinator.on_double_click,
                on_motion=self.tree_coordinator.on_motion,
                on_leave=self.tree_coordinator.on_leave,
                on_selection_change=self.tree_coordinator.on_selection_change,
                on_pdf=lambda: self.on_pdf_export_clicked(self.get_data_to_search()),
                on_txt=lambda: self.on_text_export_clicked(self.get_data_to_search()),
                on_refresh=lambda: self.on_refresh_clicked(self.get_data_to_search()),
                on_exit=self.quit,
            )

            # Update callbacks and manually rebind tree events
            self.results_panel_manager.callbacks = updated_callbacks

            # Rebind tree events with coordinator methods
            try:
                self.results_tree.bind("<Double-Button-1>", self.tree_coordinator.on_double_click)
                self.results_tree.bind("<Motion>", self.tree_coordinator.on_motion)
                self.results_tree.bind("<Leave>", self.tree_coordinator.on_leave)
                self.results_tree.bind(
                    "<<TreeviewSelect>>", self.tree_coordinator.on_selection_change
                )
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to rebind tree events with coordinator")

            # Update column sort commands to use coordinator
            try:
                for col, is_numeric in [
                    ("name", False),
                    ("type", False),
                    ("magnitude", True),
                    ("date", False),
                    ("observation_time", False),
                    ("host", False),
                    ("constellation", False),
                    ("ra", False),
                    ("dec", False),
                    ("rochester", False),
                    ("tns", False),
                ]:
                    self.results_tree.heading(
                        col,
                        command=lambda c=col, n=is_numeric: self.tree_coordinator.sort_column(c, n),
                    )
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to update column sort commands")

            # Create toolbar manager callbacks
            toolbar_callbacks = ToolbarCallbacks(
                on_find_stars=self.tree_coordinator.find_stars_in_simbad,
                on_ignore_selected=self.on_ignore_selected,
                on_edit_old=self.on_edit_old_supernovae,
                on_dark_mode_toggle=self.theme_coordinator.apply_theme,
            )

            # Create and build toolbar manager
            self.toolbar_manager = ToolbarManager(
                parent=self,
                callbacks=toolbar_callbacks,
                dark_mode=self.dark_mode,
                grid_column=3,
                grid_row=11,
                columnspan=2,
            )

            self.toolbar_manager.build()

            # Store toolbar widget references
            self.find_stars_button = self.toolbar_manager.get_widget("button_find_stars")
            self.ignore_selected_button = self.toolbar_manager.get_widget("button_ignore_selected")
            self.edit_old_button = self.toolbar_manager.get_widget("button_edit_old")
            self.dark_toggle = self.toolbar_manager.get_widget("toggle_dark_mode")

            # Configure results tree styling
            self.theme_coordinator.configure_results_tree_styling()
        except (AttributeError, TypeError, tk.TclError):
            log_exception(logger, "Failed to build results panel")

    def refilter_from_cache(self, source="REFRESH"):
        """Re-run selection/filtering on the cached data (if available).

        Uses the search coordinator to refilter without re-downloading.
        If no cached data exists, falls back to a full network download.
        """
        try:
            self.search_coordinator.refilter_from_cache(self.get_data_to_search(), source)
        except (AttributeError, TypeError):
            log_exception(logger, f"Failed to refilter from cache for source={source}")

    def on_ignore_selected(self):
        """Add the currently selected SN to the ignore list."""
        self.dialog_coordinator.ignore_selected_supernova()

    def on_edit_old_supernovae(self):
        """Open the old supernovae editor dialog."""
        self.dialog_coordinator.edit_old_supernovae()

    def on_add_site(self):
        """Open the sites configuration dialog."""
        self.dialog_coordinator.open_sites_dialog()

    def on_add_visibility_window(self):
        """Open the visibility window configuration dialog."""
        self.dialog_coordinator.open_visibility_window_dialog()

    def __init__(
        self, filters, presenter=None, visibility_factory=None, provider_factory=None, reporter=None
    ):

        super().__init__()

        # Use InitializationBuilder to handle complex setup
        from app.ui.initialization_builder import InitializationBuilder

        builder = InitializationBuilder(self, filters)
        builder.build(presenter, visibility_factory, provider_factory, reporter)


def represents_int(s):
    """Check if a string represents an integer."""
    try:
        int(s)
        return True
    except ValueError:
        return False


def main():
    """Main entry point for the application."""
    if len(sys.argv) > 3:
        raise ValueError(_("Usage: getsupernovae.py maxMag lastDays"))

    mag = DEFAULT_VALUES.MAGNITUDE
    daysToSearch = DEFAULT_VALUES.DAYS_TO_SEARCH

    if len(sys.argv) == 3:
        if represents_int(sys.argv[2]):
            daysToSearch = int(sys.argv[2])
            mag = sys.argv[1]
    elif len(sys.argv) == 2:
        if represents_int(sys.argv[1]):
            mag = sys.argv[1]

    # pylint: disable=no-member  # astropy.units members exist at runtime
    site = EarthLocation(lat=41.55 * u.deg, lon=2.09 * u.deg, height=224 * u.m)

    site = list(sites.keys())[0]

    filters = SearchFilters(
        mag,
        daysToSearch,
        datetime.now(),
        DEFAULT_VALUES.OBSERVATION_TIME,
        DEFAULT_VALUES.OBSERVATION_HOURS,
        site,
        DEFAULT_VALUES.MIN_LATITUDE,
    )
    app = SupernovasApp(filters)
    app.mainloop()


# `_parse_row_safe` is provided by `snparser.py` and imported at the top of this file.


if __name__ == "__main__":
    main()
