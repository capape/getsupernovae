from dataclasses import dataclass, field
from datetime import date
from typing import Any, List, Optional

from astropy.coordinates import SkyCoord
from astropy.time import Time


@dataclass
class AxCordInTime:
    """A sampled coordinate at a specific time (used for visibility traces)."""

    time: Time
    coord: Any  # typically an AltAz object with .alt/.az attributes


@dataclass
class Visibility:
    """Visibility metadata for a target: list of `AxCordInTime` samples."""

    visible: bool
    azCords: List[AxCordInTime] = field(default_factory=list)
    # Optional aggregated summary fields (degrees)
    minAlt: Optional[float] = None
    maxAlt: Optional[float] = None
    minAz: Optional[float] = None
    maxAz: Optional[float] = None


@dataclass
class Supernova:
    # Keep original field order for backward compatibility with existing callers/tests
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
    # optional parsed date objects (kept as date for compatibility)
    maxMagnitudeDate_obj: Optional[date] = None
    firstObserved_obj: Optional[date] = None
