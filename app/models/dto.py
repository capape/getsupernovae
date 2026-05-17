"""Data Transfer Objects for supernova data.

Defines lightweight DTOs used for data transfer between providers and domain models.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional


@dataclass
class SupernovaDTO:
    """Data Transfer Object produced by providers.

    This mirrors the fields used by `Supernova` but is intended as a
    lightweight, provider-facing representation.
    """

    name: str
    last_observed_date: Optional[str] = None
    last_observed_date_obj: Optional[date] = None
    mag: Optional[float] = None
    host: Optional[str] = None
    ra: Optional[str] = None
    decl: Optional[str] = None
    link: Optional[str] = None
    coordinates: Optional[Any] = None
    first_observed: Optional[str] = None
    max_magnitude: Optional[str] = None
    max_magnitude_date: Optional[str] = None
    type: Optional[str] = None
    max_magnitude_date_obj: Optional[date] = None
    first_observed_obj: Optional[date] = None
