#!/usr/bin/python
# Check supernova data
#

from threading import Thread
from typing import Any
import urllib.request
import urllib.parse
import urllib.error
from bs4 import BeautifulSoup, ResultSet
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
import ssl
from datetime import datetime, timedelta
import sys
import astropy.units as u

import tkinter as tk
from tkinter import ttk

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import Color, black, blue, red


old = [
    "2023ixf",
    "2023wcr",
    "2023wrk",
    "2024akh",
    "2024ana",
    "2024axg",
    "2024bhp",
    "2024byg",
    "2024cld",
    "2024dlk",
    "2024dru",
    "2024drv",
    "2024ehs",
    "2024eys",
    "2024fjp",
    "2024gqf",
    "2024gwq",
    "2024gyr",
    "2024hcj",
    "2024iey",
    "AT2024ajf",
    "AT2024ccb",
    "AT2024cva",
    "AT2024dgr",
    "AT2024ego",
    "AT2024eqz",
    "AT2024evp",
    "AT2024fpe",
    "AT2024gfh",
    "AT2024iwq",
    "AT2025lqh",
    "Nova M31 2024-03b?",
]


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


class Supernova:
    def __init__(
        self,
        date,
        mag,
        host,
        name,
        ra,
        decl,
        link,
        constellation,
        coordinates,
        firstObserved,
        maxMagnitude,
        maxMagnitudeDate,
        type,
        visibility,
    ):
        self.name = name
        self.date = date
        self.mag = mag
        self.host = host
        self.name = name
        self.ra = ra
        self.decl = decl
        self.link = link
        self.constellation = constellation
        self.coordinates = coordinates
        self.type = type
        self.firstObserved = firstObserved
        self.maxMagnitude = maxMagnitude
        self.maxMagnitudeDate = maxMagnitudeDate
        self.visibility = visibility


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
        for dataRow in dataRows:
            if dataRow.contents[0].name == "td":
                mag = dataRow.contents[5].contents[0]
                date = dataRow.contents[6].contents[0]
                dateToCompare = date.replace("/", "-")
                fromDateToCompare = fromDate.replace("/", "-")

                if mag < maxMag and dateToCompare > fromDateToCompare:
                    ra = dataRow.contents[2].contents[0]
                    decl = dataRow.contents[3].contents[0]
                    name = dataRow.contents[0].contents[0].contents[0]
                    host = dataRow.contents[1].contents[0]
                    coord = SkyCoord(ra, decl, frame="icrs", unit=(u.hourangle, u.deg))

                    visibility = getVisibility(
                        site, coord, time1, time2, minAlt, maxAlt, minAz, maxAz
                    )

                    if visibility.visible and name not in old:

                        constellation = coord.get_constellation()
                        firstObserved = dataRow.contents[11].contents[0]
                        maxMagnitudeDate = dataRow.contents[10].contents[0]
                        maxMagnitude = dataRow.contents[9].contents[0]
                        type = dataRow.contents[7].contents[0]

                        link = (
                            "https://www.rochesterastronomy.org/"
                            + dataRow.contents[0].contents[0].get("href")[3:]
                        )
                        data = Supernova(
                            date,
                            mag,
                            host,
                            name,
                            ra,
                            decl,
                            link,
                            constellation,
                            coord,
                            firstObserved,
                            maxMagnitude,
                            maxMagnitudeDate,
                            type,
                            visibility,
                        )

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
        data.visibility.azCords[0].time.strftime("%y-%m-%d %H:%M"),
        "to:",
        data.visibility.azCords[-1].time.strftime("%y-%m-%d %H:%M"),
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


class AsyncRochesterDownload(Thread):
    def __init__(self, e: SupernovaCallBackData):
        super().__init__()
        self.result = None
        # url = 'https://www.physics.purdue.edu/brightsupernovae/snimages/sndate.html'
        self.url = "https://www.rochesterastronomy.org/snimages/snactive.html"
        self.config = e

    def run(self):
        # Ignore ssl cert errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        html = urllib.request.urlopen(self.url, context=ctx).read()
        soup = BeautifulSoup(html, "html.parser")
        # Find all supernovae rows

        rows = soup("tr")
        rochesterSupernova = RochesterSupernova()
        self.result = rochesterSupernova.selectAndSortSupernovas(self.config, rows)


class SearchFilters:
    def __init__(
        self,
        magnitude: str,
        daysToSearch: int,
        observationDate: datetime,
        observationTime: str,
        observationHours: int,
        site: EarthLocation,
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
        "  Visible from :"
        + data.visibility.azCords[0].time.strftime("%y-%m-%d %H:%M")
        + "to:"
        + data.visibility.azCords[-1].time.strftime("%y-%m-%d %H:%M"),
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
        data.visibility.azCords[0].time.strftime("%y-%m-%d %H:%M"),
        "to:",
        data.visibility.azCords[-1].time.strftime("%y-%m-%d %H:%M"),
        "az:",
        data.visibility.azCords[0].coord.az.to_string(sep=" ", precision=2),
        ", LAT:",
        data.visibility.azCords[0].coord.alt.to_string(sep=" ", precision=2),
    )
    print("")


def getVisibility(site, coord, time1, time2, minAlt=0, maxAlt=90, minAz=0, maxAz=360):

    visible = False
    loopTime = time1
    azVisibles = []
    while loopTime < time2:
        altaz = coord.transform_to(AltAz(obstime=loopTime, location=site))
        loopTime = loopTime + timedelta(hours=0.5)
        if (
            altaz.alt.dms.d >= minAlt
            and altaz.alt.dms.d <= maxAlt
            and altaz.az.dms.d >= minAz
            and altaz.az.dms.d <= maxAz
        ):
            visible = True
            azVisibles.append(AxCordInTime(loopTime, altaz))

    azVisibles.sort(key=lambda x: x.time)

    return Visibility(visible, azVisibles)


def createText(
    supernovas, fromDate: str, observationDate: str, magnitude, site, minLatitude
):

    print(
        f"Supernovae from: {fromDate} to {observationDate}. Magnitud <= {magnitude}"
    )  # , 'for location ', location)
    print(
        "Site: lon: {lon:.2f} lat: {lat:.2f} height: {height:.2f}m . Min alt {minAlt}º".format(
            lon=site.lon.value,
            lat=site.lat.value,
            height=site.height.value,
            minAlt=minLatitude,
        )
    )
    print("")

    for data in supernovas:
        printSupernova(data)

    # for data in supernovas:
    #    printSupernovaShort(data)


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

    def getDataToSearch(self):

        callbackData = SupernovaCallBackData(
            self.magnitude.get(),
            self.observationDate.get(),
            self.observationTime.get(),
            self.observationDuration.get(),
            self.daysToSearch.get(),
            self.site,
            self.minLatitud.get(),
        )

        return callbackData

    def withData(self):
        if self.supernovasFound == None:
            return False
        return True

    def callbackPdfSupernovas(self, e: SupernovaCallBackData):

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "PDF")
        else:
            createPdf(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
            )

    def callbackTextSupernovas(self, e: SupernovaCallBackData):

        if not self.withData():
            self.callbackSearchSupernovasAsync(e, "TXT")
        else:
            createText(
                self.supernovasFound,
                e.fromDate,
                e.observationDate,
                e.magnitude,
                e.site,
                float(e.minLatitude),
            )

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

            if source == "PDF":
                self.pdfButton["state"] = tk.NORMAL
                self.pdfButton.invoke()
            elif source == "TXT":
                self.txtButton["state"] = tk.NORMAL
                self.txtButton.invoke()

            self.txtButton["state"] = tk.NORMAL
            self.pdfButton["state"] = tk.NORMAL
            self.searchButton["state"] = tk.NORMAL            
            self.end_progress_bar()

    def start_progress_bar(self):
        self.progressBar.grid(column=0, row=9, columnspan=2)
        self.progressBar.start()

    def end_progress_bar(self):
        self.progressBar.stop()
        self.progressBar.grid_forget()


    def callbackClearResults(self, var, index, mode):
        self.supernovasFound = None

    def __init__(self, filters):

        super().__init__()

        self.supernovasFound = None
        
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

        self.site = filters.site
        self.title("Find latest supernovae")

        window_width = 600
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

        self.labelMagnitude = ttk.Label(self, text="Max. magnitude: ").grid(
            column=0, row=0, padx=5, pady=5, sticky=tk.E
        )
        self.entryMagnitude = ttk.Entry(
            self.labelMagnitude, textvariable=self.magnitude
        )
        self.entryMagnitude.grid(column=1, row=0, padx=5, pady=5)

        self.labelDaysToSearch = ttk.Label(
            self, text="Find the n previous days: "
        ).grid(column=0, row=1, padx=5, pady=5, sticky=tk.E)
        self.entryDaysToSearch = ttk.Entry(
            self.labelDaysToSearch, textvariable=self.daysToSearch
        )
        self.entryDaysToSearch.grid(column=1, row=1, padx=5, pady=5)

        self.labelObservationDate = ttk.Label(self, text="Observation date: ").grid(
            column=0, row=2, padx=5, pady=5, sticky=tk.E
        )
        self.entryObservationDate = ttk.Entry(
            self.labelObservationDate, textvariable=self.observationDate
        )
        self.entryObservationDate.grid(column=1, row=2, padx=5, pady=5)

        self.labelInitTime = ttk.Label(
            self, text="Init time in observation date: "
        ).grid(column=0, row=3, padx=5, pady=5, sticky=tk.E)
        self.entryInitTime = ttk.Entry(
            self.labelInitTime, textvariable=self.observationTime
        )
        self.entryInitTime.grid(column=1, row=3, padx=5, pady=5)

        self.labelDuration = ttk.Label(self, text="Hours of observation: ").grid(
            column=0, row=4, padx=5, pady=5, sticky=tk.E
        )
        self.entryDuration = ttk.Entry(
            self.labelDuration, textvariable=self.observationDuration
        )
        self.entryDuration.grid(column=1, row=4, padx=5, pady=5)

        self.labelLatitud = ttk.Label(self, text="Min latitude: ").grid(
            column=0, row=5, padx=5, pady=5, sticky=tk.E
        )
        self.entryLatitud = ttk.Entry(self.labelLatitud, textvariable=self.minLatitud)
        self.entryLatitud.grid(column=1, row=5, padx=5, pady=5)

        callbackData = SupernovaCallBackData(
            self.magnitude.get(),
            self.observationDate.get(),
            self.observationTime.get(),
            self.observationDuration.get(),
            self.daysToSearch.get(),
            self.site,
            self.minLatitud.get(),
        )

        self.pdfButton = ttk.Button(
            self,
            text="PDF",
            command=lambda: self.callbackPdfSupernovas(self.getDataToSearch()),
        )
        self.pdfButton.grid(column=0, row=6, sticky=tk.E)

        self.txtButton = ttk.Button(
            self,
            text="TXT",
            command=lambda: self.callbackTextSupernovas(self.getDataToSearch()),
        )
        self.txtButton.grid(column=1, row=6, sticky=tk.W)

        self.searchButton = ttk.Button(
            self,
            text="Search",
            command=lambda: self.callbackSearchSupernovasAsync(self.getDataToSearch()),
        )
        self.searchButton.grid(column=1, row=7, sticky=tk.W)

        self.exitButton = ttk.Button(self, text="Exit", command=lambda: self.quit())
        self.exitButton.grid(column=1, row=8, padx=5, pady=5, sticky=tk.E)

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

    filters = SearchFilters(mag, daysToSearch, datetime.now(), "23:00", 5, site, 25)
    app = SupernovasApp(filters)
    app.mainloop()


if __name__ == "__main__":
    main()
