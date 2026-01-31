from ast import List
import os
import sys
from bs4 import BeautifulSoup
from datetime import datetime

# Ensure package imports work when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.dto import SupernovaDTO
from app.models.snmodels import Visibility, AxCordInTime
from getsupernovae import RochesterSupernova, sites
from astropy.coordinates import SkyCoord
import astropy.units as u


class DummyVisibilityFactory:
    def __init__(self, minAlt, maxAlt, minAz, maxAz):
        # record params for later inspection if needed
        self.minAlt = minAlt
        self.maxAlt = maxAlt
        self.minAz = minAz
        self.maxAz = maxAz

    def getVisibility(self, site, coord, t1, t2):
        # Return a minimal Visibility object that will be treated as visible
        return Visibility(True, [AxCordInTime(t1, None)])


def test_rochester_uses_injected_visibility_factory():
    # Build a minimal HTML row similar to provider tests
    snList : List[SupernovaDTO] = []
    sn = SupernovaDTO(
        name="SN2025abc",
        host="NGC 1234",
        ra="12:34:56",
        decl="+12:34:56",
        mag=15.3,
        date="2025/12/01",
        date_obj=datetime.strptime("2025/12/01", "%Y/%m/%d").date(),
        coordinates= SkyCoord("12:34:56", "+12:34:56", frame="icrs", unit=(u.hourangle, u.deg)),
        type="Ia"
    )
    snList.append(sn)


    html = '''
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
    '''

    

    # Instantiate RochesterSupernova with the dummy factory
    rv = RochesterSupernova(visibility_factory=DummyVisibilityFactory)

    # Run selection with permissive thresholds so the single row is included
    results = rv.selectSupernovas(
        snList,
        maxMag="16",
        observationDay=datetime.now(),
        localStartTime="21:00",
        hoursObservation=2,
        fromDate="2024-01-01",
        site=sites["Sabadell"],
        minAlt=0,
        maxAlt=90,
        minAz=0,
        maxAz=360,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    sn = results[0]
    assert getattr(sn, 'visibility', None) is not None
    assert getattr(sn.visibility, 'visible', False) is True
    assert len(getattr(sn.visibility, 'azCords', [])) == 1
