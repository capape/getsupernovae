"""Results Tree Coordinator - Handles results treeview interactions.

This coordinator manages:
- Column sorting
- Selection change events
- Double-click to open links
- Tooltip display on hover
- SIMBAD star search
"""
import tkinter as tk
import urllib.parse
import webbrowser
from typing import Dict, Callable, Optional, Any

from app.utils.logger import log_exception, get_logger
from app.config.ui_constants import (
    UI_CONSTANTS,
    THEME_COLORS,
    NETWORK_CONSTANTS,
)

logger = get_logger(__name__)


class ResultsTreeCoordinator:
    """Coordinates all results treeview event handlers and interactions."""

    def __init__(
        self,
        tree_widget: tk.Widget,
        supernova_data: Dict[str, Any],
        get_dark_mode: Callable[[], bool],
        on_enable_button: Callable[[str], None],
        on_disable_button: Callable[[str], None],
        on_show_error: Callable[[str, str], None],
    ):
        """Initialize the results tree coordinator.

        Args:
            tree_widget: The ttk.Treeview widget
            supernova_data: Dictionary mapping tree item IDs to supernova objects
            get_dark_mode: Function that returns current dark mode state
            on_enable_button: Callback to enable a button by name
            on_disable_button: Callback to disable a button by name
            on_show_error: Callback to show error dialog (title, message)
        """
        self.tree = tree_widget
        self.supernova_data = supernova_data
        self.get_dark_mode = get_dark_mode
        self.on_enable_button = on_enable_button
        self.on_disable_button = on_disable_button
        self.on_show_error = on_show_error

        # Sorting state
        self._sort_column = None
        self._sort_reverse = False

        # Tooltip state
        self.tooltip_window = None
        self.tooltip_item = None

    def sort_column(self, col: str, is_numeric: bool = False):
        """Sort treeview by column.

        Args:
            col: Column name to sort by
            is_numeric: Whether to use numeric or alphabetic sorting
        """
        try:
            # Toggle sort direction if same column clicked
            if self._sort_column == col:
                self._sort_reverse = not self._sort_reverse
            else:
                self._sort_column = col
                self._sort_reverse = False

            # Get column index
            col_idx = self.tree['columns'].index(col)

            # Get all items with their values
            items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

            # Sort items
            if is_numeric:
                # Numeric sort - handle empty values
                def sort_key(x):
                    try:
                        return float(x[0]) if x[0] else float('inf')
                    except (ValueError, TypeError):
                        return float('inf')
                items.sort(key=sort_key, reverse=self._sort_reverse)
            else:
                # Alphabetic sort
                items.sort(key=lambda x: x[0].lower() if x[0] else '', reverse=self._sort_reverse)

            # Rearrange items in sorted order
            for index, (val, item) in enumerate(items):
                self.tree.move(item, '', index)

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

                        self.tree.item(item, tags=(tag,))
                except Exception:
                    log_exception(logger, "Failed to re-tag sorted tree row")
        except Exception:
            log_exception(logger, "Failed to sort results tree column")

    def on_selection_change(self, event=None):
        """Enable or disable Find stars button based on tree selection.

        Args:
            event: Tkinter event (unused)
        """
        try:
            selection = self.tree.selection()
            if selection and len(selection) > 0:
                self.on_enable_button("find_stars")
            else:
                self.on_disable_button("find_stars")
        except Exception:
            log_exception(logger, "Failed to update Find Stars button state on selection change")

    def find_stars_in_simbad(self):
        """Query SIMBAD for objects near the selected supernova."""
        # Import here to avoid circular dependency
        from app.i18n import _
        
        try:
            selection = self.tree.selection()
            if not selection or len(selection) == 0:
                return

            item = selection[0]
            if item not in self.supernova_data:
                return

            sn = self.supernova_data[item]

            # Build SIMBAD query URL for the region around the supernova
            coord = getattr(sn, 'coordinates', None)
            if coord is not None:
                ra_str = coord.ra.to_string(unit='hour', sep=':', precision=1)
                dec_str = coord.dec.to_string(unit='degree', sep=':', precision=1, alwayssign=True)
            else:
                ra_str = dec_str = ""

            # SIMBAD coordinate query URL
            try:
                criteria_str = (
                    f"region(box,{ra_str} {dec_str},{NETWORK_CONSTANTS.SIMBAD_SEARCH_RADIUS}) & "
                    f"Vmag<{NETWORK_CONSTANTS.SIMBAD_MAX_VMAG} & "
                    f"maintype='{NETWORK_CONSTANTS.SIMBAD_MAIN_TYPE}'"
                )
                criteria_enc = urllib.parse.quote(criteria_str)
            except Exception:
                log_exception(logger, "Failed to build SIMBAD criteria query")
                criteria_enc = ""

            simbad_url = (
                f"{NETWORK_CONSTANTS.SIMBAD_QUERY_URL}?"
                f"Criteria={criteria_enc}&"
                f"OutputMode=LIST&"
                f"maxObject={NETWORK_CONSTANTS.SIMBAD_MAX_OBJECTS}&"
                f"submit=submit+query"
            )

            # Open in browser
            webbrowser.open(simbad_url)

        except Exception as e:
            try:
                self.on_show_error(
                    _("Error"),
                    _("Failed to query SIMBAD: ") + str(e)
                )
            except Exception:
                log_exception(logger, "Failed to show SIMBAD error message")

    def on_double_click(self, event):
        """Handle double-click on results table to open links.

        Args:
            event: Tkinter event with x, y coordinates
        """
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region != "cell":
                return

            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)

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

    def _open_url(self, url: str):
        """Open URL in default browser.

        Args:
            url: URL to open
        """
        try:
            webbrowser.open(url)
        except Exception:
            log_exception(logger, "Failed to open URL")

    def on_motion(self, event):
        """Show tooltip with visibility and discovery info on hover.

        Args:
            event: Tkinter event with x, y coordinates
        """
        try:
            item = self.tree.identify_row(event.y)

            # If we're over a different item or no item, update tooltip
            if item != self.tooltip_item:
                self.hide_tooltip()

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

                                first_alt = getattr(first_coord, 'coord', None)
                                last_alt = getattr(last_coord, 'coord', None)

                                if first_alt is not None and hasattr(first_alt, 'alt'):
                                    tooltip_lines.append(f"Start altitude: {first_alt.alt.degree:.1f}°")
                                if last_alt is not None and hasattr(last_alt, 'alt'):
                                    tooltip_lines.append(f"End altitude: {last_alt.alt.degree:.1f}°")

                                # Find max altitude
                                max_alt = max(
                                    (getattr(c.coord, 'alt', None) for c in az_coords if hasattr(c.coord, 'alt')),
                                    default=None,
                                    key=lambda a: a.degree if a is not None else -999
                                )
                                if max_alt is not None:
                                    tooltip_lines.append(f"Max altitude: {max_alt.degree:.1f}°")
                            except Exception:
                                log_exception(logger, "Failed to compute tooltip altitude values")

                    if tooltip_lines:
                        self.show_tooltip(event.x_root, event.y_root, "\n".join(tooltip_lines))
        except Exception:
            log_exception(logger, "Failed to process results hover tooltip")

    def on_leave(self, event=None):
        """Hide tooltip when mouse leaves the tree.

        Args:
            event: Tkinter event (unused)
        """
        self.hide_tooltip()

    def show_tooltip(self, x: int, y: int, text: str):
        """Display tooltip at specified position.

        Args:
            x: X coordinate (root window)
            y: Y coordinate (root window)
            text: Tooltip text to display
        """
        try:
            self.hide_tooltip()

            # Get parent window from tree widget
            parent = self.tree.winfo_toplevel()

            self.tooltip_window = tk.Toplevel(parent)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x+UI_CONSTANTS.TOOLTIP_OFFSET_X}+{y+UI_CONSTANTS.TOOLTIP_OFFSET_Y}")

            # Style tooltip based on dark mode
            dark = self.get_dark_mode()
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

    def hide_tooltip(self):
        """Hide and destroy tooltip window."""
        try:
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None
            self.tooltip_item = None
        except Exception:
            log_exception(logger, "Failed to hide tooltip")
