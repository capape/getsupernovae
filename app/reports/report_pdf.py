"""PDF report generation for supernova observations.

This module creates comprehensive PDF reports with supernova data, sky charts,
and visibility plots.
"""

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
from app.config.snconfig import (
    SYSTEM_FONT_CANDIDATES,
)
from app.config.snconfig import load_visibility_windows as _load_visibility_windows
from app.models.snmodels import Supernova
from app.reports.plotutils import VisibilityPlotter
from app.utils.logger import setup_module_logger
from app.utils.skychart import make_sky_chart
from app.utils.snparser import format_iso_datetime

# Module logger: ensure a simple stderr StreamHandler so exceptions are visible
logger = setup_module_logger(__name__)


def _determine_pdf_output_directory() -> Path:
    """Determine user-friendly save location for PDF reports.

    Returns:
        Path object for the output directory (Documents, Desktop, or cwd)
    """
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

    return docs


def _register_pdf_font() -> str:
    """Register a Unicode-compatible font for PDF generation.

    Tries to register DejaVuSans font from various locations. Falls back
    to Courier if no suitable font is found.

    Returns:
        Name of the registered font to use ("DejaVuSans" or "Courier")
    """
    used_font = "Courier"
    bundled_font = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    font_candidates = [bundled_font] + SYSTEM_FONT_CANDIDATES

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

    return used_font


def add_supernova_to_pdf(text_object, data: Supernova):
    """Add a single supernova's information to a PDF text object.

    Args:
        text_object: ReportLab text object to write to
        data: Supernova object with observation data
    """
    lines = [
        i18n._("-------------------------------------------------"),
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


# PDF layout settings
class PDFSettings:
    """Container for PDF layout configuration.

    Attributes:
        fontsize: Base font size in points
        leading: Line spacing (fontsize * 1.25)
        marginx: Horizontal margin in cm
        margintop: Top margin in cm
        marginbottom: Bottom margin in cm
        topy: Y-coordinate of top content area
        page_width: Total page width (A4: 21 cm)
        usable_width: Content width excluding margins
        bottom_threshold: Bottom threshold to create new page
        used_font: Name of the registered font to use
    """

    def __init__(self):
        self.fontsize = 10
        self.leading = self.fontsize * 1.25
        self.marginx = 1.0 * cm
        self.margintop = 1.0 * cm
        self.marginbottom = 1.0 * cm
        self.topy = 29.7 * cm - self.margintop
        self.page_width = 21.0 * cm
        self.usable_width = self.page_width - (2 * self.marginx)
        self.bottom_threshold = self.marginbottom + self.leading
        # Register Unicode-compatible font for better mobile compatibility
        self.used_font = _register_pdf_font()


class _Header:
    """Container for PDF report header data.

    Attributes:
        from_date: Start date of observation period
        observation_date: End date of observation period
        magnitude: Maximum magnitude filter threshold
        site: EarthLocation of observation site
        visibility_window_name: Optional name of visibility window configuration
    """

    def __init__(self, from_date, observation_date, magnitude, site, visibility_window_name):
        self.from_date = from_date
        self.observation_date = observation_date
        self.magnitude = magnitude
        self.site = site
        self.visibility_window_name = visibility_window_name


def write_page_header(txtobj, header):
    """Write header section to PDF text object.

    Args:
        txtobj: ReportLab text object to write to
        header: _Header instance with report metadata
    """

    txtobj.textLine(
        i18n._("Supernovae from: {from_date} to {to}. Magnitud <= {magnitude}").format(
            from_date=header.from_date, to=header.observation_date, magnitude=header.magnitude
        )
    )
    # reuse local visibility windows loader for header/site summary
    vis = _load_visibility_windows()
    site = header.site
    site_info = i18n._("Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m").format(
        lon=site.lon.value, lat=site.lat.value, height=site.height.value
    )
    if header.visibility_window_name and header.visibility_window_name in vis:
        cfg = vis.get(header.visibility_window_name, {})
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


def supernova_lines_info(data):
    """Generate formatted text lines for a supernova entry.
    Args:
        data: Supernova object with observation data
    Returns:
        List of formatted strings for PDF text output
    """
    lines = [
        "",
        i18n._("Date: {date}, Mag: {mag}, T: {type}, Name: {name}").format(
            date=data.last_observed_date, mag=data.mag, type=data.type, name=data.name
        ),
        i18n._("  Const: {const}, Host: {host}").format(const=data.constellation, host=data.host),
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
    ]
    return lines


def create_pdf(
    supernovas,
    from_date: str,
    observation_date: str,
    magnitude,
    site,
    visibility_window_name=None,
):
    """Generate a comprehensive PDF report of supernova observations.

    Args:
        supernovas: List of Supernova objects with visibility data
        from_date: Start date of search period
        observation_date: End date of search period
        magnitude: Maximum magnitude filter value
        site: EarthLocation of observation site
        visibility_window_name: Optional visibility window configuration name

    Returns:
        Path to the generated PDF file
    """
    logger.info("Creating pdf")

    settings = PDFSettings()

    # Determine user-friendly save location
    docs = _determine_pdf_output_directory()
    pdf_filename = docs / f"{observation_date}.pdf"
    canvas = Canvas(str(pdf_filename), pagesize=A4)
    try:
        canvas.setPageCompression(0)
    except (AttributeError, RuntimeError):
        logger.exception("failed to set page compression (non-fatal)")
    canvas.setFont(settings.used_font, settings.fontsize)
    canvas.setFillColor(black)

    text_object = canvas.beginText()
    text_object.setTextOrigin(settings.marginx, settings.topy)
    text_object.setFont(settings.used_font, settings.fontsize)
    text_object.setLeading(settings.leading)

    header = _Header(from_date, observation_date, magnitude, site, visibility_window_name)

    write_page_header(text_object, header)

    plotter = VisibilityPlotter()

    for data in supernovas:

        img = plotter.make_image(data, "png", True, site)
        sky_img = make_sky_chart_image(data)

        img_y = add_supernova_to_report(settings, canvas, text_object, data, img, sky_img)

        text_object = canvas.beginText()
        text_object.setTextOrigin(settings.marginx, img_y - (0.2 * cm) if img else settings.topy)
        text_object.setFont(settings.used_font, settings.fontsize)
        text_object.setLeading(settings.leading)
        canvas.setFont(settings.used_font, settings.fontsize)
        canvas.setFillColor(black)

    canvas.drawText(text_object)
    canvas.save()

    return str(pdf_filename)


def add_supernova_to_report(settings, canvas, text_object, data, img, sky_img):
    """Add a complete supernova entry to the PDF report with text, links, and images.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        text_object: ReportLab text object for text rendering
        data: Supernova object with observation data
        img: visibility image
        sky_img: skychart image

    Returns:
        img_y is the Y-coordinate after placing images
    """
    supernova_main_info = supernova_lines_info(data)
    img_height_pts = (6 * cm) if img else 0
    lines_height = len(supernova_main_info) * settings.leading
    required_space = lines_height + img_height_pts + settings.leading

    if text_object.getY() - required_space < settings.bottom_threshold:
        text_object = create_new_page(settings, canvas, text_object)

    new_posy = text_object.getY()

    highlight_box(settings, canvas, data, new_posy)

    for line in supernova_main_info:
        if text_object.getY() - settings.leading < settings.bottom_threshold:
            text_object = create_new_page(settings, canvas, text_object)
        text_object.textLine(line)

    canvas.drawText(text_object)

    new_posy = text_object.getY()

    new_posy = add_rochester_link(settings, canvas, data, new_posy)
    new_posy = add_tns_link(settings, canvas, data, new_posy)
    img_y = add_images(settings, canvas, data, img, sky_img, img_height_pts, new_posy)
    return img_y

def create_new_page(settings, canvas, text_object):
    """Create new page.

    Create a new page.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        text_object: ReportLab text object for text rendering

    Return:
        Text object udpated
    """
    canvas.drawText(text_object)
    canvas.showPage()
    text_object = canvas.beginText()
    text_object.setTextOrigin(settings.marginx, settings.topy)
    text_object.setFont(settings.used_font, settings.fontsize)
    text_object.setLeading(settings.leading)
    text_object.textLine("")
    canvas.setFont(settings.used_font, settings.fontsize)
    canvas.setFillColor(black)
    return text_object


def add_images(settings, canvas, data, img, sky_img, img_height_pts, y_after_text):
    """Add visibility plot and sky chart images to PDF report.

    Handles page breaks when images don't fit on current page.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        data: Supernova object (used for error logging)
        img: Visibility plot image object or None
        sky_img: Sky chart image object or None
        img_height_pts: Height of images in points
        y_after_text: Y-coordinate where images should start

    Returns:
        Y-coordinate after placing images
    """
    logger.info(
        "adding images for %s: plot=%s skychart=%s",
        getattr(data, "name", None),
        "yes" if img else "no",
        "yes" if sky_img else "no",
    )
    img_y = y_after_text  # Default return value if no images
    if img or sky_img:
        try:
            gap = 0.5 * cm
            if img and sky_img:
                img_w = settings.usable_width * 0.66
                sky_w = settings.usable_width - img_w - gap
            else:
                img_w = min(12.0 * cm, settings.usable_width)
                sky_w = 0

            img_h = img_height_pts
            img_x = settings.marginx
            img_y = y_after_text - img_h - (0.2 * cm)

            if img_y < settings.marginbottom:
                canvas.showPage()
                # start a fresh text object and print only the minimal header
                text_object = canvas.beginText()
                text_object.setTextOrigin(settings.marginx, settings.topy)
                text_object.setFont(settings.used_font, settings.fontsize)
                text_object.setLeading(settings.leading)
                text_object.textLine("")
                # draw the header before continuing
                canvas.drawText(text_object)
                # compute image origin below the header we just drew
                img_y = settings.topy - (2 * settings.leading) - img_h - (0.2 * cm)
                canvas.setFont(settings.used_font, settings.fontsize)
                canvas.setFillColor(black)

            if img:
                canvas.drawImage(img, img_x, img_y, width=img_w, height=img_h)

            if sky_img:
                sky_x = img_x + img_w + gap
                if sky_x + sky_w > settings.marginx + settings.usable_width:
                    sky_w = settings.marginx + settings.usable_width - sky_x
                canvas.drawImage(sky_img, sky_x, img_y, width=sky_w, height=img_h)
        except (AttributeError, TypeError, ValueError, OSError):
            logger.exception("failed to draw images for %s", getattr(data, "name", None))
    return img_y


def add_tns_link(settings, canvas, data, posy):
    """Add clickable TNS (Transient Name Server) link to PDF report.

    Positions the link below the Rochester link if present, or at a calculated position.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        data: Supernova object with name for TNS URL
        posy: Y-coordinate of Rochester link, or None if not present
    """
    try:
        name = getattr(data, "name", None)
        if name:
            try:
                tnser = f"https://www.wis-tns.org/object/{quote(name)}"
                new_posy = posy - settings.leading
                canvas.setFillColor(blue)
                canvas.setFont(settings.used_font, settings.fontsize)
                canvas.drawString(settings.marginx, new_posy, tnser)
                w2 = pdfmetrics.stringWidth(tnser, settings.used_font, settings.fontsize)
                canvas.linkURL(
                    tnser,
                    (
                        settings.marginx,
                        new_posy - 2,
                        settings.marginx + w2,
                        new_posy + settings.fontsize + 2,
                    ),
                    relative=0,
                )
                canvas.setFillColor(black)
                return new_posy
            except (AttributeError, TypeError, ValueError, ImportError):
                logger.exception("failed to draw tnser link for %s", getattr(data, "name", None))
    except (AttributeError, TypeError):
        logger.exception(
            "error while attempting to add tnser link for %s",
            getattr(data, "name", None))
    return posy


def add_rochester_link(settings, canvas, data, posy):
    """Add clickable Rochester supernova link to PDF report.

    Positions the link on the Discovery line if found, otherwise near the bottom.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        data: Supernova object with Rochester link URL
        posy: Original Y-coordinate before text rendering

    Returns:
        Y-coordinate of the drawn link, or None if no link was drawn
    """
    try:
        link = getattr(data, "link", None) or ""
        if link:

            new_posy = posy - settings.leading
            canvas.setFillColor(blue)
            canvas.setFont(settings.used_font, settings.fontsize)
            canvas.drawString(settings.marginx, new_posy, link)
            w = pdfmetrics.stringWidth(link, settings.used_font, settings.fontsize)
            canvas.linkURL(
                link,
                (
                    settings.marginx,
                    new_posy - 2,
                    settings.marginx + w,
                    new_posy + settings.fontsize + 2,
                ),
                relative=0,
            )
            canvas.setFillColor(black)
            return new_posy
    except (AttributeError, TypeError, ValueError):
        logger.exception("failed to draw link for %s", getattr(data, "name", None))
    return posy


def make_sky_chart_image(data):
    """Generate a sky chart image for a supernova with error handling.

    Args:
        data: Supernova object with observation data

    Returns:
        Sky chart image object (PNG format) or None if generation fails
    """
    try:
        sky_img = make_sky_chart(data, fmt="png")
    except (OSError, ValueError, TypeError, AttributeError, ImportError):
        logger.exception("make_sky_chart raised an exception for %s", getattr(data, "name", None))
        sky_img = None
    return sky_img


def highlight_box(settings, canvas, data, origin_y):
    """Draw a highlight box behind supernova entry header lines.

    Args:
        settings: PDFSettings instance with layout configuration
        canvas: ReportLab Canvas object for drawing
        data: Supernova object (used for error logging)
        origin_y: Y-coordinate of the top of the text to highlight
    """
    try:
        highlight_lines = 4
        pad = max(2, settings.fontsize * 0.25)
        rect_top = origin_y + pad
        rect_bottom = origin_y - (highlight_lines * settings.leading) - pad
        rect_height = rect_top - rect_bottom
        canvas.saveState()
        canvas.setFillColor(Color(0.95, 0.95, 0.95))
        canvas.rect(
            settings.marginx, rect_bottom, settings.usable_width, rect_height, fill=1, stroke=0
        )

        # draw a subtle top border on the highlight box
        try:
            canvas.setStrokeColor(Color(0.75, 0.75, 0.75))
            canvas.setLineWidth(0.6)
            canvas.line(
                settings.marginx, rect_top, settings.marginx + settings.usable_width, rect_top
            )
        except (AttributeError, TypeError, ValueError):
            logger.exception(
                "failed drawing highlight top border for %s",
                getattr(data, "name", None),
            )
        canvas.restoreState()
    except (AttributeError, TypeError, ValueError):
        logger.exception("failed drawing highlight box for %s", getattr(data, "name", None))
