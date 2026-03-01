"""Results presenter for formatting supernova data for display."""

from typing import Any, Optional, Tuple

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from app.services.visibility import visibility_summary


def _format_time_obj(t: Any) -> str:
    if t is None:
        return ""
    try:
        if isinstance(t, Time):
            dt = t.to_datetime()
            return dt.strftime("%H:%M")
        # datetime-like
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M")
        s = str(t)
        parts = s.rsplit(" ", 1)
        if len(parts) == 2:
            return parts[1]
        if len(s) >= 5:
            return s[-5:]
    except (AttributeError, TypeError, ValueError, IndexError):
        pass
    return ""


def format_observation_time(visibility: Any) -> str:
    """Return 'HH:MM - HH:MM' or empty string if not available."""
    try:
        if not visibility:
            return ""
        az = getattr(visibility, "az_cords", None)
        if not az or len(az) == 0:
            return ""
        tfrom = getattr(az[0], "time", None)
        tto = getattr(az[-1], "time", None)
        return f"{_format_time_obj(tfrom)} - {_format_time_obj(tto)}".strip(" -")
    except (AttributeError, TypeError, IndexError):
        return ""


def format_ra_dec(coord: Optional[SkyCoord]) -> Tuple[str, str]:
    """Format RA/Dec to human-readable strings."""
    if coord is None:
        return "", ""
    try:
        # pylint: disable=no-member  # astropy.units members exist at runtime
        ra = coord.ra.to_string(unit=u.hour, sep=":", precision=1)
        dec = coord.dec.to_string(unit=u.degree, sep=":", precision=1, alwayssign=True)
        return ra, dec
    except (AttributeError, TypeError, ValueError):
        try:
            return str(coord.ra), str(coord.dec)
        except (AttributeError, TypeError):
            return "", ""


def format_magnitude(mag: Any) -> str:
    """Return magnitude formatted with one decimal when numeric."""
    if mag is None:
        return ""
    try:
        mv = float(mag)
        return f"{mv:.1f}"
    except (ValueError, TypeError):
        return str(mag)


class ResultsPresenter:  # pylint: disable=too-few-public-methods
    """Present Supernova domain object as UI row values."""

    ROCH_ICON = "🔗"
    TNS_ICON = "🔗"

    def present(self, sn: Any) -> Tuple[str, str, str, str, str, str, str, str, str, str, str]:
        """Format supernova data for tree view display."""
        name = getattr(sn, "name", "") or ""
        sn_type = getattr(sn, "type", "") or ""
        mag_str = format_magnitude(getattr(sn, "mag", ""))
        date_str = getattr(sn, "date", "") or ""
        visibility = getattr(sn, "visibility", None)
        obs_time = format_observation_time(visibility)
        # If a visibility summary is available, append max altitude for quick glance
        try:
            max_alt = getattr(visibility, "max_alt", None)
            if max_alt is None and getattr(visibility, "az_cords", None):
                summary = visibility_summary(visibility.az_cords)
                if summary:
                    max_alt = summary.get("max_alt")
            if max_alt is not None:
                obs_time = f"{obs_time} (max_alt: {float(max_alt):.1f}°)"
        except (AttributeError, TypeError, KeyError, ValueError):
            pass
        host = getattr(sn, "host", "") or ""
        constellation = getattr(sn, "constellation", "") or ""
        ra_str, dec_str = format_ra_dec(getattr(sn, "coordinates", None))
        return (
            name,
            sn_type,
            mag_str,
            date_str,
            obs_time,
            host,
            constellation,
            ra_str,
            dec_str,
            self.ROCH_ICON,
            self.TNS_ICON,
        )
