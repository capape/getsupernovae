"""Language Coordinator

This module coordinates language-related operations for the supernova application.
Handles language switching and refreshing UI labels across all managers and widgets.
"""

import tkinter as tk
from typing import Any, Callable, Dict, Optional

from app.i18n import _, set_language
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class LanguageCoordinator:
    """Coordinates language switching and UI label refreshing.

    This coordinator handles:
    - Language selection changes
    - Refreshing labels in all UI managers
    - Updating individual widget texts
    - Reapplying theme after language change
    - Updating visibility UI

    Follows Single Responsibility Principle by focusing on language orchestration.
    Uses callbacks to avoid tight coupling with the main application.
    """

    def __init__(
        self,
        root_window: tk.Tk,
        get_langvar: Callable[[], Optional[tk.StringVar]],
        get_filter_panel_manager: Callable[[], Optional[Any]],
        get_results_panel_manager: Callable[[], Optional[Any]],
        get_toolbar_manager: Callable[[], Optional[Any]],
        get_widgets: Callable[[], Dict[str, Optional[tk.Widget]]],
        on_configure_tree_styling: Callable[[], None],
        on_apply_theme: Callable[[], None],
        on_update_visibility_ui: Callable[[], None],
    ):
        """Initialize the language coordinator.

        Args:
            root_window: Main application window
            get_langvar: Callback to get language StringVar
            get_filter_panel_manager: Callback to get filter panel manager
            get_results_panel_manager: Callback to get results panel manager
            get_toolbar_manager: Callback to get toolbar manager
            get_widgets: Callback to get dict of widget references
            on_configure_tree_styling: Callback to reconfigure results tree styling
            on_apply_theme: Callback to reapply theme
            on_update_visibility_ui: Callback to update visibility UI
        """
        self.root_window = root_window
        self.get_langvar = get_langvar
        self.get_filter_panel_manager = get_filter_panel_manager
        self.get_results_panel_manager = get_results_panel_manager
        self.get_toolbar_manager = get_toolbar_manager
        self.get_widgets = get_widgets
        self.on_configure_tree_styling = on_configure_tree_styling
        self.on_apply_theme = on_apply_theme
        self.on_update_visibility_ui = on_update_visibility_ui

    def on_language_change(self):
        """Handler when UI language selection changes: apply and refresh labels."""
        # Apply selected language
        self._apply_selected_language()

        # Update all UI labels
        self._refresh_ui_labels()

        # Reapply theme and styling
        self._reapply_theme_and_styling()

        # Update visibility UI
        self._update_visibility_ui()

    def _apply_selected_language(self):
        """Apply the selected language from langVar."""
        try:
            langvar = self.get_langvar()
            if langvar is None:
                return

            lang = langvar.get().strip()
            if not lang:
                set_language(None)
            else:
                set_language(lang)
        except Exception:
            log_exception(logger, "Failed to apply selected language")

    def _refresh_ui_labels(self):
        """Refresh all UI labels to the new language."""
        try:
            # Get all widgets
            widgets = self.get_widgets()

            # Refresh filter panel manager labels
            self._refresh_filter_panel_labels()

            # Refresh labelLatitud (special case)
            if widgets.get("labelLatitud") is not None:
                widgets["labelLatitud"].config(text=_("Min latitude: "))

            # Refresh results panel manager labels
            self._refresh_results_panel_labels()

            # Refresh toolbar manager labels
            self._refresh_toolbar_labels()

            # Refresh toolbar button labels (ignore/edit)
            self._refresh_toolbar_button_labels(widgets)

            # Refresh action button labels (PDF/TXT/Refresh/Exit)
            self._refresh_action_button_labels(widgets)

            # Update window title
            self._update_window_title()

        except Exception:
            log_exception(logger, "Failed to refresh UI labels after language change")

    def _refresh_filter_panel_labels(self):
        """Refresh filter panel manager labels."""
        try:
            filter_panel = self.get_filter_panel_manager()
            if filter_panel is not None:
                filter_panel.refresh_labels()
        except Exception:
            log_exception(logger, "Failed to refresh filter panel labels")

    def _refresh_results_panel_labels(self):
        """Refresh results panel manager labels."""
        try:
            results_panel = self.get_results_panel_manager()
            if results_panel is not None:
                results_panel.refresh_labels()
        except Exception:
            log_exception(logger, "Failed to refresh results panel labels")

    def _refresh_toolbar_labels(self):
        """Refresh toolbar manager labels."""
        try:
            toolbar = self.get_toolbar_manager()
            if toolbar is not None:
                toolbar.refresh_labels()
        except Exception:
            log_exception(logger, "Failed to refresh toolbar labels")

    def _refresh_toolbar_button_labels(self, widgets: Dict[str, Optional[tk.Widget]]):
        """Refresh ignore and edit toolbar button labels."""
        try:
            ignore_button = widgets.get("ignoreSelectedButton")
            if ignore_button is not None:
                ignore_button.config(text=_("Ignore selected SN"))

            edit_button = widgets.get("editOldButton")
            if edit_button is not None:
                edit_button.config(text=_("Edit Ignored SN"))
        except Exception:
            log_exception(logger, "Failed to refresh ignore/edit toolbar labels")

    def _refresh_action_button_labels(self, widgets: Dict[str, Optional[tk.Widget]]):
        """Refresh PDF, TXT, Refresh Search, and Exit button labels."""
        try:
            pdf_button = widgets.get("pdfButton")
            if pdf_button is not None:
                pdf_button.config(text=_("PDF"))

            txt_button = widgets.get("txtButton")
            if txt_button is not None:
                txt_button.config(text=_("TXT"))

            search_button = widgets.get("searchButton")
            if search_button is not None:
                search_button.config(text=_("Refresh Search"))

            exit_button = widgets.get("exitButton")
            if exit_button is not None:
                exit_button.config(text=_("Exit"))
        except Exception:
            log_exception(logger, "Failed to refresh action button labels")

    def _update_window_title(self):
        """Update main window title."""
        try:
            self.root_window.title(_("Find latest supernovae"))
        except Exception:
            log_exception(
                logger, "Failed to refresh window title after language change"
            )

    def _reapply_theme_and_styling(self):
        """Reapply results tree styling and theme after language change."""
        try:
            self.on_configure_tree_styling()
        except Exception:
            log_exception(
                logger, "Failed to reconfigure results tree after language change"
            )

        try:
            # Re-apply theme in case translations affected widget styles
            self.on_apply_theme()
        except Exception:
            log_exception(logger, "Failed to reapply theme after language change")

    def _update_visibility_ui(self):
        """Update visibility UI after language change."""
        try:
            self.on_update_visibility_ui()
        except Exception:
            log_exception(
                logger, "Failed to refresh visibility UI after language change"
            )
