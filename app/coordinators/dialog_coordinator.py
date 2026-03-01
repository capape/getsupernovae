"""Dialog Coordinator - Orchestrates modal dialogs and their side effects.

This coordinator handles:
- Ignore selected supernova dialog
- Edit old supernovae dialog
- Sites configuration dialog
- Visibility window configuration dialog

It uses callbacks to interact with the UI without tight coupling.
"""
# pylint: disable=cyclic-import  # Lazy imports in methods break cycle at runtime

import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from app.config.snconfig import (
    get_user_config_dir,
    load_old_supernovae,
    load_sites,
    load_visibility_windows,
)
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class DialogCoordinator:
    """Coordinates modal dialogs and their side effects."""

    def __init__(
        self,
        parent_window: tk.Tk,
        get_selected_supernova: Callable[[], Optional[Any]],
        on_update_sites: Callable[[list, Optional[str]], None],
        on_update_visibility_windows: Callable[[list, Optional[str]], None],
        on_refilter: Callable[[], None],
        on_search_async: Callable[[dict, str], None],
        on_show_info: Callable[[str, str], None],
        on_show_error: Callable[[str, str], None],
        on_get_current_site: Callable[[], str],
        on_get_current_visibility_window: Callable[[], str],
        get_combobox_site: Callable[[], Optional[tk.Widget]],
        get_combobox_visibility: Callable[[], Optional[tk.Widget]],
    ):
        """Initialize the dialog coordinator.

        Args:
            parent_window: Parent Tk window for modal dialogs
            get_selected_supernova: Returns currently selected supernova from results
            on_update_sites: Update site combobox with new values
            on_update_visibility_windows: Update visibility window combobox
            on_refilter: Trigger refilter from cache
            on_search_async: Trigger async search
            on_show_info: Show info messagebox
            on_show_error: Show error messagebox
            on_get_current_site: Get current site selection
            on_get_current_visibility_window: Get current visibility window selection
            get_combobox_site: Get site combobox widget
            get_combobox_visibility: Get visibility window combobox widget
        """
        self.parent = parent_window
        self.get_selected_supernova = get_selected_supernova
        self.on_update_sites = on_update_sites
        self.on_update_visibility_windows = on_update_visibility_windows
        self.on_refilter = on_refilter
        self.on_search_async = on_search_async
        self.on_show_info = on_show_info
        self.on_show_error = on_show_error
        self.on_get_current_site = on_get_current_site
        self.on_get_current_visibility_window = on_get_current_visibility_window
        self.get_combobox_site = get_combobox_site
        self.get_combobox_visibility = get_combobox_visibility

    def ignore_selected_supernova(self):
        """Add the currently selected SN to the ignore list (old_supernovae.txt)."""
        # Import here to avoid circular dependency
        from app.i18n import _

        # Get selected supernova from UI
        sn = self.get_selected_supernova()
        if sn is None:
            self.on_show_info(_("No selection"), _("No supernova selected in the Results table."))
            return

        name = getattr(sn, "name", "").strip()
        if not name:
            self.on_show_info(_("No selection"), _("Selected supernova has no name."))
            return

        # Determine path to old_supernovae.txt
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except (OSError, IOError, TypeError, AttributeError):
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # Read existing entries
        existing = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                existing = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
        except (OSError, IOError, UnicodeDecodeError):
            existing = []

        if name in existing:
            self.on_show_info(
                _("Already present"), _("'{name}' is already ignored.").format(name=name)
            )
            return

        # Add and write back sorted unique list
        existing.append(name)
        unique_sorted = sorted(set(existing), key=lambda s: s.lower())

        try:
            with open(path, "w", encoding="utf-8") as fh:
                for ln in unique_sorted:
                    fh.write(ln + "\n")

            # Reload global old list
            try:
                import getsupernovae

                getsupernovae.old_supernovae = load_old_supernovae(path)
            except (ImportError, AttributeError, OSError, IOError):
                log_exception(logger, "Failed to reload ignored supernovae after add")

            self.on_show_info(
                _("Added"), _("Added '{name}' to ignored supernovae.").format(name=name)
            )

            # Auto-reload results using cached rows when possible
            try:
                self.on_refilter()
            except (AttributeError, TypeError):
                # Fallback to network refresh
                try:
                    self.on_search_async({}, "REFRESH")
                except (AttributeError, TypeError):
                    log_exception(logger, "Failed to refresh after adding ignored supernova")
        except (OSError, IOError, PermissionError, UnicodeEncodeError) as ex:
            self.on_show_error(
                _("Save error"), _("Failed to update ignore file: {ex}").format(ex=ex)
            )

    def edit_old_supernovae(self):
        """Open a dialog to edit the old_supernovae.txt file."""
        # Import here to avoid circular dependency
        from app.i18n import _

        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except (OSError, IOError, TypeError, AttributeError):
            # Fallback to package-local file
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # Load current contents
        try:
            with open(path, "r", encoding="utf-8") as fh:
                current = fh.read()
        except (OSError, IOError, UnicodeDecodeError):
            # Try to load from global old list
            try:
                import getsupernovae

                current = "" if getsupernovae.old_supernovae is None else "\n".join(getsupernovae.old_supernovae)
            except (ImportError, AttributeError, TypeError):
                current = ""

        # Create editor window
        editor = tk.Toplevel(self.parent)
        editor.title(_("Edit ignored/old supernovae"))
        editor.geometry("600x400")

        # Apply parent theme to dialog
        try:
            if hasattr(self.parent, "theme_coordinator"):
                self.parent.theme_coordinator.apply_theme()
            elif hasattr(self.parent, "apply_theme"):
                self.parent.apply_theme()
        except (AttributeError, tk.TclError, TypeError):
            pass

        # Make dialog transient and modal
        try:
            editor.transient(self.parent)
            editor.grab_set()
        except (AttributeError, tk.TclError):
            pass

        txt = tk.Text(editor, wrap="none")
        txt.grid(column=0, row=0, columnspan=3, sticky="nsew")

        # Apply theme colors to Text widget
        try:
            from app.config.ui_constants import THEME_COLORS

            dark_mode = False
            if hasattr(self.parent, "dark_mode"):
                try:
                    dark_mode = self.parent.dark_mode.get()
                except (AttributeError, tk.TclError):
                    pass

            if dark_mode:
                txt.configure(
                    bg=THEME_COLORS.DARK_ENTRY_BG,
                    fg=THEME_COLORS.DARK_FG,
                    insertbackground=THEME_COLORS.DARK_FG,
                )
            else:
                txt.configure(
                    bg=THEME_COLORS.LIGHT_ENTRY_BG,
                    fg=THEME_COLORS.LIGHT_FG,
                    insertbackground=THEME_COLORS.LIGHT_FG,
                )
        except (ImportError, AttributeError, tk.TclError):
            pass

        txt.insert("1.0", current)

        # Save handler
        def do_save():
            content = txt.get("1.0", "end").strip()
            try:
                # Normalize: keep only non-empty, non-comment lines
                lines = [
                    line.strip()
                    for line in content.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                # Deduplicate and sort (case-insensitive)
                unique_sorted = sorted(set(lines), key=lambda s: s.lower())

                with open(path, "w", encoding="utf-8") as fh:
                    for ln in unique_sorted:
                        fh.write(ln + "\n")

                # Update global old list
                try:
                    import getsupernovae

                    getsupernovae.old_supernovae = load_old_supernovae(path)
                except (ImportError, AttributeError, OSError, IOError):
                    log_exception(logger, "Failed to reload ignored supernovae after edit")

                editor.destroy()

                # Auto-reload results
                try:
                    self.on_refilter()
                except (AttributeError, TypeError):
                    try:
                        self.on_search_async({}, "REFRESH")
                    except (AttributeError, TypeError):
                        log_exception(logger, "Failed to refresh after editing ignored supernovae")
            except (OSError, IOError, PermissionError, UnicodeEncodeError) as ex:
                self.on_show_error(_("Save error"), _("Failed to save file: {ex}").format(ex=ex))

        # Close handler
        def do_close():
            editor.destroy()

        # Add buttons
        save_btn = ttk.Button(editor, text=_("Save"), command=do_save)
        save_btn.grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        close_btn = ttk.Button(editor, text=_("Close"), command=do_close)
        close_btn.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)

        # Allow text widget to expand
        editor.grid_rowconfigure(0, weight=1)
        editor.grid_columnconfigure(0, weight=1)

    def open_sites_dialog(self):
        """Open the Sites configuration dialog."""

        try:
            from app.ui.sites_dialog import SitesDialog
        except (ImportError, AttributeError):
            return

        # Get current sites
        try:
            current_sites = load_sites()
        except (OSError, IOError, ValueError, TypeError):
            current_sites = {}

        # Launch dialog and wait
        dlg = SitesDialog(self.parent, current_sites)
        self.parent.wait_window(dlg)

        # Reload persisted sites
        try:
            try:
                new_sites = load_sites()
            except (OSError, IOError, ValueError, TypeError):
                new_sites = None

            if new_sites is not None:
                # Update global sites
                try:
                    import getsupernovae

                    getsupernovae.sites = new_sites
                except (ImportError, AttributeError):
                    pass

                try:
                    # Update UI combobox values
                    vals = (
                        sorted(list(new_sites.keys()))
                        if isinstance(new_sites, dict) or hasattr(new_sites, "keys")
                        else []
                    )

                    # Prefer newly added site, otherwise preserve selection
                    sel_name = None
                    try:
                        old_keys = (
                            set(current_sites.keys()) if isinstance(current_sites, dict) else set()
                        )
                        new_keys = set(vals)
                        added = sorted(new_keys - old_keys)
                        if added:
                            sel_name = added[0]
                    except (AttributeError, TypeError, KeyError):
                        sel_name = None

                    # Get previous selection
                    prev = None
                    try:
                        prev = self.on_get_current_site()
                    except (AttributeError, TypeError):
                        prev = None

                    if not sel_name:
                        if prev in vals:
                            sel_name = prev
                        elif vals:
                            sel_name = vals[0]

                    # Update UI
                    self.on_update_sites(vals, sel_name)

                    # Update combobox widget
                    if sel_name:
                        try:
                            cb = self.get_combobox_site()
                            if cb:
                                cb.update_idletasks()
                        except (AttributeError, tk.TclError, TypeError):
                            log_exception(logger, "Failed to update site combobox after dialog")
                except (AttributeError, TypeError, KeyError):
                    log_exception(logger, "Failed to refresh site values after site dialog")
        except (AttributeError, TypeError, OSError):
            log_exception(logger, "Failed to process site dialog result")

    def open_visibility_window_dialog(self):
        """Open the Visibility Window configuration dialog."""

        try:
            from app.ui.visibility_dialog import VisibilityDialog
        except (ImportError, AttributeError):
            return

        # Get current visibility windows
        try:
            current = load_visibility_windows()
        except (OSError, IOError, ValueError, TypeError):
            current = {}

        # Launch dialog and wait
        dlg = VisibilityDialog(self.parent, current)
        self.parent.wait_window(dlg)

        # Process result
        try:
            new_vis = getattr(dlg, "result", None)
            if new_vis is None:
                try:
                    new_vis = load_visibility_windows()
                except (OSError, IOError, ValueError, TypeError):
                    new_vis = None

            if new_vis is not None:
                # Update global visibility_windows
                try:
                    import getsupernovae

                    getsupernovae.visibility_windows = new_vis
                except (ImportError, AttributeError):
                    pass

                try:
                    # Update UI combobox values
                    vals = [""] + sorted(list(new_vis.keys()))

                    # Prefer newly added window
                    sel_name = None
                    try:
                        old_keys = set(current.keys()) if isinstance(current, dict) else set()
                        new_keys = set(new_vis.keys())
                        added = sorted(new_keys - old_keys)
                        if added:
                            sel_name = added[0]
                    except (AttributeError, TypeError, KeyError):
                        sel_name = None

                    # Get previous selection
                    prev = None
                    try:
                        prev = self.on_get_current_visibility_window()
                    except (AttributeError, TypeError):
                        prev = None

                    if not sel_name:
                        if prev in vals:
                            sel_name = prev
                        elif vals:
                            sel_name = vals[0]

                    # Update UI
                    self.on_update_visibility_windows(vals, sel_name)

                    # Update combobox widget
                    if sel_name:
                        try:
                            cb = self.get_combobox_visibility()
                            if cb:
                                cb.update_idletasks()
                        except (AttributeError, tk.TclError, TypeError):
                            log_exception(
                                logger, "Failed to update visibility window combobox after dialog"
                            )
                except (AttributeError, TypeError, KeyError):
                    log_exception(logger, "Failed to refresh visibility window values after dialog")
        except (AttributeError, TypeError, OSError):
            log_exception(logger, "Failed to process visibility window dialog result")
