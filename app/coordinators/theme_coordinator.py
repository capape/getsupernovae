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

from app.config.ui_constants import (
    DEFAULT_VALUES,
    THEME_COLORS,
    UI_CONSTANTS,
    UI_STRINGS,
)
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
            style.configure(UI_STRINGS.RESULTS_TREE_STYLE, rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT)

            # Configure alternating row colors based on current theme
            dark = self.get_dark_mode()
            if dark:
                tree.tag_configure(
                    UI_STRINGS.TAG_EVEN_ROW,
                    background=THEME_COLORS.DARK_EVEN_ROW,
                    foreground=THEME_COLORS.DARK_FG,
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW,
                    background=THEME_COLORS.DARK_ODD_ROW,
                    foreground=THEME_COLORS.DARK_FG,
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
                    UI_STRINGS.TAG_EVEN_ROW,
                    background=THEME_COLORS.LIGHT_EVEN_ROW,
                    foreground=THEME_COLORS.LIGHT_FG,
                )
                tree.tag_configure(
                    UI_STRINGS.TAG_ODD_ROW,
                    background=THEME_COLORS.LIGHT_ODD_ROW,
                    foreground=THEME_COLORS.LIGHT_FG,
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
                            is_bright = (
                                mag is not None
                                and float(mag) < DEFAULT_VALUES.BRIGHT_MAGNITUDE_THRESHOLD
                            )
                        except (ValueError, TypeError):
                            is_bright = False

                        if is_bright:
                            tag = (
                                UI_STRINGS.TAG_EVEN_ROW_BRIGHT
                                if index % 2 == 0
                                else UI_STRINGS.TAG_ODD_ROW_BRIGHT
                            )
                        else:
                            tag = (
                                UI_STRINGS.TAG_EVEN_ROW
                                if index % 2 == 0
                                else UI_STRINGS.TAG_ODD_ROW
                            )

                        tree.item(item, tags=(tag,))
                except (AttributeError, tk.TclError, TypeError, KeyError):
                    log_exception(logger, "Failed to reapply tree tag for item")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to reapply tree tags")

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors based on current dark mode setting.

        Returns:
            Dictionary with color keys: bg, fg, entry_bg, btn_bg, tree_bg
        """
        dark = self.get_dark_mode()
        if dark:
            return {
                "bg": THEME_COLORS.DARK_BG,
                "fg": THEME_COLORS.DARK_FG,
                "entry_bg": THEME_COLORS.DARK_ENTRY_BG,
                "btn_bg": THEME_COLORS.DARK_BUTTON_BG,
                "tree_bg": THEME_COLORS.DARK_TREE_BG,
                "sel_color": THEME_COLORS.DARK_SELECTION,
            }
        return {
            "bg": THEME_COLORS.LIGHT_BG,
            "fg": THEME_COLORS.LIGHT_FG,
            "entry_bg": THEME_COLORS.LIGHT_ENTRY_BG,
            "btn_bg": THEME_COLORS.LIGHT_BUTTON_BG,
            "tree_bg": THEME_COLORS.LIGHT_TREE_BG,
            "sel_color": THEME_COLORS.LIGHT_SELECTION,
        }

    def _configure_ttk_styles(self, style: ttk.Style, colors: Dict[str, str]) -> None:
        """Configure all ttk widget styles.

        Args:
            style: The ttk.Style instance to configure
            colors: Dictionary of theme colors
        """
        style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        style.configure("TButton", background=colors["btn_bg"], foreground=colors["fg"])
        style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["fg"])
        style.configure("TCombobox", fieldbackground=colors["entry_bg"], foreground=colors["fg"])
        # Explicitly clear foreground in Treeview style to allow tag foreground colors
        style.configure(
            "Treeview",
            background=colors["tree_bg"],
            fieldbackground=colors["tree_bg"],
            foreground="",
            rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT,
        )
        style.configure(
            UI_STRINGS.RESULTS_TREE_STYLE,
            background=colors["tree_bg"],
            fieldbackground=colors["tree_bg"],
            foreground="",
            rowheight=UI_CONSTANTS.TREE_ROW_HEIGHT,
        )
        style.configure("TFrame", background=colors["bg"])
        style.configure("TCheckbutton", background=colors["bg"], foreground=colors["fg"])

    def _apply_treeview_selection_color(self, style: ttk.Style, colors: Dict[str, str]) -> None:
        """Apply treeview selection highlight color.

        Args:
            style: The ttk.Style instance to configure
            colors: Dictionary of theme colors
        """
        try:
            style.map("Treeview", background=[("selected", colors["sel_color"])])
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to map Treeview selection color")

    def _configure_widget_backgrounds(self, bg_color: str) -> None:
        """Configure root and child widget backgrounds.

        Args:
            bg_color: Background color to apply
        """
        try:
            self.root.configure(bg=bg_color)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to set root background color")

        try:
            for child in self.root.winfo_children():
                try:
                    child.configure(background=bg_color)
                except tk.TclError:
                    # Many ttk/native widgets do not expose a `background` option.
                    continue
                except (AttributeError, TypeError):
                    log_exception(logger, "Failed to configure child widget background")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to apply theme to child widgets")

    def apply_theme(self):
        """Apply light/dark theme to ttk widgets and some native widgets."""
        # Persist dark mode preference
        try:
            self.on_persist_prefs()
        except (AttributeError, TypeError, RuntimeError):
            log_exception(logger, "Failed to persist preferences during theme apply")

        # Initialize ttk style
        style = None
        try:
            style = ttk.Style()
            style.theme_use("clam")
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to initialize ttk style")

        # Get theme colors
        colors = self._get_theme_colors()

        # Configure ttk widget styles
        if style is not None:
            try:
                self._configure_ttk_styles(style, colors)
                self._apply_treeview_selection_color(style, colors)
            except (AttributeError, tk.TclError, TypeError):
                log_exception(logger, "Failed to apply ttk theme configuration")

        # Configure results tree styling
        try:
            tree = self.get_results_tree()
            if tree is not None:
                tree.configure(style="Treeview")
            self.configure_results_tree_styling()
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to configure results tree")

        # Apply background colors to root and child widgets
        self._configure_widget_backgrounds(colors["bg"])
