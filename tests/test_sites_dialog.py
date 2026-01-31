import json
import os
import sys
import tkinter as tk
from tkinter import ttk

import pytest

# Ensure package imports work when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.i18n import _
except Exception:
    def _(s):
        return s


def _find_widgets(root, cls=None, text=None):
    """Recursively find widgets under `root` matching tkinter class `cls` and optional `text`."""
    found = []

    def walk(w):
        for ch in w.winfo_children():
            # match class
            if cls is None or isinstance(ch, cls):
                if text is None:
                    found.append(ch)
                else:
                    try:
                        if str(ch.cget("text")) == text:
                            found.append(ch)
                    except Exception:
                        pass
            walk(ch)

    walk(root)
    return found


def test_sites_dialog_save_creates_file(tmp_path):
    # create a temporary path for sites.json
    p = tmp_path / "sites.json"
    root = tk.Tk()
    root.withdraw()

    try:
        from app.ui.sites_dialog import SitesDialog

        dlg = SitesDialog(root, sites={}, path=str(p))

        # find entries and set values (order not guaranteed so match by widget geometry)
        entries = _find_widgets(dlg, ttk.Entry)
        assert len(entries) >= 4

        # heuristic: set first four entries to name, lat, lon, height
        entries[0].delete(0, "end")
        entries[0].insert(0, "TestSite")
        entries[1].delete(0, "end")
        entries[1].insert(0, "10.0")
        entries[2].delete(0, "end")
        entries[2].insert(0, "20.0")
        entries[3].delete(0, "end")
        entries[3].insert(0, "5.0")

        # find Save button and invoke
        save_text = str(_("Save"))
        buttons = _find_widgets(dlg, ttk.Button, text=save_text)
        assert buttons, "Save button not found"
        buttons[0].invoke()

        # dialog should have set result mapping
        assert getattr(dlg, "result", None) is not None
        assert "TestSite" in dlg.result

        # file should be created and contain mapping
        assert p.exists()
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert "TestSite" in data

    finally:
        try:
            dlg.destroy()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        # restore global sites mapping in getsupernovae in case it was modified
        try:
            import getsupernovae as gs
            try:
                gs.sites = gs.load_sites()
            except Exception:
                pass
        except Exception:
            pass


def test_sites_dialog_overwrite_and_delete(tmp_path):
    # pre-create a sites file with an entry
    p = tmp_path / "sites.json"
    initial = {"Existing": {"lat": 1.0, "lon": 2.0, "height": 3.0}}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(initial, fh)

    root = tk.Tk()
    root.withdraw()
    try:
        from app.ui.sites_dialog import SitesDialog

        dlg = SitesDialog(root, sites={}, path=str(p))

        # select the existing item in the tree by finding the tree and selecting first item
        trees = _find_widgets(dlg, ttk.Treeview)
        assert trees
        tree = trees[0]
        children = tree.get_children()
        assert children
        tree.selection_set(children[0])
        # ensure selection callback runs to populate selected_name
        dlg.update_idletasks()
        dlg.update()
        tree.event_generate('<<TreeviewSelect>>')

        # find Delete button and invoke
        del_text = str(_("Delete"))
        buttons = _find_widgets(dlg, ttk.Button, text=del_text)
        assert buttons, "Delete button not found"
        buttons[0].invoke()

        # after delete, persist file should not contain 'Existing'
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert "Existing" not in data

    finally:
        try:
            dlg.destroy()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        # restore global sites mapping in getsupernovae in case it was modified
        try:
            import getsupernovae as gs
            try:
                gs.sites = gs.load_sites()
            except Exception:
                pass
        except Exception:
            pass
