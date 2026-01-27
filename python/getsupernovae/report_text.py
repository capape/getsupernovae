import os
import json
from typing import List
from snmodels import Supernova
from snparser import format_iso_datetime
from snconfig import load_visibility_windows
import i18n


def textSupernova(data: Supernova) -> str:
    tpl = i18n._(
        """
Date: {date}, Mag: {mag}, T: {type}, Name:{name}
Const: {constellation}, Host:{host}
RA:{ra}, DECL.{decl}

    Observation time: {observation_time}
    Visible from :{visible_from} to: {visible_to}
    AzCoords az:{az0}, lat: {alt0}
    Last azCoords az:{az1}, lat: {alt1}

  Discovered: {firstObserved}, MAX Mag: {maxMagnitude} on: {maxMagnitudeDate}
  {link}

"""
    )

    # compute from/to and an observation time string
    visible_from = format_iso_datetime(data.visibility.azCords[0].time)
    visible_to = format_iso_datetime(data.visibility.azCords[-1].time)
    observation_time = f"{visible_from} - {visible_to}"

    return tpl.format(
        date=data.date,
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
        az0=data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2),
        alt0=data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
        az1=data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2),
        alt1=data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2),
        firstObserved=data.firstObserved,
        maxMagnitude=data.maxMagnitude,
        maxMagnitudeDate=data.maxMagnitudeDate,
        link=getattr(data, "link", ""),
    )


def textSite(site, minLatitude, visibilityWindowName=None):
    try:
        vis = load_visibility_windows()
        if visibilityWindowName and visibilityWindowName in vis:
            cfg = vis.get(visibilityWindowName, {})
            return i18n._("Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Window: minAlt {minAlt:.1f}º maxAlt {maxAlt:.1f}º minAz {minAz:.1f}º maxAz {maxAz:.1f}º").format(
                lon=site.lon.value,
                lat=site.lat.value,
                height=site.height.value,
                minAlt=float(cfg.get("minAlt", 0.0)),
                maxAlt=float(cfg.get("maxAlt", 90.0)),
                minAz=float(cfg.get("minAz", 0.0)),
                maxAz=float(cfg.get("maxAz", 360.0)),
            )
    except Exception:
        pass

    return i18n._("Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Min alt {minAlt}º").format(
        lon=site.lon.value,
        lat=site.lat.value,
        height=site.height.value,
        minAlt=minLatitude,
    )


def createText(supernovas: List[Supernova], fromDate: str, observationDate: str, magnitude, site, minLatitude, visibilityWindowName=None):
    header = i18n._("Supernovae from: {fromDate} to {to}. Magnitud <= {magnitude}").format(fromDate=fromDate, to=observationDate, magnitude=magnitude)
    siteInfo = textSite(site, minLatitude, visibilityWindowName)
    print(header)
    print(siteInfo)

    for data in supernovas:
        print(textSupernova(data))


def createTextAsString(supernovas: List[Supernova], fromDate: str, observationDate: str, magnitude, site, minLatitude, visibilityWindowName=None) -> str:
    header = i18n._("Supernovae from: {fromDate} to {to}. Magnitud <= {magnitude}").format(fromDate=fromDate, to=observationDate, magnitude=magnitude)
    siteInfo = textSite(site, minLatitude, visibilityWindowName)

    fulltext = i18n._("{header}\n{siteInfo}\n\n").format(header=header, siteInfo=siteInfo)

    for data in supernovas:
        fulltext += i18n._("\n{sn}\n").format(sn=textSupernova(data))

    return fulltext


def printSupernova(data: Supernova):
    """Print a verbose supernova report to stdout (legacy helper)."""
    print("-------------------------------------------------")
    print(i18n._("Date: {date}, Mag: {mag}, T: {type}, Name: {name}").format(date=data.date, mag=data.mag, type=data.type, name=data.name))
    print(i18n._("  Const: {const}, Host: {host}").format(const=data.constellation, host=data.host))
    print(i18n._("  RA: {ra}, DECL. {decl}").format(ra=data.ra, decl=data.decl))
    print("")
    # observation time
    print(i18n._("  Observation time: {obs}").format(obs=f"{format_iso_datetime(data.visibility.azCords[0].time)} - {format_iso_datetime(data.visibility.azCords[-1].time)}"))
    print(i18n._("  Visible from : {from_} to: {to}").format(from_=format_iso_datetime(data.visibility.azCords[0].time), to=format_iso_datetime(data.visibility.azCords[-1].time)))
    print(i18n._("  AzCoords az: {az}, lat: {lat}").format(az=data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2), lat=data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2)))
    print(i18n._("  Last azCoords az: {az}, lat: {lat}").format(az=data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2), lat=data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2)))
    print("")
    print(i18n._("  Discovered: {first} , MAX Mag: {max} on: {on}").format(first=data.firstObserved, max=data.maxMagnitude, on=data.maxMagnitudeDate))
    print(" ", data.link)
    print("")


def printSupernovaShort(data: Supernova):
    """Print a compact single-line summary for the supernova."""
    print("-------------------------------------------------")
    print(i18n._("Const: {const} - {host} S: {name}, M: {mag}, T: {type}").format(const=data.constellation, host=data.host, name=data.name, mag=data.mag, type=data.type))
    print(i18n._("D: {date} RA: {ra}, DEC: {dec}").format(date=data.date, ra=data.ra, dec=data.decl))
    print(i18n._("Observation time: {from_} - {to} az: {az}, LAT: {lat}").format(from_=format_iso_datetime(data.visibility.azCords[0].time), to=format_iso_datetime(data.visibility.azCords[-1].time), az=data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2), lat=data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2)))
    print("")
