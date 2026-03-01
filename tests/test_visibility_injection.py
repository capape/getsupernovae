import os
import sys
from ast import List
from datetime import datetime

# Ensure package imports work when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.models.dto import SupernovaDTO
from app.models.snmodels import AxCordInTime, Visibility
from app.services.rochester_supernova import RochesterSupernova
from getsupernovae import sites


class DummyVisibilityFactory:
    def __init__(self, min_alt, max_alt, min_az, max_az):
        # record params for later inspection if needed
        self.min_alt = min_alt
        self.max_alt = max_alt
        self.min_az = min_az
        self.max_az = max_az

    def get_visibility(self, site, coord, t1, t2):
        # Return a minimal Visibility object that will be treated as visible
        return Visibility(True, [AxCordInTime(t1, None)])


def test_rochester_uses_injected_visibility_factory():
    # Build a minimal HTML row similar to provider tests
    sn_list: List[SupernovaDTO] = []
    sn = SupernovaDTO(
        name="SN2025abc",
        host="NGC 1234",
        ra="12:34:56",
        decl="+12:34:56",
        mag=15.3,
        last_observed_date="2025/12/01",
        last_observed_date_obj=datetime.strptime("2025/12/01", "%Y/%m/%d").date(),
        coordinates=SkyCoord("12:34:56", "+12:34:56", frame="icrs", unit=(u.hourangle, u.deg)),
        type="Ia",
    )
    sn_list.append(sn)

    html = """
    <table>
    <tr>
        <td><a href="../snimages/sn2025abc.html">SN2025abc</a></td>
        <td>NGC 1234</td>
        <td>12:34:56</td>
        <td>+12:34:56</td>
        <td></td>
        <td>15.3</td>
        <td>2025/12/01</td>
        <td>Ia</td>
        <td></td>
        <td>14.8</td>
        <td>2025/12/03</td>
        <td>2025/11/30</td>
    </tr>
    </table>
    """

    # Instantiate RochesterSupernova with the dummy factory
    rv = RochesterSupernova(
        old_supernovae=set(), visibility_windows={}, visibility_factory=DummyVisibilityFactory
    )

    # Run selection with permissive thresholds so the single row is included
    results = rv.select_supernovae(
        sn_list,
        max_mag="16",
        observation_day=datetime.now(),
        local_start_time="21:00",
        hours_observation=2,
        from_date="2024-01-01",
        site=sites["Sabadell"],
        min_alt=0,
        max_alt=90,
        min_az=0,
        max_az=360,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    sn = results[0]
    assert getattr(sn, "visibility", None) is not None
    assert getattr(sn.visibility, "visible", False) is True
    assert len(getattr(sn.visibility, "az_coords", [])) == 1
