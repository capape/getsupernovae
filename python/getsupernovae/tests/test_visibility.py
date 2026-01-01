from datetime import timedelta
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

# Import VisibilityWindow directly from snvisibility; keep `sites` from the
# application module for site definitions.
from snvisibility import VisibilityWindow
from getsupernovae import sites


def test_getVisibility_timestamps():
    # Use a coordinate near the north celestial pole so it's above horizon
    coord = SkyCoord(ra=0 * u.deg, dec=90 * u.deg, frame="icrs")
    site = sites["Sabadell"]

    t1 = Time("2025-12-03T00:00:00")
    t2 = t1 + timedelta(hours=2)

    vw = VisibilityWindow(minAlt=0)
    vis = vw.getVisibility(site, coord, t1, t2)
    assert vis is not None
    assert vis.visible
    assert len(vis.azCords) > 0

    # First sample time should equal t1 (no 0.5h offset)
    first_sample_time = vis.azCords[0].time
    assert first_sample_time.to_value('iso')[:16] == t1.to_value('iso')[:16]

    # ensure subsequent samples are spaced by 30 minutes
    if len(vis.azCords) > 1:
        t0 = vis.azCords[0].time.to_datetime()
        t1s = vis.azCords[1].time.to_datetime()
        delta = t1s - t0
        assert delta.total_seconds() in (1800.0,)
