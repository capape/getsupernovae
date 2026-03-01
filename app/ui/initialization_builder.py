"""Initialization Builder - Handles complex app initialization logic.

This builder encapsulates the multi-step initialization process for the
SupernovasApp, separating setup concerns from the application class itself.
"""

import os
import tkinter as tk
from typing import Any

from app import __version__
from app.config.ui_constants import FILE_CONSTANTS, UI_CONSTANTS
from app.i18n import _, set_language
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class InitializationBuilder:
    """Builds and initializes a SupernovasApp instance."""

    def __init__(self, app: tk.Tk, filters: Any):
        """Initialize the builder.

        Args:
            app: The Tk application window being initialized
            filters: Filter configuration object
        """
        self.app = app
        self.filters = filters

    def setup_state_management(self):
        """Initialize state managers and coordinator infrastructure."""
        from app.state import AppStateManager, PreferencesManager

        self.app.state_manager = AppStateManager()
        self.app.preferences_manager = PreferencesManager()
        self.app._initializing = True
        self.app.supernovas_found = None
        self.app.refreshing = False

    def setup_theme_and_language(self):
        """Initialize theme coordinator and set default language."""
        from app.coordinators.theme_coordinator import ThemeCoordinator

        # Create dark_mode variable first (required by theme coordinator)
        self.app.dark_mode = tk.BooleanVar(value=True)

        # Initialize ThemeCoordinator (will get persist callback later from preferences coordinator)
        self.app.theme_coordinator = ThemeCoordinator(
            root_window=self.app,
            get_results_tree=lambda: getattr(self.app, "results_tree", None),
            get_supernova_data=lambda: getattr(self.app, "supernova_data", {}),
            get_dark_mode=lambda: (
                self.app.dark_mode.get() if hasattr(self.app, "dark_mode") else False
            ),
            on_persist_prefs=lambda: (
                self.app.preferences_coordinator.persist_prefs()
                if hasattr(self.app, "preferences_coordinator")
                else None
            ),
        )

        # Set default language
        try:
            set_language("en")
        except (OSError, IOError, ValueError):
            log_exception(logger, "Failed to set default startup language")

        # Apply initial theme
        try:
            self.app.theme_coordinator.apply_theme()
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to apply initial theme during startup")

    def create_tk_variables(self):
        """Create all Tkinter variables with trace callbacks."""
        # Create variables with clear results callback
        self.app.magnitude = tk.StringVar()
        self.app.magnitude.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.days_to_search = tk.StringVar()
        self.app.days_to_search.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.observation_date = tk.StringVar()
        self.app.observation_date.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.observation_duration = tk.StringVar()
        self.app.observation_duration.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.min_latitud = tk.StringVar()
        self.app.min_latitud.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.observation_time = tk.StringVar()
        self.app.observation_time.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.site = tk.StringVar()
        self.app.site.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.visibility_window = tk.StringVar()
        self.app.visibility_window.trace_add(["write", "unset"], self.app.on_clear_results)

        self.app.results = tk.StringVar()
        self.app.results.trace_add(["write", "unset"], self.app.on_clear_results)

        # Dark mode variable already created in setup_theme_and_language
        self.app.dark_mode.trace_add(["write", "unset"], lambda *a: None)

    def initialize_services(self, presenter, visibility_factory, provider_factory, reporter):
        """Initialize service layer components."""
        from app.services.provider import NetworkRochesterProvider
        from app.ui.results_presenter import ResultsPresenter
        from app.ui.snvisibility import VisibilityWindow

        # Set up dependency injection
        self.app.presenter = presenter if presenter is not None else ResultsPresenter()
        self.app.visibility_factory = (
            visibility_factory if visibility_factory is not None else VisibilityWindow
        )
        self.app.provider_factory = (
            provider_factory if provider_factory is not None else NetworkRochesterProvider
        )
        self.app.reporter = reporter

        # Initialize RochesterSupernova
        from getsupernovae import RochesterSupernova

        self.app.rochester_supernova = RochesterSupernova(
            visibility_factory=self.app.visibility_factory,
            provider_factory=self.app.provider_factory,
            reporter=self.app.reporter,
        )

    def initialize_coordinators(self):
        """Initialize all coordinator objects."""
        from app.coordinators.dialog_coordinator import DialogCoordinator
        from app.coordinators.report_coordinator import ReportCoordinator
        from app.coordinators.search_coordinator import SearchCoordinator

        # SearchCoordinator
        self.app.search_coordinator = SearchCoordinator(
            rochester_supernova=self.app.rochester_supernova,
            visibility_factory=self.app.visibility_factory,
            provider_factory=self.app.provider_factory,
            reporter=self.app.reporter,
            on_results_updated=self.app._handle_search_results,
            on_button_state_change=self.app._set_button_state,
            on_progress_start=self.app.start_progress_bar,
            on_progress_end=self.app.end_progress_bar,
            on_pdf_invoke=lambda: (
                self.app.pdfButton.invoke() if hasattr(self.app, "pdfButton") else None
            ),
            on_txt_invoke=lambda: (
                self.app.txtButton.invoke() if hasattr(self.app, "txtButton") else None
            ),
            after_callback=self.app.after,
        )

        # ReportCoordinator
        self.app.report_coordinator = ReportCoordinator(
            has_results=self.app.has_results,
            get_results=lambda: self.app.supernovas_found,
            on_search_async=self.app.on_search_async,
            on_results_text_update=self.app.set_results_text,
            on_show_message=self.app._show_yes_no_dialog,
            on_show_warning=self.app._show_warning_dialog,
        )

        # DialogCoordinator
        self.app.dialog_coordinator = DialogCoordinator(
            parent_window=self.app,
            get_selected_supernova=self.app._get_selected_supernova,
            on_update_sites=self.app._update_sites_combobox,
            on_update_visibility_windows=self.app._update_visibility_windows_combobox,
            on_refilter=lambda: self.app.refilter_from_cache("REFRESH"),
            on_search_async=self.app.on_search_async,
            on_show_info=self.app._show_info_dialog,
            on_show_error=self.app._show_error_dialog,
            on_get_current_site=lambda: (self.app.site.get() if hasattr(self.app, "site") else ""),
            on_get_current_visibility_window=lambda: (
                self.app.visibility_window.get() if hasattr(self.app, "visibility_window") else ""
            ),
            get_combobox_site=lambda: (self.app.cb_site if hasattr(self.app, "cb_site") else None),
            get_combobox_visibility=lambda: (
                self.app.cb_visibility if hasattr(self.app, "cb_visibility") else None
            ),
        )

    def configure_window_properties(self):
        """Set up window title, icon, size, and position."""
        # Set window title
        self.app.title(_("Find latest supernovae - {}").format(__version__))

        # Set application icon
        self._setup_application_icon()

        # Configure window geometry
        window_width = UI_CONSTANTS.WINDOW_WIDTH
        window_height = UI_CONSTANTS.WINDOW_HEIGHT

        # Center window on screen
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        self.app.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        # Set minimum window size
        try:
            self.app.minsize(window_width, window_height)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to enforce minimum window size")

    def _setup_application_icon(self):
        """Load and set application icon (ICO, PNG, or SVG)."""
        try:
            icon_dir = os.path.join(os.path.dirname(__file__), "..", "..", FILE_CONSTANTS.ICONS_DIR)
            ico = os.path.join(icon_dir, FILE_CONSTANTS.ICON_ICO)
            png = os.path.join(icon_dir, FILE_CONSTANTS.ICON_PNG)
            svg = os.path.join(icon_dir, FILE_CONSTANTS.ICON_SVG)

            if os.path.exists(ico) and os.name == "nt":
                try:
                    self.app.iconbitmap(ico)
                except (OSError, tk.TclError):
                    log_exception(logger, "Failed to set ICO application icon")
            elif os.path.exists(png):
                try:
                    img = tk.PhotoImage(file=png)
                    self.app.iconphoto(False, img)
                    # Keep reference to avoid GC
                    self.app._icon_image = img
                except (OSError, tk.TclError):
                    log_exception(logger, "Failed to set PNG application icon")
            else:
                # SVG present but not supported directly
                if os.path.exists(svg):
                    pass
        except (OSError, AttributeError, TypeError):
            log_exception(logger, "Failed during application icon setup")

    def set_initial_filter_values(self):
        """Set initial values for filter variables from configuration."""
        from app.config.snconfig import load_visibility_windows

        visibility_windows = load_visibility_windows()

        self.app.magnitude.set(self.filters.magnitude)
        self.app.days_to_search.set(self.filters.days_to_search)
        self.app.observation_date.set(self.filters.observation_date.strftime("%Y-%m-%d"))
        self.app.observation_time.set(self.filters.observation_time)
        self.app.observation_duration.set(self.filters.observation_hours)
        self.app.min_latitud.set(self.filters.min_latitude)
        self.app.site.set(self.filters.site)

        # Set visibility window
        try:
            if getattr(self.filters, "visibility_window_name", None):
                self.app.visibility_window.set(self.filters.visibility_window_name)
            else:
                # Choose first available key or Default
                keys = list(visibility_windows.keys())
                if "Default" in visibility_windows:
                    self.app.visibility_window.set("Default")
                elif keys:
                    self.app.visibility_window.set(keys[0])
        except (AttributeError, KeyError, IndexError, tk.TclError):
            try:
                self.app.visibility_window.set("Default")
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to set default visibility window")

        self.app.results.set("")

    def build_ui_panels(self):
        """Build left and results panels."""
        # Build left panel
        try:
            self.app.build_left_panel()
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to build left panel during startup")

        # Build results panel
        try:
            self.app.build_results_panel()
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to build results panel during startup")

    def initialize_language_coordinator(self):
        """Initialize the language coordinator after UI panels are built."""
        from app.coordinators.language_coordinator import LanguageCoordinator

        try:
            self.app.language_coordinator = LanguageCoordinator(
                root_window=self.app,
                get_langvar=lambda: getattr(self.app, "lang_var", None),
                get_filter_panel_manager=lambda: getattr(self.app, "filter_panel_manager", None),
                get_results_panel_manager=lambda: getattr(self.app, "results_panel_manager", None),
                get_toolbar_manager=lambda: getattr(self.app, "toolbar_manager", None),
                get_widgets=lambda: {
                    "labelLatitud": getattr(self.app, "labelLatitud", None),
                    "ignore_selected_button": getattr(self.app, "ignore_selected_button", None),
                    "edit_old_button": getattr(self.app, "edit_old_button", None),
                    "pdfButton": getattr(self.app, "pdfButton", None),
                    "txtButton": getattr(self.app, "txtButton", None),
                    "searchButton": getattr(self.app, "searchButton", None),
                    "exit_button": getattr(self.app, "exit_button", None),
                },
                on_configure_tree_styling=self.app.theme_coordinator.configure_results_tree_styling,
                on_apply_theme=self.app.theme_coordinator.apply_theme,
                on_update_visibility_ui=lambda: (
                    self.app.preferences_coordinator.update_visibility_ui()
                    if hasattr(self.app, "preferences_coordinator")
                    else None
                ),
            )
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to initialize language coordinator")

    def initialize_preferences_coordinator(self):
        """Initialize the preferences coordinator before loading preferences."""
        import getsupernovae as gs
        from app.coordinators.preferences_coordinator import PreferencesCoordinator

        try:
            self.app.preferences_coordinator = PreferencesCoordinator(
                state_manager=self.app.state_manager,
                preferences_manager=self.app.preferences_manager,
                get_initializing_flag=lambda: getattr(self.app, "_initializing", False),
                get_tk_variables=lambda: {
                    "magnitude": getattr(self.app, "magnitude", None),
                    "days_to_search": getattr(self.app, "days_to_search", None),
                    "observation_date": getattr(self.app, "observation_date", None),
                    "observation_time": getattr(self.app, "observation_time", None),
                    "observation_duration": getattr(self.app, "observation_duration", None),
                    "site": getattr(self.app, "site", None),
                    "visibility_window": getattr(self.app, "visibility_window", None),
                    "min_latitud": getattr(self.app, "min_latitud", None),
                    "lang_var": getattr(self.app, "lang_var", None),
                    "dark_mode": getattr(self.app, "dark_mode", None),
                },
                get_sites=lambda: gs.sites,
                get_visibility_windows=lambda: gs.visibility_windows,
                get_filter_panel_manager=lambda: getattr(self.app, "filter_panel_manager", None),
                get_language_coordinator=lambda: getattr(self.app, "language_coordinator", None),
                get_theme_coordinator=lambda: getattr(self.app, "theme_coordinator", None),
            )
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to initialize preferences coordinator")

    def build(
        self,
        presenter=None,
        visibility_factory=None,
        provider_factory=None,
        reporter=None,
    ):
        """Execute the full initialization sequence.

        Args:
            presenter: Optional custom results presenter
            visibility_factory: Optional custom visibility calculator factory
            provider_factory: Optional custom data provider factory
            reporter: Optional custom reporter

        Returns:
            The initialized app instance
        """
        self.setup_state_management()
        self.setup_theme_and_language()
        self.create_tk_variables()
        self.initialize_services(presenter, visibility_factory, provider_factory, reporter)
        self.initialize_coordinators()
        self.configure_window_properties()
        self.set_initial_filter_values()
        self.initialize_language_coordinator()
        self.initialize_preferences_coordinator()
        self.build_ui_panels()

        return self.app
