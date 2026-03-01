"""Theme Coordinator - Manages application theme and styling.

This coordinator handles:
- Light/dark theme switching
- Ttk widget styling
- Results tree row coloring and tagging
- Theme persistence
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from app.config.ui_constants import THEME_COLORS, UI_CONSTANTS, UI_STRINGS
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class ThemeCoordinator:
    """Coordinates all theme-related operations."""

    def __init__(
        self,
        root_window: tk.Tk,
        get_results_tree: Callable[[], Optional[tk.Widget]],
        get_supernova_data: Callable[[], Dict[str, Any]],
        get_dark_mode: Callable[[], bool],
        on_persist_prefs: Callable[[], None],
    ):
        """Initialize the theme coordinator.

        Args:
            root_window: The main Tk window
            get_results_tree: Callback that returns the results treeview widget
            get_supernova_data: Callback that returns the supernova data dictionary
            get_dark_mode: Callback that returns current dark mode state
            on_persist_prefs: Callback to persist preferences when theme changes
        """
        self.root = root_window
        self.get_results_tree = get_results_tree
        self.get_supernova_data = get_supernova_data
        self.get_dark_mode = get_dark_mode
        self.on_persist_prefs = on_persist_prefs

    def configure_results_tree_styling(self):
        """Configure results tree row height and alternating row colors."""
        try:
            tree = self.get_results_tree()
            if tree is None:
                return

            # Configure row height - must use root as the first argument
            style = ttk.Style(self.root)
            style.configure(
                UI_STRINGS.RESULTS_TREE_STYLE, rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT
            )

            # Configure alternating row colors based on current theme
            dark = self.get_dark_mode()
            if dark:
                tree.tag_configure(
                    UI_STRINGS.TAG_EVEN_ROW, background=THEME_COLORS.DARK_EVEN_ROW
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW, background=THEME_COLORS.DARK_ODD_ROW
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_EVEN_ROW_BRIGHT,
                    background=THEME_COLORS.DARK_EVEN_ROW,
                    foreground=THEME_COLORS.BRIGHT_FG_DARK,
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW_BRIGHT,
                    background=THEME_COLORS.DARK_ODD_ROW,
                    foreground=THEME_COLORS.BRIGHT_FG_DARK,
                )
            else:
                tree.tag_configure(
                    UI_STRINGS.TAG_EVEN_ROW, background=THEME_COLORS.LIGHT_EVEN_ROW
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW, background=THEME_COLORS.LIGHT_ODD_ROW
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_EVEN_ROW_BRIGHT,
                    background=THEME_COLORS.LIGHT_EVEN_ROW,
                    foreground=THEME_COLORS.BRIGHT_FG_LIGHT,
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW_BRIGHT,
                    background=THEME_COLORS.LIGHT_ODD_ROW,
                    foreground=THEME_COLORS.BRIGHT_FG_LIGHT,
                )

            # Reapply tags to all existing items to preserve bright highlighting
            self.reapply_tree_tags()
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to configure results tree styling")

    def reapply_tree_tags(self):
        """Reapply tags to all tree items based on magnitude and position."""
        try:
            tree = self.get_results_tree()
            if tree is None:
                return

            supernova_data = self.get_supernova_data()
            items = tree.get_children("")
            for index, item in enumerate(items):
                try:
                    if item in supernova_data:
                        sn = supernova_data[item]
                        mag = getattr(sn, "mag", None)
                        try:
                            is_bright = mag is not None and float(mag) < 15
                        except (ValueError, TypeError):
                            is_bright = False

                        if is_bright:
                            tag = (
                                "evenrow_bright" if index % 2 == 0 else "oddrow_bright"
                            )
                        else:
                            tag = "evenrow" if index % 2 == 0 else "oddrow"

                        tree.item(item, tags=(tag,))
                except (AttributeError, tk.TclError, TypeError, KeyError):
                    log_exception(logger, "Failed to reapply tree tag for item")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to reapply tree tags")

    def apply_theme(self):
        """Apply light/dark theme to ttk widgets and some native widgets."""
        try:
            # Persist dark mode preference when changed
            try:
                self.on_persist_prefs()
            except (AttributeError, TypeError, RuntimeError):
                log_exception(
                    logger, "Failed to persist preferences during theme apply"
                )

            style = ttk.Style()
            try:
                style.theme_use("clam")
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to apply ttk theme 'clam'")
        except (AttributeError, tk.TclError, TypeError):
            style = None

        dark = self.get_dark_mode()
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
                style.configure(
                    "Treeview",
                    background=tree_bg,
                    fieldbackground=tree_bg,
                    foreground=fg,
                    rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT,
                )
                style.configure(
                    UI_STRINGS.RESULTS_TREE_STYLE,
                    background=tree_bg,
                    fieldbackground=tree_bg,
                    foreground=fg,
                    rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT,
                )
                style.configure("TFrame", background=bg)
                style.configure("TCheckbutton", background=bg, foreground=fg)
                # selection highlight for treeview — choose a subtle color per theme
                try:
                    sel_color = (
                        THEME_COLORS.DARK_SELECTION
                        if dark
                        else THEME_COLORS.LIGHT_SELECTION
                    )
                    style.map("Treeview", background=[("selected", sel_color)])
                except (AttributeError, tk.TclError):
                    log_exception(logger, "Failed to map Treeview selection color")
                try:
                    # also set the main window background for non-ttk widgets
                    try:
                        self.root.configure(background=bg)
                    except (AttributeError, tk.TclError):
                        log_exception(
                            logger, "Failed to configure root window background"
                        )
                    # Treeview styling
                    try:
                        tree = self.get_results_tree()
                        if tree is not None:
                            tree.configure(style="Treeview")
                    except (AttributeError, tk.TclError):
                        log_exception(logger, "Failed to configure results tree style")
                except (AttributeError, tk.TclError, TypeError):
                    log_exception(logger, "Failed while applying non-ttk theme updates")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to apply ttk theme configuration")

        # Reapply results tree styling after theme change
        try:
            self.configure_results_tree_styling()
        except (AttributeError, tk.TclError, TypeError):
            log_exception(
                logger, "Failed to reconfigure results tree after theme change"
            )

        try:
            if bg:
                self.root.configure(bg=bg)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to set root background color")

        # Update some known frames/widgets that are not styled by ttk
        try:
            for child in self.root.winfo_children():
                try:
                    child.configure(background=bg)
                except tk.TclError:
                    # Many ttk/native widgets do not expose a `background` option.
                    # This is expected and should not be logged as an error.
                    continue
                except (AttributeError, TypeError):
                    log_exception(logger, "Failed to configure child widget background")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to apply theme to child widgets")
