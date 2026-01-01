#!/usr/bin/python
# Check supernova data
#

from threading import Thread
from typing import Any
import urllib.request
import urllib.parse
import urllib.error
from bs4 import BeautifulSoup, ResultSet, Tag
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
import ssl
from datetime import datetime, date, timedelta
import sys
import astropy.units as u
import re

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import Color, black, blue, red
from collections import OrderedDict
import os
import json
# local modules extracted for clarity
from snmodels import Supernova, AxCordInTime, Visibility
from snparser import parse_magnitude, parse_date, format_iso_datetime, _parse_row_safe
from snvisibility import VisibilityWindow


def load_old_supernovae(path=None):
    """Load old supernova names from a file (one per line). If the file
    is missing, returns an empty list."""
    # Try a set of candidate config locations (XDG, macOS, Windows, package dir)
    candidates = []
    if path:
        candidates.append(path)
    # XDG config
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(os.path.join(xdg, "getsupernovae", "old_supernovae.txt"))
    else:
        candidates.append(os.path.expanduser("~/.config/getsupernovae/old_supernovae.txt"))
    # macOS
    candidates.append(os.path.expanduser("~/Library/Application Support/getsupernovae/old_supernovae.txt"))
    # Windows APPDATA
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "getsupernovae", "old_supernovae.txt"))
    # finally, package-local file
    candidates.append(os.path.join(os.path.dirname(__file__), "old_supernovae.txt"))

    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                lines = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
            return lines
        except Exception:
            continue

    return []


def load_sites(path=None):
    """Load observing sites from a JSON file and return an OrderedDict of
    name -> EarthLocation. If the file is missing or invalid, fall back to
    built-in defaults."""
    defaults = OrderedDict(
        [
            ("Sabadell", {"lat": 41.55, "lon": 2.09, "height": 224}),
            ("Sant Quirze", {"lat": 41.32, "lon": 2.04, "height": 196}),
            ("Requena", {"lat": 39.45, "lon": -1.21, "height": 587}),
        ]
    )

    # Candidate config locations in order: explicit path, XDG, macOS, Windows, package-local
    candidates = []
    if path:
        candidates.append(path)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(os.path.join(xdg, "getsupernovae", "sites.json"))
    else:
        candidates.append(os.path.expanduser("~/.config/getsupernovae/sites.json"))
    candidates.append(os.path.expanduser("~/Library/Application Support/getsupernovae/sites.json"))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "getsupernovae", "sites.json"))
    candidates.append(os.path.join(os.path.dirname(__file__), "sites.json"))

    sites_conf = None
    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                sites_conf = json.load(fh)
            # stop at first successful load
            break
        except Exception:
            sites_conf = None
            continue

    result = OrderedDict()
    source = sites_conf if isinstance(sites_conf, dict) else defaults
    for name, info in source.items():
        try:
            lat = info.get("lat")
            lon = info.get("lon")
            height = info.get("height", 0)
            result[name] = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=height * u.m)
        except Exception:
            # skip invalid entries
            continue

    # Ensure there's at least a default site named 'Sabadell'
    if "Sabadell" not in result:
        result["Sabadell"] = EarthLocation(lat=41.55 * u.deg, lon=2.09 * u.deg, height=224 * u.m)

    return result


def get_user_config_dir() -> str:
    """Return the user config directory for getsupernovae depending on platform.

    Order: $XDG_CONFIG_HOME/getsupernovae, macOS ~/Library/Application Support/getsupernovae,
    Windows %APPDATA%\\getsupernovae, fallback ~/.config/getsupernovae
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "getsupernovae")

    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/getsupernovae")

    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "getsupernovae")

    return os.path.expanduser("~/.config/getsupernovae")


def bootstrap_config():
    """Create user config dir and write default config files if missing."""
    cfg = get_user_config_dir()
    try:
        os.makedirs(cfg, exist_ok=True)
    except Exception:
        return

    sites_path = os.path.join(cfg, "sites.json")
    old_path = os.path.join(cfg, "old_supernovae.txt")

    # default sites
    default_sites = {
        "Sabadell": {"lat": 41.55, "lon": 2.09, "height": 224}
    }

    # default old list
    default_old = [       
    ]

    try:
        if not os.path.exists(sites_path):
            with open(sites_path, "w", encoding="utf-8") as fh:
                json.dump(default_sites, fh, indent=2)
    except Exception:
        pass

    try:
        if not os.path.exists(old_path):
            with open(old_path, "w", encoding="utf-8") as fh:
                for name in default_old:
                    fh.write(name + "\n")
    except Exception:
        pass


# Ensure user config exists (bootstrap) then load configuration files
bootstrap_config()
old = load_old_supernovae()
sites = load_sites()

class SupernovaCallBackData:
    def __init__(
        self,
        magnitude,
        observationDate,
        observationTime,
        observationHours,
        daysToSearch,
        site,
        minLatitude,
    ):

        self.magnitude = magnitude
        self.observationDate = observationDate
        self.observationTime = observationTime
        self.observationHours = observationHours
        self.daysToSearch = daysToSearch
        self.site = site
        self.minLatitude = minLatitude
        self.observationStart = Time(observationDate + "T" + observationTime + "Z")
        self.fromDateTime = self.observationStart - timedelta(days=int(daysToSearch))
        self.fromDate = self.fromDateTime.strftime("%Y-%m-%d")


# `Supernova`, `AxCordInTime`, and `Visibility` moved to `snmodels.py`.
# See `snmodels.py` for the dataclass definitions used by the app.


class RochesterSupernova:

    def selectAndSortSupernovas(
        self, e: SupernovaCallBackData, dataRows: ResultSet[Any]
    ):

        supernovas = self.selectSupernovas(
            dataRows,
            e.magnitude,
            e.observationStart,
            e.observationTime,
            int(e.observationHours),
            e.fromDate,
            e.site,
            float(e.minLatitude),
        )

        supernovas.sort(key=lambda x: x.visibility.azCords[-1].time)
        supernovas.sort(key=lambda x: x.visibility.azCords[0].time)

        return supernovas

    def selectSupernovas(
        self,
        dataRows: ResultSet[Any],
        maxMag: str,
        observationDay: datetime,
        localStartTime: str,
        hoursObservation: int,
        fromDate: str,
        site: EarthLocation,
        minAlt: float = 0,
        maxAlt: float = 90,
        minAz: float = 0,
        maxAz: float = 360,
    ):

        observationStart = (
            observationDay.strftime("%Y-%m-%d") + "T" + localStartTime + "Z"
        )

        time1 = Time(observationStart)
        time2 = time1 + timedelta(hours=hoursObservation)

        supernovas = []
        # parse fromDate string to a date object for reliable comparisons
        try:
            from_date_obj = parse_date(fromDate)[0]
        except Exception:
            from_date_obj = None
        for dataRow in dataRows:
            parsed = _parse_row_safe(dataRow)
            if not parsed:
                continue

            # numeric comparison (ensure maxMag param is numeric)
            try:
                max_mag_threshold = float(maxMag)
            except Exception:
                max_mag_threshold = float(str(maxMag))

            if parsed["mag"] > max_mag_threshold:
                continue

            # if parsed date failed to parse, skip
            if parsed.get("date_obj") is None:
                continue

            if from_date_obj is not None and parsed["date_obj"] <= from_date_obj:
                continue

            visibility = VisibilityWindow(minAlt, maxAlt, minAz, maxAz).getVisibility(
                site, parsed["coord"], time1, time2)

            if visibility.visible and parsed["name"] not in old:
                data = Supernova(
                    parsed["date"],
                    str(parsed["mag"]),
                    parsed["host"],
                    parsed["name"],
                    parsed["ra"],
                    parsed["decl"],
                    parsed["link"] or "",
                    parsed["coord"].get_constellation(),
                    parsed["coord"],
                    parsed["firstObserved"],
                    parsed["maxMagnitude"],
                    parsed["maxMagnitudeDate"],
                    parsed["type"],
                    visibility,
                )
                # attach parsed date objects for downstream use
                try:
                    data.maxMagnitudeDate_obj = parsed.get("maxMagnitudeDate_obj")
                    data.firstObserved_obj = parsed.get("firstObserved_obj")
                except Exception:
                    pass
                supernovas.append(data)

        return supernovas


class AxCordInTime:
    def __init__(self, time, coord):
        self.time = time
        self.coord = coord


class Visibility:
    def __init__(self, visible, azCords):
        self.visible = visible
        self.azCords = azCords


def printSupernova(data):
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


def textSupernova(data):
    
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

class AsyncRochesterDownload(Thread):
    def __init__(self, e: SupernovaCallBackData):
        super().__init__()
        self.result = None
        self.error = None
        # url = 'https://www.physics.purdue.edu/brightsupernovae/snimages/sndate.html'
        self.url = "https://www.rochesterastronomy.org/snimages/snactive.html"
        self.config = e

    def run(self):
        try:
            # Ignore ssl cert errors for now (legacy behaviour)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            html = urllib.request.urlopen(self.url, context=ctx, timeout=20).read()
            soup = BeautifulSoup(html, "html.parser")
            # Find all supernovae rows
            rows = soup("tr")
            rochesterSupernova = RochesterSupernova()
            self.result = rochesterSupernova.selectAndSortSupernovas(self.config, rows)
            # keep raw rows so the app can re-filter without re-downloading
            self.raw_rows = rows
        except Exception as ex:
            # record the error for the main thread to show
            try:
                self.error = str(ex)
            except Exception:
                self.error = "unknown error"
            self.result = None


class SearchFilters:
    def __init__(
        self,
        magnitude: str,
        daysToSearch: int,
        observationDate: datetime,
        observationTime: str,
        observationHours: int,
        site: str,
        minLatitude: float,
    ):
        self.magnitude = magnitude
        self.daysToSearch = daysToSearch
        self.observationDate = observationDate
        self.observationTime = observationTime
        self.observationHours = observationHours
        self.site = site
        self.minLatitude = minLatitude


def addSupernovaToPdf(textObject, data):

    lines = [
        "-------------------------------------------------",
        "Date:"
        + data.date
        + ", Mag:"
        + data.mag
        + ", T: "
        + data.type
        + " Name:"
        + data.name,
        "  Const:" + data.constellation + ", Host:" + data.host,
        "  RA:" + data.ra + ", DECL." + data.decl,
        "",
        "  Visible from :" + format_iso_datetime(data.visibility.azCords[0].time)
        + " to: "
        + format_iso_datetime(data.visibility.azCords[-1].time),
        "  AzCoords az:"
        + data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2)
        + ", lat:"
        + data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
        "  Last azCoords az:"
        + data.visibility.azCords[-1].coord.az.to_string(sep=" ", precision=2)
        + ", lat:"
        + data.visibility.azCords[-1].coord.alt.to_string(sep=" ", precision=2),
        "",
        "  Discovered:"
        + data.firstObserved
        + " MAX Mag:"
        + data.maxMagnitude
        + " on: "
        + data.maxMagnitudeDate,
        " " + data.link,
        "",
    ]

    for line in lines:
        textObject.textLine(line)

    textObject.textLine("")


def printSupernovaShort(data):
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


def createText(
    supernovas, fromDate: str, observationDate: str, magnitude, site, minLatitude
):

    header = f"""Supernovae from: {fromDate} to {observationDate}. Magnitud <= {magnitude}"""
    siteInfo = textSite(site, minLatitude)
    print(header)
    print(siteInfo)        

    for data in supernovas:
        print(textSupernova(data))


    # for data in supernovas:
    #    printSupernovaShort(data)


def textSite(site, minLatitude):
    return "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Min alt {minAlt}º".format(
            lon=site.lon.value,
            lat=site.lat.value,
            height=site.height.value,
            minAlt=minLatitude,
        )


def createTextAsString(
    supernovas, fromDate: str, observationDate: str, magnitude, site, minLatitude
):

    header = f"""Supernovae from: {fromDate} to {observationDate}. Magnitud <= {magnitude}"""
    siteInfo = textSite(site, minLatitude)
    
    fulltext = f"""{header}
{siteInfo}

"""

    for data in supernovas:
        fulltext += f"""
        {textSupernova(data)}
    """
        
    return fulltext

# parsing helpers extracted to `snparser.py` (parse_magnitude, parse_date,
# format_iso_datetime, _parse_row_safe)

def createPdf(
    supernovas, fromDate: str, observationDate: str, magnitude, site, minLatitude
):

    pdfName = observationDate + ".pdf"

    fontsize = 10
    marginx = 1.0 * cm
    margintop = 1.0 * cm
    marginbotton = 1.0 * cm

    topy = 29.7 * cm - margintop

    canvas = Canvas(pdfName, pagesize=A4)
    canvas.setFont("Courier", fontsize)
    canvas.setFillColor(black)

    textObject = canvas.beginText()
    textObject.setTextOrigin(marginx, topy)
    textObject.setFont("Courier", fontsize)

    supernovasAdded = 0
    totalSize = 0
    createPage = True
    estimatedSupernovasSize = 0
    # print(f"previousPosy: {previousPosy}, posy: {posy}, totalsize: {totalSize}, estimated:{estimatedSupernovasSize}, supernovasAdded:{supernovasAdded}")
    textObject.textLine(
        f"Supernovae from: {fromDate} to {observationDate}. Magnitud <= { magnitude}"
    )
    textObject.textLine(
        f"Site: lon: {site.lon.value:.2f} lat: {site.lat.value:.2f} height: {site.height.value:.2f}m . Min alt {minLatitude}º"
    )
    textObject.textLine("")
    posy = textObject.getY()
    previousPosy = posy

    for data in supernovas:
        addSupernovaToPdf(textObject, data)
        canvas.drawText(textObject)

        previousPosy = posy
        posy = textObject.getY()
        supernovasAdded = supernovasAdded + 1
        totalSize = totalSize + (previousPosy - posy)
        estimatedSupernovasSize = totalSize / supernovasAdded
        createPage = posy < (estimatedSupernovasSize + margintop)
        # print(f"previousPosy: {previousPosy}, posy: {posy}, totalsize: {totalSize}, estimated:{estimatedSupernovasSize}, supernovasAdded:{supernovasAdded}")

        if createPage:
            canvas.showPage()
            textObject = canvas.beginText()
            textObject.setTextOrigin(marginx, topy)
            posy = textObject.getY()
            textObject.setFont("Courier", fontsize)
            canvas.setFont("Courier", fontsize)
            canvas.setFillColor(black)

    canvas.save()


class SupernovasApp(tk.Tk):

    #
    # Create object with filters to search
    #    
    def getDataToSearch(self):
        
        callbackData = SupernovaCallBackData(
            self.magnitude.get(),
            self.observationDate.get(),
            self.observationTime.get(),
            self.observationDuration.get(),
            self.daysToSearch.get(),
            sites[self.site.get()],
            self.minLatitud.get(),
        )

        return callbackData

    #
    # Check if there is already a search done with current filters
    #
    def withData(self):
        if self.supernovasFound == None:
            return False
        return True
    
    
    #    
    # PDF button callback
    #
    def callbackPdfSupernovas(self, e: SupernovaCallBackData):

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "PDF")
        else:
            datatxt = createTextAsString(self.supernovasFound, e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude))
            self.set_results_text(datatxt)

            createPdf(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
            )

    #    
    # TXT button callback
    #
    def callbackTextSupernovas(self, e: SupernovaCallBackData):

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "TXT")
        else:
            datatxt = createTextAsString(self.supernovasFound, e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude))
            self.set_results_text(datatxt)
            createText(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
            )
    #    
    #  Refresh button callback
    #
    def callbackRefreshSearchSupernovas(self, e: SupernovaCallBackData):

        # If a refresh isn't already running, start an async refresh.
        # If we are already refreshing, ignore the extra click. If there
        # are cached results, they will be updated once the running
        # refresh completes and `monitor` finishes.
        if not self.refreshing:
            self.refreshing = True
            # disable the refresh button (searchButton) while refresh is running
            try:
                self.searchButton["state"] = tk.DISABLED
            except Exception:
                pass
            self.callbackSearchSupernovasAsync(e, "REFRESH")
        else:
            # Already refreshing: do nothing (avoid using None results).
            return
        
            
    #
    # Do a async search
    #
    def callbackSearchSupernovasAsync(self, e: SupernovaCallBackData, source="SEARCH"):

        self.txtButton["state"] = tk.DISABLED
        self.pdfButton["state"] = tk.DISABLED
        self.searchButton["state"] = tk.DISABLED
        
        self.start_progress_bar()

        download_thread = AsyncRochesterDownload(e)
        download_thread.start()

        self.monitor(download_thread, source)

    def monitor(self, thread, source="SEARCH"):
        if thread.is_alive():
            # check the thread every 100ms
            self.after(100, lambda: self.monitor(thread, source))
        else:

            self.supernovasFound = thread.result

            # If download/parsing failed, show an error banner in the results
            if self.supernovasFound is None:
                err = getattr(thread, "error", None)
                if err:
                    self.set_results_text(f"ERROR: Failed to fetch/parse data - {err}")
                else:
                    self.set_results_text("ERROR: Failed to fetch data (no details)")

            if source == "PDF":
                try:
                    self.pdfButton["state"] = tk.NORMAL
                    self.pdfButton.invoke()
                except Exception:
                    pass
                # ensure other controls are re-enabled after PDF generation
                try:
                    self.txtButton["state"] = tk.NORMAL
                except Exception:
                    pass
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    pass
            elif source == "TXT":
                try:
                    self.txtButton["state"] = tk.NORMAL
                    self.txtButton.invoke()
                except Exception:
                    pass
                # ensure other controls are re-enabled after text output
                try:
                    self.pdfButton["state"] = tk.NORMAL
                except Exception:
                    pass
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    pass
            elif source == "REFRESH":
                self.txtButton["state"] = tk.NORMAL
                self.txtButton.invoke()
                # refresh completed
                self.refreshing = False
                self.txtButton["state"] = tk.NORMAL
                self.pdfButton["state"] = tk.NORMAL
                self.searchButton["state"] = tk.NORMAL            
                # cache raw rows if available for later re-filtering
                try:
                    self.last_rows = getattr(thread, "raw_rows", None)
                except Exception:
                    self.last_rows = None
            self.end_progress_bar()

    def start_progress_bar(self):
        self.progressBar.grid(column=0, row=9, columnspan=2)
        self.progressBar.start()

    def end_progress_bar(self):
        self.progressBar.stop()
        self.progressBar.grid_forget()


    def callbackClearResults(self, var, index, mode):
        self.supernovasFound = None

    def set_results_text(self, datatxt: str):
        """Helper to update the results Text widget safely and consistently."""
        try:
            self.textResults['state'] = 'normal'
            self.textResults.delete('1.0', 'end')
            self.textResults.insert('1.0', datatxt)
            self.textResults['state'] = 'disabled'
        except Exception:
            # Best-effort: ignore GUI errors to avoid crashing background operations
            pass

    def refilter_from_cache(self, source="REFRESH"):
        """Re-run selection/filtering on the cached HTML rows (if available).

        If no cached rows exist, fall back to performing a normal async download.
        """
        if not hasattr(self, "last_rows") or self.last_rows is None:
            # fallback to full download
            try:
                self.refreshing = True
                self.callbackSearchSupernovasAsync(self.getDataToSearch(), source)
            except Exception:
                pass
            return

        try:
            rochester = RochesterSupernova()
            # compute with current filters
            new_results = rochester.selectAndSortSupernovas(self.getDataToSearch(), self.last_rows)
            self.supernovasFound = new_results

            # show results according to source
            if source == "PDF":
                try:
                    self.pdfButton["state"] = tk.NORMAL
                    self.pdfButton.invoke()
                except Exception:
                    pass
                try:
                    self.txtButton["state"] = tk.NORMAL
                except Exception:
                    pass
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    pass
            else:
                # default to text output for SEARCH/TXT/REFRESH
                try:
                    self.txtButton["state"] = tk.NORMAL
                    self.txtButton.invoke()
                except Exception:
                    pass
                try:
                    self.pdfButton["state"] = tk.NORMAL
                except Exception:
                    pass
                try:
                    self.searchButton["state"] = tk.NORMAL
                except Exception:
                    pass
        except Exception:
            # If re-filter fails, fall back to network refresh
            try:
                self.refreshing = True
                self.callbackSearchSupernovasAsync(self.getDataToSearch(), source)
            except Exception:
                pass

    def callbackIgnoreSelectedSN(self):
        """Add the currently selected SN from the Results text area to the
        user's `old_supernovae.txt`, sorting and deduplicating the file.
        """
        # get selection
        try:
            sel = self.textResults.get("sel.first", "sel.last").strip()
        except Exception:
            sel = ""

        if not sel:
            messagebox.showinfo("No selection", "No text selected in the Results pane.")
            return

        # extract SN-like token
        m = re.search(r"\bSN[-A-Za-z0-9_]+\b", sel, re.IGNORECASE)
        if m:
            name = m.group(0)
        else:
            name = sel.split()[0]

        # determine path
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except Exception:
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # read existing
        existing = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                existing = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
        except Exception:
            existing = []

        if name in existing:
            messagebox.showinfo("Already present", f"{name} is already ignored.")
            return

        existing.append(name)
        unique_sorted = sorted(set(existing), key=lambda s: s.lower())

        try:
            with open(path, "w", encoding="utf-8") as fh:
                for ln in unique_sorted:
                    fh.write(ln + "\n")
            # reload global old list
            try:
                global old
                old = load_old_supernovae(path)
            except Exception:
                pass
            messagebox.showinfo("Added", f"Added {name} to ignored supernovae.")
            # Auto-reload results using cached rows when possible
            try:
                self.refilter_from_cache("REFRESH")
            except Exception:
                # fallback to network refresh
                try:
                    self.refreshing = True
                    self.callbackSearchSupernovasAsync(self.getDataToSearch(), "REFRESH")
                except Exception:
                    pass
        except Exception as ex:
            messagebox.showerror("Save error", f"Failed to update ignore file: {ex}")

    def callbackEditOldSupernovae(self):
        """Open a simple dialog to edit the user's `old_supernovae.txt` file.

        The editor writes to the user config directory returned by
        `get_user_config_dir()` and updates the global `old` list when saved.
        """
        try:
            cfgdir = get_user_config_dir()
            os.makedirs(cfgdir, exist_ok=True)
            path = os.path.join(cfgdir, "old_supernovae.txt")
        except Exception:
            # fallback to package-local file if user config dir can't be used
            path = os.path.join(os.path.dirname(__file__), "old_supernovae.txt")

        # Load current contents (preserve comments and blank lines minimally)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                current = fh.read()
        except Exception:
            current = "" if old is None else "\n".join(old)

        # Create editor window
        editor = tk.Toplevel(self)
        editor.title("Edit ignored/old supernovae")
        editor.geometry("600x400")

        txt = tk.Text(editor, wrap="none")
        txt.grid(column=0, row=0, columnspan=3, sticky="nsew")
        txt.insert("1.0", current)

        # Add simple save and close buttons
        def do_save():
            content = txt.get("1.0", "end").strip()
            try:
                # Normalize: keep only non-empty, non-comment lines
                lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
                # Deduplicate and sort (case-insensitive sort)
                unique_sorted = sorted(set(lines), key=lambda s: s.lower())
                with open(path, "w", encoding="utf-8") as fh:
                    for ln in unique_sorted:
                        fh.write(ln + "\n")
                # update global old list so the running app respects changes
                try:
                    global old
                    old = load_old_supernovae(path)
                except Exception:
                    pass
                editor.destroy()
                # Auto-reload results using cached rows when possible
                try:
                    self.refilter_from_cache("REFRESH")
                except Exception:
                    try:
                        self.refreshing = True
                        self.callbackSearchSupernovasAsync(self.getDataToSearch(), "REFRESH")
                    except Exception:
                        pass
            except Exception as ex:
                messagebox.showerror("Save error", f"Failed to save file: {ex}")

        def do_close():
            editor.destroy()

        save_btn = ttk.Button(editor, text="Save", command=do_save)
        save_btn.grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        close_btn = ttk.Button(editor, text="Close", command=do_close)
        close_btn.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        # allow the text widget and buttons to expand
        editor.grid_rowconfigure(0, weight=1)
        editor.grid_columnconfigure(0, weight=1)

    def __init__(self, filters):

        super().__init__()

        self.supernovasFound = None
        self.refreshing = False
        
        self.magnitude = tk.StringVar()
        self.magnitude.trace_add(["write", "unset"], self.callbackClearResults)
        
        self.daysToSearch = tk.StringVar()
        self.daysToSearch.trace_add(["write", "unset"], self.callbackClearResults)
        
        self.observationDate = tk.StringVar()
        self.observationDate.trace_add(["write", "unset"], self.callbackClearResults)
        
        self.observationDuration = tk.StringVar()
        self.observationDuration.trace_add(["write", "unset"], self.callbackClearResults)
        
        self.minLatitud = tk.StringVar()
        self.minLatitud.trace_add(["write", "unset"], self.callbackClearResults)
        
        self.observationTime = tk.StringVar()
        self.observationTime.trace_add(["write", "unset"], self.callbackClearResults)

        self.site = tk.StringVar()
        self.site.trace_add(["write", "unset"], self.callbackClearResults)

        self.results = tk.StringVar()
        self.results.trace_add(["write", "unset"], self.callbackClearResults)
        

        self.title("Find latest supernovae")

        window_width = 1400
        window_height = 600

        # get the screen dimension
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # find the center point
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        # set the position of the window to the center of the screen
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        self.magnitude.set(filters.magnitude)
        self.daysToSearch.set(filters.daysToSearch)
        self.observationDate.set(filters.observationDate.strftime("%Y-%m-%d"))
        self.observationTime.set(filters.observationTime)
        self.observationDuration.set(filters.observationHours)
        self.minLatitud.set(filters.minLatitude)
        self.site.set(filters.site)
        self.results.set("")

        # Labels and entries: create widgets first, then grid them.
        self.labelMagnitude = ttk.Label(self, text="Max. magnitude: ")
        self.labelMagnitude.grid(column=0, row=0, padx=5, pady=5, sticky=tk.E)
        self.entryMagnitude = ttk.Entry(self, textvariable=self.magnitude)
        self.entryMagnitude.grid(column=1, row=0, padx=5, pady=5)

        self.labelDaysToSearch = ttk.Label(self, text="Find the n previous days: ")
        self.labelDaysToSearch.grid(column=0, row=1, padx=5, pady=5, sticky=tk.E)
        self.entryDaysToSearch = ttk.Entry(self, textvariable=self.daysToSearch)
        self.entryDaysToSearch.grid(column=1, row=1, padx=5, pady=5)

        self.labelObservationDate = ttk.Label(self, text="Observation date: ")
        self.labelObservationDate.grid(column=0, row=2, padx=5, pady=5, sticky=tk.E)
        self.entryObservationDate = ttk.Entry(self, textvariable=self.observationDate)
        self.entryObservationDate.grid(column=1, row=2, padx=5, pady=5)

        self.labelInitTime = ttk.Label(self, text="Init time in observation date: ")
        self.labelInitTime.grid(column=0, row=3, padx=5, pady=5, sticky=tk.E)
        self.entryInitTime = ttk.Entry(self, textvariable=self.observationTime)
        self.entryInitTime.grid(column=1, row=3, padx=5, pady=5)

        self.labelDuration = ttk.Label(self, text="Hours of observation: ")
        self.labelDuration.grid(column=0, row=4, padx=5, pady=5, sticky=tk.E)
        self.entryDuration = ttk.Entry(self, textvariable=self.observationDuration)
        self.entryDuration.grid(column=1, row=4, padx=5, pady=5)

        self.labelLatitud = ttk.Label(self, text="Min latitude: ")
        self.labelLatitud.grid(column=0, row=5, padx=5, pady=5, sticky=tk.E)
        self.entryLatitud = ttk.Entry(self, textvariable=self.minLatitud)
        self.entryLatitud.grid(column=1, row=5, padx=5, pady=5)

        self.labelSite = ttk.Label(self, text="Site: ")
        self.labelSite.grid(column=0, row=6, padx=5, pady=5, sticky=tk.E)

        siteValues = list(sites.keys())
        self.cbSite = ttk.Combobox(self, values=siteValues, textvariable=self.site)
        self.cbSite.grid(column=1, row=6, padx=5, pady=5)

        self.labelResults = ttk.Label(self, text="Results: ")
        self.labelResults.grid(column=3, row=0, padx=5, pady=5, sticky=tk.W)
        self.textResults = tk.Text(self, width = 70, height = 10)
        self.textResults.grid(column = 3, row=1, rowspan=7)        
        self.textResults['state']='normal'
        # Make results column expandable so we can align buttons nicely
        try:
            self.grid_columnconfigure(3, weight=1)
        except Exception:
            pass

        # Toolbar frame to hold action buttons for the Results pane
        toolbar = ttk.Frame(self)
        toolbar.grid(column=3, row=8, columnspan=2, padx=5, pady=5, sticky="ew")
        # allow the left cell to expand so the right button aligns to the window edge
        try:
            toolbar.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        # Button to ignore a selected SN from the Results pane (left)
        self.ignoreSelectedButton = ttk.Button(
            toolbar, text="Ignore selected SN", command=lambda: self.callbackIgnoreSelectedSN()
        )
        self.ignoreSelectedButton.grid(column=0, row=0, sticky=tk.W)

        # Button to edit ignored SN (right-aligned in the toolbar)
        self.editOldButton = ttk.Button(
            toolbar, text="Edit Ignored SN", command=lambda: self.callbackEditOldSupernovae()
        )
        self.editOldButton.grid(column=1, row=0, sticky=tk.E)
        
        callbackData = SupernovaCallBackData(
            self.magnitude.get(),
            self.observationDate.get(),
            self.observationTime.get(),
            self.observationDuration.get(),
            self.daysToSearch.get(),
            self.site.get(),
            self.minLatitud.get(),
        )

        self.pdfButton = ttk.Button(
            self,
            text="PDF",
            command=lambda: self.callbackPdfSupernovas(self.getDataToSearch()),
        )
        self.pdfButton.grid(column=0, row=7, sticky=tk.E)

        self.txtButton = ttk.Button(
            self,
            text="TXT",
            command=lambda: self.callbackTextSupernovas(self.getDataToSearch()),
        )
        self.txtButton.grid(column=1, row=7, sticky=tk.W)

        self.searchButton = ttk.Button(
            self,
            text="Refresh Search",
            command=lambda: self.callbackRefreshSearchSupernovas(self.getDataToSearch()),
        )
        self.searchButton.grid(column=1, row=8, sticky=tk.W)

        self.exitButton = ttk.Button(self, text="Exit", command=lambda: self.quit())
        self.exitButton.grid(column=1, row=11, padx=5, pady=5, sticky=tk.E)

        # legacy placement removed; button moved next to the Results controls

        self.progressBar = ttk.Progressbar(self, mode='indeterminate', length = 400 );
       


def representsInt(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


def main():

    if len(sys.argv) > 3:
        raise ValueError("Usage: getsupernovae.py maxMag lastDays")

    mag = "17"
    daysToSearch = 21

    if len(sys.argv) == 3:
        if representsInt(sys.argv[2]):
            daysToSearch = int(sys.argv[2])
            mag = sys.argv[1]
    elif len(sys.argv) == 2:
        if representsInt(sys.argv[1]):
            mag = sys.argv[1]

    site = EarthLocation(lat=41.55 * u.deg, lon=2.09 * u.deg, height=224 * u.m)

    site = list(sites.keys())[0]
    

    filters = SearchFilters(mag, daysToSearch, datetime.now(), "23:00", 5, site, 25)
    app = SupernovasApp(filters)
    app.mainloop()



# `_parse_row_safe` is provided by `snparser.py` and imported at the top of this file.


if __name__ == "__main__":
    main()
