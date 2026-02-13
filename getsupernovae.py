#!/usr/bin/python
# Check supernova data
#

from threading import Thread
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
        self.observationTime = self._normalize_observation_time(observationTime)
        self.observationHours = observationHours
        self.daysToSearch = daysToSearch
        self.site = site
        self.minLatitude = minLatitude
        self.observationStart = Time(observationDate + "T" + self.observationTime + "Z")
        self.fromDateTime = self.observationStart - timedelta(days=int(daysToSearch))
        self.fromDate = self.fromDateTime.strftime("%Y-%m-%d")
        self.visibilityWindowName = visibilityWindowName

    @staticmethod
    def _normalize_observation_time(observation_time: str) -> str:
        """Normalize observation time to HH:MM or HH:MM:SS format."""
        text = str(observation_time).strip()
        if not text:
            raise ValueError("Observation time is required")

        parts = text.split(":")
        if len(parts) not in (1, 2, 3):
            raise ValueError("Observation time must be HH, HH:MM or HH:MM:SS")

        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) >= 2 else 0
            second = int(parts[2]) if len(parts) == 3 else None
        except (TypeError, ValueError):
            raise ValueError("Observation time must contain numeric values")

        if hour < 0 or hour > 23:
            raise ValueError("Hour must be between 0 and 23")
        if minute < 0 or minute > 59:
            raise ValueError("Minute must be between 0 and 59")

        if second is None:
            return f"{hour:02d}:{minute:02d}"

        if second < 0 or second > 59:
            raise ValueError("Second must be between 0 and 59")
        return f"{hour:02d}:{minute:02d}:{second:02d}"

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

class AsyncRochesterDownload(Thread):
    def __init__(self, e: SupernovaCallBackData, visibility_factory=None, provider_factory=None, reporter=None):
        super().__init__()

        # Don't reset language - respect the user's current language setting
        self.result = None
        self.error = None
        self.config = e
        self.visibility_factory = visibility_factory
        # provider_factory may be a class or callable that accepts timeout kwarg
        self.provider_factory = provider_factory if provider_factory is not None else NetworkRochesterProvider
        # optional reporter object/module for DI
        self.reporter = reporter
        self.dto_list = None

    def run(self):
        try:
            # Use the injected provider factory to download and parse content.
            try:
                provider = self.provider_factory(timeout=20)
            except TypeError:
                # provider_factory may be a class that doesn't accept timeout
                provider = self.provider_factory()
            supernovaeList = provider.fetch()
            # propagate injected provider_factory and reporter to selection logic
            rochesterSupernova = RochesterSupernova(
                visibility_factory=self.visibility_factory,
                provider_factory=self.provider_factory,
                reporter=self.reporter,
            )
            # Continue using existing selection/filtering logic which expects raw rows
            self.result = rochesterSupernova.selectAndSortSupernovas(self.config, supernovaeList)
            # keep raw rows so the app can re-filter without re-downloading
            self.dto_list = supernovaeList
        except Exception as ex:
            # record the error for the main thread to show
            try:
                self.error = str(ex)
            except Exception:
                self.error = "unknown error"
            self.result = None


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
    def _configure_results_tree_styling(self):
        """Configure results tree row height and alternating row colors."""
        try:
            if not hasattr(self, 'resultsTree') or self.resultsTree is None:
                return

            # Configure row height - must use self as the first argument
            style = ttk.Style(self)
            style.configure(UI_STRINGS.RESULTS_TREE_STYLE, rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT)

            # Configure alternating row colors based on current theme
            dark = getattr(self, "dark_mode", None) and self.dark_mode.get()
            if dark:
                self.resultsTree.tag_configure(UI_STRINGS.TAG_EVEN_ROW, background=THEME_COLORS.DARK_EVEN_ROW)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_ODD_ROW, background=THEME_COLORS.DARK_ODD_ROW)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_EVEN_ROW_BRIGHT, background=THEME_COLORS.DARK_EVEN_ROW, foreground=THEME_COLORS.BRIGHT_FG_DARK)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_ODD_ROW_BRIGHT, background=THEME_COLORS.DARK_ODD_ROW, foreground=THEME_COLORS.BRIGHT_FG_DARK)
            else:
                self.resultsTree.tag_configure(UI_STRINGS.TAG_EVEN_ROW, background=THEME_COLORS.LIGHT_EVEN_ROW)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_ODD_ROW, background=THEME_COLORS.LIGHT_ODD_ROW)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_EVEN_ROW_BRIGHT, background=THEME_COLORS.LIGHT_EVEN_ROW, foreground=THEME_COLORS.BRIGHT_FG_LIGHT)
                self.resultsTree.tag_configure(UI_STRINGS.TAG_ODD_ROW_BRIGHT, background=THEME_COLORS.LIGHT_ODD_ROW, foreground=THEME_COLORS.BRIGHT_FG_LIGHT)

            # Reapply tags to all existing items to preserve bright highlighting
            self._reapply_tree_tags()
        except Exception:
            log_exception(logger, "Failed to configure results tree styling")

    def _reapply_tree_tags(self):
        """Reapply tags to all tree items based on magnitude and position."""
        try:
            if not hasattr(self, 'resultsTree') or self.resultsTree is None:
                return

            items = self.resultsTree.get_children('')
            for index, item in enumerate(items):
                try:
                    if item in self.supernova_data:
                        sn = self.supernova_data[item]
                        mag = getattr(sn, 'mag', None)
                        try:
                            is_bright = mag is not None and float(mag) < 15
                        except (ValueError, TypeError):
                            is_bright = False

                        if is_bright:
                            tag = 'evenrow_bright' if index % 2 == 0 else 'oddrow_bright'
                        else:
                            tag = 'evenrow' if index % 2 == 0 else 'oddrow'

                        self.resultsTree.item(item, tags=(tag,))
                except Exception:
                    log_exception(logger, "Failed to reapply tree tag for item")
        except Exception:
            log_exception(logger, "Failed to reapply tree tags")

    def apply_theme(self):
        """Apply light/dark theme to ttk widgets and some native widgets."""
        try:
            # Persist dark mode preference when changed
            try:
                self._persist_prefs()
            except Exception:
                log_exception(logger, "Failed to persist preferences during theme apply")

            style = ttk.Style()
            try:
                style.theme_use("clam")
            except Exception:
                log_exception(logger, "Failed to apply ttk theme 'clam'")
        except Exception:
            style = None

        dark = getattr(self, "dark_mode", None) and self.dark_mode.get()
        if dark:
            bg = THEME_COLORS.DARK_BG
            fg = THEME_COLORS.DARK_FG
            entry_bg = THEME_COLORS.DARK_ENTRY_BG
            btn_bg = THEME_COLORS.DARK_BUTTON_BG
            tree_bg = THEME_COLORS.DARK_TREE_BG
        else:
            # Explicitly set light-mode colors so previously-applied dark
            # styling is cleared when toggling off.
            bg = THEME_COLORS.LIGHT_BG
            fg = THEME_COLORS.LIGHT_FG
            entry_bg = THEME_COLORS.LIGHT_ENTRY_BG
            btn_bg = THEME_COLORS.LIGHT_BUTTON_BG
            tree_bg = THEME_COLORS.LIGHT_TREE_BG

        try:
            if style is not None:
                style.configure("TLabel", background=bg, foreground=fg)
                style.configure("TButton", background=btn_bg, foreground=fg)
                style.configure("TEntry", fieldbackground=entry_bg, foreground=fg)
                style.configure("TCombobox", fieldbackground=entry_bg, foreground=fg)
                style.configure("Treeview", background=tree_bg, fieldbackground=tree_bg, foreground=fg, rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT)
                style.configure(UI_STRINGS.RESULTS_TREE_STYLE, background=tree_bg, fieldbackground=tree_bg, foreground=fg, rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT)
                style.configure("TFrame", background=bg)
                style.configure("TCheckbutton", background=bg, foreground=fg)
                # selection highlight for treeview — choose a subtle color per theme
                try:
                    sel_color = THEME_COLORS.DARK_SELECTION if dark else THEME_COLORS.LIGHT_SELECTION
                    style.map('Treeview', background=[('selected', sel_color)])
                except Exception:
                    log_exception(logger, "Failed to map Treeview selection color")
                try:
                    # also set the main window background for non-ttk widgets
                    try:
                        self.configure(background=bg)
                    except Exception:
                        log_exception(logger, "Failed to configure root window background")
                    # Treeview styling
                    try:
                        if hasattr(self, 'resultsTree') and self.resultsTree is not None:
                            self.resultsTree.configure(style="Treeview")
                    except Exception:
                        log_exception(logger, "Failed to configure results tree style")
                except Exception:
                    log_exception(logger, "Failed while applying non-ttk theme updates")
        except Exception:
            log_exception(logger, "Failed to apply ttk theme configuration")

        # Reapply results tree styling after theme change
        try:
            self._configure_results_tree_styling()
        except Exception:
            log_exception(logger, "Failed to reconfigure results tree after theme change")

        try:
            if bg:
                self.configure(bg=bg)
        except Exception:
            log_exception(logger, "Failed to set root background color")

        # Update some known frames/widgets that are not styled by ttk
        try:
            for child in self.winfo_children():
                try:
                    child.configure(background=bg)
                except tk.TclError:
                    # Many ttk/native widgets do not expose a `background` option.
                    # This is expected and should not be logged as an error.
                    continue
                except Exception:
                    log_exception(logger, "Failed to configure child widget background")
        except Exception:
            log_exception(logger, "Failed to apply theme to child widgets")

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
                        self.apply_theme()
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
        if e is None:
            return

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "PDF")
        else:
            datatxt = createTextAsString(self.supernovasFound, e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
                getattr(e, 'visibilityWindowName', None))
            self.set_results_text(datatxt)
            pdf_path = createPdf(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
                getattr(e, 'visibilityWindowName', None),
            )

            # Show success message with PDF location
            import os
            import subprocess
            msg = _("PDF report saved to:\n{path}").format(path=pdf_path)
            if messagebox.askyesno(_("PDF Created"), msg + "\n\n" + _("Do you want to open it?")):
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(pdf_path)
                    elif os.name == 'posix':  # Linux/Mac
                        subprocess.run(['xdg-open' if 'linux' in os.sys.platform else 'open', pdf_path])
                except Exception as ex:
                    messagebox.showwarning(_("Cannot open file"), _("File saved but could not be opened automatically: {error}").format(error=str(ex)))

    #
    # TXT button callback
    #
    def callbackTextSupernovas(self, e: SupernovaCallBackData):
        if e is None:
            return

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "TXT")
        else:
            datatxt = createTextAsString(self.supernovasFound, e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
                getattr(e, 'visibilityWindowName', None))
            self.set_results_text(datatxt)
            createText(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
                getattr(e, 'visibilityWindowName', None),
            )
    #
    #  Refresh button callback
    #
    def callbackRefreshSearchSupernovas(self, e: SupernovaCallBackData):
        if e is None:
            return

        # If a refresh isn't already running, start an async refresh.
        # If we are already refreshing, ignore the extra click. If there
        # are cached results, they will be updated once the running
        # refresh completes and `monitor` finishes.
        if not self.refreshing:
            self.refreshing = True
            # disable the refresh button (searchButton) while refresh is running
            try:
                self.searchButton["state"] = tk.DISABLED
            except Exception:
                log_exception(logger, "Failed to disable refresh button during refresh start")
            self.callbackSearchSupernovasAsync(e, "REFRESH")
        else:
            # Already refreshing: do nothing (avoid using None results).
            return


    #
    # Do a async search
    #
    def callbackSearchSupernovasAsync(self, e: SupernovaCallBackData, source="SEARCH"):

        self.txtButton["state"] = tk.DISABLED
        self.pdfButton["state"] = tk.DISABLED
        self.searchButton["state"] = tk.DISABLED

        self.start_progress_bar()

        download_thread = AsyncRochesterDownload(
            e,
            visibility_factory=self.visibility_factory,
            provider_factory=self.provider_factory,
            reporter=self.reporter,
        )
        download_thread.start()

        self.monitor(download_thread, source)

    def monitor(self, thread, source="SEARCH"):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread, source))
        else:

            self.supernovasFound = thread.result

            # Populate results grid when data is available (also for PDF path)
            try:
                if self.supernovasFound:
                    # pass empty datatxt to indicate no error message
                    try:
                        self.set_results_text("")
                    except Exception:
                        log_exception(logger, "Failed to populate results text after async search")
            except Exception:
                log_exception(logger, "Failed while processing async search results")

            # If download/parsing failed, show an error banner in the results
            if self.supernovasFound is None:
                err = getattr(thread, "error", None)
                if err:
                    self.set_results_text(f"ERROR: Failed to fetch/parse data - {err}")
                else:
                    self.set_results_text("ERROR: Failed to fetch data (no details)")

            if source == "PDF":
                try:
                    self.pdfButton["state"] = tk.NORMAL
                    self.pdfButton.invoke()
                except Exception:
                    log_exception(logger, "Failed to invoke PDF generation after search")
                # ensure other controls are re-enabled after PDF generation
                try:
                    self.txtButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable TXT button after PDF flow")
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable refresh button after PDF flow")
            elif source == "TXT":
                try:
                    self.txtButton["state"] = tk.NORMAL
                    self.txtButton.invoke()
                except Exception:
                    log_exception(logger, "Failed to invoke TXT generation after search")
                # ensure other controls are re-enabled after text output
                try:
                    self.pdfButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable PDF button after TXT flow")
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable refresh button after TXT flow")
            elif source == "REFRESH":
                self.txtButton["state"] = tk.NORMAL
                self.txtButton.invoke()
                # refresh completed
                self.refreshing = False
                self.txtButton["state"] = tk.NORMAL
                self.pdfButton["state"] = tk.NORMAL
                self.searchButton["state"] = tk.NORMAL
                # cache raw rows if available for later re-filtering
                try:
                    self.last_rows = getattr(thread, "dto_list", None)
                except Exception:
                    log_exception(logger, "Failed to cache downloaded rows after refresh")
                    self.last_rows = None
            self.end_progress_bar()

    def start_progress_bar(self):
        """Start the progress bar animation."""
        self.results_panel_manager.start_progress_bar()

    def end_progress_bar(self):
        """Stop the progress bar animation."""
        self.results_panel_manager.stop_progress_bar()


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

    def _sort_column(self, col, is_numeric):
        """Sort treeview by column."""
        try:
            # Toggle sort direction if same column clicked
            if self.sort_column == col:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = col
                self.sort_reverse = False

            # Get column index
            col_idx = self.resultsTree['columns'].index(col)

            # Get all items with their values
            items = [(self.resultsTree.set(item, col), item) for item in self.resultsTree.get_children('')]

            # Sort items
            if is_numeric:
                # Numeric sort - handle empty values
                def sort_key(x):
                    try:
                        return float(x[0]) if x[0] else float('inf')
                    except (ValueError, TypeError):
                        return float('inf')
                items.sort(key=sort_key, reverse=self.sort_reverse)
            else:
                # Alphabetic sort
                items.sort(key=lambda x: x[0].lower() if x[0] else '', reverse=self.sort_reverse)

            # Rearrange items in sorted order
            for index, (val, item) in enumerate(items):
                self.resultsTree.move(item, '', index)

                # Reapply alternating row colors and brightness after sorting
                try:
                    if item in self.supernova_data:
                        sn = self.supernova_data[item]
                        mag = getattr(sn, 'mag', None)
                        try:
                            is_bright = mag is not None and float(mag) < 15
                        except (ValueError, TypeError):
                            is_bright = False

                        if is_bright:
                            tag = 'evenrow_bright' if index % 2 == 0 else 'oddrow_bright'
                        else:
                            tag = 'evenrow' if index % 2 == 0 else 'oddrow'

                        self.resultsTree.item(item, tags=(tag,))
                except Exception:
                    log_exception(logger, "Failed to re-tag sorted tree row")
        except Exception:
            log_exception(logger, "Failed to sort results tree column")

    def _on_selection_change(self, event):
        """Enable or disable Find stars button based on tree selection."""
        try:
            selection = self.resultsTree.selection()
            if selection and len(selection) > 0:
                self.findStarsButton.config(state=tk.NORMAL)
            else:
                self.findStarsButton.config(state=tk.DISABLED)
        except Exception:
            log_exception(logger, "Failed to update Find Stars button state on selection change")

    def _find_stars_in_simbad(self):
        """Query SIMBAD for objects near the selected supernova."""
        try:
            selection = self.resultsTree.selection()
            if not selection or len(selection) == 0:
                return

            item = selection[0]
            if item not in self.supernova_data:
                return

            sn = self.supernova_data[item]


            # Build SIMBAD query URL for the region around the supernova
            # Using the web interface format
            coord = getattr(sn, 'coordinates', None)
            if coord:
                ra_str = coord.ra.to_string(unit='hour', sep=':', precision=1)
                dec_str = coord.dec.to_string(unit='degree', sep=':', precision=1, alwayssign=True)
            else:
               ra_str = dec_str = ""

            # SIMBAD coordinate query URL (searches within configured box radius)
            # Filter for stellar objects (maintype '*') with Vmag < configured threshold
            # URL-encode the region parameter to handle colons/spaces in RA/Dec
            try:
                criteria_str = (
                    f"region(box,{ra_str} {dec_str},{NETWORK_CONSTANTS.SIMBAD_SEARCH_RADIUS}) & "
                    f"Vmag<{NETWORK_CONSTANTS.SIMBAD_MAX_VMAG} & "
                    f"maintype='{NETWORK_CONSTANTS.SIMBAD_MAIN_TYPE}'"
                )
                criteria_enc=urllib.parse.quote(criteria_str)

            except Exception:
                log_exception(logger, "Failed to build SIMBAD criteria query")
                criteria_enc = ""

            simbad_url = (
                f"{NETWORK_CONSTANTS.SIMBAD_QUERY_URL}?"
                f"Criteria={criteria_enc}&"
                f"OutputMode=LIST&"
                f"maxObjectect={NETWORK_CONSTANTS.SIMBAD_MAX_OBJECTS}&"
                f"submit=submit+query"
            )

            # Open in browser
            import webbrowser
            webbrowser.open(simbad_url)

        except Exception as e:
            try:
                messagebox.showerror(
                    _("Error"),
                    _("Failed to query SIMBAD: ") + str(e)
                )
            except Exception:
                log_exception(logger, "Failed to show SIMBAD error message")

    def _on_results_double_click(self, event):
        """Handle double-click on results table to open links."""
        try:
            region = self.resultsTree.identify("region", event.x, event.y)
            if region != "cell":
                return

            column = self.resultsTree.identify_column(event.x)
            item = self.resultsTree.identify_row(event.y)

            if not item or item not in self.supernova_data:
                return

            sn = self.supernova_data[item]

            # Column #10 is rochester, #11 is tns (1-indexed)
            if column == "#10":  # Rochester
                url = getattr(sn, 'rochesterUrl', None) or f"{getattr(sn, 'link', '')}"
                self._open_url(url)
            elif column == "#11":  # TNS
                url = getattr(sn, 'tnsUrl', None) or f"{NETWORK_CONSTANTS.TNS_OBJECT_URL}{getattr(sn, 'name', '')}"
                self._open_url(url)
        except Exception:
            log_exception(logger, "Failed to process results table double click")

    def _open_url(self, url):
        """Open URL in default browser."""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            log_exception(logger, "Failed to open URL")

    def _on_results_motion(self, event):
        """Show tooltip with visibility and discovery info on hover."""
        try:
            item = self.resultsTree.identify_row(event.y)

            # If we're over a different item or no item, update tooltip
            if item != self.tooltip_item:
                self._hide_tooltip()

                if item and item in self.supernova_data:
                    self.tooltip_item = item
                    sn = self.supernova_data[item]

                    # Build tooltip text with visibility and discovery info
                    tooltip_lines = []

                    # Discovery information
                    first_obs = getattr(sn, 'firstObserved', None)
                    if first_obs:
                        tooltip_lines.append(f"First observed: {first_obs}")

                    max_mag = getattr(sn, 'maxMagnitude', None)
                    max_mag_date = getattr(sn, 'maxMagnitudeDate', None)
                    if max_mag:
                        mag_line = f"Max magnitude: {max_mag}"
                        if max_mag_date:
                            mag_line += f" on {max_mag_date}"
                        tooltip_lines.append(mag_line)

                    # Visibility information
                    visibility = getattr(sn, 'visibility', None)
                    if visibility:
                        is_visible = getattr(visibility, 'visible', False)
                        tooltip_lines.append(f"Visible: {'Yes' if is_visible else 'No'}")

                        # Get altitude/azimuth coordinates if available
                        az_coords = getattr(visibility, 'azCords', None)
                        if az_coords and len(az_coords) > 0:
                            # Show first and last altitudes
                            try:
                                first_coord = az_coords[0]
                                last_coord = az_coords[-1]

                                first_time = getattr(first_coord, 'time', None)
                                first_alt = getattr(first_coord, 'coord', None)
                                last_time = getattr(last_coord, 'time', None)
                                last_alt = getattr(last_coord, 'coord', None)

                                if first_alt and hasattr(first_alt, 'alt'):
                                    tooltip_lines.append(f"Start altitude: {first_alt.alt.degree:.1f}°")
                                if last_alt and hasattr(last_alt, 'alt'):
                                    tooltip_lines.append(f"End altitude: {last_alt.alt.degree:.1f}°")

                                # Find max altitude
                                max_alt = max((getattr(c.coord, 'alt', None) for c in az_coords if hasattr(c.coord, 'alt')),
                                             default=None, key=lambda a: a.degree if a else -999)
                                if max_alt:
                                    tooltip_lines.append(f"Max altitude: {max_alt.degree:.1f}°")
                            except Exception:
                                log_exception(logger, "Failed to compute tooltip altitude values")

                    if tooltip_lines:
                        self._show_tooltip(event.x_root, event.y_root, "\n".join(tooltip_lines))
        except Exception:
            log_exception(logger, "Failed to process results hover tooltip")

    def _on_results_leave(self, event):
        """Hide tooltip when mouse leaves the tree."""
        self._hide_tooltip()

    def _show_tooltip(self, x, y, text):
        """Display tooltip at specified position."""
        try:
            self._hide_tooltip()

            self.tooltip_window = tk.Toplevel(self)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x+UI_CONSTANTS.TOOLTIP_OFFSET_X}+{y+UI_CONSTANTS.TOOLTIP_OFFSET_Y}")

            # Style tooltip based on dark mode
            dark = getattr(self, "dark_mode", None) and self.dark_mode.get()
            bg_color = THEME_COLORS.DARK_TOOLTIP_BG if dark else THEME_COLORS.LIGHT_TOOLTIP_BG
            fg_color = THEME_COLORS.DARK_TOOLTIP_FG if dark else THEME_COLORS.LIGHT_TOOLTIP_FG

            label = tk.Label(
                self.tooltip_window,
                text=text,
                justify=tk.LEFT,
                background=bg_color,
                foreground=fg_color,
                relief=tk.SOLID,
                borderwidth=1,
                padx=UI_CONSTANTS.TOOLTIP_PADX,
                pady=UI_CONSTANTS.TOOLTIP_PADY,
                font=("TkDefaultFont", 9)
            )
            label.pack()
        except Exception:
            log_exception(logger, "Failed to show tooltip")

    def _hide_tooltip(self):
        """Hide and destroy tooltip window."""
        try:
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None
            self.tooltip_item = None
        except Exception:
            log_exception(logger, "Failed to hide tooltip")

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
            # Create callbacks for the results panel
            callbacks = ResultsPanelCallbacks(
                on_sort_column=self._sort_column,
                on_double_click=self._on_results_double_click,
                on_motion=self._on_results_motion,
                on_leave=self._on_results_leave,
                on_selection_change=self._on_selection_change,
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

            # Create toolbar manager callbacks
            toolbar_callbacks = ToolbarCallbacks(
                on_find_stars=self._find_stars_in_simbad,
                on_ignore_selected=self.callbackIgnoreSelectedSN,
                on_edit_old=self.callbackEditOldSupernovae,
                on_dark_mode_toggle=self.apply_theme,
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

            # Store references to commonly accessed widgets for backward compatibility
            self.resultsTree = self.results_panel_manager.get_tree()
            self.labelResults = self.results_panel_manager.widgets.get('label_results')
            self.findStarsButton = self.toolbar_manager.get_widget('button_find_stars')
            self.ignoreSelectedButton = self.toolbar_manager.get_widget('button_ignore_selected')
            self.editOldButton = self.toolbar_manager.get_widget('button_edit_old')
            self.darkToggle = self.toolbar_manager.get_widget('toggle_dark_mode')
            self.pdfButton = self.results_panel_manager.widgets.get('button_pdf')
            self.txtButton = self.results_panel_manager.widgets.get('button_txt')
            self.searchButton = self.results_panel_manager.widgets.get('button_refresh')
            self.exitButton = self.results_panel_manager.widgets.get('button_exit')
            self.progressBar = self.results_panel_manager.widgets.get('progress_bar')

            # Use manager's data storage
            self.supernova_data = self.results_panel_manager.supernova_data
            self.tooltip_window = self.results_panel_manager.tooltip_window
            self.tooltip_item = self.results_panel_manager.tooltip_item

            # Use manager's sort state
            self.sort_column = self.results_panel_manager.sort_column
            self.sort_reverse = self.results_panel_manager.sort_reverse

            # Configure results tree styling
            self._configure_results_tree_styling()
        except Exception:
            log_exception(logger, "Failed to build results panel")

    def refilter_from_cache(self, source="REFRESH"):
        """Re-run selection/filtering on the cached HTML rows (if available).

        If no cached rows exist, fall back to performing a normal async download.
        """
        if not hasattr(self, "last_rows") or self.last_rows is None:
            # fallback to full download
            try:
                self.refreshing = True
                self.callbackSearchSupernovasAsync(self.getDataToSearch(), source)
            except Exception:
                log_exception(logger, "Failed to fallback to async search without cached rows")
            return

        try:
            rochester = RochesterSupernova(
                visibility_factory=self.visibility_factory,
                provider_factory=self.provider_factory,
                reporter=self.reporter,
            )
            # compute with current filters
            new_results = rochester.selectAndSortSupernovas(self.getDataToSearch(), self.last_rows)
            self.supernovasFound = new_results

            # show results according to source
            if source == "PDF":
                try:
                    self.pdfButton["state"] = tk.NORMAL
                    self.pdfButton.invoke()
                except Exception:
                    log_exception(logger, "Failed to invoke PDF in refilter flow")
                try:
                    self.txtButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable TXT button in refilter PDF flow")
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable refresh button in refilter PDF flow")
            else:
                # default to text output for SEARCH/TXT/REFRESH
                try:
                    self.txtButton["state"] = tk.NORMAL
                    self.txtButton.invoke()
                except Exception:
                    log_exception(logger, "Failed to invoke TXT in refilter flow")
                try:
                    self.pdfButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable PDF button in refilter flow")
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    log_exception(logger, "Failed to re-enable refresh button in refilter flow")
        except Exception:
            # If re-filter fails, fall back to network refresh
            try:
                self.refreshing = True
                self.callbackSearchSupernovasAsync(self.getDataToSearch(), source)
            except Exception:
                log_exception(logger, "Failed to fallback to network refresh after refilter error")

    def callbackIgnoreSelectedSN(self):
        """Add the currently selected SN from the Results table to the
        user's `old_supernovae.txt`, sorting and deduplicating the file.
        """
        # get selection from tree
        try:
            selection = self.resultsTree.selection()
            if not selection:
                messagebox.showinfo(_("No selection"), _("No supernova selected in the Results table."))
                return

            item = selection[0]
            if item not in self.supernova_data:
                messagebox.showinfo(_("No selection"), _("No supernova data found for selection."))
                return

            sn = self.supernova_data[item]
            name = getattr(sn, 'name', '').strip()
        except Exception:
            messagebox.showinfo(_("No selection"), _("No supernova selected in the Results table."))
            return

        if not name:
            messagebox.showinfo(_("No selection"), _("Selected supernova has no name."))
            return

        # determine path
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except Exception:
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # read existing
        existing = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                existing = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
        except Exception:
            existing = []

        if name in existing:
            messagebox.showinfo(_("Already present"), _("'{name}' is already ignored.").format(name=name))
            return

        existing.append(name)
        unique_sorted = sorted(set(existing), key=lambda s: s.lower())

        try:
            with open(path, "w", encoding="utf-8") as fh:
                for ln in unique_sorted:
                    fh.write(ln + "\n")
            # reload global old list
            try:
                global old
                old = load_old_supernovae(path)
            except Exception:
                log_exception(logger, "Failed to reload ignored supernovae after add")
            messagebox.showinfo(_("Added"), _("Added '{name}' to ignored supernovae.").format(name=name))
            # Auto-reload results using cached rows when possible
            try:
                self.refilter_from_cache("REFRESH")
            except Exception:
                # fallback to network refresh
                try:
                    self.refreshing = True
                    self.callbackSearchSupernovasAsync(self.getDataToSearch(), "REFRESH")
                except Exception:
                    log_exception(logger, "Failed to refresh after adding ignored supernova")
        except Exception as ex:
            messagebox.showerror(_("Save error"), _("Failed to update ignore file: {ex}").format(ex=ex))

    def callbackEditOldSupernovae(self):
        """Open a simple dialog to edit the user's `old_supernovae.txt` file.

        The editor writes to the user config directory returned by
        `get_user_config_dir()` and updates the global `old` list when saved.
        """
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except Exception:
            # fallback to package-local file if user config dir can't be used
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # Load current contents (preserve comments and blank lines minimally)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                current = fh.read()
        except Exception:
            current = "" if old is None else "\n".join(old)

        # Create editor window
        editor = tk.Toplevel(self)
        editor.title(_("Edit ignored/old supernovae"))
        editor.geometry("600x400")

        txt = tk.Text(editor, wrap="none")
        txt.grid(column=0, row=0, columnspan=3, sticky="nsew")
        txt.insert("1.0", current)

        # Add simple save and close buttons
        def do_save():
            content = txt.get("1.0", "end").strip()
            try:
                # Normalize: keep only non-empty, non-comment lines
                lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
                # Deduplicate and sort (case-insensitive sort)
                unique_sorted = sorted(set(lines), key=lambda s: s.lower())
                with open(path, "w", encoding="utf-8") as fh:
                    for ln in unique_sorted:
                        fh.write(ln + "\n")
                # update global old list so the running app respects changes
                try:
                    global old
                    old = load_old_supernovae(path)
                except Exception:
                    log_exception(logger, "Failed to reload ignored supernovae after edit")
                editor.destroy()
                # Auto-reload results using cached rows when possible
                try:
                    self.refilter_from_cache("REFRESH")
                except Exception:
                    try:
                        self.refreshing = True
                        self.callbackSearchSupernovasAsync(self.getDataToSearch(), "REFRESH")
                    except Exception:
                        log_exception(logger, "Failed to refresh after editing ignored supernovae")
            except Exception as ex:
                messagebox.showerror(_("Save error"), _("Failed to save file: {ex}").format(ex=ex))

        def do_close():
            editor.destroy()

        save_btn = ttk.Button(editor, text=_("Save"), command=do_save)
        save_btn.grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        close_btn = ttk.Button(editor, text=_("Close"), command=do_close)
        close_btn.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        # allow the text widget and buttons to expand
        editor.grid_rowconfigure(0, weight=1)
        editor.grid_columnconfigure(0, weight=1)

    def callbackAddSite(self):
        """Open the Sites dialog implemented in `app.ui.sites_dialog`.

        The full dialog UI and persistence logic was extracted to a separate
        module to keep this class focused. After the dialog closes, reload the
        `sites` mapping and update the site combobox values.
        """
        try:
            from app.ui.sites_dialog import SitesDialog
        except Exception:
            # fallback: nothing to do
            return

        # obtain current mapping to show in dialog (best-effort)
        try:
            current_sites = load_sites()
        except Exception:
            current_sites = {}

        # launch dialog and wait for it to close
        dlg = SitesDialog(self, current_sites)
        self.wait_window(dlg)

        # Reload persisted sites using the canonical loader so the global
        # `sites` mapping contains `EarthLocation` objects (not plain dicts).
        try:
            try:
                new_sites = load_sites()
            except Exception:
                new_sites = None

            if new_sites is not None:
                try:
                    global sites
                    sites = new_sites
                except Exception:
                    sites = new_sites

                try:
                    vals = sorted(list(sites.keys())) if isinstance(sites, dict) or hasattr(sites, 'keys') else []
                    self.filter_panel_manager.update_site_values(vals)

                    # prefer selecting a newly added site (difference between
                    # previous and new), otherwise preserve previous selection.
                    sel_name = None
                    try:
                        old_keys = set(current_sites.keys()) if isinstance(current_sites, dict) else set()
                        new_keys = set(vals)
                        added = sorted(new_keys - old_keys)
                        if added:
                            sel_name = added[0]
                    except Exception:
                        sel_name = None

                    prev = None
                    try:
                        prev = self.site.get()
                    except Exception:
                        prev = None

                    if not sel_name:
                        if prev in vals:
                            sel_name = prev
                        elif vals:
                            sel_name = vals[0]

                    if sel_name:
                        try:
                            self.site.set(sel_name)
                            if self.cbSite:
                                self.cbSite.update_idletasks()
                        except Exception:
                            log_exception(logger, "Failed to apply selected site after site dialog")
                except Exception:
                    log_exception(logger, "Failed to refresh site values after site dialog")
        except Exception:
            log_exception(logger, "Failed to process site dialog result")

    def callbackAddVisibilityWindow(self):
        try:
            from app.ui.visibility_dialog import VisibilityDialog
        except Exception:
            return

        try:
            current = load_visibility_windows()
        except Exception:
            current = {}

        dlg = VisibilityDialog(self, current)
        self.wait_window(dlg)

        try:
            new_vis = getattr(dlg, "result", None)
            if new_vis is None:
                try:
                    new_vis = load_visibility_windows()
                except Exception:
                    new_vis = None

            if new_vis is not None:
                try:
                    global visibility_windows
                    visibility_windows = new_vis
                except Exception:
                    visibility_windows = new_vis

                try:
                    vals = [""] + sorted(list(visibility_windows.keys()))
                    self.filter_panel_manager.update_visibility_window_values(vals)

                    # Prefer newly added selection when possible
                    sel_name = None
                    try:
                        old_keys = set(current.keys()) if isinstance(current, dict) else set()
                        new_keys = set(visibility_windows.keys())
                        added = sorted(new_keys - old_keys)
                        if added:
                            sel_name = added[0]
                    except Exception:
                        sel_name = None

                    prev = None
                    try:
                        prev = self.visibilityWindow.get()
                    except Exception:
                        prev = None

                    if not sel_name:
                        if prev in vals:
                            sel_name = prev
                        elif vals:
                            sel_name = vals[0]

                    if sel_name:
                        try:
                            self.visibilityWindow.set(sel_name)
                            if self.cbVisibility:
                                self.cbVisibility.update_idletasks()
                        except Exception:
                            log_exception(logger, "Failed to apply selected visibility window after dialog")
                except Exception:
                    log_exception(logger, "Failed to refresh visibility window values after dialog")
        except Exception:
            log_exception(logger, "Failed to process visibility window dialog result")

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

        # Force default UI language to English on startup
        try:
            set_language("en")
        except Exception:
            log_exception(logger, "Failed to set default startup language")

        # Apply theme early so initial widgets pick up dark mode colors
        try:
            self.apply_theme()
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
            self._configure_results_tree_styling()
        except Exception:
            log_exception(logger, "Failed to reconfigure results tree after language change")
        try:
            # re-apply theme in case translations affected widget styles
            self.apply_theme()
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
