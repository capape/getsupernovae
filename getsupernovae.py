#!/usr/bin/python
# Check supernova data
#

from typing import List
import urllib.parse
from astropy.coordinates import EarthLocation
from astropy.time import Time
from datetime import datetime, timedelta
import sys
import os

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from app.models.dto import SupernovaDTO
# ensure local modules in this directory can be imported when script run directly
sys.path.insert(0, os.path.dirname(__file__))
import astropy.units as u



from app.models.snmodels import Supernova
from app.utils.snparser import parse_date
from app.ui.snvisibility import VisibilityWindow
from app.ui.results_presenter import ResultsPresenter
from app.ui.filter_panel_manager import FilterPanelManager, FilterPanelCallbacks
from app.ui.results_panel_manager import ResultsPanelManager, ResultsPanelCallbacks
from app.ui.toolbar_manager import ToolbarManager, ToolbarCallbacks
from app.services.supernova_filter_service import SupernovaFilterService
from app.services.supernova_selection_service import SupernovaSelectionService
from app.services.observation_time_service import ObservationTimeService
from app.coordinators.search_coordinator import SearchCoordinator
from app.coordinators.report_coordinator import ReportCoordinator
from app.coordinators.dialog_coordinator import DialogCoordinator
from app.coordinators.results_tree_coordinator import ResultsTreeCoordinator
from app.coordinators.theme_coordinator import ThemeCoordinator
from app.reports.report_text import createText, createTextAsString
from app.reports.report_pdf import createPdf
from app.state import AppStateManager, PreferencesManager
from app.config.snconfig import (
    load_old_supernovae,
    load_sites,
    load_visibility_windows,
    bootstrap_config,
    get_user_config_dir,
    load_user_prefs,
    save_user_prefs,
)

# import the external plotter helper
from app.i18n import _, set_language, get_language
from app.services.provider import NetworkRochesterProvider
from app import __version__
from app.config.ui_constants import (
    THEME_COLORS,
    UI_CONSTANTS,
    DEFAULT_VALUES,
    NETWORK_CONSTANTS,
    FILE_CONSTANTS,
    UI_STRINGS,
)
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

    def __init__(self, visibility_factory=None, provider_factory=None, reporter=None, filter_service=None, selection_service=None):
        # visibility_factory should be a callable/class that creates a
        # visibility window instance with signature
        # VisibilityWindow(minAlt, maxAlt, minAz, maxAz)
        self.visibility_factory = visibility_factory if visibility_factory is not None else VisibilityWindow
        # provider_factory constructs a provider used to fetch Rochester data
        self.provider_factory = provider_factory if provider_factory is not None else NetworkRochesterProvider
        # reporter is optional; selection logic does not require it but keep for DI consistency
        self.reporter = reporter
        # filter_service handles all filtering logic
        self.filter_service = filter_service if filter_service is not None else SupernovaFilterService(visibility_factory=self.visibility_factory)
        # selection_service coordinates selection and sorting
        self.selection_service = selection_service if selection_service is not None else SupernovaSelectionService(
            filter_service=self.filter_service,
            visibility_windows=visibility_windows
        )

    def selectAndSortSupernovas(
        self, e: SupernovaCallBackData, supernovaeList: List[SupernovaDTO]
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
            supernova_list=supernovaeList,
            max_magnitude=max_magnitude,
            observation_start=e.observationStart,
            observation_hours=int(e.observationHours),
            from_date=e.fromDate,
            site=e.site,
            exclusion_list=set(old) if old else set(),
            visibility_window_name=getattr(e, "visibilityWindowName", None),
            min_latitude=float(e.minLatitude),
            visibility_factory=self.visibility_factory
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
        observationStart = (
            observationDay.strftime("%Y-%m-%d") + "T" + localStartTime + "Z"
        )

        time1 = Time(observationStart)
        time2 = time1 + timedelta(hours=hoursObservation)

        # Convert maxMag to float
        try:
            max_mag_threshold = float(maxMag)
        except Exception:
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
            visibility_factory=self.visibility_factory
        )

        # Convert to domain models
        supernovas = self.filter_service.convert_to_domain_models(filtered_results)

        return supernovas


# Note: domain model dataclasses live in `app.models.snmodels` and are imported
# at the top of this module. Do not redefine them here to avoid drift.


class SearchFilters:
    def __init__(
        self,
        magnitude: str,
        daysToSearch: int,
        observationDate: datetime,
        observationTime: str,
        observationHours: int,
        site: str,
        minLatitude: float,
        visibilityWindowName: str = None,
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
        except Exception:
            log_exception(logger, "Failed to add combined trace callback")
        try:
            var.trace_add("write", callback)
            return
        except Exception:
            log_exception(logger, "Failed to add write trace callback")
        try:
            var.trace_add("unset", callback)
        except Exception:
            log_exception(logger, "Failed to add unset trace callback")

    def _update_visibility_ui(self):
        """Enable/disable minLatitude entry depending on visibility window selection

        If a named visibility window is selected (present in `visibility_windows`),
        disable the `minLatitude` entry and show its numeric values in
        `visibilityValuesLabel`. If no valid window is selected, enable the
        `minLatitude` entry and clear the label.
        """
        try:
            sel = (getattr(self, "visibilityWindow", None) and self.visibilityWindow.get()) or ""
        except Exception:
            log_exception(logger, "Failed to read selected visibility window")
            sel = ""

        try:
            if sel and sel in visibility_windows:
                cfg = visibility_windows.get(sel, {})
                minAlt = cfg.get("minAlt", 0.0)
                maxAlt = cfg.get("maxAlt", 90.0)
                minAz = cfg.get("minAz", 0.0)
                maxAz = cfg.get("maxAz", 360.0)
                txt = f"minAlt: {minAlt:.1f}°  maxAlt: {maxAlt:.1f}°  minAz: {minAz:.1f}°  maxAz: {maxAz:.1f}°"

                self.filter_panel_manager.update_visibility_values_label(txt)
                self.filter_panel_manager.set_min_latitude_state("disabled")
            else:
                self.filter_panel_manager.update_visibility_values_label("")
                self.filter_panel_manager.set_min_latitude_state("normal")

        except Exception:
            log_exception(logger, "Failed to update visibility UI")

    def _persist_prefs(self, *args):
        """Collect current tracked UI values and persist them to disk."""
        # Don't persist during initialization (before prefs are loaded)
        if getattr(self, '_initializing', False):
            return

        try:
            # Update state manager with current UI values (store names, not computed values)
            self.state_manager.update_search_state(
                magnitude=(getattr(self, "magnitude", None) and self.magnitude.get()) or "",
                days_to_search=(getattr(self, "daysToSearch", None) and self.daysToSearch.get()) or "30",
                observation_date=(getattr(self, "observationDate", None) and self.observationDate.get()) or "",
                observation_time=(getattr(self, "observationTime", None) and self.observationTime.get()) or "",
                observation_duration=(getattr(self, "observationDuration", None) and self.observationDuration.get()) or "",
                site=(getattr(self, "site", None) and self.site.get()) or None,
                visibility_window=(getattr(self, "visibilityWindow", None) and self.visibilityWindow.get()) or None,
                min_latitude=(getattr(self, "minLatitud", None) and self.minLatitud.get()) or "",
            )

            self.state_manager.update_ui_state(
                language=(getattr(self, "langVar", None) and self.langVar.get()) or "en",
                dark_mode=(getattr(self, "dark_mode", None) and self.dark_mode.get()) or False,
            )

            # Save to disk using preferences manager
            try:
                self.preferences_manager.save_preferences(self.state_manager.state)
            except Exception:
                log_exception(logger, "Failed to save preferences to disk")
        except Exception:
            log_exception(logger, "Failed to persist preferences")

    def _load_and_apply_prefs(self):
        """Load persisted prefs and apply to UI variables where valid."""
        try:
            # Try to load new format first
            loaded_state = self.preferences_manager.load_preferences()

            # If no new format exists, try to migrate from old format
            if loaded_state is None:
                try:
                    old_prefs = load_user_prefs()
                    if old_prefs and isinstance(old_prefs, dict):
                        # Migrate old flat dict format to new state structure
                        from app.state.app_state import AppState
                        loaded_state = AppState()

                        # Map old keys to new state
                        if 'magnitude' in old_prefs:
                            loaded_state.search.magnitude = old_prefs['magnitude']
                        if 'daysToSearch' in old_prefs:
                            loaded_state.search.days_to_search = old_prefs['daysToSearch']
                        if 'observationTime' in old_prefs:
                            loaded_state.search.observation_time = old_prefs['observationTime']
                        if 'observationHours' in old_prefs:
                            loaded_state.search.observation_duration = old_prefs['observationHours']
                        if 'minLatitude' in old_prefs:
                            loaded_state.search.min_latitude = old_prefs['minLatitude']
                        if 'site' in old_prefs:
                            loaded_state.search.site = old_prefs['site']
                        if 'visibilityWindow' in old_prefs:
                            loaded_state.search.visibility_window = old_prefs['visibilityWindow']
                        if 'language' in old_prefs:
                            loaded_state.ui.language = old_prefs['language']

                        # Save in new format for next time
                        self.preferences_manager.save_preferences(loaded_state)
                except Exception:
                    log_exception(logger, "Failed to migrate legacy preferences")

            if loaded_state is None:
                return

            # Update state manager with loaded state
            self.state_manager.state = loaded_state

            # Apply search state to UI
            try:
                if loaded_state.search.magnitude:
                    self.magnitude.set(str(loaded_state.search.magnitude))
            except Exception:
                log_exception(logger, "Failed to restore magnitude preference")

            try:
                if loaded_state.search.days_to_search:
                    self.daysToSearch.set(str(loaded_state.search.days_to_search))
            except Exception:
                log_exception(logger, "Failed to restore days_to_search preference")

            try:
                if loaded_state.search.observation_date:
                    self.observationDate.set(str(loaded_state.search.observation_date))
            except Exception:
                log_exception(logger, "Failed to restore observation_date preference")

            try:
                if loaded_state.search.observation_time:
                    self.observationTime.set(str(loaded_state.search.observation_time))
            except Exception:
                log_exception(logger, "Failed to restore observation_time preference")

            try:
                if loaded_state.search.observation_duration:
                    self.observationDuration.set(str(loaded_state.search.observation_duration))
            except Exception:
                log_exception(logger, "Failed to restore observation_duration preference")

            try:
                if loaded_state.search.min_latitude:
                    self.minLatitud.set(str(loaded_state.search.min_latitude))
            except Exception:
                log_exception(logger, "Failed to restore min_latitude preference")

            try:
                site = loaded_state.search.site
                if site and site in list(sites.keys()):
                    self.site.set(site)
            except Exception:
                log_exception(logger, "Failed to restore site preference")

            try:
                vw = loaded_state.search.visibility_window
                if vw and vw in visibility_windows:
                    self.visibilityWindow.set(vw)
            except Exception:
                log_exception(logger, "Failed to restore visibility window preference")

            # Apply UI state
            try:
                lang = loaded_state.ui.language
                if lang:
                    try:
                        set_language(lang)
                        if getattr(self, "langVar", None):
                            self.langVar.set(lang)
                        try:
                            self._on_language_change()
                        except Exception:
                            log_exception(logger, "Failed to refresh UI after language restoration")
                    except Exception:
                        log_exception(logger, "Failed to apply restored language")
            except Exception:
                log_exception(logger, "Failed while restoring language preference")

            try:
                dark_mode = loaded_state.ui.dark_mode
                if dark_mode is not None and getattr(self, "dark_mode", None):
                    self.dark_mode.set(dark_mode)
                    try:
                        self.theme_coordinator.apply_theme()
                    except Exception:
                        log_exception(logger, "Failed to apply restored dark mode theme")
            except Exception:
                log_exception(logger, "Failed to restore dark mode preference")

            try:
                self._update_visibility_ui()
            except Exception:
                log_exception(logger, "Failed to refresh visibility UI after restoring preferences")
        except Exception:
            log_exception(logger, "Failed to load and apply preferences")

    def getDataToSearch(self):
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
        except Exception as ex:
            messagebox.showerror(
                _("Invalid input"),
                _("Invalid observation time. Use HH, HH:MM or HH:MM:SS.\n\nDetails: {error}").format(error=str(ex)),
            )
            return None

    #
    # Check if there is already a search done with current filters
    #
    def withData(self):
        if self.supernovasFound == None:
            return False
        return True


    #
    # PDF button callback
    #
    def callbackPdfSupernovas(self, e: SupernovaCallBackData):
        """Generate PDF report using report coordinator."""
        self.report_coordinator.generate_pdf_report(e)

    #
    # TXT button callback
    #
    def callbackTextSupernovas(self, e: SupernovaCallBackData):
        """Generate TXT report using report coordinator."""
        self.report_coordinator.generate_txt_report(e)
    #
    #  Refresh button callback
    #
    def callbackRefreshSearchSupernovas(self, e: SupernovaCallBackData):
        """Refresh search results using the search coordinator."""
        if e is None:
            return
        self.search_coordinator.refresh_search(e)

    #
    # Do a async search
    #
    def callbackSearchSupernovasAsync(self, e: SupernovaCallBackData, source="SEARCH"):
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
        except Exception:
            log_exception(logger, "Failed to handle search results")

    def _set_button_state(self, button_name: str, state: str):
        """Set button state from coordinator.

        Args:
            button_name: Button identifier ("pdf", "txt", "refresh")
            state: Button state ("normal", "disabled")
        """
        try:
            tk_state = tk.NORMAL if state == "normal" else tk.DISABLED
            if button_name == "pdf" and hasattr(self, 'pdfButton'):
                self.pdfButton["state"] = tk_state
            elif button_name == "txt" and hasattr(self, 'txtButton'):
                self.txtButton["state"] = tk_state
            elif button_name == "refresh" and hasattr(self, 'searchButton'):
                self.searchButton["state"] = tk_state
        except Exception:
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
        except Exception:
            return None

    def _update_sites_combobox(self, values: list, selected: str = None):
        """Update site combobox with new values.
        
        Args:
            values: List of site names
            selected: Site name to select
        """
        try:
            self.filter_panel_manager.update_site_values(values)
            if selected:
                self.site.set(selected)
        except Exception:
            log_exception(logger, "Failed to update sites combobox")

    def _update_visibility_windows_combobox(self, values: list, selected: str = None):
        """Update visibility window combobox with new values.
        
        Args:
            values: List of visibility window names
            selected: Visibility window name to select
        """
        try:
            self.filter_panel_manager.update_visibility_window_values(values)
            if selected:
                self.visibilityWindow.set(selected)
        except Exception:
            log_exception(logger, "Failed to update visibility windows combobox")

    def _enable_find_stars_button(self, button_name: str):
        """Enable the find stars button.
        
        Args:
            button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, 'findStarsButton') and self.findStarsButton:
                self.findStarsButton.config(state=tk.NORMAL)
        except Exception:
            log_exception(logger, "Failed to enable find stars button")

    def _disable_find_stars_button(self, button_name: str):
        """Disable the find stars button.
        
        Args:
            button_name: Button name (not used, kept for interface compatibility)
        """
        try:
            if hasattr(self, 'findStarsButton') and self.findStarsButton:
                self.findStarsButton.config(state=tk.DISABLED)
        except Exception:
            log_exception(logger, "Failed to disable find stars button")

    def callbackClearResults(self, var, index, mode):
        self.supernovasFound = None

    def set_results_text(self, datatxt: str):
        """Helper to update the results table from supernova data."""
        # Clear existing tree entries
        try:
            for item in self.resultsTree.get_children():
                self.resultsTree.delete(item)
            self.supernova_data.clear()
        except Exception:
            log_exception(logger, "Failed to clear existing results tree entries")

        # If datatxt is an error message, show it
        if datatxt and (datatxt.startswith("ERROR") or self.supernovasFound is None):
            try:
                # Insert error as a single row
                self.resultsTree.insert("", "end", values=(datatxt, "", "", "", "", "", "", "", "", "", ""))
            except Exception:
                log_exception(logger, "Failed to render error row in results tree")
            return

        # Populate tree from self.supernovasFound
        try:
            if self.supernovasFound:
                for idx, sn in enumerate(self.supernovasFound):
                    presenter = self.presenter
                    try:
                        row = presenter.present(sn)
                    except Exception:
                        # Fallback to minimal row on presenter error
                        row = (
                            getattr(sn, 'name', ''),
                            getattr(sn, 'type', ''),
                            getattr(sn, 'mag', '') or '',
                            getattr(sn, 'date', '') or '',
                            '',
                            getattr(sn, 'host', ''),
                            getattr(sn, 'constellation', ''),
                            '',
                            '',
                            '🔗',
                            '🔗',
                        )

                    # Determine brightness tag based on numeric magnitude
                    mag_val = None
                    try:
                        mag_val = float(getattr(sn, 'mag', None)) if getattr(sn, 'mag', None) is not None else None
                    except Exception:
                        mag_val = None

                    is_bright = mag_val is not None and mag_val < DEFAULT_VALUES.BRIGHT_MAGNITUDE_THRESHOLD
                    tag = (UI_STRINGS.TAG_EVEN_ROW_BRIGHT if idx % 2 == 0 else UI_STRINGS.TAG_ODD_ROW_BRIGHT) if is_bright else (UI_STRINGS.TAG_EVEN_ROW if idx % 2 == 0 else UI_STRINGS.TAG_ODD_ROW)

                    item_id = self.resultsTree.insert("", "end", values=row, tags=(tag,))
                    self.supernova_data[item_id] = sn
        except Exception as e:
            # If population fails, show error
            try:
                self.resultsTree.insert("", "end", values=(f"Error: {str(e)}", "", "", "", "", "", "", "", "", "", ""))
            except Exception:
                log_exception(logger, "Failed to render exception row in results tree")

    def build_left_panel(self):
        """Build the left-side filter controls using FilterPanelManager."""
        try:
            # Prepare variables dictionary for the filter panel
            filter_variables = {
                'magnitude': self.magnitude,
                'days_to_search': self.daysToSearch,
                'observation_date': self.observationDate,
                'observation_time': self.observationTime,
                'observation_duration': self.observationDuration,
                'site': self.site,
                'visibility_window': self.visibilityWindow,
                'min_latitude': self.minLatitud,
            }

            # Create callbacks for the filter panel
            callbacks = FilterPanelCallbacks(
                on_clear_results=self.callbackClearResults,
                on_persist_prefs=self._persist_prefs,
                on_update_visibility_ui=self._update_visibility_ui,
                on_language_change=self._on_language_change,
                on_add_site=self.callbackAddSite,
                on_add_visibility_window=self.callbackAddVisibilityWindow,
            )

            # Create and build the filter panel manager
            self.filter_panel_manager = FilterPanelManager(
                parent=self,
                variables=filter_variables,
                sites=sites,
                visibility_windows=visibility_windows,
                callbacks=callbacks,
                dark_mode=self.dark_mode
            )

            self.filter_panel_manager.build()

            # Store references to commonly accessed widgets for backward compatibility
            self.cbSite = self.filter_panel_manager.widgets.get('combobox_site')
            self.cbVisibility = self.filter_panel_manager.widgets.get('combobox_visibility')
            self.entryLatitud = self.filter_panel_manager.widgets.get('entry_min_latitude')
            self.visibilityValuesLabel = self.filter_panel_manager.widgets.get('label_visibility_values')

            # Store widget references for language change updates
            self.labelMagnitude = self.filter_panel_manager.widgets.get('label_magnitude')
            self.labelDaysToSearch = self.filter_panel_manager.widgets.get('label_days_to_search')
            self.labelObservationDate = self.filter_panel_manager.widgets.get('label_observation_date')
            self.labelInitTime = self.filter_panel_manager.widgets.get('label_init_time')
            self.labelDuration = self.filter_panel_manager.widgets.get('label_duration')
            self.labelSite = self.filter_panel_manager.widgets.get('label_site')
            self.labelLang = self.filter_panel_manager.widgets.get('label_language')
            self.labelVisibility = self.filter_panel_manager.widgets.get('label_visibility')
            self.labelLatitud = self.filter_panel_manager.widgets.get('label_min_latitude')
            self.rochesterText = self.filter_panel_manager.widgets.get('text_rochester')
            self.cbLang = self.filter_panel_manager.widgets.get('combobox_language')

            # Get langVar from filter panel manager
            if 'language' in filter_variables:
                self.langVar = filter_variables['language']

            # Apply persisted prefs if present (best-effort)
            try:
                self._load_and_apply_prefs()
            except Exception:
                log_exception(logger, "Failed to load and apply preferences while building left panel")

            # Initialization complete, enable preference persistence
            self._initializing = False
        except Exception:
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
                on_pdf=lambda: self.callbackPdfSupernovas(self.getDataToSearch()),
                on_txt=lambda: self.callbackTextSupernovas(self.getDataToSearch()),
                on_refresh=lambda: self.callbackRefreshSearchSupernovas(self.getDataToSearch()),
                on_exit=self.quit,
            )

            # Create and build the results panel manager
            self.results_panel_manager = ResultsPanelManager(
                parent=self,
                callbacks=callbacks,
                dark_mode=self.dark_mode
            )

            self.results_panel_manager.build()

            # Store references to commonly accessed widgets for backward compatibility
            self.resultsTree = self.results_panel_manager.get_tree()
            self.labelResults = self.results_panel_manager.widgets.get('label_results')
            self.pdfButton = self.results_panel_manager.widgets.get('button_pdf')
            self.txtButton = self.results_panel_manager.widgets.get('button_txt')
            self.searchButton = self.results_panel_manager.widgets.get('button_refresh')
            self.exitButton = self.results_panel_manager.widgets.get('button_exit')
            self.progressBar = self.results_panel_manager.widgets.get('progress_bar')

            # Use manager's data storage
            self.supernova_data = self.results_panel_manager.supernova_data

            # Initialize ResultsTreeCoordinator to handle all tree interactions
            self.tree_coordinator = ResultsTreeCoordinator(
                tree_widget=self.resultsTree,
                supernova_data=self.supernova_data,
                get_dark_mode=lambda: self.dark_mode.get() if hasattr(self, 'dark_mode') else False,
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
                on_pdf=lambda: self.callbackPdfSupernovas(self.getDataToSearch()),
                on_txt=lambda: self.callbackTextSupernovas(self.getDataToSearch()),
                on_refresh=lambda: self.callbackRefreshSearchSupernovas(self.getDataToSearch()),
                on_exit=self.quit,
            )
            
            # Update callbacks and manually rebind tree events
            self.results_panel_manager.callbacks = updated_callbacks
            
            # Rebind tree events with coordinator methods
            try:
                self.resultsTree.bind("<Double-Button-1>", self.tree_coordinator.on_double_click)
                self.resultsTree.bind("<Motion>", self.tree_coordinator.on_motion)
                self.resultsTree.bind("<Leave>", self.tree_coordinator.on_leave)
                self.resultsTree.bind("<<TreeviewSelect>>", self.tree_coordinator.on_selection_change)
            except Exception:
                log_exception(logger, "Failed to rebind tree events with coordinator")
            
            # Update column sort commands to use coordinator
            try:
                for col, is_numeric in [("name", False), ("type", False), ("magnitude", True), 
                                       ("date", False), ("observation_time", False), ("host", False),
                                       ("constellation", False), ("ra", False), ("dec", False),
                                       ("rochester", False), ("tns", False)]:
                    self.resultsTree.heading(col, command=lambda c=col, n=is_numeric: self.tree_coordinator.sort_column(c, n))
            except Exception:
                log_exception(logger, "Failed to update column sort commands")

            # Create toolbar manager callbacks
            toolbar_callbacks = ToolbarCallbacks(
                on_find_stars=self.tree_coordinator.find_stars_in_simbad,
                on_ignore_selected=self.callbackIgnoreSelectedSN,
                on_edit_old=self.callbackEditOldSupernovae,
                on_dark_mode_toggle=self.theme_coordinator.apply_theme,
            )

            # Create and build toolbar manager
            self.toolbar_manager = ToolbarManager(
                parent=self,
                callbacks=toolbar_callbacks,
                dark_mode=self.dark_mode,
                grid_column=3,
                grid_row=11,
                columnspan=2
            )

            self.toolbar_manager.build()

            # Store toolbar widget references
            self.findStarsButton = self.toolbar_manager.get_widget('button_find_stars')
            self.ignoreSelectedButton = self.toolbar_manager.get_widget('button_ignore_selected')
            self.editOldButton = self.toolbar_manager.get_widget('button_edit_old')
            self.darkToggle = self.toolbar_manager.get_widget('toggle_dark_mode')

            # Configure results tree styling
            self.theme_coordinator.configure_results_tree_styling()
        except Exception:
            log_exception(logger, "Failed to build results panel")

    def refilter_from_cache(self, source="REFRESH"):
        """Re-run selection/filtering on the cached data (if available).

        Uses the search coordinator to refilter without re-downloading.
        If no cached data exists, falls back to a full network download.
        """
        try:
            self.search_coordinator.refilter_from_cache(self.getDataToSearch(), source)
        except Exception:
            log_exception(logger, f"Failed to refilter from cache for source={source}")

    def callbackIgnoreSelectedSN(self):
        """Add the currently selected SN to the ignore list."""
        self.dialog_coordinator.ignore_selected_supernova()

    def callbackEditOldSupernovae(self):
        """Open the old supernovae editor dialog."""
        self.dialog_coordinator.edit_old_supernovae()

    def callbackAddSite(self):
        """Open the sites configuration dialog."""
        self.dialog_coordinator.open_sites_dialog()

    def callbackAddVisibilityWindow(self):
        """Open the visibility window configuration dialog."""
        self.dialog_coordinator.open_visibility_window_dialog()

    def __init__(self, filters, presenter=None, visibility_factory=None, provider_factory=None, reporter=None):

        super().__init__()

        # Initialize state management (parallel infrastructure, existing code unchanged)
        self.state_manager = AppStateManager()
        self.preferences_manager = PreferencesManager()

        # Flag to prevent persisting preferences before they're loaded
        self._initializing = True

        self.supernovasFound = None
        self.refreshing = False

        # Create dark_mode variable first (required by apply_theme)
        self.dark_mode = tk.BooleanVar(value=True)

        # Initialize ThemeCoordinator to manage all theme operations
        self.theme_coordinator = ThemeCoordinator(
            root_window=self,
            get_results_tree=lambda: getattr(self, 'resultsTree', None),
            get_supernova_data=lambda: getattr(self, 'supernova_data', {}),
            get_dark_mode=lambda: self.dark_mode.get() if hasattr(self, 'dark_mode') else False,
            on_persist_prefs=self._persist_prefs,
        )

        # Force default UI language to English on startup
        try:
            set_language("en")
        except Exception:
            log_exception(logger, "Failed to set default startup language")

        # Apply theme early so initial widgets pick up dark mode colors
        try:
            self.theme_coordinator.apply_theme()
        except Exception:
            log_exception(logger, "Failed to apply initial theme during startup")

        self.magnitude = tk.StringVar()
        self.magnitude.trace_add(["write", "unset"], self.callbackClearResults)

        self.daysToSearch = tk.StringVar()
        self.daysToSearch.trace_add(["write", "unset"], self.callbackClearResults)

        self.observationDate = tk.StringVar()
        self.observationDate.trace_add(["write", "unset"], self.callbackClearResults)

        self.observationDuration = tk.StringVar()
        self.observationDuration.trace_add(["write", "unset"], self.callbackClearResults)

        self.minLatitud = tk.StringVar()
        self.minLatitud.trace_add(["write", "unset"], self.callbackClearResults)

        self.observationTime = tk.StringVar()
        self.observationTime.trace_add(["write", "unset"], self.callbackClearResults)

        self.site = tk.StringVar()
        self.site.trace_add(["write", "unset"], self.callbackClearResults)

        # Selected named visibility window (optional)
        self.visibilityWindow = tk.StringVar()
        self.visibilityWindow.trace_add(["write", "unset"], self.callbackClearResults)

        self.results = tk.StringVar()
        self.results.trace_add(["write", "unset"], self.callbackClearResults)
        # Dark mode variable already created earlier (before apply_theme call)
        self.dark_mode.trace_add(["write", "unset"], lambda *a: None)


        # injectable presenter and optional visibility factory (for testing)
        self.presenter = presenter if presenter is not None else ResultsPresenter()
        self.visibility_factory = visibility_factory if visibility_factory is not None else VisibilityWindow
        # provider_factory and reporter DI
        self.provider_factory = provider_factory if provider_factory is not None else NetworkRochesterProvider
        self.reporter = reporter

        # Initialize RochesterSupernova for data processing
        self.rochester_supernova = RochesterSupernova(
            visibility_factory=self.visibility_factory,
            provider_factory=self.provider_factory,
            reporter=self.reporter,
        )

        # Initialize SearchCoordinator for managing async searches
        self.search_coordinator = SearchCoordinator(
            rochester_supernova=self.rochester_supernova,
            visibility_factory=self.visibility_factory,
            provider_factory=self.provider_factory,
            reporter=self.reporter,
            on_results_updated=self._handle_search_results,
            on_button_state_change=self._set_button_state,
            on_progress_start=self.start_progress_bar,
            on_progress_end=self.end_progress_bar,
            on_pdf_invoke=lambda: self.pdfButton.invoke() if hasattr(self, 'pdfButton') else None,
            on_txt_invoke=lambda: self.txtButton.invoke() if hasattr(self, 'txtButton') else None,
            after_callback=self.after,
        )

        # Initialize ReportCoordinator for managing report generation
        self.report_coordinator = ReportCoordinator(
            has_results=self.withData,
            get_results=lambda: self.supernovasFound,
            on_search_async=self.callbackSearchSupernovasAsync,
            on_results_text_update=self.set_results_text,
            on_show_message=self._show_yes_no_dialog,
            on_show_warning=self._show_warning_dialog,
        )

        # Initialize DialogCoordinator for managing modal dialogs
        self.dialog_coordinator = DialogCoordinator(
            parent_window=self,
            get_selected_supernova=self._get_selected_supernova,
            on_update_sites=self._update_sites_combobox,
            on_update_visibility_windows=self._update_visibility_windows_combobox,
            on_refilter=lambda: self.refilter_from_cache("REFRESH"),
            on_search_async=lambda data, source: self.callbackSearchSupernovasAsync(data, source),
            on_show_info=self._show_info_dialog,
            on_show_error=self._show_error_dialog,
            on_get_current_site=lambda: self.site.get() if hasattr(self, 'site') else "",
            on_get_current_visibility_window=lambda: self.visibilityWindow.get() if hasattr(self, 'visibilityWindow') else "",
            get_combobox_site=lambda: self.cbSite if hasattr(self, 'cbSite') else None,
            get_combobox_visibility=lambda: self.cbVisibility if hasattr(self, 'cbVisibility') else None,
        )

        self.title(_("Find latest supernovae - {}").format(__version__))

        # Load application icon if available. Prefer app_icon.ico (Windows),
        # then app_icon.png. If present, set the window icon; fallback is silent.
        try:
            icon_dir = os.path.join(os.path.dirname(__file__), FILE_CONSTANTS.ICONS_DIR)
            ico = os.path.join(icon_dir, FILE_CONSTANTS.ICON_ICO)
            png = os.path.join(icon_dir, FILE_CONSTANTS.ICON_PNG)
            svg = os.path.join(icon_dir, FILE_CONSTANTS.ICON_SVG)
            if os.path.exists(ico) and os.name == 'nt':
                try:
                    self.iconbitmap(ico)
                except Exception:
                    log_exception(logger, "Failed to set ICO application icon")
            elif os.path.exists(png):
                try:
                    img = tk.PhotoImage(file=png)
                    self.iconphoto(False, img)
                    # keep reference to avoid GC
                    self._icon_image = img
                except Exception:
                    log_exception(logger, "Failed to set PNG application icon")
            else:
                # If only SVG is present, we don't attempt to parse it here.
                # Users can convert the SVG to PNG/ICO (see docs).
                if os.path.exists(svg):
                    pass
        except Exception:
            log_exception(logger, "Failed during application icon setup")

        window_width = UI_CONSTANTS.WINDOW_WIDTH
        window_height = UI_CONSTANTS.WINDOW_HEIGHT

        # get the screen dimension
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # find the center point
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        # set the position of the window to the center of the screen
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        # enforce a minimum size so the dialog cannot be shrunk below layout assumptions
        try:
            self.minsize(window_width, window_height)
        except Exception:
            log_exception(logger, "Failed to enforce minimum window size")

        self.magnitude.set(filters.magnitude)
        self.daysToSearch.set(filters.daysToSearch)
        self.observationDate.set(filters.observationDate.strftime("%Y-%m-%d"))
        self.observationTime.set(filters.observationTime)
        self.observationDuration.set(filters.observationHours)
        self.minLatitud.set(filters.minLatitude)
        self.site.set(filters.site)
        # set visibility window (use provided filter or fallback to Default)
        try:
            if getattr(filters, "visibilityWindowName", None):
                self.visibilityWindow.set(filters.visibilityWindowName)
            else:
                # choose first available key or Default
                keys = list(visibility_windows.keys())
                if "Default" in visibility_windows:
                    self.visibilityWindow.set("Default")
                elif keys:
                    self.visibilityWindow.set(keys[0])
        except Exception:
            try:
                self.visibilityWindow.set("Default")
            except Exception:
                log_exception(logger, "Failed to set default visibility window")
        self.results.set("")

        # Build UI panels using dedicated builder methods
        try:
            self.build_left_panel()
        except Exception:
            log_exception(logger, "Failed to build left panel during startup")

        try:
            self.build_results_panel()
        except Exception:
            log_exception(logger, "Failed to build results panel during startup")

    def _on_language_change(self):
        """Handler when UI language selection changes: apply and refresh labels."""
        try:
            if not hasattr(self, 'langVar') or self.langVar is None:
                return
            lang = self.langVar.get().strip()
            if not lang:
                set_language(None)
            else:
                set_language(lang)
        except Exception:
            log_exception(logger, "Failed to apply selected language")

        # Update visible widget texts to the new language
        try:
            if hasattr(self, 'filter_panel_manager') and self.filter_panel_manager is not None:
                self.filter_panel_manager.refresh_labels()
            if hasattr(self, 'labelLatitud') and self.labelLatitud is not None:
                self.labelLatitud.config(text=_("Min latitude: "))

            # Refresh UI manager labels
            if hasattr(self, 'results_panel_manager') and self.results_panel_manager is not None:
                self.results_panel_manager.refresh_labels()
            if hasattr(self, 'toolbar_manager') and self.toolbar_manager is not None:
                self.toolbar_manager.refresh_labels()
            try:
                if hasattr(self, 'ignoreSelectedButton') and self.ignoreSelectedButton is not None:
                    self.ignoreSelectedButton.config(text=_("Ignore selected SN"))
                if hasattr(self, 'editOldButton') and self.editOldButton is not None:
                    self.editOldButton.config(text=_("Edit Ignored SN"))
            except Exception:
                log_exception(logger, "Failed to refresh ignore/edit toolbar labels")
            try:
                if hasattr(self, 'pdfButton') and self.pdfButton is not None:
                    self.pdfButton.config(text=_("PDF"))
                if hasattr(self, 'txtButton') and self.txtButton is not None:
                    self.txtButton.config(text=_("TXT"))
                if hasattr(self, 'searchButton') and self.searchButton is not None:
                    self.searchButton.config(text=_("Refresh Search"))
                if hasattr(self, 'exitButton') and self.exitButton is not None:
                    self.exitButton.config(text=_("Exit"))
            except Exception:
                log_exception(logger, "Failed to refresh action button labels")
            # Update window title
            try:
                self.title(_("Find latest supernovae"))
            except Exception:
                log_exception(logger, "Failed to refresh window title after language change")
        except Exception:
            log_exception(logger, "Failed to refresh UI labels after language change")

        # Reapply results tree styling after language change
        try:
            self.theme_coordinator.configure_results_tree_styling()
        except Exception:
            log_exception(logger, "Failed to reconfigure results tree after language change")
        try:
            # re-apply theme in case translations affected widget styles
            self.theme_coordinator.apply_theme()
        except Exception:
            log_exception(logger, "Failed to reapply theme after language change")
        try:
            # ensure visibility UI reflects current selection at startup
            self._update_visibility_ui()
        except Exception:
            log_exception(logger, "Failed to refresh visibility UI after language change")


def representsInt(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


def main():

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

    site = EarthLocation(lat=41.55 * u.deg, lon=2.09 * u.deg, height=224 * u.m)

    site = list(sites.keys())[0]


    filters = SearchFilters(mag, daysToSearch, datetime.now(), DEFAULT_VALUES.OBSERVATION_TIME, DEFAULT_VALUES.OBSERVATION_HOURS, site, DEFAULT_VALUES.MIN_LATITUDE)
    app = SupernovasApp(filters)
    app.mainloop()



# `_parse_row_safe` is provided by `snparser.py` and imported at the top of this file.


if __name__ == "__main__":
    main()
