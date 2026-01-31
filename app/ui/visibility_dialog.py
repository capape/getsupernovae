"""Visibility windows editor dialog.

Provides `VisibilityDialog` which extracts the inline editor from
`getsupernovae.callbackAddVisibilityWindow` into a testable component.
"""

import json
import os
from typing import Dict, Optional

import tkinter as tk
from tkinter import messagebox, ttk

from app.i18n import _

from app.config.snconfig import get_user_config_dir, load_visibility_windows


class VisibilityDialog(tk.Toplevel):
    """Dialog to view, add, edit and persist named visibility windows.

    Usage: dlg = VisibilityDialog(parent, visibility_windows_mapping, path=optional_path)
    After the dialog closes, `dlg.result` will be the effective mapping.
    """

    def __init__(self, parent, current: Dict[str, dict], path: Optional[str] = None):
        super().__init__(parent)
        self.parent = parent
        self.path = path
        self.title(_("Edit visibility windows"))
        self.geometry("1300x420")
        self.minsize(850, 360)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)

        self._effective_path = self._determine_path()
        self._current = self._load_current(current)
        # adopt parent's theme where possible and act as a transient modal
        try:
            if hasattr(parent, "apply_theme"):
                parent.apply_theme()
        except Exception:
            pass

        try:
            self.transient(parent)
            self.grab_set()
        except Exception:
            pass

        self._build_ui()
        self._populate_tree()
        self.result = None

    def _determine_path(self):
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            return os.path.join(cfgdir, "visibility_windows.json") if self.path is None else self.path
        except Exception:
            return os.path.join(os.path.dirname(__file__), "visibility_windows.json") if self.path is None else self.path

    def _normalize(self, v):
        try:
            return {
                "minAlt": float(v.get("minAlt", 0.0)),
                "maxAlt": float(v.get("maxAlt", 90.0)),
                "minAz": float(v.get("minAz", 0.0)),
                "maxAz": float(v.get("maxAz", 360.0)),
            }
        except Exception:
            return {"minAlt": 0.0, "maxAlt": 90.0, "minAz": 0.0, "maxAz": 360.0}

    def _load_current(self, current):
        try:
            # if current is a path-like mapping, normalize; otherwise default
            items = current.items() if isinstance(current, dict) else {}
            loaded = {k: self._normalize(v) for k, v in items}
        except Exception:
            loaded = {}
        return loaded

    def _build_ui(self):
        frame_left = ttk.Frame(self)
        frame_left.grid(column=0, row=0, sticky="nsew", padx=8, pady=8)
        frame_left.grid_rowconfigure(0, weight=1)
        frame_left.grid_columnconfigure(0, weight=1)

        self.columns = ("name", "minAlt", "maxAlt", "minAz", "maxAz")
        try:
            style = ttk.Style()
            style.configure("VisTreeview.Treeview", rowheight=26)
            self.tree = ttk.Treeview(frame_left, columns=self.columns, show="headings", selectmode="browse", style="VisTreeview.Treeview", height=12)
        except Exception:
            self.tree = ttk.Treeview(frame_left, columns=self.columns, show="headings", selectmode="browse", height=12)
        for col in self.columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=100, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(frame_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")

        frame_right = ttk.Frame(self)
        frame_right.grid(column=1, row=0, sticky="ne", padx=8, pady=8)

        ttk.Label(frame_right, text=_("Name:")).grid(column=0, row=0, sticky=tk.E, padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.name_var, width=30).grid(column=1, row=0, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Min Alt (deg):")).grid(column=0, row=1, sticky=tk.E, padx=5, pady=5)
        self.minalt_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.minalt_var, width=20).grid(column=1, row=1, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Max Alt (deg):")).grid(column=0, row=2, sticky=tk.E, padx=5, pady=5)
        self.maxalt_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.maxalt_var, width=20).grid(column=1, row=2, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Min Az (deg):")).grid(column=0, row=3, sticky=tk.E, padx=5, pady=5)
        self.minaz_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.minaz_var, width=20).grid(column=1, row=3, padx=5, pady=5)

        ttk.Label(frame_right, text=_("Max Az (deg):")).grid(column=0, row=4, sticky=tk.E, padx=5, pady=5)
        self.maxaz_var = tk.StringVar()
        ttk.Entry(frame_right, textvariable=self.maxaz_var, width=20).grid(column=1, row=4, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(column=0, row=1, columnspan=2, sticky="ew", padx=8, pady=8)

        self._selected_name = {"value": None}

        self.tree.bind("<<TreeviewSelect>>", lambda ev=None: self._on_select())

        save_btn = ttk.Button(btn_frame, text=_("Save"), command=self._on_save)
        save_btn.grid(column=0, row=0, sticky="w", padx=6)
        delete_btn = ttk.Button(btn_frame, text=_("Delete"), command=self._on_delete)
        delete_btn.grid(column=1, row=0, padx=6)
        close_btn = ttk.Button(btn_frame, text=_("Close"), command=self._on_close)
        close_btn.grid(column=2, row=0, sticky="e", padx=6)

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for nm, info in sorted(self._current.items(), key=lambda kv: kv[0].lower()):
            try:
                ma = float(info.get("minAlt", 0.0))
                xa = float(info.get("maxAlt", 90.0))
                mz = float(info.get("minAz", 0.0))
                xz = float(info.get("maxAz", 360.0))
                self.tree.insert("", "end", values=(nm, f"{ma:.1f}", f"{xa:.1f}", f"{mz:.1f}", f"{xz:.1f}"))
            except Exception:
                self.tree.insert("", "end", values=(nm, "", "", "", ""))

    def _persist_current(self):
        normalized = {k: {"minAlt": float(v.get("minAlt", 0.0)), "maxAlt": float(v.get("maxAlt", 90.0)), "minAz": float(v.get("minAz", 0.0)), "maxAz": float(v.get("maxAz", 360.0))} for k, v in self._current.items()}
        try:
            cfg_dir = get_user_config_dir()
            os.makedirs(cfg_dir, exist_ok=True)
            user_path = os.path.join(cfg_dir, "visibility_windows.json")
            with open(user_path, "w", encoding="utf-8") as fh:
                json.dump(normalized, fh, indent=2)
        except Exception:
            try:
                with open(self._effective_path, "w", encoding="utf-8") as fh:
                    json.dump(normalized, fh, indent=2)
            except Exception:
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
        nm, mina, maxa, minz, maxz = vals
        self._selected_name["value"] = nm
        self.name_var.set(nm)
        self.minalt_var.set(str(mina))
        self.maxalt_var.set(str(maxa))
        self.minaz_var.set(str(minz))
        self.maxaz_var.set(str(maxz))

    def _on_save(self):
        nm = self.name_var.get().strip()
        if not nm:
            messagebox.showerror(_("Error"), _("Name is required"), parent=self)
            return
        try:
            mina = float(self.minalt_var.get())
            maxa = float(self.maxalt_var.get())
            minz = float(self.minaz_var.get())
            maxz = float(self.maxaz_var.get())
        except Exception as e:
            messagebox.showerror(_("Error"), _("Invalid numeric input: {e}").format(e=e), parent=self)
            return

        old = self._selected_name["value"]
        if nm in self._current and old is not None and nm != old:
            if not messagebox.askyesno(_("Overwrite"), _("Window '{nm}' already exists. Overwrite?").format(nm=nm), parent=self):
                return

        if old and old != nm and old in self._current:
            try:
                del self._current[old]
            except Exception:
                pass

        self._current[nm] = {"minAlt": mina, "maxAlt": maxa, "minAz": minz, "maxAz": maxz}
        try:
            self._persist_current()
            global_visibility = load_visibility_windows()
        except Exception as e:
            messagebox.showerror(_("Error"), _("Failed to save visibility windows: {e}").format(e=e), parent=self)
            return

        self._populate_tree()
        # set result for caller
        self.result = self._current

    def _on_add(self):
        nm = self.name_var.get().strip()
        if not nm:
            messagebox.showerror(_("Invalid input"), _("Name is required."), parent=self)
            return
        try:
            mina = float(self.minalt_var.get())
            maxa = float(self.maxalt_var.get())
            minz = float(self.minaz_var.get())
            maxz = float(self.maxaz_var.get())
        except Exception:
            messagebox.showerror(_("Invalid input"), _("Numeric fields must be valid numbers."), parent=self)
            return
        if nm in self._current:
            messagebox.showerror(_("Invalid input"), _("A window with that name already exists."), parent=self)
            return
        self._current[nm] = {"minAlt": mina, "maxAlt": maxa, "minAz": minz, "maxAz": maxz}
        try:
            self._persist_current()
        except Exception as e:
            messagebox.showerror(_("Error"), _("Failed to add window: {e}").format(e=e), parent=self)
            return
        self._populate_tree()
        self.result = self._current

    def _on_delete(self):
        nm = self._selected_name["value"]
        if not nm:
            return
        if not messagebox.askyesno(_("Delete"), _("Delete visibility window '{nm}'?").format(nm=nm), parent=self):
            return
        try:
            if nm in self._current:
                del self._current[nm]
            self._persist_current()
        except Exception as e:
            messagebox.showerror(_("Error"), _("Failed to delete window: {e}").format(e=e), parent=self)
            return
        self._populate_tree()
        self.result = self._current

    def _on_close(self):
        self.destroy()
