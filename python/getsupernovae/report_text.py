import os
import json
from typing import List
from snmodels import Supernova
from snparser import format_iso_datetime
from snconfig import load_visibility_windows


def textSupernova(data: Supernova) -> str:
    return f"""
-------------------------------------------------
Date: {data.date}, Mag: {data.mag}, , T: {data.type}, Name:{data.name}
Const: {data.constellation}, Host:{data.host}
RA:{data.ra}, DECL.{ data.decl}

    Visible from :{format_iso_datetime(data.visibility.azCords[0].time)} to: {format_iso_datetime(data.visibility.azCords[-1].time)}
    AzCoords az:{data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2)}, lat: {data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2)}
    Last azCoords az:{data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2)}, lat: {data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2)}

  Discovered: {data.firstObserved}, MAX Mag: {data.maxMagnitude} on: {data.maxMagnitudeDate}
  {data.link}

"""


def textSite(site, minLatitude, visibilityWindowName=None):
    try:
        vis = load_visibility_windows()
        if visibilityWindowName and visibilityWindowName in vis:
            cfg = vis.get(visibilityWindowName, {})
            return "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Window: minAlt {minAlt:.1f}º maxAlt {maxAlt:.1f}º minAz {minAz:.1f}º maxAz {maxAz:.1f}º".format(
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

    return "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Min alt {minAlt}º".format(
        lon=site.lon.value,
        lat=site.lat.value,
        height=site.height.value,
        minAlt=minLatitude,
    )


def createText(supernovas: List[Supernova], fromDate: str, observationDate: str, magnitude, site, minLatitude, visibilityWindowName=None):
    header = f"""Supernovae from: {fromDate} to {observationDate}. Magnitud <= {magnitude}"""
    siteInfo = textSite(site, minLatitude, visibilityWindowName)
    print(header)
    print(siteInfo)

    for data in supernovas:
        print(textSupernova(data))


def createTextAsString(supernovas: List[Supernova], fromDate: str, observationDate: str, magnitude, site, minLatitude, visibilityWindowName=None) -> str:
    header = f"""Supernovae from: {fromDate} to {observationDate}. Magnitud <= {magnitude}"""
    siteInfo = textSite(site, minLatitude, visibilityWindowName)

    fulltext = f"""{header}
{siteInfo}

"""

    for data in supernovas:
        fulltext += f"""
        {textSupernova(data)}
    """

    return fulltext


def printSupernova(data: Supernova):
    """Print a verbose supernova report to stdout (legacy helper)."""
    print("-------------------------------------------------")
    print(
        "Date:", data.date, ", Mag:", data.mag, ", T: ", data.type, ", Name:", data.name
    )
    print("  Const:", data.constellation, ", Host:", data.host)
    print("  RA:", data.ra, ", DECL.", data.decl)
    print("")
    print(
        "  Visible from :",
        format_iso_datetime(data.visibility.azCords[0].time),
        "to:",
        format_iso_datetime(data.visibility.azCords[-1].time),
    )
    print(
        "  AzCoords az:",
        data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2),
        ", lat:",
        data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
    )
    print(
        "  Last azCoords az:",
        data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2),
        ", lat:",
        data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2),
    )
    print("")
    print(
        "  Discovered:",
        data.firstObserved,
        ", MAX Mag:",
        data.maxMagnitude,
        "on: ",
        data.maxMagnitudeDate,
    )
    print(" ", data.link)
    print("")


def printSupernovaShort(data: Supernova):
    """Print a compact single-line summary for the supernova."""
    print("-------------------------------------------------")
    print(
        "Const:",
        data.constellation,
        "-",
        data.host,
        " S: ",
        data.name,
        ", M:",
        data.mag,
        ", T: ",
        data.type,
    )
    print("D: ", data.date, " RA:", data.ra, ", DEC:", data.decl)
    print(
        "Visible from :",
        format_iso_datetime(data.visibility.azCords[0].time),
        "to:",
        format_iso_datetime(data.visibility.azCords[-1].time),
        "az:",
        data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2),
        ", LAT:",
        data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
    )
    print("")
