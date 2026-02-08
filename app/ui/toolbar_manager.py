"""Toolbar Manager

This module manages toolbar UI components for the supernova application.
Follows SOLID principles by isolating toolbar creation, event handling, and state management.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional
from dataclasses import dataclass

from app.i18n import _
from app.config.ui_constants import UI_CONSTANTS


@dataclass
class ToolbarCallbacks:
    """Callbacks for toolbar interactions."""
    on_find_stars: Callable[[], None]
    on_ignore_selected: Callable[[], None]
    on_edit_old: Callable[[], None]
    on_dark_mode_toggle: Callable[[], None]


class ToolbarManager:
    """Manages toolbar UI components and their interactions.
    
    This class is responsible for:
    - Creating the toolbar with action buttons (Find Stars, Ignore SN, Edit Old, Dark Mode)
    - Managing button states (enable/disable)
    - Coordinating with callbacks for business logic
    
    Follows Single Responsibility Principle by focusing only on toolbar UI management.
    """

    def __init__(
        self,
        parent: tk.Widget,
        callbacks: ToolbarCallbacks,
        dark_mode: Optional[tk.BooleanVar] = None,
        grid_column: int = 3,
        grid_row: int = 11,
        columnspan: int = 2
    ):
        """Initialize the toolbar manager.
        
        Args:
            parent: Parent widget to contain the toolbar
            callbacks: ToolbarCallbacks object with event handlers
            dark_mode: Optional BooleanVar for dark mode state
            grid_column: Column position for toolbar placement (default: 3)
            grid_row: Row position for toolbar placement (default: 11)
            columnspan: Number of columns to span (default: 2)
        """
        self.parent = parent
        self.callbacks = callbacks
        self.dark_mode = dark_mode
        self.grid_column = grid_column
        self.grid_row = grid_row
        self.columnspan = columnspan
        
        # Widget references
        self.widgets: Dict[str, tk.Widget] = {}
        self.toolbar_frame: Optional[ttk.Frame] = None
        
    def build(self) -> None:
        """Build the toolbar with all its components."""
        try:
            # Create toolbar frame
            self.toolbar_frame = ttk.Frame(self.parent)
            self.toolbar_frame.grid(
                column=self.grid_column,
                row=self.grid_row,
                columnspan=self.columnspan,
                padx=5,
                pady=5,
                sticky="ew"
            )
            
            # Configure grid weights
            try:
                self.toolbar_frame.grid_columnconfigure(0, weight=1)
            except Exception:
                pass
            
            # Build toolbar buttons
            self._build_find_stars_button()
            self._build_ignore_selected_button()
            self._build_edit_old_button()
            self._build_dark_mode_toggle()
            
        except Exception:
            pass
    
    def _build_find_stars_button(self) -> None:
        """Build the Find Stars button."""
        try:
            button = ttk.Button(
                self.toolbar_frame,
                text=_("Find stars"),
                command=self.callbacks.on_find_stars,
                state=tk.DISABLED
            )
            button.grid(column=0, row=0, sticky=tk.W, padx=UI_CONSTANTS.BUTTON_PADX)
            self.widgets['button_find_stars'] = button
        except Exception:
            pass
    
    def _build_ignore_selected_button(self) -> None:
        """Build the Ignore Selected SN button."""
        try:
            button = ttk.Button(
                self.toolbar_frame,
                text=_("Ignore selected SN"),
                command=self.callbacks.on_ignore_selected
            )
            button.grid(column=1, row=0, sticky=tk.W, padx=UI_CONSTANTS.BUTTON_PADX)
            self.widgets['button_ignore_selected'] = button
        except Exception:
            pass
    
    def _build_edit_old_button(self) -> None:
        """Build the Edit Ignored SN button."""
        try:
            button = ttk.Button(
                self.toolbar_frame,
                text=_("Edit Ignored SN"),
                command=self.callbacks.on_edit_old
            )
            button.grid(column=2, row=0, sticky=tk.W, padx=UI_CONSTANTS.BUTTON_PADX)
            self.widgets['button_edit_old'] = button
        except Exception:
            pass
    
    def _build_dark_mode_toggle(self) -> None:
        """Build the Dark Mode toggle."""
        try:
            if self.dark_mode is not None:
                toggle = ttk.Checkbutton(
                    self.toolbar_frame,
                    text=_("Dark mode"),
                    variable=self.dark_mode,
                    command=self.callbacks.on_dark_mode_toggle
                )
                toggle.grid(column=3, row=0, sticky=tk.E, padx=UI_CONSTANTS.BUTTON_PADX)
                self.widgets['toggle_dark_mode'] = toggle
        except Exception:
            pass
    
    def get_widget(self, name: str) -> Optional[tk.Widget]:
        """Get a specific toolbar widget by name.
        
        Args:
            name: Widget identifier (e.g., 'button_find_stars', 'toggle_dark_mode')
            
        Returns:
            The widget if found, None otherwise
        """
        return self.widgets.get(name)
    
    def get_all_widgets(self) -> Dict[str, tk.Widget]:
        """Get all toolbar widgets.
        
        Returns:
            Dictionary mapping widget names to widget instances
        """
        return self.widgets.copy()
    
    def set_find_stars_state(self, state: str) -> None:
        """Set the state of the Find Stars button.
        
        Args:
            state: Button state (tk.NORMAL, tk.DISABLED, etc.)
        """
        button = self.widgets.get('button_find_stars')
        if button:
            try:
                button.config(state=state)
            except Exception:
                pass
    
    def set_ignore_selected_state(self, state: str) -> None:
        """Set the state of the Ignore Selected SN button.
        
        Args:
            state: Button state (tk.NORMAL, tk.DISABLED, etc.)
        """
        button = self.widgets.get('button_ignore_selected')
        if button:
            try:
                button.config(state=state)
            except Exception:
                pass
    
    def set_edit_old_state(self, state: str) -> None:
        """Set the state of the Edit Ignored SN button.
        
        Args:
            state: Button state (tk.NORMAL, tk.DISABLED, etc.)
        """
        button = self.widgets.get('button_edit_old')
        if button:
            try:
                button.config(state=state)
            except Exception:
                pass
    
    def set_all_buttons_state(self, state: str) -> None:
        """Set the state of all toolbar buttons.
        
        Args:
            state: Button state to apply to all buttons
        """
        for name, widget in self.widgets.items():
            if name.startswith('button_') and isinstance(widget, ttk.Button):
                try:
                    widget.config(state=state)
                except Exception:
                    pass
    
    def refresh_labels(self) -> None:
        """Refresh all button labels with current translations."""
        try:
            # Update Find Stars button
            button = self.widgets.get('button_find_stars')
            if button:
                button.config(text=_("Find stars"))
            
            # Update Ignore Selected SN button
            button = self.widgets.get('button_ignore_selected')
            if button:
                button.config(text=_("Ignore selected SN"))
            
            # Update Edit Ignored SN button
            button = self.widgets.get('button_edit_old')
            if button:
                button.config(text=_("Edit Ignored SN"))
            
            # Update Dark Mode toggle
            toggle = self.widgets.get('toggle_dark_mode')
            if toggle:
                toggle.config(text=_("Dark mode"))
                
        except Exception:
            pass
    
    def destroy(self) -> None:
        """Destroy the toolbar and clean up resources."""
        try:
            if self.toolbar_frame:
                self.toolbar_frame.destroy()
                self.toolbar_frame = None
            self.widgets.clear()
        except Exception:
            pass
