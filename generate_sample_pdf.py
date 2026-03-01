from datetime import timedelta

import astropy.units as u
from astropy.coordinates import Angle
from astropy.time import Time

# import app helpers
import getsupernovae as gs
from app.i18n import _
from app.models.snmodels import AxCordInTime, Supernova, Visibility

# build visibility az_coords: 10 time points over next 5 hours
now = Time.now()
az_coords = []
for i in range(10):
    t = now + timedelta(minutes=30 * i)
    coord = type("Coord", (), {})()
    coord.alt = Angle(20.0 + i * 3.0, u.deg)
    coord.az = Angle(100.0 + i * 4.0, u.deg)
    az_coords.append(AxCordInTime(t, coord))

vis = Visibility(True, az_coords)

sn = Supernova(
    name="2025aftz",
    last_observed_date=str(now.iso),
    mag="16.5",
    host="HostGalaxy",
    ra="12:34:56",
    decl="+12:34:56",
    link="https://www.rochesterastronomy.org/supernova.html#2025aftz",
    constellation="Ori",
    coordinates=None,
    first_observed="2025-01-01",
    max_magnitude="16.0",
    max_magnitude_date="2025-01-02",
    type="Ia",
    visibility=vis,
)

outname = gs.createPdf(
    [sn],
    from_date="2025-01-01",
    observation_date="sample",
    magnitude="17",
    site=gs.sites.get("Sabadell"),
    min_latitude=25,
    visibility_window_name=None,
)
print(_("Created PDF: {name}").format(name=outname))
