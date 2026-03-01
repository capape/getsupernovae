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
from typing import TYPE_CHECKING, List

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time

from app.models.dto import SupernovaDTO

# ensure local modules in this directory can be imported when script run directly
sys.path.insert(0, os.path.dirname(__file__))

from app.config.snconfig import (
    bootstrap_config,
    load_old_supernovae,
    load_sites,
    load_visibility_windows,
)
from app.config.ui_constants import (
    DEFAULT_VALUES,
    UI_STRINGS,
)
from app.coordinators.results_tree_coordinator import ResultsTreeCoordinator

# import the external plotter helper
from app.i18n import _

if TYPE_CHECKING:
    from app.coordinators.report_coordinator import ReportCoordinator
    from app.coordinators.search_coordinator import SearchCoordinator
    from app.ui.results_presenter import ResultsPresenter
from app.services.observation_time_service import ObservationTimeService
from app.services.provider import NetworkRochesterProvider
from app.services.supernova_filter_service import SupernovaFilterService
from app.services.supernova_selection_service import SupernovaSelectionService
from app.ui.filter_panel_manager import FilterPanelCallbacks, FilterPanelManager
from app.ui.results_panel_manager import ResultsPanelCallbacks, ResultsPanelManager
from app.ui.snvisibility import VisibilityWindow
from app.ui.toolbar_manager import ToolbarCallbacks, ToolbarManager
from app.utils.logger import get_logger, log_exception

bootstrap_config()
old = load_old_supernovae()
sites = load_sites()
visibility_windows = load_visibility_windows()
logger = get_logger(__name__)


class SupernovaCallBackData:
    """Data container for supernova observation search parameters.

    This class holds the search criteria and observation parameters
    needed for supernova queries and visibility calculations.
    """

    def __init__(
        self,
        magnitude,
        observationDate,
        observationTime,
        observationHours,
        daysToSearch,
        site,
        minLatitude,
        visibilityWindowName=None,
    ):
        self.magnitude = magnitude
        self.observationDate = observationDate
        self.observationTime = ObservationTimeService.normalize_time(observationTime)
        self.observationHours = observationHours
        self.daysToSearch = daysToSearch
        self.site = site
        self.minLatitude = minLatitude
        self.observationStart = Time(observationDate + "T" + self.observationTime + "Z")
        self.fromDateTime = self.observationStart - timedelta(days=int(daysToSearch))
        self.fromDate = self.fromDateTime.strftime("%Y-%m-%d")
        self.visibilityWindowName = visibilityWindowName


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
        # VisibilityWindow(minAlt, maxAlt, minAz, maxAz)
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

    def selectAndSortSupernovas(self, e: SupernovaCallBackData, supernovaeList: List[SupernovaDTO]):
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
            supernova_list=supernovaeList,
            max_magnitude=max_magnitude,
            observation_start=e.observationStart,
            observation_hours=int(e.observationHours),
            from_date=e.fromDate,
            site=e.site,
            exclusion_list=set(old) if old else set(),
            visibility_window_name=getattr(e, "visibilityWindowName", None),
            min_latitude=float(e.minLatitude),
            visibility_factory=self.visibility_factory,
        )

        return supernovas

    def selectSupernovas(
        self,
        supernovaeList: List[SupernovaDTO],
        maxMag: str,
        observationDay: datetime,
        localStartTime: str,
        hoursObservation: int,
        fromDate: str,
        site: EarthLocation,
        minAlt: float = 0,
        maxAlt: float = 90,
        minAz: float = 0,
        maxAz: float = 360,
    ):
        """Select supernovae using the filter service.

        Legacy method kept for backward compatibility. Delegates to filter service.
        For new code, prefer using selectAndSortSupernovas with SupernovaCallBackData.
        """
        observationStart = observationDay.strftime("%Y-%m-%d") + "T" + localStartTime + "Z"

        time1 = Time(observationStart)
        time2 = time1 + timedelta(hours=hoursObservation)

        # Convert maxMag to float
        try:
            max_mag_threshold = float(maxMag)
        except (ValueError, TypeError):
            max_mag_threshold = float(str(maxMag))

        # Use filter service to apply all filters and get results
        filtered_results = self.filter_service.apply_all_filters(
            supernovae=supernovaeList,
            max_magnitude=max_mag_threshold,
            from_date=fromDate,
            exclusion_list=set(old) if old else set(),
            site=site,
            observation_start=time1,
            observation_end=time2,
            min_altitude=minAlt,
            max_altitude=maxAlt,
            min_azimuth=minAz,
            max_azimuth=maxAz,
            visibility_factory=self.visibility_factory,
        )

        # Convert to domain models
        supernovas = self.filter_service.convert_to_domain_models(filtered_results)

        return supernovas


# Note: domain model dataclasses live in `app.models.snmodels` and are imported
# at the top of this module. Do not redefine them here to avoid drift.


class SearchFilters:
    """Data class to hold supernova search filter parameters."""

    def __init__(
        self,
        magnitude: str,
        daysToSearch: int,
        observationDate: datetime,
        observationTime: str,
        observationHours: int,
        site: str,
        minLatitude: float,
        visibilityWindowName: str | None = None,
    ):
        self.magnitude = magnitude
        self.daysToSearch = daysToSearch
        self.observationDate = observationDate
        self.observationTime = observationTime
        self.observationHours = observationHours
        self.site = site
        self.minLatitude = minLatitude
        self.visibilityWindowName = visibilityWindowName


class SupernovasApp(tk.Tk):
    """Main application class for Get Supernovae.

    Many attributes are initialized by InitializationBuilder.build().
    """

    # Type hints for attributes set by InitializationBuilder
    report_coordinator: "ReportCoordinator"
    search_coordinator: "SearchCoordinator"
    presenter: "ResultsPresenter"
    site: tk.StringVar
    visibilityWindow: tk.StringVar

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

    def getDataToSearch(self):
        """Retrieve current search filter parameters from UI variables."""
        try:
            callbackData = SupernovaCallBackData(
                self.magnitude.get(),
                self.observationDate.get(),
                self.observationTime.get(),
                self.observationDuration.get(),
                self.daysToSearch.get(),
                sites[self.site.get()],
                self.minLatitud.get(),
                getattr(self, "visibilityWindow", None) and self.visibilityWindow.get(),
            )
            return callbackData
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
        if self.supernovasFound is None:
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
            self.supernovasFound = results

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
                self.pdfButton["state"] = tk_state
            elif button_name == "txt" and hasattr(self, "txtButton"):
                self.txtButton["state"] = tk_state
            elif button_name == "refresh" and hasattr(self, "searchButton"):
                self.searchButton["state"] = tk_state
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
            selection = self.resultsTree.selection()
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
                self.visibilityWindow.set(selected)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to update visibility windows combobox")

    def _enable_find_stars_button(self, _button_name: str):
        """Enable the find stars button.

        Args:
            _button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, "findStarsButton") and self.findStarsButton:
                self.findStarsButton.config(state=tk.NORMAL)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to enable find stars button")

    def _disable_find_stars_button(self, _button_name: str):
        """Disable the find stars button.

        Args:
            _button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, "findStarsButton") and self.findStarsButton:
                self.findStarsButton.config(state=tk.DISABLED)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to disable find stars button")

    def on_clear_results(self, _var, _index, _mode):
        """Clear results when any filter variable changes.

        Args:
            _var: Variable that changed (unused, required by trace callback)
            _index: Index (unused, required by trace callback)
            _mode: Mode (unused, required by trace callback)
        """
        self.supernovasFound = None

    def set_results_text(self, datatxt: str):
        """Helper to update the results table from supernova data."""
        # Clear existing tree entries
        try:
            for item in self.resultsTree.get_children():
                self.resultsTree.delete(item)
            self.supernova_data.clear()
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to clear existing results tree entries")

        # If datatxt is an error message, show it
        if datatxt and (datatxt.startswith("ERROR") or self.supernovasFound is None):
            try:
                # Insert error as a single row
                self.resultsTree.insert(
                    "", "end", values=(datatxt, "", "", "", "", "", "", "", "", "", "")
                )
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to render error row in results tree")
            return

        # Populate tree from self.supernovasFound
        try:
            if self.supernovasFound:
                for idx, sn in enumerate(self.supernovasFound):
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

                    item_id = self.resultsTree.insert("", "end", values=row, tags=(tag,))
                    self.supernova_data[item_id] = sn
        except (AttributeError, TypeError, KeyError, tk.TclError) as e:
            # If population fails, show error
            try:
                self.resultsTree.insert(
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
                "days_to_search": self.daysToSearch,
                "observation_date": self.observationDate,
                "observation_time": self.observationTime,
                "observation_duration": self.observationDuration,
                "site": self.site,
                "visibility_window": self.visibilityWindow,
                "min_latitude": self.minLatitud,
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
            self.cbSite = self.filter_panel_manager.widgets.get("combobox_site")
            self.cbVisibility = self.filter_panel_manager.widgets.get("combobox_visibility")
            self.entryLatitud = self.filter_panel_manager.widgets.get("entry_min_latitude")
            self.visibilityValuesLabel = self.filter_panel_manager.widgets.get(
                "label_visibility_values"
            )

            # Store widget references for language change updates
            self.labelMagnitude = self.filter_panel_manager.widgets.get("label_magnitude")
            self.labelDaysToSearch = self.filter_panel_manager.widgets.get("label_days_to_search")
            self.labelObservationDate = self.filter_panel_manager.widgets.get(
                "label_observation_date"
            )
            self.labelInitTime = self.filter_panel_manager.widgets.get("label_init_time")
            self.labelDuration = self.filter_panel_manager.widgets.get("label_duration")
            self.labelSite = self.filter_panel_manager.widgets.get("label_site")
            self.labelLang = self.filter_panel_manager.widgets.get("label_language")
            self.labelVisibility = self.filter_panel_manager.widgets.get("label_visibility")
            self.labelLatitud = self.filter_panel_manager.widgets.get("label_min_latitude")
            self.rochesterText = self.filter_panel_manager.widgets.get("text_rochester")
            self.cbLang = self.filter_panel_manager.widgets.get("combobox_language")

            # Get langVar from filter panel manager
            if "language" in filter_variables:
                self.langVar = filter_variables["language"]

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
                on_pdf=lambda: self.on_pdf_export_clicked(self.getDataToSearch()),
                on_txt=lambda: self.on_text_export_clicked(self.getDataToSearch()),
                on_refresh=lambda: self.on_refresh_clicked(self.getDataToSearch()),
                on_exit=self.quit,
            )

            # Create and build the results panel manager
            self.results_panel_manager = ResultsPanelManager(
                parent=self, callbacks=callbacks, dark_mode=self.dark_mode
            )

            self.results_panel_manager.build()

            # Store references to commonly accessed widgets for backward compatibility
            self.resultsTree = self.results_panel_manager.get_tree()
            self.labelResults = self.results_panel_manager.widgets.get("label_results")
            self.pdfButton = self.results_panel_manager.widgets.get("button_pdf")
            self.txtButton = self.results_panel_manager.widgets.get("button_txt")
            self.searchButton = self.results_panel_manager.widgets.get("button_refresh")
            self.exitButton = self.results_panel_manager.widgets.get("button_exit")
            self.progressBar = self.results_panel_manager.widgets.get("progress_bar")

            # Use manager's data storage
            self.supernova_data = self.results_panel_manager.supernova_data

            # Initialize ResultsTreeCoordinator to handle all tree interactions
            self.tree_coordinator = ResultsTreeCoordinator(
                tree_widget=self.resultsTree,
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
                on_pdf=lambda: self.on_pdf_export_clicked(self.getDataToSearch()),
                on_txt=lambda: self.on_text_export_clicked(self.getDataToSearch()),
                on_refresh=lambda: self.on_refresh_clicked(self.getDataToSearch()),
                on_exit=self.quit,
            )

            # Update callbacks and manually rebind tree events
            self.results_panel_manager.callbacks = updated_callbacks

            # Rebind tree events with coordinator methods
            try:
                self.resultsTree.bind("<Double-Button-1>", self.tree_coordinator.on_double_click)
                self.resultsTree.bind("<Motion>", self.tree_coordinator.on_motion)
                self.resultsTree.bind("<Leave>", self.tree_coordinator.on_leave)
                self.resultsTree.bind(
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
                    self.resultsTree.heading(
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
            self.findStarsButton = self.toolbar_manager.get_widget("button_find_stars")
            self.ignoreSelectedButton = self.toolbar_manager.get_widget("button_ignore_selected")
            self.editOldButton = self.toolbar_manager.get_widget("button_edit_old")
            self.darkToggle = self.toolbar_manager.get_widget("toggle_dark_mode")

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
            self.search_coordinator.refilter_from_cache(self.getDataToSearch(), source)
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


def representsInt(s):
    """Check if a string represents an integer."""
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


def main():
    """Main entry point for the application."""
    if len(sys.argv) > 3:
        raise ValueError(_("Usage: getsupernovae.py maxMag lastDays"))

    mag = DEFAULT_VALUES.MAGNITUDE
    daysToSearch = DEFAULT_VALUES.DAYS_TO_SEARCH

    if len(sys.argv) == 3:
        if representsInt(sys.argv[2]):
            daysToSearch = int(sys.argv[2])
            mag = sys.argv[1]
    elif len(sys.argv) == 2:
        if representsInt(sys.argv[1]):
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
