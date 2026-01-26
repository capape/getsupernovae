import os
import io
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import Color, black, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from snparser import format_iso_datetime
from snmodels import Supernova
from plotutils import VisibilityPlotter
import json


from snconfig import load_visibility_windows as _load_visibility_windows
import i18n
from pathlib import Path
import platform


def addSupernovaToPdf(textObject, data: Supernova):
    lines = [
        i18n.i18n._("-------------------------------------------------"),
        i18n._("Date: {date}, Mag:{mag}, T: {type}, Name:{name}").format(date=data.date, mag=data.mag, type=data.type, name=data.name),
        i18n._("  Const: {constellation}, Host: {host}").format(constellation=data.constellation, host=data.host),
        i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl),
        "",
        i18n._("    Visible from :{visible_from} to: {visible_to}").format(
            visible_from=format_iso_datetime(data.visibility.azCords[0].time),
            visible_to=format_iso_datetime(data.visibility.azCords[-1].time),
        ),
        i18n._("    AzCoords az:{az0}, lat: {alt0}").format(
            az0=data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2),
            alt0=data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
        ),
        i18n._("    Last azCoords az:{az1}, lat: {alt1}").format(
            az1=data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2),
            alt1=data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2),
        ),
        "",
        i18n._("  Discovered: {firstObserved}, MAX Mag: {maxMagnitude} on: {maxMagnitudeDate}").format(
            firstObserved=data.firstObserved, maxMagnitude=data.maxMagnitude, maxMagnitudeDate=data.maxMagnitudeDate
        ),
        " " + (getattr(data, "link", "") or ""),
        "",
    ]

    for line in lines:
        textObject.textLine(line)


def createPdf(supernovas, fromDate: str, observationDate: str, magnitude, site, minLatitude, visibilityWindowName=None):
    import i18n as i18n_module
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
                except Exception:
                    continue
        except Exception:
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
        except:
            docs = Path.cwd()
    else:
        # Linux/Mac: use Documents or home directory
        try:
            docs = Path.home() / "Documents"
            if not docs.exists():
                docs = Path.home()
        except:
            docs = Path.cwd()
    
    pdf_filename = docs / f"{observationDate}.pdf"
    canvas = Canvas(str(pdf_filename), pagesize=A4)
    try:
        canvas.setPageCompression(0)
    except Exception:
        pass
    canvas.setFont(used_font, fontsize)
    canvas.setFillColor(black)

    def write_header(txtobj, full=True):
        txtobj.setTextOrigin(marginx, topy)
        txtobj.setFont(used_font, fontsize)
        txtobj.setLeading(leading)
        # full header (printed only on first page)
        if full:
            txtobj.textLine(i18n._("Supernovae from: {fromDate} to {to}. Magnitud <= {magnitude}").format(fromDate=fromDate, to=observationDate, magnitude=magnitude))
            # reuse local visibility windows loader for header/site summary
            vis = _load_visibility_windows()
            site_info = i18n._("Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m").format(lon=site.lon.value, lat=site.lat.value, height=site.height.value)
            if visibilityWindowName and visibilityWindowName in vis:
                cfg = vis.get(visibilityWindowName, {})
                site_info = site_info + i18n._(" . Window: minAlt {minAlt:.1f}º maxAlt {maxAlt:.1f}º minAz {minAz:.1f}º maxAz {maxAz:.1f}º").format(
                    minAlt=float(cfg.get("minAlt", 0.0)),
                    maxAlt=float(cfg.get("maxAlt", 90.0)),
                    minAz=float(cfg.get("minAz", 0.0)),
                    maxAz=float(cfg.get("maxAz", 360.0)),
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

    textObject = canvas.beginText()
    write_header(textObject)

    def supernova_lines(data):
        lines = [
            "",
            i18n._("Date: {date}, Mag: {mag}, T: {type}, Name: {name}").format(date=data.date, mag=data.mag, type=data.type, name=data.name),
            i18n._("  Const: {const}, Host: {host}").format(const=data.constellation, host=data.host),
            i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl),
            "",
            i18n._("  Visible from : {from_} to: {to}").format(from_=format_iso_datetime(data.visibility.azCords[0].time), to=format_iso_datetime(data.visibility.azCords[-1].time)),
            i18n._("  AzCoords az: {az}, lat: {lat}").format(az=data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2), lat=data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2)),
            i18n._("  Last azCoords az: {az}, lat: {lat}").format(az=data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2), lat=data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2)),
            "",
            i18n._("  Discovered: {first} , MAX Mag: {max} on: {on}").format(first=data.firstObserved, max=data.maxMagnitude, on=data.maxMagnitudeDate),
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

        if textObject.getY() - required_space < bottom_threshold:
            canvas.drawText(textObject)
            canvas.showPage()
            textObject = canvas.beginText()
            # on subsequent pages print only a minimal header
            write_header(textObject, full=False)
            canvas.setFont(used_font, fontsize)
            canvas.setFillColor(black)

        origin_y = textObject.getY()

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
            except Exception:
                pass
            canvas.restoreState()
        except Exception:
            pass

        for line in lines:
            if textObject.getY() - leading < bottom_threshold:
                canvas.drawText(textObject)
                canvas.showPage()
                textObject = canvas.beginText()
                write_header(textObject, full=False)
                canvas.setFont(used_font, fontsize)
                canvas.setFillColor(black)

            textObject.textLine(line)

        y_after_text = textObject.getY()
        canvas.drawText(textObject)

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
                canvas.linkURL(link, (marginx, link_y - 2, marginx + w, link_y + fontsize + 2), relative=0)
                canvas.setFillColor(black)
        except Exception:
            pass

        try:
            name = getattr(data, "name", None)
            if name:
                try:
                    from urllib.parse import quote

                    tnser = f"https://www.wis-tns.org/object/{quote(name)}"
                    second_y = link_y - leading if 'link_y' in locals() else origin_y - ((len(lines) - 2) * leading)
                    canvas.setFillColor(blue)
                    canvas.setFont(used_font, fontsize)
                    canvas.drawString(marginx, second_y, tnser)
                    w2 = pdfmetrics.stringWidth(tnser, used_font, fontsize)
                    canvas.linkURL(tnser, (marginx, second_y - 2, marginx + w2, second_y + fontsize + 2), relative=0)
                    canvas.setFillColor(black)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            sky_img = plotter.make_sky_chart(data, fmt="png")
        except Exception:
            sky_img = None

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
                    textObject = canvas.beginText()
                    write_header(textObject, full=False)
                    canvas.setFont(used_font, fontsize)
                    canvas.setFillColor(black)
                    # compute image origin below header
                    img_y = textObject.getY() - img_h - (0.2 * cm)

                if img:
                    canvas.drawImage(img, img_x, img_y, width=img_w, height=img_h)

                if sky_img:
                    sky_x = img_x + img_w + gap
                    if sky_x + sky_w > marginx + usable_width:
                        sky_w = marginx + usable_width - sky_x
                    canvas.drawImage(sky_img, sky_x, img_y, width=sky_w, height=img_h)
            except Exception:
                pass

        textObject = canvas.beginText()
        textObject.setTextOrigin(marginx, img_y - (0.2 * cm) if img else topy)
        textObject.setFont(used_font, fontsize)
        textObject.setLeading(leading)
        canvas.setFont(used_font, fontsize)
        canvas.setFillColor(black)

    canvas.drawText(textObject)
    canvas.save()

    return str(pdf_filename)
