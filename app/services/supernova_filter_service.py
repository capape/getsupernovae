"""Supernova filtering service.

This module provides pure business logic for filtering supernovae based on
various criteria such as magnitude, date, visibility, and user-defined exclusions.
Following SOLID principles, this service has a single responsibility: filtering
supernova data without any UI dependencies.
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List, Optional, Set, Tuple
from astropy.coordinates import EarthLocation
from astropy.time import Time

from app.models.dto import SupernovaDTO
from app.models.snmodels import Supernova
from app.utils.snparser import parse_date
from app.config.ui_constants import DEFAULT_VALUES

if TYPE_CHECKING:
    from app.ui.snvisibility import Visibility


class SupernovaFilterService:
    """Pure business logic for filtering supernovae.

    This service provides methods to filter supernovae based on various criteria
    without any coupling to UI components. All methods are stateless and can be
    tested independently.
    """

    def __init__(self, visibility_factory: Optional[Callable] = None) -> None:
        """Initialize the filter service.

        Args:
            visibility_factory: Optional factory for creating visibility calculators.
                               If None, must be provided to filter_by_visibility.
        """
        self.visibility_factory = visibility_factory

    def filter_by_magnitude(
        self,
        supernovae: List[SupernovaDTO],
        max_magnitude: float
    ) -> List[SupernovaDTO]:
        """Filter supernovae by maximum magnitude.

        Args:
            supernovae: List of supernova DTOs to filter
            max_magnitude: Maximum magnitude threshold (lower is brighter)

        Returns:
            List of supernovae with magnitude <= max_magnitude
        """
        filtered: List[SupernovaDTO] = []
        for sn in supernovae:
            try:
                if sn.mag is not None and sn.mag <= max_magnitude:
                    filtered.append(sn)
            except (TypeError, ValueError):
                # Skip entries with invalid magnitude
                continue
        return filtered

    def filter_by_date_range(
        self,
        supernovae: List[SupernovaDTO],
        from_date: str
    ) -> List[SupernovaDTO]:
        """Filter supernovae discovered after a specific date.

        Args:
            supernovae: List of supernova DTOs to filter
            from_date: ISO format date string (YYYY-MM-DD)

        Returns:
            List of supernovae discovered after from_date
        """
        try:
            from_date_obj = parse_date(from_date)[0]
        except (ValueError, TypeError, AttributeError):
            # If date parsing fails, return all supernovae
            return supernovae

        if from_date_obj is None:
            return supernovae

        filtered: List[SupernovaDTO] = []
        for sn in supernovae:
            if sn.date is None:
                # Skip entries without a valid date
                continue

            if sn.date_obj is not None and sn.date_obj > from_date_obj:
                filtered.append(sn)

        return filtered

    def filter_by_exclusion_list(
        self,
        supernovae: List[SupernovaDTO],
        exclusion_list: Set[str]
    ) -> List[SupernovaDTO]:
        """Filter out supernovae that are in the exclusion list.

        Args:
            supernovae: List of supernova DTOs to filter
            exclusion_list: Set of supernova names to exclude

        Returns:
            List of supernovae not in the exclusion list
        """
        return [sn for sn in supernovae if sn.name not in exclusion_list]

    def filter_by_visibility(
        self,
        supernovae: List[SupernovaDTO],
        site: EarthLocation,
        observation_start: Time,
        observation_end: Time,
        min_altitude: float = 0.0,
        max_altitude: float = 90.0,
        min_azimuth: float = 0.0,
        max_azimuth: float = 360.0,
        visibility_factory=None
    ) -> List[Tuple[SupernovaDTO, Visibility]]:
        """Filter supernovae by visibility at observation site and time.

        Args:
            supernovae: List of supernova DTOs to filter
            site: Observer's location on Earth
            observation_start: Start time of observation window
            observation_end: End time of observation window
            min_altitude: Minimum altitude in degrees
            max_altitude: Maximum altitude in degrees
            min_azimuth: Minimum azimuth in degrees
            max_azimuth: Maximum azimuth in degrees
            visibility_factory: Optional visibility calculator factory

        Returns:
            List of tuples (supernova, visibility) for visible supernovae
        """
        factory = visibility_factory or self.visibility_factory
        if factory is None:
            raise ValueError(
                "visibility_factory must be provided either in __init__ or as parameter"
            )

        visibility_calculator = factory(min_altitude, max_altitude, min_azimuth, max_azimuth)

        visible = []
        for sn in supernovae:
            try:
                visibility = visibility_calculator.getVisibility(
                    site,
                    sn.coordinates,
                    observation_start,
                    observation_end
                )

                if visibility.visible:
                    visible.append((sn, visibility))
            except (AttributeError, TypeError, ValueError):
                # Skip supernovae with invalid coordinates or visibility calculation errors
                continue

        return visible

    def apply_all_filters(
        self,
        supernovae: List[SupernovaDTO],
        max_magnitude: float,
        from_date: str,
        exclusion_list: Set[str],
        site: EarthLocation,
        observation_start: Time,
        observation_end: Time,
        min_altitude: float = 0.0,
        max_altitude: float = 90.0,
        min_azimuth: float = 0.0,
        max_azimuth: float = 360.0,
        visibility_factory=None
    ) -> List[Tuple[SupernovaDTO, Visibility]]:
        """Apply all filters in sequence to get final visible supernovae list.

        This is a convenience method that chains all filtering operations in the
        correct order for optimal performance.

        Args:
            supernovae: List of supernova DTOs to filter
            max_magnitude: Maximum magnitude threshold
            from_date: Earliest discovery date to include
            exclusion_list: Set of supernova names to exclude
            site: Observer's location
            observation_start: Start of observation window
            observation_end: End of observation window
            min_altitude: Minimum altitude constraint
            max_altitude: Maximum altitude constraint
            min_azimuth: Minimum azimuth constraint
            max_azimuth: Maximum azimuth constraint
            visibility_factory: Optional visibility calculator factory

        Returns:
            List of tuples (supernova, visibility) that pass all filters
        """
        # Apply filters in order from cheapest to most expensive
        filtered = self.filter_by_magnitude(supernovae, max_magnitude)
        filtered = self.filter_by_date_range(filtered, from_date)
        filtered = self.filter_by_exclusion_list(filtered, exclusion_list)

        # Visibility check is most expensive, do it last
        visible = self.filter_by_visibility(
            filtered,
            site,
            observation_start,
            observation_end,
            min_altitude,
            max_altitude,
            min_azimuth,
            max_azimuth,
            visibility_factory
        )

        return visible

    def convert_to_domain_models(
        self,
        filtered_results: List[Tuple[SupernovaDTO, Visibility]]
    ) -> List[Supernova]:
        """Convert filtered DTO/Visibility pairs to domain model Supernova objects.

        Args:
            filtered_results: List of (SupernovaDTO, Visibility) tuples

        Returns:
            List of Supernova domain model objects
        """
        supernovas = []
        for sn_dto, visibility in filtered_results:
            try:
                supernova = Supernova(
                    name=sn_dto.name,
                    date=sn_dto.date,
                    mag=sn_dto.mag,
                    host=sn_dto.host,
                    ra=sn_dto.ra,
                    decl=sn_dto.decl,
                    link=sn_dto.link or "",
                    constellation=(
                        sn_dto.coordinates.get_constellation()
                        if sn_dto.coordinates
                        else "Unknown"
                    ),
                    coordinates=sn_dto.coordinates,
                    firstObserved=sn_dto.firstObserved,
                    maxMagnitude=sn_dto.maxMagnitude,
                    maxMagnitudeDate=sn_dto.maxMagnitudeDate,
                    type=sn_dto.type,
                    visibility=visibility,
                    maxMagnitudeDate_obj=sn_dto.maxMagnitudeDate_obj,
                    firstObserved_obj=sn_dto.firstObserved_obj,
                )
                supernovas.append(supernova)
            except Exception:
                # Skip entries that can't be converted
                continue

        return supernovas

    def is_bright_supernova(self, magnitude: Optional[float]) -> bool:
        """Check if a supernova is considered bright based on magnitude.

        Args:
            magnitude: Magnitude value (None if unknown)

        Returns:
            True if magnitude is below the brightness threshold
        """
        if magnitude is None:
            return False

        try:
            return float(magnitude) < DEFAULT_VALUES.BRIGHT_MAGNITUDE_THRESHOLD
        except (ValueError, TypeError):
            return False

    def sort_by_magnitude(
        self,
        supernovae: List[Supernova],
        reverse: bool = False
    ) -> List[Supernova]:
        """Sort supernovae by magnitude.

        Args:
            supernovae: List of Supernova objects to sort
            reverse: If True, sort from dimmest to brightest

        Returns:
            Sorted list of supernovae
        """
        def magnitude_key(sn: Supernova) -> float:
            try:
                return float(sn.mag) if sn.mag else float('inf')
            except (ValueError, TypeError):
                return float('inf')

        return sorted(supernovae, key=magnitude_key, reverse=reverse)

    def sort_by_date(
        self,
        supernovae: List[Supernova],
        reverse: bool = True
    ) -> List[Supernova]:
        """Sort supernovae by discovery date.

        Args:
            supernovae: List of Supernova objects to sort
            reverse: If True, sort from newest to oldest (default)

        Returns:
            Sorted list of supernovae
        """
        def date_key(sn: Supernova) -> datetime:
            try:
                if sn.date:
                    return parse_date(sn.date)[0] or datetime.min
            except Exception:
                pass
            return datetime.min

        return sorted(supernovae, key=date_key, reverse=reverse)
