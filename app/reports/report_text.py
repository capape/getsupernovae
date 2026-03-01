"""Text report generation for supernova observations.

This module generates plain text reports with supernova data and visibility information.
"""
from typing import List

from app import i18n
from app.config.snconfig import load_visibility_windows
from app.models.snmodels import Supernova
from app.utils.snparser import format_iso_datetime


def text_supernova(data: Supernova) -> str:
    """Generate a text representation of a single supernova with visibility data.

    Args:
        data: Supernova object with observation and visibility information

    Returns:
        Formatted text string with supernova details
    """
    tpl = i18n._("""
Date: {date}, Mag: {mag}, T: {type}, Name:{name}
Const: {constellation}, Host:{host}
RA:{ra}, DECL.{decl}

    Observation time: {observation_time}
    Visible from :{visible_from} to: {visible_to}
    AzCoords az:{az0}, lat: {alt0}
    Last azCoords az:{az1}, lat: {alt1}

  Discovered: {first_observed}, MAX Mag: {max_magnitude} on: {max_magnitude_date}
  {link}

""")

    # compute from/to and an observation time string
    visible_from = format_iso_datetime(data.visibility.az_coords[0].time)
    visible_to = format_iso_datetime(data.visibility.az_coords[-1].time)
    observation_time = f"{visible_from} - {visible_to}"

    return tpl.format(
        date=data.last_observed_date,
        mag=data.mag,
        type=data.type,
        name=data.name,
        constellation=data.constellation,
        host=data.host,
        ra=data.ra,
        decl=data.decl,
        observation_time=observation_time,
        visible_from=visible_from,
        visible_to=visible_to,
        az0=data.visibility.az_coords[0].coord.az.to_string(sep=" ", precision=2),
        alt0=data.visibility.az_coords[0].coord.alt.to_string(sep=" ", precision=2),
        az1=data.visibility.az_coords[-1].coord.az.to_string(sep=" ", precision=2),
        alt1=data.visibility.az_coords[-1].coord.alt.to_string(sep=" ", precision=2),
        first_observed=data.first_observed,
        max_magnitude=data.max_magnitude,
        max_magnitude_date=data.max_magnitude_date,
        link=getattr(data, "link", ""),
    )


def text_site(site, min_latitude, visibility_window_name=None):
    """Generate text description of observation site and visibility window.

    Args:
        site: EarthLocation with observation site coordinates
        min_latitude: Minimum altitude threshold in degrees
        visibility_window_name: Optional name of visibility window configuration

    Returns:
        Formatted string with site information
    """
    try:
        vis = load_visibility_windows()
        if visibility_window_name and visibility_window_name in vis:
            cfg = vis.get(visibility_window_name, {})
            msg = (
                "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . "
                "Window: min_alt {min_alt:.1f}º max_alt {max_alt:.1f}º "
                "min_az {min_az:.1f}º max_az {max_az:.1f}º"
            )
            return i18n._(msg).format(
                lon=site.lon.value,
                lat=site.lat.value,
                height=site.height.value,
                min_alt=float(cfg.get("min_alt", 0.0)),
                max_alt=float(cfg.get("max_alt", 90.0)),
                min_az=float(cfg.get("min_az", 0.0)),
                max_az=float(cfg.get("max_az", 360.0)),
            )
    except (AttributeError, TypeError, ValueError, KeyError):
        pass

    return i18n._(
        "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Min alt {min_alt}º"
    ).format(
        lon=site.lon.value,
        lat=site.lat.value,
        height=site.height.value,
        min_alt=min_latitude,
    )


def create_text(
    supernovas: List[Supernova],
    from_date: str,
    observation_date: str,
    magnitude,
    site,
    min_latitude,
    visibility_window_name=None,
):
    """Print text report of supernovae to stdout.

    Args:
        supernovas: List of Supernova objects to report
        from_date: Start date of search period
        observation_date: End date of search period
        magnitude: Maximum magnitude filter value
        site: EarthLocation of observation site
        min_latitude: Minimum altitude threshold in degrees
        visibility_window_name: Optional visibility window configuration name
    """
    header = i18n._("Supernovae from: {from_date} to {to}. Magnitud <= {magnitude}").format(
        from_date=from_date, to=observation_date, magnitude=magnitude
    )
    site_info = text_site(site, min_latitude, visibility_window_name)
    print(header)
    print(site_info)

    for data in supernovas:
        print(text_supernova(data))


def create_text_as_string(
    supernovas: List[Supernova],
    from_date: str,
    observation_date: str,
    magnitude,
    site,
    min_latitude,
    visibility_window_name=None,
) -> str:
    """Generate text report of supernovae as a string.

    Args:
        supernovas: List of Supernova objects to report
        from_date: Start date of search period
        observation_date: End date of search period
        magnitude: Maximum magnitude filter value
        site: EarthLocation of observation site
        min_latitude: Minimum altitude threshold in degrees
        visibility_window_name: Optional visibility window configuration name

    Returns:
        Complete text report as a string
    """
    header = i18n._("Supernovae from: {from_date} to {to}. Magnitud <= {magnitude}").format(
        from_date=from_date, to=observation_date, magnitude=magnitude
    )
    site_info = text_site(site, min_latitude, visibility_window_name)

    fulltext = i18n._("{header}\n{site_info}\n\n").format(header=header, site_info=site_info)

    for data in supernovas:
        fulltext += i18n._("\n{sn}\n").format(sn=text_supernova(data))

    return fulltext


def print_supernova(data: Supernova):
    """Print a verbose supernova report to stdout (legacy helper)."""
    print("-------------------------------------------------")
    print(
        i18n._("Date: {date}, Mag: {mag}, T: {type}, Name: {name}").format(
            date=data.last_observed_date, mag=data.mag, type=data.type, name=data.name
        )
    )
    print(i18n._("  Const: {const}, Host: {host}").format(const=data.constellation, host=data.host))
    print(i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl))
    print("")
    # observation time
    obs_start = format_iso_datetime(data.visibility.az_coords[0].time)
    obs_end = format_iso_datetime(data.visibility.az_coords[-1].time)
    print(i18n._("  Observation time: {obs}").format(obs=f"{obs_start} - {obs_end}"))
    print(
        i18n._("  Visible from : {from_} to: {to}").format(
            from_=format_iso_datetime(data.visibility.az_coords[0].time),
            to=format_iso_datetime(data.visibility.az_coords[-1].time),
        )
    )
    print(
        i18n._("  AzCoords az: {az}, lat: {lat}").format(
            az=data.visibility.az_coords[0].coord.az.to_string(sep=" ", precision=2),
            lat=data.visibility.az_coords[0].coord.alt.to_string(sep=" ", precision=2),
        )
    )
    print(
        i18n._("  Last azCoords az: {az}, lat: {lat}").format(
            az=data.visibility.az_coords[-1].coord.az.to_string(sep=" ", precision=2),
            lat=data.visibility.az_coords[-1].coord.alt.to_string(sep=" ", precision=2),
        )
    )
    print("")
    print(
        i18n._("  Discovered: {first} , MAX Mag: {max} on: {on}").format(
            first=data.first_observed, max=data.max_magnitude, on=data.max_magnitude_date
        )
    )
    print(" ", data.link)
    print("")


def print_supernova_short(data: Supernova):
    """Print a compact single-line summary for the supernova."""
    print("-------------------------------------------------")
    print(
        i18n._("Const: {const} - {host} S: {name}, M: {mag}, T: {type}").format(
            const=data.constellation,
            host=data.host,
            name=data.name,
            mag=data.mag,
            type=data.type,
        )
    )
    print(
        i18n._("D: {date} RA: {ra}, DEC: {dec}").format(
            date=data.last_observed_date, ra=data.ra, dec=data.decl
        )
    )
    print(
        i18n._("Observation time: {from_} - {to} az: {az}, LAT: {lat}").format(
            from_=format_iso_datetime(data.visibility.az_coords[0].time),
            to=format_iso_datetime(data.visibility.az_coords[-1].time),
            az=data.visibility.az_coords[0].coord.az.to_string(sep=" ", precision=2),
            lat=data.visibility.az_coords[0].coord.alt.to_string(sep=" ", precision=2),
        )
    )
    print("")
