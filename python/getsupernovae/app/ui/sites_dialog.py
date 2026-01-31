"""Sites editor dialog.

This module provides `SitesDialog`, a small Tk `Toplevel` used to view,
add, edit and persist observing site definitions (a simple mapping of name
-> lat/lon/height). The dialog is intentionally lightweight and testable: a
`path` may be provided to control where `sites.json` is read/written.
"""

import json
import os
from typing import Dict, Optional

import tkinter as tk
from tkinter import messagebox, ttk

from app.i18n import _

# Note: avoid importing the top-level `getsupernovae` module here to prevent
# import-time side-effects during test collection. Callers may still invoke
# the application's `load_sites()` or `get_user_config_dir()` if needed.
def get_user_config_dir():
    """Return a writable user config directory.

    Respects `GETSUPERNOVAE_CONFIG_DIR` and falls back to a pytest-local
    directory when tests are running to avoid touching the real user's
    configuration.
    """
    # Allow overriding config dir via environment (useful for tests).
    env = os.getenv("GETSUPERNOVAE_CONFIG_DIR")
    if env:
        return env
    # Detect pytest and use a workspace-local test config dir to avoid
    # writing into the real user's home during automated tests.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return os.path.join(os.getcwd(), ".getsupernovae_test_config")
    return os.path.expanduser("~")


def load_sites():
    """Fallback loader used when the application-level loader is unavailable.

    Returns an empty mapping — callers should prefer the package `load_sites`
    helpers when available.
    """
    return {}


class SitesDialog(tk.Toplevel):
    """Toplevel dialog to view, add, edit and persist observing sites.

    The dialog presents a left-hand tree of existing sites and a right-hand
    form to edit or add entries. When saved, the dialog writes a JSON file at
    `self.path` (if provided) or in the user config directory returned by
    `get_user_config_dir()`.
    """

    def __init__(self, parent, sites: Dict[str, dict], path: Optional[str] = None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self._original_sites = sites or {}
        self.path = path

        self.title(_("Add observing site"))
        self.geometry("1024x480")
        self.minsize(700, 420)
        self.resizable(True, True)

        # compute effective path and load existing entries
        self._effective_path = self._determine_path()
        self._current = self._load_current(self._effective_path)

        # Build UI components and wire callbacks
        self._build_ui()
        self._populate_tree()

    def _normalize_site_info(self, v):
        """Normalize various site representations into a plain dict.

        Accepts dict-like objects or objects with `lat`, `lon`, `height` attributes.
        """
        try:
            if isinstance(v, dict):
                lat = float(v.get("lat"))
                lon = float(v.get("lon"))
                h = float(v.get("height", 0.0))
                return {"lat": lat, "lon": lon, "height": h}
        except Exception:
            pass
        try:
            lat = float(v.lat.value)
            lon = float(v.lon.value)
            h = float(v.height.value)
            return {"lat": lat, "lon": lon, "height": h}
        except Exception:
            return {"lat": 0.0, "lon": 0.0, "height": 0.0}

    def _determine_path(self):
        """Return the path to use for reading/writing sites.json.

        Prefers `self.path` if provided; otherwise uses `get_user_config_dir()`
        with sensible fallbacks.
        """
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            return os.path.join(cfgdir, "sites.json") if self.path is None else self.path
        except Exception:
            return os.path.join(os.path.dirname(__file__), "sites.json") if self.path is None else self.path

    def _load_current(self, path):
        """Load existing sites from `path` or fall back to `self._original_sites`.

        Returns a mapping name -> normalized dict(lat, lon, height).
        """
        try:
            with open(path, "r", encoding="utf-8") as fh:
                current = json.load(fh)
                if not isinstance(current, dict):
                    current = {k: {"lat": v.lat.value, "lon": v.lon.value, "height": v.height.value} for k, v in self._original_sites.items()}
        except Exception:
            current = {k: {"lat": v.lat.value, "lon": v.lon.value, "height": v.height.value} for k, v in self._original_sites.items()}

        try:
            current = {k: self._normalize_site_info(v) for k, v in current.items()}
        except Exception:
            current = {}
        try:
            for k, v in self._original_sites.items():
                if k not in current:
                    current[k] = self._normalize_site_info(v)
        except Exception:
            pass

        return current

    def _build_ui(self):
        """Construct UI widgets and assign them to `self` for use by handlers."""
        frame_left = ttk.Frame(self)
        frame_left.grid(column=0, row=0, sticky="nsew", padx=8, pady=8)
        frame_left.grid_rowconfigure(0, weight=1)
        frame_left.grid_columnconfigure(0, weight=1)

        self.columns = ("name", "lat", "lon", "height")
        try:
            style = ttk.Style()
            style.configure("SiteTreeview.Treeview", rowheight=28)
            self.tree = ttk.Treeview(frame_left, columns=self.columns, show="headings", selectmode="browse", style="SiteTreeview.Treeview", height=12)
        except Exception:
            self.tree = ttk.Treeview(frame_left, columns=self.columns, show="headings", selectmode="browse", height=12)

        for col in self.columns:
            self.tree.heading(col, text=col.capitalize())
            if col == "name":
                self.tree.column(col, width=420, anchor=tk.W)
            else:
                self.tree.column(col, width=110, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(frame_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")

        frame_right = ttk.Frame(self)
        frame_right.grid(column=1, row=0, sticky="ne", padx=8, pady=8)

        ttk.Label(frame_right, text=_("Site name:")).grid(column=0, row=0, sticky=tk.E, padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.name_var, width=30).grid(column=1, row=0, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Latitude (deg):")).grid(column=0, row=1, sticky=tk.E, padx=5, pady=5)
        self.lat_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.lat_var, width=20).grid(column=1, row=1, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Longitude (deg):")).grid(column=0, row=2, sticky=tk.E, padx=5, pady=5)
        self.lon_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.lon_var, width=20).grid(column=1, row=2, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Height (m):")).grid(column=0, row=3, sticky=tk.E, padx=5, pady=5)
        self.height_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.height_var, width=20).grid(column=1, row=3, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(column=0, row=1, columnspan=2, sticky="ew", padx=8, pady=8)
        btn_frame.grid_columnconfigure(0, weight=1)

        self._selected_name = {"value": None}

        # wire events and buttons
        self.tree.bind("<<TreeviewSelect>>", lambda ev=None: self._on_select())

        save_btn = ttk.Button(btn_frame, text=_("Save"), command=self._on_save)
        save_btn.grid(column=0, row=0, sticky="w", padx=6)
        delete_btn = ttk.Button(btn_frame, text=_("Delete"), command=self._on_delete)
        delete_btn.grid(column=1, row=0, padx=6)
        close_btn = ttk.Button(btn_frame, text=_("Close"), command=self._on_close)
        close_btn.grid(column=2, row=0, sticky="e", padx=6)

        # try to align dialog visual theme to parent application
        try:
            self._apply_parent_theme()
        except Exception:
            pass

    def _apply_parent_theme(self):
        """Copy a few theme settings from the parent to make the dialog visually
        consistent with the main application.

        This attempts to use the same ttk theme and copy Treeview rowheight and
        the parent's background where possible. It's best-effort and won't raise
        on failure.
        """
        try:
            parent_style = ttk.Style(self.parent)
            parent_theme = parent_style.theme_use()
            style = ttk.Style(self)
            style.theme_use(parent_theme)

            # copy Treeview rowheight if parent configured it
            try:
                tree_cfg = parent_style.configure("Treeview") or {}
                rowh = tree_cfg.get("rowheight")
                if rowh:
                    style.configure("SiteTreeview.Treeview", rowheight=rowh)
            except Exception:
                pass

            # set dialog background to match parent if available
            try:
                bg = self.parent.cget("bg")
                if bg:
                    self.configure(bg=bg)
            except Exception:
                pass
        except Exception:
            pass

    def _autosize_columns(self):
        try:
            from tkinter import font as tkfont
            font = tkfont.Font(font=self.tree.cget("font"))
        except Exception:
            font = None
        max_widths = {col: 0 for col in self.columns}
        for col in self.columns:
            hdr = self.tree.heading(col).get("text", col)
            if font:
                w = font.measure(hdr) + 18
            else:
                w = max(80, len(str(hdr)) * 7)
            max_widths[col] = int(w)
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            for i, col in enumerate(self.columns):
                txt = str(vals[i]) if i < len(vals) else ""
                if font:
                    w = font.measure(txt) + 18
                else:
                    w = max(50, len(txt) * 7)
                if w > max_widths[col]:
                    max_widths[col] = int(w)
        for col in self.columns:
            try:
                self.tree.column(col, width=max_widths[col])
            except Exception:
                pass

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for nm, info in sorted(self._current.items(), key=lambda kv: kv[0].lower()):
            try:
                lat = float(info.get("lat", 0.0))
                lon = float(info.get("lon", 0.0))
                height = float(info.get("height", 0.0))
                lat_s = f"{lat:.2f}"
                lon_s = f"{lon:.2f}"
                height_s = f"{height:.2f}"
            except Exception:
                lat_s = lon_s = height_s = ""
            self.tree.insert("", "end", values=(nm, lat_s, lon_s, height_s))
        self._autosize_columns()

    def _persist_current(self):
        normalized = {k: {"lat": float(v.get("lat", 0.0)), "lon": float(v.get("lon", 0.0)), "height": float(v.get("height", 0.0))} for k, v in self._current.items()}
        try:
            # Prefer an explicit path if the caller provided one (testable).
            if self.path:
                target = self.path
            else:
                cfg_dir = get_user_config_dir()
                os.makedirs(cfg_dir, exist_ok=True)
                target = os.path.join(cfg_dir, "sites.json")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                json.dump(normalized, fh, indent=2)
        except Exception:
            # Fallback to module-local path variable computed earlier in __init__
            try:
                with open(self._effective_path, "w", encoding="utf-8") as fh:
                    json.dump(normalized, fh, indent=2)
            except Exception:
                # Give up silently; callers will be informed elsewhere.
                pass

    def _on_select(self):
        sel = self.tree.selection()
        if not sel:
            self._selected_name["value"] = None
            return
        vals = self.tree.item(sel[0], "values")
        if not vals:
            self._selected_name["value"] = None
            return
        nm, lat, lon, height = vals
        self._selected_name["value"] = nm
        self.name_var.set(nm)
        self.lat_var.set(str(lat))
        self.lon_var.set(str(lon))
        self.height_var.set(str(height))

    def _validate_coords(self, lat: float, lon: float, height: float):
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(_("Latitude must be between -90 and 90 degrees"))
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(_("Longitude must be between -180 and 180 degrees"))

    def _on_save(self):
        nm = self.name_var.get().strip()
        if not nm:
            messagebox.showerror(_("Error"), _("Site name is required"), parent=self)
            return
        try:
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
            height = float(self.height_var.get()) if self.height_var.get().strip() != "" else 0.0
            self._validate_coords(lat, lon, height)
        except ValueError as e:
            messagebox.showerror(_("Error"), _("Invalid input: {e}").format(e=e), parent=self)
            return

        old = self._selected_name["value"]
        if nm in self._current and old is not None and nm != old:
            if not messagebox.askyesno(_("Overwrite"), _("Site '{nm}' already exists. Overwrite?").format(nm=nm), parent=self):
                return

        if old and old != nm and old in self._current:
            try:
                del self._current[old]
            except Exception:
                pass

        self._current[nm] = {"lat": lat, "lon": lon, "height": height}
        try:
            self._persist_current()
            try:
                # attempt to refresh global sites mapping if available
                global_sites = load_sites()
            except Exception:
                global_sites = None
        except Exception as e:
            messagebox.showerror(_("Error"), _("Failed to save site: {e}").format(e=e), parent=self)
            return

        # Reload from disk to ensure UI reflects the persisted representation
        try:
            self._current = self._load_current(self._effective_path)
        except Exception:
            # fall back to in-memory copy already present
            pass

        self._populate_tree()

        # select the newly saved site in the tree for visual feedback
        try:
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, "values")
                if vals and vals[0] == nm:
                    self.tree.selection_set(iid)
                    try:
                        self.tree.see(iid)
                    except Exception:
                        pass
                    break
            self._selected_name["value"] = nm
            self.name_var.set(nm)
            self.lat_var.set(f"{float(self._current[nm].get('lat',0.0)):.2f}")
            self.lon_var.set(f"{float(self._current[nm].get('lon',0.0)):.2f}")
            self.height_var.set(f"{float(self._current[nm].get('height',0.0)):.2f}")
        except Exception:
            pass

        # set result for caller
        self.result = self._current

    def _on_delete(self):
        nm = self._selected_name["value"]
        if not nm:
            return
        if not messagebox.askyesno(_("Delete"), _("Delete site '{nm}'?").format(nm=nm), parent=self):
            return
        try:
            if nm in self._current:
                del self._current[nm]
            self._persist_current()
        except Exception as e:
            messagebox.showerror(_("Error"), _("Failed to delete site: {e}").format(e=e), parent=self)
            return
        self._populate_tree()
        self.name_var.set("")
        self.lat_var.set("")
        self.lon_var.set("")
        self.height_var.set("")
        self._selected_name["value"] = None

    def _on_close(self):
        self.destroy()
