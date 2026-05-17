"""Plotting utilities for visibility graphs in PDF reports.

Provides VisibilityPlotter class for generating matplotlib-based visibility charts.
"""

import io

from reportlab.lib.utils import ImageReader
from typing import Optional
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, get_sun, EarthLocation

# matplotlib is optional; use Agg backend for non-GUI plotting
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except (ImportError, AttributeError, OSError):
    HAS_MATPLOTLIB = False

from datetime import datetime

import astropy.units as u
from astropy.time import Time

try:
    from astropy.coordinates import AltAz, get_moon

    HAS_GET_MOON = True
except (ImportError, AttributeError):
    from astropy.coordinates import AltAz

    HAS_GET_MOON = False
from app.utils.snparser import format_iso_datetime


def save_matplotlib_figure(fig, fmt: str = "png", dpi: int = 150):
    """Save matplotlib figure to buffer and return appropriate object.

    Args:
        fig: Matplotlib figure object
        fmt: Output format ('png' or 'svg')
        dpi: DPI for PNG output (ignored for SVG)

    Returns:
        For PNG: ImageReader object (for ReportLab)
        For SVG: io.BytesIO containing SVG data
    """
    bio = io.BytesIO()
    if fmt == "svg":
        fig.savefig(bio, format="svg")
        plt.close(fig)
        bio.seek(0)
        return bio

    fig.savefig(bio, format="png", dpi=dpi)
    plt.close(fig)
    bio.seek(0)
    return ImageReader(bio)


class VisibilityPlotter:  # pylint: disable=too-few-public-methods
    """Helper to create visibility charts for supernovas.

    By default `make_image()` returns a ReportLab `ImageReader` (SVG) so it
    can be embedded directly into PDFs via `canvas.drawImage`.

    If you prefer SVG output, call `make_image(data, fmt="svg")` which
    returns an `io.BytesIO` containing SVG bytes (caller may convert or
    render as needed). SVG output is only available when matplotlib is
    installed (it uses the SVG backend via `savefig`).

    Usage:
        plotter = VisibilityPlotter()
        svg_bytes = plotter.make_image(data)            # BytesIO (SVG)
        img = plotter.make_image(data, fmt='png')  # ImageReader (PNG)
    """

    def __init__(self, width_cm: float = 8.0, height_cm: float = 6.0, dpi: int = 150):
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.dpi = dpi

    def make_image(self, data, fmt: str = "png", show_moon: bool = False, location=None):
        """Render the visibility plot.

        Args:
            data: object with `visibility.az_coords` iterable of objects with
                  `.time` (astropy Time-like) and `.coord.alt` (Angle-like).
            fmt: 'png' (default) or 'svg'.

        Returns:
            If fmt == 'png': a `reportlab.lib.utils.ImageReader` suitable for
                `canvas.drawImage`.
            If fmt == 'svg': an `io.BytesIO` containing the SVG bytes.
            Returns `None` on error or if matplotlib is unavailable.
        """

        if not HAS_MATPLOTLIB:
            return None
        try:
            times = []
            alts = []
            for ac in data.visibility.az_coords:
                try:
                    dt = ac.time.to_datetime()
                except (AttributeError, TypeError, ValueError):
                    dt = datetime.strptime(format_iso_datetime(ac.time), "%Y-%m-%dT%H:%M:%SZ")
                times.append(dt)
                alts.append(ac.coord.alt.to_value(u.deg))

            if not times:
                return None

            w_in = self.width_cm / 2.54
            h_in = self.height_cm / 2.54
            fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=100)
            # plot supernova altitude curve and label it with the supernova name
            sn_label = getattr(data, "name", "Supernova")
            ax.plot(times, alts, color="#1f77b4", linewidth=1, label=sn_label)
            ax.fill_between(times, alts, 0, color="#c6dbef", alpha=0.3)
            # optionally plot moon altitude for the same times if requested
            if show_moon and location is not None and HAS_GET_MOON:
                try:
                    t_astropy = Time(times)
                    moon_coord = get_moon(t_astropy)
                    aa = AltAz(obstime=t_astropy, location=location)
                    moon_altaz = moon_coord.transform_to(aa)
                    moon_alts = [ma.alt.to_value(u.deg) for ma in moon_altaz]
                    ax.plot(
                        times,
                        moon_alts,
                        color="#666666",
                        linestyle="--",
                        linewidth=1,
                        label="Moon",
                    )
                    # shade when moon above horizon
                    try:
                        # pylint: disable=import-outside-toplevel  # Lazy load numpy
                        import numpy as _np

                        moon_arr = _np.array(moon_alts)
                        ax.fill_between(
                            times,
                            moon_arr,
                            0,
                            where=moon_arr > 0,
                            color="#999999",
                            alpha=0.12,
                        )
                    except (ValueError, TypeError, AttributeError):
                        pass
                except (AttributeError, TypeError, ValueError, ImportError):
                    # best-effort: if moon calculation fails, continue without it
                    pass
            # Add legend for supernova and moon
            try:
                ax.legend(fontsize=7, frameon=False, loc="upper right")
            except (AttributeError, TypeError, ValueError):
                pass
            ax.set_ylim(0, 90)
            ax.set_ylabel("Alt (deg)", fontsize=8)
            ax.set_xlabel("Time (UTC)", fontsize=8)
            ax.tick_params(axis="both", which="major", labelsize=7)
            # rotate x-axis labels vertically (time and date fully vertical)
            fig.autofmt_xdate(rotation=90, ha="center")
            plt.tight_layout()

            return save_matplotlib_figure(fig, fmt=fmt, dpi=self.dpi)
        except (OSError, ValueError, TypeError, AttributeError):
            return None


def astronomical_dawn(location: EarthLocation, date: Time) -> Optional[Time]:
    """
    Return astronomical dawn (Time) for the given location and date.
    Returns None if no dawn found in +/-12h window (polar day/night).
    """
    # search window: ±12 hours around date
    steps = 288  # 5-minute sampling over 24 h (288 * 5 min = 1440 min)
    jd_start = (date - 12 * u.hour).jd
    jd_end = (date + 12 * u.hour).jd
    jds = np.linspace(jd_start, jd_end, steps)
    times = Time(jds, format="jd")
    altaz = AltAz(obstime=times, location=location)
    sun_alt = get_sun(times).transform_to(altaz).alt.to(u.deg).value

    target = -18.0
    idx = np.where((sun_alt[:-1] < target) & (sun_alt[1:] >= target))[0]
    if len(idx) == 0:
        return None

    i = idx[0]
    # linear interpolation between times[i] and times[i+1]
    a1, a2 = sun_alt[i], sun_alt[i + 1]
    t1, t2 = times[i], times[i + 1]
    if a2 == a1:
        return t1
    frac = (target - a1) / (a2 - a1)
    return Time(t1.jd + frac * (t2.jd - t1.jd), format="jd")


def astronomical_set(location: EarthLocation, date: Time) -> Optional[Time]:
    """
    Return astronomical sunset (Time) for the given location and date.
    Returns None if no set is found in ±12h window (polar day/night).
    """
    # search window: ±12 hours around date
    steps = 288  # 5-min sampling over 24h
    jd_start = (date - 12 * u.hour).jd
    jd_end = (date + 12 * u.hour).jd
    jds = np.linspace(jd_start, jd_end, steps)
    times = Time(jds, format="jd")
    aa = AltAz(obstime=times, location=location)
    sun_alt = get_sun(times).transform_to(aa).alt.to(u.deg).value

    target = -18.0
    # find descending crossing: above (>=) then below (<)
    idx = np.where((sun_alt[:-1] >= target) & (sun_alt[1:] < target))[0]
    if len(idx) == 0:
        return None

    i = idx[0]
    a1, a2 = sun_alt[i], sun_alt[i + 1]
    t1, t2 = times[i], times[i + 1]
    if a2 == a1:
        return t1
    frac = (target - a1) / (a2 - a1)
    return Time(t1.jd + frac * (t2.jd - t1.jd), format="jd")