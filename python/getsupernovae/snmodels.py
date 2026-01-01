from dataclasses import dataclass
from typing import Optional
from astropy.coordinates import SkyCoord
from datetime import date


class AxCordInTime:
    def __init__(self, time, coord):
        self.time = time
        self.coord = coord


class Visibility:
    def __init__(self, visible, azCords):
        self.visible = visible
        self.azCords = azCords


@dataclass
class Supernova:
    name: str
    date: Optional[str]
    mag: Optional[float]
    host: Optional[str]
    ra: Optional[str]
    decl: Optional[str]
    link: Optional[str]
    constellation: Optional[str]
    coordinates: Optional[SkyCoord]
    firstObserved: Optional[str]
    maxMagnitude: Optional[str]
    maxMagnitudeDate: Optional[str]
    type: Optional[str]
    visibility: Visibility
    # optional parsed date objects
    maxMagnitudeDate_obj: Optional[date] = None
    firstObserved_obj: Optional[date] = None
