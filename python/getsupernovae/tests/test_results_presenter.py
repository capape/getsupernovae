from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from app.ui.results_presenter import ResultsPresenter, format_observation_time, format_ra_dec, format_magnitude
from app.models.snmodels import Supernova, AxCordInTime, Visibility


def test_format_observation_time_with_astropy_times():
    t1 = Time("2026-01-27T21:30:00")
    t2 = Time("2026-01-27T23:45:00")
    az1 = AxCordInTime(t1, None)
    az2 = AxCordInTime(t2, None)
    vis = Visibility(True, [az1, az2])
    assert format_observation_time(vis) == "21:30 - 23:45"


def test_format_ra_dec_and_magnitude_and_present():
    coord = SkyCoord(ra=10.0 * u.degree, dec=20.0 * u.degree, frame="icrs")
    ra, dec = format_ra_dec(coord)
    assert ":" in ra and ":" in dec
    assert format_magnitude("14.23") == "14.2"
    # Build a minimal Supernova with positional args compatible with constructors used in the app
    sn = Supernova(
        "SN2026abc",
        "2026-01-27",
        "14.23",
        "HostGalaxy",
        "02:00:00",
        "+20:00:00",
        "",
        "Ori",
        coord,
        "2026-01-20",
        "14.23",
        "2026-01-27",
        "Ia",
        Visibility(True, [AxCordInTime(Time("2026-01-27T21:30:00"), None), AxCordInTime(Time("2026-01-27T23:45:00"), None)]),
    )
    presenter = ResultsPresenter()
    row = presenter.present(sn)
    assert row[0] == "SN2026abc"
    assert row[4] == "21:30 - 23:45"
    assert row[2] == "14.2"
    assert row[7] != "" and row[8] != ""
