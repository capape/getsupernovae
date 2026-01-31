from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import date

from app.models.snmodels import Visibility


@dataclass
class SupernovaDTO:
    """Data Transfer Object produced by providers.

    This mirrors the fields used by `Supernova` but is intended as a
    lightweight, provider-facing representation.
    """
    name: str
    date: Optional[str] = None
    date_obj: Optional[date] = None
    mag: Optional[float] = None
    host: Optional[str] = None
    ra: Optional[str] = None
    decl: Optional[str] = None
    link: Optional[str] = None
    coordinates: Optional[Any] = None
    firstObserved: Optional[str] = None
    maxMagnitude: Optional[str] = None
    maxMagnitudeDate: Optional[str] = None
    type: Optional[str] = None
    maxMagnitudeDate_obj: Optional[date] = None
    firstObserved_obj: Optional[date] = None
