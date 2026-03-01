"""Supernova data models.

Defines core domain models for supernova observations, coordinates, and visibility data.
"""

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
    az_coords: List[AxCordInTime] = field(default_factory=list)
    # Optional aggregated summary fields (degrees)
    min_alt: Optional[float] = None
    max_alt: Optional[float] = None
    min_az: Optional[float] = None
    max_az: Optional[float] = None


@dataclass
class Supernova:
    # Keep original field order for backward compatibility with existing callers/tests
    name: str
    last_observed_date: Optional[str]
    mag: Optional[float]
    host: Optional[str]
    ra: Optional[str]
    decl: Optional[str]
    link: Optional[str]
    constellation: Optional[str]
    coordinates: Optional[SkyCoord]
    first_observed: Optional[str]
    max_magnitude: Optional[str]
    max_magnitude_date: Optional[str]
    type: Optional[str]
    visibility: Visibility
    # optional parsed date objects (kept as date for compatibility)
    max_magnitude_date_obj: Optional[date] = None
    first_observed_obj: Optional[date] = None
