"""PDF report generation for supernova observations.

This module creates comprehensive PDF reports with supernova data, sky charts,
and visibility plots.
"""

import logging
import os
import platform
from pathlib import Path
from urllib.parse import quote

from reportlab.lib.colors import Color, black, blue
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app import i18n
from app.config.snconfig import load_visibility_windows as _load_visibility_windows
from app.models.snmodels import Supernova
from app.reports.plotutils import VisibilityPlotter
from app.utils.skychart import make_sky_chart
from app.utils.snparser import format_iso_datetime

# Module logger: ensure a simple stderr StreamHandler so exceptions are visible
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


def add_supernova_to_pdf(text_object, data: Supernova):
    """Add a single supernova's information to a PDF text object.

    Args:
        text_object: ReportLab text object to write to
        data: Supernova object with observation data
    """
    lines = [
        i18n.i18n._("-------------------------------------------------"),
        i18n._("Date: {date}, Mag:{mag}, T: {type}, Name:{name}").format(
            date=data.last_observed_date, mag=data.mag, type=data.type, name=data.name
        ),
        i18n._("  Const: {constellation}, Host: {host}").format(
            constellation=data.constellation, host=data.host
        ),
        i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl),
        "",
        i18n._("    Visible from :{visible_from} to: {visible_to}").format(
            visible_from=format_iso_datetime(data.visibility.az_coords[0].time),
            visible_to=format_iso_datetime(data.visibility.az_coords[-1].time),
        ),
        i18n._("    AzCoords az:{az0}, lat: {alt0}").format(
            az0=data.visibility.az_coords[0].coord.az.to_string(sep=" ", precision=2),
            alt0=data.visibility.az_coords[0].coord.alt.to_string(sep=" ", precision=2),
        ),
        i18n._("    Last azCoords az:{az1}, lat: {alt1}").format(
            az1=data.visibility.az_coords[-1].coord.az.to_string(sep=" ", precision=2),
            alt1=data.visibility.az_coords[-1].coord.alt.to_string(sep=" ", precision=2),
        ),
        "",
        i18n._(
            "  Discovered: {first_observed}, MAX Mag: {max_magnitude} on: {max_magnitude_date}"
        ).format(
            first_observed=data.first_observed,
            max_magnitude=data.max_magnitude,
            max_magnitude_date=data.max_magnitude_date,
        ),
        " " + (getattr(data, "link", "") or ""),
        "",
    ]

    for line in lines:
        text_object.textLine(line)


def create_pdf(
    supernovas,
    from_date: str,
    observation_date: str,
    magnitude,
    site,
    _min_latitude,
    visibility_window_name=None,
):
    """Generate a comprehensive PDF report of supernova observations.

    Args:
        supernovas: List of Supernova objects with visibility data
        from_date: Start date of search period
        observation_date: End date of search period
        magnitude: Maximum magnitude filter value
        site: EarthLocation of observation site
        _min_latitude: Minimum altitude threshold (unused, kept for compatibility)
        visibility_window_name: Optional visibility window configuration name

    Returns:
        Path to the generated PDF file
    """
    logger.info("Creating pdf")

    # choose a font to embed for better mobile compatibility (Unicode, degree sign)
    used_font = "Courier"
    # prefer bundled font in package/fonts if available
    bundled_font = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    font_candidates = [
        bundled_font,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for fp in font_candidates:
        try:
            if not fp:
                continue
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("DejaVuSans", fp))
                    used_font = "DejaVuSans"
                    break
                except (OSError, IOError, ValueError, RuntimeError):
                    logger.exception("failed to register font %s", fp)
                    continue
        except (AttributeError, TypeError, OSError):
            logger.exception("unexpected error while checking font candidate %s", fp)
            continue

    fontsize = 10
    leading = fontsize * 1.25
    marginx = 1.0 * cm
    margintop = 1.0 * cm
    marginbotton = 1.0 * cm

    topy = 29.7 * cm - margintop

    # Determine user-friendly save location
    if platform.system() == "Windows":
        # Try Documents folder first, fall back to Desktop, then current dir
        try:
            docs = Path.home() / "Documents"
            if not docs.exists():
                docs = Path.home() / "Desktop"
            if not docs.exists():
                docs = Path.cwd()
        except (OSError, AttributeError, RuntimeError):
            logger.exception(
                "failed to determine Documents/Desktop path on Windows; falling back to cwd"
            )
            docs = Path.cwd()
    else:
        # Linux/Mac: use Documents or home directory
        try:
            docs = Path.home() / "Documents"
            if not docs.exists():
                docs = Path.home()
        except (OSError, AttributeError, RuntimeError):
            logger.exception("failed to determine Documents/home path; falling back to cwd")
            docs = Path.cwd()

    pdf_filename = docs / f"{observation_date}.pdf"
    canvas = Canvas(str(pdf_filename), pagesize=A4)
    try:
        canvas.setPageCompression(0)
    except (AttributeError, RuntimeError):
        logger.exception("failed to set page compression (non-fatal)")
    canvas.setFont(used_font, fontsize)
    canvas.setFillColor(black)

    def write_header(txtobj, full=True):
        txtobj.setTextOrigin(marginx, topy)
        txtobj.setFont(used_font, fontsize)
        txtobj.setLeading(leading)
        # full header (printed only on first page)
        if full:
            txtobj.textLine(
                i18n._("Supernovae from: {from_date} to {to}. Magnitud <= {magnitude}").format(
                    from_date=from_date, to=observation_date, magnitude=magnitude
                )
            )
            # reuse local visibility windows loader for header/site summary
            vis = _load_visibility_windows()
            site_info = i18n._("Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m").format(
                lon=site.lon.value, lat=site.lat.value, height=site.height.value
            )
            if visibility_window_name and visibility_window_name in vis:
                cfg = vis.get(visibility_window_name, {})
                window_msg = (
                    " . Window: min_alt {min_alt:.1f}º max_alt {max_alt:.1f}º "
                    "min_az {min_az:.1f}º max_az {max_az:.1f}º"
                )
                site_info = site_info + i18n._(window_msg).format(
                    min_alt=float(cfg.get("min_alt", 0.0)),
                    max_alt=float(cfg.get("max_alt", 90.0)),
                    min_az=float(cfg.get("min_az", 0.0)),
                    max_az=float(cfg.get("max_az", 360.0)),
                )

            # place site info on two lines if it contains window details
            if ". Window:" in site_info:
                part0, part1 = site_info.split(". Window:", 1)
                txtobj.textLine(part0.strip() + ".")
                txtobj.textLine(i18n._("Window: {rest}").format(rest=part1.strip()))
            else:
                txtobj.textLine(site_info)
            txtobj.textLine("")
        else:
            # minimal header on continued pages: leave a blank line for spacing
            txtobj.textLine("")

    text_object = canvas.beginText()
    write_header(text_object)

    def supernova_lines(data):
        lines = [
            "",
            i18n._("Date: {date}, Mag: {mag}, T: {type}, Name: {name}").format(
                date=data.last_observed_date, mag=data.mag, type=data.type, name=data.name
            ),
            i18n._("  Const: {const}, Host: {host}").format(
                const=data.constellation, host=data.host
            ),
            i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl),
            "",
            i18n._("  Visible from : {from_} to: {to}").format(
                from_=format_iso_datetime(data.visibility.az_coords[0].time),
                to=format_iso_datetime(data.visibility.az_coords[-1].time),
            ),
            i18n._("  AzCoords az: {az}, lat: {lat}").format(
                az=data.visibility.az_coords[0].coord.az.to_string(sep=" ", precision=2),
                lat=data.visibility.az_coords[0].coord.alt.to_string(sep=" ", precision=2),
            ),
            i18n._("  Last azCoords az: {az}, lat: {lat}").format(
                az=data.visibility.az_coords[-1].coord.az.to_string(sep=" ", precision=2),
                lat=data.visibility.az_coords[-1].coord.alt.to_string(sep=" ", precision=2),
            ),
            "",
            i18n._("  Discovered: {first} , MAX Mag: {max} on: {on}").format(
                first=data.first_observed,
                max=data.max_magnitude,
                on=data.max_magnitude_date,
            ),
            "",
            "",
        ]
        return lines

    plotter = VisibilityPlotter()
    bottom_threshold = marginbotton + leading

    for data in supernovas:
        lines = supernova_lines(data)
        img = plotter.make_image(data, "png", True, site)
        img_height_pts = (6 * cm) if img else 0
        lines_height = len(lines) * leading
        required_space = lines_height + img_height_pts + leading

        if text_object.getY() - required_space < bottom_threshold:
            canvas.drawText(text_object)
            canvas.showPage()
            text_object = canvas.beginText()
            # on subsequent pages print only a minimal header
            write_header(text_object, full=False)
            canvas.setFont(used_font, fontsize)
            canvas.setFillColor(black)

        origin_y = text_object.getY()

        # draw highlight behind first four lines
        try:
            highlight_lines = 4
            pad = max(2, fontsize * 0.25)
            usable_width = (21.0 * cm) - (2 * marginx)
            rect_top = origin_y + pad
            rect_bottom = origin_y - (highlight_lines * leading) - pad
            rect_height = rect_top - rect_bottom
            canvas.saveState()
            canvas.setFillColor(Color(0.95, 0.95, 0.95))
            canvas.rect(marginx, rect_bottom, usable_width, rect_height, fill=1, stroke=0)
            # draw a subtle top border on the highlight box
            try:
                canvas.setStrokeColor(Color(0.75, 0.75, 0.75))
                canvas.setLineWidth(0.6)
                canvas.line(marginx, rect_top, marginx + usable_width, rect_top)
            except (AttributeError, TypeError, ValueError):
                logger.exception(
                    "failed drawing highlight top border for %s",
                    getattr(data, "name", None),
                )
            canvas.restoreState()
        except (AttributeError, TypeError, ValueError):
            logger.exception("failed drawing highlight box for %s", getattr(data, "name", None))

        for line in lines:
            if text_object.getY() - leading < bottom_threshold:
                canvas.drawText(text_object)
                canvas.showPage()
                text_object = canvas.beginText()
                write_header(text_object, full=False)
                canvas.setFont(used_font, fontsize)
                canvas.setFillColor(black)

            text_object.textLine(line)

        y_after_text = text_object.getY()
        canvas.drawText(text_object)

        try:
            link = getattr(data, "link", None) or ""
            if link:
                discovered_index = None
                for idx, txt in enumerate(lines):
                    if isinstance(txt, str) and txt.strip().startswith("Discovered:"):
                        discovered_index = idx
                        break

                if discovered_index is None:
                    discovered_index = len(lines) - 3

                link_y = origin_y - ((discovered_index + 1) * leading)
                canvas.setFillColor(blue)
                canvas.setFont(used_font, fontsize)
                canvas.drawString(marginx, link_y, link)
                w = pdfmetrics.stringWidth(link, used_font, fontsize)
                canvas.linkURL(
                    link,
                    (marginx, link_y - 2, marginx + w, link_y + fontsize + 2),
                    relative=0,
                )
                canvas.setFillColor(black)
        except (AttributeError, TypeError, ValueError):
            logger.exception("failed to draw link for %s", getattr(data, "name", None))

        try:
            name = getattr(data, "name", None)
            if name:
                try:
                    tnser = f"https://www.wis-tns.org/object/{quote(name)}"
                    second_y = (
                        link_y - leading
                        if "link_y" in locals()
                        else origin_y - ((len(lines) - 2) * leading)
                    )
                    canvas.setFillColor(blue)
                    canvas.setFont(used_font, fontsize)
                    canvas.drawString(marginx, second_y, tnser)
                    w2 = pdfmetrics.stringWidth(tnser, used_font, fontsize)
                    canvas.linkURL(
                        tnser,
                        (marginx, second_y - 2, marginx + w2, second_y + fontsize + 2),
                        relative=0,
                    )
                    canvas.setFillColor(black)
                except (AttributeError, TypeError, ValueError, ImportError):
                    logger.exception(
                        "failed to draw tnser link for %s", getattr(data, "name", None)
                    )
        except (AttributeError, TypeError):
            logger.exception(
                "error while attempting to add tnser link for %s",
                getattr(data, "name", None),
            )

        try:
            sky_img = make_sky_chart(data, fmt="png")
        except (OSError, ValueError, TypeError, AttributeError, ImportError):
            logger.exception(
                "make_sky_chart raised an exception for %s", getattr(data, "name", None)
            )
            sky_img = None

        logger.info(
            "adding images for %s: plot=%s skychart=%s",
            getattr(data, "name", None),
            "yes" if img else "no",
            "yes" if sky_img else "no",
        )
        if img or sky_img:
            try:
                usable_width = (21.0 * cm) - (2 * marginx)
                gap = 0.5 * cm
                if img and sky_img:
                    img_w = usable_width * 0.66
                    sky_w = usable_width - img_w - gap
                else:
                    img_w = min(12.0 * cm, usable_width)
                    sky_w = 0

                img_h = img_height_pts
                img_x = marginx
                img_y = y_after_text - img_h - (0.2 * cm)

                if img_y < marginbotton:
                    canvas.showPage()
                    # start a fresh text object and print only the minimal header
                    text_object = canvas.beginText()
                    write_header(text_object, full=False)
                    canvas.setFont(used_font, fontsize)
                    canvas.setFillColor(black)
                    # compute image origin below header
                    img_y = text_object.getY() - img_h - (0.2 * cm)

                if img:
                    canvas.drawImage(img, img_x, img_y, width=img_w, height=img_h)

                if sky_img:
                    sky_x = img_x + img_w + gap
                    if sky_x + sky_w > marginx + usable_width:
                        sky_w = marginx + usable_width - sky_x
                    canvas.drawImage(sky_img, sky_x, img_y, width=sky_w, height=img_h)
            except (AttributeError, TypeError, ValueError, OSError):
                logger.exception("failed to draw images for %s", getattr(data, "name", None))

        text_object = canvas.beginText()
        text_object.setTextOrigin(marginx, img_y - (0.2 * cm) if img else topy)
        text_object.setFont(used_font, fontsize)
        text_object.setLeading(leading)
        canvas.setFont(used_font, fontsize)
        canvas.setFillColor(black)

    canvas.drawText(text_object)
    canvas.save()

    return str(pdf_filename)
