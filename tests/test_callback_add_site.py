import types
from collections import OrderedDict

import tkinter as tk

from astropy.coordinates import EarthLocation
import astropy.units as u

import pytest


def test_callback_add_site_reloads_sites(monkeypatch, tmp_path):
    """Ensure `callbackAddSite` reloads the canonical `sites` mapping
    (via `load_sites`) and updates the caller's combobox values.
    """

    import getsupernovae as gs

    # prepare two site mappings: old and new
    old = OrderedDict([
        ("A", EarthLocation(lat=1 * u.deg, lon=2 * u.deg, height=0 * u.m)),
    ])
    new = OrderedDict([
        ("A", EarthLocation(lat=1 * u.deg, lon=2 * u.deg, height=0 * u.m)),
        ("B", EarthLocation(lat=3 * u.deg, lon=4 * u.deg, height=0 * u.m)),
    ])

    # stub load_sites to return `old` first, then `new`
    calls = {"n": 0}

    def fake_load_sites():
        calls["n"] += 1
        return old if calls["n"] == 1 else new

    monkeypatch.setattr(gs, "load_sites", fake_load_sites)

    # stub SitesDialog so no real UI is shown
    class FakeDialog:
        def __init__(self, parent, current_sites):
            # do nothing; callbackAddSite will call load_sites() again
            self.result = None

    import app.ui.sites_dialog as sd

    monkeypatch.setattr(sd, "SitesDialog", FakeDialog)

    # build a minimal fake caller with required attributes used by the method
    class DummyCB:
        def __init__(self):
            self._d = {}

        def __setitem__(self, k, v):
            self._d[k] = v

        def __getitem__(self, k):
            return self._d[k]

        def update_idletasks(self):
            pass

    class DummyVar:
        def __init__(self):
            self._v = None

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    class DummyApp:
        def __init__(self):
            self.cbSite = DummyCB()
            self.site = DummyVar()

        def wait_window(self, dlg):
            # no-op; dialog is fake
            return

    dummy = DummyApp()

    # call the method (unbound) with our dummy
    gs.SupernovasApp.callbackAddSite(dummy)

    # after call, global sites should have been set to `new`
    assert getattr(gs, "sites", None) is not None
    # compare keys
    assert list(gs.sites.keys()) == list(new.keys())

    # combobox values were updated to the new names
    assert dummy.cbSite._d.get("values") == list(new.keys())
