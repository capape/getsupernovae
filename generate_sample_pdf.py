from datetime import timedelta
from astropy.time import Time
from astropy.coordinates import Angle
import astropy.units as u

# import app helpers
import getsupernovae as gs
from app.models.snmodels import Supernova, AxCordInTime, Visibility
from i18n import _

# build visibility azCords: 10 time points over next 5 hours
now = Time.now()
azCords = []
for i in range(10):
    t = now + timedelta(minutes=30 * i)
    coord = type("Coord", (), {})()
    coord.alt = Angle(20.0 + i * 3.0, u.deg)
    coord.az = Angle(100.0 + i * 4.0, u.deg)
    azCords.append(AxCordInTime(t, coord))

vis = Visibility(True, azCords)

sn = Supernova(
    name="2025aftz",
    date=str(now.iso),
    mag="16.5",
    host="HostGalaxy",
    ra="12:34:56",
    decl="+12:34:56",
    link="https://www.rochesterastronomy.org/supernova.html#2025aftz",
    constellation="Ori",
    coordinates=None,
    firstObserved="2025-01-01",
    maxMagnitude="16.0",
    maxMagnitudeDate="2025-01-02",
    type="Ia",
    visibility=vis,
)

outname = gs.createPdf([sn], fromDate="2025-01-01", observationDate="sample", magnitude="17", site=gs.sites.get("Sabadell"), minLatitude=25, visibilityWindowName=None)
print(_("Created PDF: {name}").format(name=outname))
