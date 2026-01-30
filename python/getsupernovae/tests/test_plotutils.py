import json
import os
import pytest
import astropy.units as u
from astropy.time import Time

import app.reports.plotutils as plotutils
from app.models.snmodels import AxCordInTime, Visibility, Supernova

HERE = os.path.dirname(__file__)
FIXTURE = os.path.join(HERE, "fixtures", "sample_supernova.json")


def test_visibility_plotter_offline_fixture():
    if not getattr(plotutils, "HAS_MATPLOTLIB", False):
        pytest.skip("matplotlib not available")

    with open(FIXTURE, "r", encoding="utf-8") as f:
        payload = json.load(f)

    az_list = []

    class SimpleCoord:
        def __init__(self, alt):
            self.alt = alt

    for item in payload["visibility"]["azCords"]:
        t = Time(item["time"])
        coord = SimpleCoord(item["alt"] * u.deg)
        az_list.append(AxCordInTime(t, coord))

    vis = Visibility(True, az_list)

    sn = Supernova(
        name=payload.get("name", "test"),
        date=None,
        mag=None,
        host=None,
        ra=None,
        decl=None,
        link=None,
        constellation=None,
        coordinates=None,
        firstObserved=None,
        maxMagnitude=None,
        maxMagnitudeDate=None,
        type=None,
        visibility=vis,
    )

    plotter = plotutils.VisibilityPlotter()
    img = plotter.make_image(sn)
    assert img is not None
