"""Results Panel Manager

This module manages the results panel UI components for the supernova application.
Follows SOLID principles by isolating UI creation, event handling, and state management
for the results display and associated controls.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass

from app.i18n import _
from app.config.ui_constants import (
    UI_CONSTANTS,
    UI_STRINGS,
)
from app.utils.logger import get_logger, log_exception


logger = get_logger(__name__)


@dataclass
class ResultsPanelCallbacks:
    """Callbacks for results panel interactions."""
    on_sort_column: Callable[[str, bool], None]
    on_double_click: Callable[[Any], None]
    on_motion: Callable[[Any], None]
    on_leave: Callable[[Any], None]
    on_selection_change: Callable[[Any], None]
    on_pdf: Callable[[], None]
    on_txt: Callable[[], None]
    on_refresh: Callable[[], None]
    on_exit: Callable[[], None]


class ResultsPanelManager:
    """Manages the results panel UI components and their interactions.

    This class is responsible for:
    - Creating the results label and treeview
    - Creating bottom action buttons (PDF, TXT, Refresh, Exit)
    - Setting up event bindings for tree interactions
    - Managing widget state (enable/disable)
    - Coordinating with callbacks for business logic

    Note: Toolbar (Find Stars, Ignore SN, Edit Old, Dark Mode) is managed by ToolbarManager.

    Follows Single Responsibility Principle by focusing only on UI management.
    """

    def __init__(
        self,
        parent: tk.Widget,
        callbacks: ResultsPanelCallbacks,
        dark_mode: Optional[tk.BooleanVar] = None
    ):
        """Initialize the results panel manager.

        Args:
            parent: Parent widget to contain the results panel
            callbacks: ResultsPanelCallbacks object with event handlers
            dark_mode: Optional BooleanVar for dark mode state
        """
        self.parent = parent
        self.callbacks = callbacks
        self.dark_mode = dark_mode

        # Widget references
        self.widgets: Dict[str, tk.Widget] = {}

        # Data storage
        self.supernova_data: Dict[str, Any] = {}
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.tooltip_item: Optional[str] = None

        # Sort state
        self.sort_column: Optional[str] = None
        self.sort_reverse: bool = False

    def build(self) -> None:
        """Build all results panel components."""
        self._build_results_label()
        self._build_results_tree()
        self._build_action_buttons()
        self._build_progress_bar()

        # Configure grid weights for resizing
        try:
            self.parent.grid_columnconfigure(3, weight=1)
            self.parent.grid_rowconfigure(1, weight=1)
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to configure results panel grid weights")

    def _build_results_label(self) -> None:
        """Build the results label."""
        try:
            label = ttk.Label(self.parent, text=_("Results: "))
            label.grid(column=3, row=0, padx=5, pady=5, sticky=tk.W)
            self.widgets['label_results'] = label
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to build results label")

    def _build_results_tree(self) -> None:
        """Build the results treeview with scrollbars."""
        try:
            # Create frame to hold treeview and scrollbars
            results_frame = ttk.Frame(self.parent)
            results_frame.grid(column=3, row=1, rowspan=9, sticky="nsew", padx=5, pady=5)
            results_frame.grid_rowconfigure(0, weight=1)
            results_frame.grid_columnconfigure(0, weight=1)
            self.widgets['results_frame'] = results_frame

            # Define columns
            columns = (
                "name", "type", "magnitude", "date", "observation_time",
                "host", "constellation", "ra", "dec", "rochester", "tns"
            )

            # Create treeview
            tree = ttk.Treeview(
                results_frame,
                columns=columns,
                show="headings",
                selectmode="browse",
                style=UI_STRINGS.RESULTS_TREE_STYLE
            )
            self.widgets['results_tree'] = tree

            # Configure column headings with sort commands
            tree.heading("name", text=_("Name"),
                        command=lambda: self.callbacks.on_sort_column("name", False))
            tree.heading("type", text=_("Type"),
                        command=lambda: self.callbacks.on_sort_column("type", False))
            tree.heading("magnitude", text=_("Mag"),
                        command=lambda: self.callbacks.on_sort_column("magnitude", True))
            tree.heading("date", text=_("Date"),
                        command=lambda: self.callbacks.on_sort_column("date", False))
            tree.heading("observation_time", text=_("Observation time"),
                        command=lambda: self.callbacks.on_sort_column("observation_time", False))
            tree.heading("host", text=_("Host"),
                        command=lambda: self.callbacks.on_sort_column("host", False))
            tree.heading("constellation", text=_("Constellation"),
                        command=lambda: self.callbacks.on_sort_column("constellation", False))
            tree.heading("ra", text=_("RA"),
                        command=lambda: self.callbacks.on_sort_column("ra", False))
            tree.heading("dec", text=_("Dec"),
                        command=lambda: self.callbacks.on_sort_column("dec", False))
            tree.heading("rochester", text=_("Rochester"),
                        command=lambda: self.callbacks.on_sort_column("rochester", False))
            tree.heading("tns", text=_("TNS"),
                        command=lambda: self.callbacks.on_sort_column("tns", False))

            # Configure column widths
            tree.column("name", width=UI_CONSTANTS.COL_WIDTH_NAME, anchor=tk.W)
            tree.column("type", width=UI_CONSTANTS.COL_WIDTH_TYPE, anchor=tk.W)
            tree.column("magnitude", width=UI_CONSTANTS.COL_WIDTH_MAGNITUDE, anchor=tk.E)
            tree.column("date", width=UI_CONSTANTS.COL_WIDTH_DATE, anchor=tk.E)
            tree.column("observation_time", width=UI_CONSTANTS.COL_WIDTH_OBS_TIME, anchor=tk.E)
            tree.column("host", width=UI_CONSTANTS.COL_WIDTH_HOST, anchor=tk.W)
            tree.column("constellation", width=UI_CONSTANTS.COL_WIDTH_CONSTELLATION, anchor=tk.W)
            tree.column("ra", width=UI_CONSTANTS.COL_WIDTH_RA, anchor=tk.E)
            tree.column("dec", width=UI_CONSTANTS.COL_WIDTH_DEC, anchor=tk.E)
            tree.column("rochester", width=UI_CONSTANTS.COL_WIDTH_ROCHESTER, anchor=tk.CENTER)
            tree.column("tns", width=UI_CONSTANTS.COL_WIDTH_TNS, anchor=tk.CENTER)

            # Create scrollbars
            vsb = ttk.Scrollbar(results_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            # Grid layout
            tree.grid(column=0, row=0, sticky="nsew")
            vsb.grid(column=1, row=0, sticky="ns")
            hsb.grid(column=0, row=1, sticky="ew")

            self.widgets['scrollbar_vertical'] = vsb
            self.widgets['scrollbar_horizontal'] = hsb

            # Bind events
            tree.bind("<Double-Button-1>", self.callbacks.on_double_click)
            tree.bind("<Motion>", self.callbacks.on_motion)
            tree.bind("<Leave>", self.callbacks.on_leave)
            tree.bind("<<TreeviewSelect>>", self.callbacks.on_selection_change)

        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to build results tree")

    def _build_action_buttons(self) -> None:
        """Build bottom action buttons (PDF, TXT, Refresh, Exit)."""
        try:
            # PDF button
            pdf_btn = ttk.Button(
                self.parent,
                text=_("PDF"),
                command=self.callbacks.on_pdf
            )
            pdf_btn.grid(column=0, row=12, sticky=tk.E)
            self.widgets['button_pdf'] = pdf_btn

            # TXT button
            txt_btn = ttk.Button(
                self.parent,
                text=_("TXT"),
                command=self.callbacks.on_txt
            )
            txt_btn.grid(column=1, row=12, sticky=tk.W)
            self.widgets['button_txt'] = txt_btn

            # Refresh Search button
            refresh_btn = ttk.Button(
                self.parent,
                text=_("Refresh Search"),
                command=self.callbacks.on_refresh
            )
            refresh_btn.grid(column=2, row=12, sticky=tk.W)
            self.widgets['button_refresh'] = refresh_btn

            # Exit button
            exit_btn = ttk.Button(
                self.parent,
                text=_("Exit"),
                command=self.callbacks.on_exit
            )

            # Add spacing above exit button
            try:
                self.parent.grid_rowconfigure(15, minsize=UI_CONSTANTS.MIN_ROW_SIZE)
                self.parent.grid_rowconfigure(16, minsize=UI_CONSTANTS.MIN_ROW_SIZE)
            except (AttributeError, tk.TclError):
                log_exception(logger, "Failed to configure exit button spacing rows")

            exit_btn.grid(
                column=3,
                row=15,
                padx=UI_CONSTANTS.DEFAULT_PADX,
                pady=UI_CONSTANTS.DEFAULT_PADY,
                sticky=tk.E
            )
            self.widgets['button_exit'] = exit_btn

        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to build results action buttons")

    def _build_progress_bar(self) -> None:
        """Build progress bar (initially hidden)."""
        try:
            progress = ttk.Progressbar(
                self.parent,
                mode='indeterminate',
                length=UI_CONSTANTS.PROGRESS_BAR_LENGTH
            )
            self.widgets['progress_bar'] = progress
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to build progress bar")

    def get_tree(self) -> Optional[ttk.Treeview]:
        """Get the results treeview widget.

        Returns:
            The treeview widget or None if not built
        """
        return self.widgets.get('results_tree')

    def clear_tree(self) -> None:
        """Clear all items from the results tree."""
        try:
            tree = self.get_tree()
            if tree:
                for item in tree.get_children():
                    tree.delete(item)
            self.supernova_data.clear()
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to clear results tree")

    def add_tree_item(self, values: tuple, tags: tuple = ()) -> Optional[str]:
        """Add an item to the results tree.

        Args:
            values: Tuple of values for the tree columns
            tags: Tuple of tags to apply to the item

        Returns:
            The item ID or None if failed
        """
        try:
            tree = self.get_tree()
            if tree:
                return tree.insert('', 'end', values=values, tags=tags)
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to add item to results tree")
        return None

    def set_button_state(self, button_name: str, state: str) -> None:
        """Set the state of a button.

        Args:
            button_name: Name of the button widget (e.g., 'button_pdf')
            state: State to set ('normal', 'disabled', etc.)
        """
        try:
            if button_name in self.widgets:
                self.widgets[button_name]['state'] = state
        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, f"Failed to set button state: {button_name}")

    def start_progress_bar(self) -> None:
        """Show and start the progress bar animation."""
        try:
            if 'progress_bar' in self.widgets:
                progress = self.widgets['progress_bar']
                progress.grid(column=3, row=10, columnspan=2, sticky="ew")
                progress.start()  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError, KeyError):
            log_exception(logger, "Failed to start progress bar")

    def stop_progress_bar(self) -> None:
        """Stop and hide the progress bar."""
        try:
            if 'progress_bar' in self.widgets:
                progress = self.widgets['progress_bar']
                progress.stop()  # type: ignore[attr-defined]
                progress.grid_forget()
        except (AttributeError, tk.TclError, KeyError):
            log_exception(logger, "Failed to stop progress bar")

    def get_selection(self) -> list:
        """Get the currently selected items in the tree.

        Returns:
            List of selected item IDs
        """
        try:
            tree = self.get_tree()
            if tree:
                return list(tree.selection())
        except (AttributeError, tk.TclError, TypeError):
            log_exception(logger, "Failed to get tree selection")
        return []

    def get_tree_children(self) -> tuple:
        """Get all child items in the tree.

        Returns:
            Tuple of item IDs
        """
        try:
            tree = self.get_tree()
            if tree:
                return tree.get_children('')
        except (AttributeError, tk.TclError):
            log_exception(logger, "Failed to get tree children")
        return ()

    def refresh_labels(self) -> None:
        """Refresh all label texts after language change."""
        try:
            if 'label_results' in self.widgets:
                self.widgets['label_results'].config(text=_("Results: "))  # type: ignore[attr-defined]

            # Action buttons
            if 'button_pdf' in self.widgets:
                self.widgets['button_pdf'].config(text=_("PDF"))  # type: ignore[attr-defined]
            if 'button_txt' in self.widgets:
                self.widgets['button_txt'].config(text=_("TXT"))  # type: ignore[attr-defined]
            if 'button_refresh' in self.widgets:
                self.widgets['button_refresh'].config(text=_("Refresh Search"))  # type: ignore[attr-defined]
            if 'button_exit' in self.widgets:
                self.widgets['button_exit'].config(text=_("Exit"))  # type: ignore[attr-defined]

            # Tree column headings
            tree = self.get_tree()
            if tree:
                tree.heading("name", text=_("Name"))
                tree.heading("type", text=_("Type"))
                tree.heading("magnitude", text=_("Mag"))
                tree.heading("date", text=_("Date"))
                tree.heading("observation_time", text=_("Observation time"))
                tree.heading("host", text=_("Host"))
                tree.heading("constellation", text=_("Constellation"))
                tree.heading("ra", text=_("RA"))
                tree.heading("dec", text=_("Dec"))
                tree.heading("rochester", text=_("Rochester"))
                tree.heading("tns", text=_("TNS"))

        except (AttributeError, tk.TclError, TypeError, KeyError):
            log_exception(logger, "Failed to refresh results panel labels")

    def update_idletasks(self) -> None:
        """Update widget idletasks."""
        try:
            for widget in self.widgets.values():
                if hasattr(widget, 'update_idletasks'):
                    widget.update_idletasks()
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to update results panel idletasks")
