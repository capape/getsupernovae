import io
from reportlab.lib.utils import ImageReader

# matplotlib is optional; use Agg backend for non-GUI plotting
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False

from datetime import datetime
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import get_moon, AltAz
from snparser import format_iso_datetime
from skychart import make_sky_chart as module_make_sky_chart


class VisibilityPlotter:
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
            data: object with `visibility.azCords` iterable of objects with
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
            for ac in data.visibility.azCords:
                try:
                    dt = ac.time.to_datetime()
                except Exception:
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
            if show_moon and location is not None:
                try:
                    t_astropy = Time(times)
                    moon_coord = get_moon(t_astropy)
                    aa = AltAz(obstime=t_astropy, location=location)
                    moon_altaz = moon_coord.transform_to(aa)
                    moon_alts = [ma.alt.to_value(u.deg) for ma in moon_altaz]
                    ax.plot(times, moon_alts, color="#666666", linestyle="--", linewidth=1, label="Moon")
                    # shade when moon above horizon
                    try:
                        import numpy as _np

                        moon_arr = _np.array(moon_alts)
                        ax.fill_between(times, moon_arr, 0, where=moon_arr > 0, color="#999999", alpha=0.12)
                    except Exception:
                        pass
                except Exception:
                    # best-effort: if moon calculation fails, continue without it
                    pass
            # Add legend for supernova and moon
            try:
                ax.legend(fontsize=7, frameon=False, loc="upper right")
            except Exception:
                pass
            ax.set_ylim(0, 90)
            ax.set_ylabel("Alt (deg)", fontsize=8)
            ax.set_xlabel("Time (UTC)", fontsize=8)
            ax.tick_params(axis="both", which="major", labelsize=7)
            # rotate x-axis labels vertically (time and date fully vertical)
            fig.autofmt_xdate(rotation=90, ha="center")
            plt.tight_layout()

            bio = io.BytesIO()
            if fmt == "svg":
                # write SVG bytes to buffer and return it
                fig.savefig(bio, format="svg")
                plt.close(fig)
                bio.seek(0)
                return bio
            else:
                fig.savefig(bio, format="png", dpi=self.dpi)
                plt.close(fig)
                bio.seek(0)
                return ImageReader(bio)
        except Exception:
            return None

    def make_sky_chart(self, data, fov_deg: float = 0.32, mag_limit: float = 17.0, fmt: str = "png"):
        """Wrapper around the module sky-chart maker that uses this instance's
        sizing and DPI settings."""
        try:
            return module_make_sky_chart(
                data,
                fov_deg=fov_deg,
                mag_limit=mag_limit,
                fmt=fmt,
                width_cm=self.width_cm,
                height_cm=self.height_cm,
                dpi=self.dpi,
            )
        except Exception:
            return None
