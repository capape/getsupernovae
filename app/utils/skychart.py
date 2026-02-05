import io
import logging
import astropy.units as u
from reportlab.lib.utils import ImageReader

# Try to import astroquery; availability flagged in HAS_ASTROQUERY
try:
    from astroquery.vizier import Vizier
    HAS_ASTROQUERY = True
except Exception as e:
    # Log the import failure so frozen executables expose the root cause
    logging.getLogger(__name__).exception("astroquery.vizier import failed: %s", e)
    HAS_ASTROQUERY = False

from astropy.coordinates import SkyCoord

# Module logger: ensure a simple stderr StreamHandler so exceptions are visible
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


def make_sky_chart(data, fov_deg: float = 0.32, mag_limit: float = 17.0, fmt: str = "png", width_cm: float = 8.0, height_cm: float = 6.0, dpi: int = 150):
    """Create a tiny sky chart centered on the supernova.

    Returns a ReportLab ImageReader (PNG) or an io.BytesIO (SVG) depending
    on `fmt`. Returns None on error or when dependencies are missing.
    """
    logger.info("generating sky chart for %s, astroquery=%s", getattr(data, "name", None), "yes" if HAS_ASTROQUERY else "no")
    center = None
    try:
        if hasattr(data, "coordinates") and data.coordinates is not None:
            center = data.coordinates
        else:
            ra = getattr(data, "ra", None)
            dec = getattr(data, "decl", None) or getattr(data, "dec", None)
            if ra and dec:
                try:
                    center = SkyCoord(ra, dec, frame="icrs", unit=(u.hourangle, u.deg))
                except Exception:
                    logger.exception("failed to create SkyCoord for %s", getattr(data, "name", None))
                    center = None
    except Exception:
        logger.exception("error obtaining center coordinates for %s", getattr(data, "name", None))
        center = None

    if center is None:
        logger.info("no valid coordinates for %s; cannot generate sky chart", getattr(data, "name", None))
        return None

    if not HAS_ASTROQUERY:
        return None

    try:
        viz = Vizier(columns=["RAJ2000", "DEJ2000", "Gmag"], column_filters={"Gmag": f"<{mag_limit}"}, row_limit=5000)
        radius = (fov_deg * (2 ** 0.5)) / 2.0
        tbls = viz.query_region(center, radius=radius * u.deg, catalog=["I/345/gaia2", "I/352/gaiaedr3"]) if HAS_ASTROQUERY else []
        stars = None
        if tbls and len(tbls) > 0:
            for t in tbls:
                if len(t) > 0:
                    stars = t
                    break
        if stars is None:
            logger.info("no stars found for sky chart of %s", getattr(data, "name", None))
            return None

        ras = stars["RAJ2000"] if "RAJ2000" in stars.colnames else stars["RAJ2000"]
        decs = stars["DEJ2000"] if "DEJ2000" in stars.colnames else stars["DEJ2000"]
        mags = None
        if "Gmag" in stars.colnames:
            mags = stars["Gmag"]
        else:
            for c in ("Vmag", "VT", "Bmag"):
                if c in stars.colnames:
                    mags = stars[c]
                    break

        from astropy.table import Table
        tbl = Table()
        tbl["ra"] = ras
        tbl["dec"] = decs
        if mags is not None:
            tbl["mag"] = mags
        else:
            tbl["mag"] = [99.0] * len(tbl)

        # Use absolute coordinates (RA, Dec in degrees) so axis shows real sky coords
        star_coords = SkyCoord(tbl["ra"], tbl["dec"], unit=(u.deg, u.deg), frame="icrs")
        ra_vals = star_coords.ra.to(u.deg).value
        dec_vals = star_coords.dec.to(u.deg).value

        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
        from astropy.coordinates import Angle

        w_in = width_cm / 2.54
        h_in = height_cm / 2.54
        fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=100)
        half = fov_deg / 2.0

        center_ra = center.ra.to(u.deg).value
        center_dec = center.dec.to(u.deg).value

        ax.set_xlim(center_ra - half, center_ra + half)
        ax.set_ylim(center_dec - half, center_dec + half)

        ax.scatter(ra_vals, dec_vals, s=_mag_to_marker_size(tbl["mag"]), c="k", alpha=0.7)
        ax.scatter([center_ra], [center_dec], s=30, c="red", marker="+", linewidths=1.2)

        def ra_formatter(x, pos=None):
            try:
                # show hours and minutes only (no seconds)
                return Angle(x * u.deg).to_string(unit=u.hourangle, sep=":", precision=0)
            except Exception:
                return f"{x:.2f}°"

        def dec_formatter(x, pos=None):
            try:
                # show degrees and arcminutes only (no seconds)
                return Angle(x * u.deg).to_string(unit=u.deg, sep=":", precision=0, alwayssign=True)
            except Exception:
                return f"{x:.2f}°"

        ax.xaxis.set_major_formatter(FuncFormatter(ra_formatter))
        ax.yaxis.set_major_formatter(FuncFormatter(dec_formatter))

        ax.set_xlabel("RA (J2000)", fontsize=7)
        ax.set_ylabel("Dec (J2000)", fontsize=7)
        # Title: show only the SN name (no coordinates)
        ax.set_title(getattr(data, "name", "SN"), fontsize=8)
        # show RA increasing to the left as customary in sky charts
        ax.invert_xaxis()
        # rotate x-axis labels vertically and reduce tick font sizes
        ax.tick_params(axis="x", rotation=90, labelsize=6)
        ax.tick_params(axis="y", labelsize=6)
        plt.tight_layout()

        bio = io.BytesIO()
        if fmt == "svg":
            fig.savefig(bio, format="svg")
            plt.close(fig)
            bio.seek(0)
            return bio
        else:
            fig.savefig(bio, format="png", dpi=dpi)
            plt.close(fig)
            bio.seek(0)
            return ImageReader(bio)
    except Exception:
        logger.exception("failed to generate sky chart for %s", getattr(data, "name", None))
        return None


def _mag_to_marker_size(mags):
    try:
        import numpy as _np

        arr = _np.array(mags, dtype=float)
        arr = _np.nan_to_num(arr, nan=99.0)
        sizes = 30.0 * (1.0 - (_np.clip(arr, 0, 17) / 17.0)) + 2.0
        return sizes
    except Exception:
        logger.exception("error computing marker sizes from mags")
        return 4.0
