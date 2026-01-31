import re
import urllib.parse
from typing import Optional, Tuple
from datetime import datetime
from bs4 import Tag
from astropy.coordinates import SkyCoord
import astropy.units as u


def parse_magnitude(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse magnitude-like strings.
    Returns (value, limit) where limit is '>' or '<' or None.
    """
    if text is None:
        return None, None
    text = text.strip()
    if text == "":
        return None, None

    m = re.search(r"^\s*([<>]?)\s*([+-]?\d+(?:\.\d+)?)", text)
    if not m:
        return None, None

    limit = m.group(1) or None
    try:
        val = float(m.group(2))
    except Exception:
        return None, limit
    return val, limit


def parse_date(text: str):
    """
    Parse date strings like 'YYYY/MM/DD' or 'YYYY-MM-DD' into a date object and
    return (date_obj, normalized_string) where normalized_string is 'YYYY-MM-DD'.
    Returns (None, None) if parsing fails.
    """
    if text is None:
        return None, None

    s = text.strip()
    if s == "":
        return None, None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            dt = datetime.strptime(s, fmt).date()
            return dt, dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    s2 = s.replace('/', '-').replace('.', '-')
    try:
        dt = datetime.strptime(s2, "%Y-%m-%d").date()
        return dt, dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None


def format_iso_datetime(obj):
    """Return ISO-like datetime string 'YYYY-MM-DD HH:MM' for various input types."""
    if obj is None:
        return ""
    try:
        if hasattr(obj, "to_datetime"):
            dt = obj.to_datetime()
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    try:
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M")
        # fallback: return string as-is
        return str(obj)
    except Exception:
        return ""


def _parse_row_safe(row: Tag):
    cols = row.find_all("td")
    if len(cols) < 12:
        return None

    try:
        name_tag = cols[0].find("a")
        name = name_tag.get_text(strip=True) if name_tag else cols[0].get_text(strip=True)
        href = name_tag.get("href") if name_tag else None
        link = None
        if href:
            if href.startswith("../"):
                link = "https://www.rochesterastronomy.org/" + href[3:]
            else:
                link = urllib.parse.urljoin("https://www.rochesterastronomy.org/", href)

        host = cols[1].get_text(strip=True)
        ra_text = cols[2].get_text(strip=True)
        dec_text = cols[3].get_text(strip=True)

        mag_text = cols[5].get_text(strip=True)
        mag_val, mag_limit = parse_magnitude(mag_text)

        raw_date_text = cols[6].get_text(strip=True)
        date_obj, date_text = parse_date(raw_date_text)

        type_text = cols[7].get_text(strip=True)
        max_mag_text = cols[9].get_text(strip=True)
        max_mag = max_mag_text

        raw_max_mag_date = cols[10].get_text(strip=True)
        max_mag_date_obj, max_mag_date = parse_date(raw_max_mag_date)

        raw_first_observed = cols[11].get_text(strip=True)
        first_observed_obj, first_observed = parse_date(raw_first_observed)

        try:
            coord = SkyCoord(ra_text, dec_text, frame="icrs", unit=(u.hourangle, u.deg))
        except Exception:
            return None

        return {
            "name": name,
            "link": link,
            "host": host,
            "ra": ra_text,
            "decl": dec_text,
            "mag": mag_val,
            "mag_limit": mag_limit,
            "date": date_text,
            "date_obj": date_obj,
            "type": type_text,
            "maxMagnitude": max_mag,
            "maxMagnitudeDate": max_mag_date,
            "maxMagnitudeDate_obj": max_mag_date_obj,
            "firstObserved": first_observed,
            "firstObserved_obj": first_observed_obj,
            "coord": coord,
        }

    except Exception:
        return None
