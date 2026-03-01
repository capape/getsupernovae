"""Supernova selection and sorting service.

This module provides business logic for selecting and sorting supernovae based on
observation criteria and visibility windows. It coordinates between the filter service
and visibility window configurations to produce a final ordered list of observable
supernovae.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from astropy.coordinates import EarthLocation
from astropy.time import Time

from app.models.dto import SupernovaDTO
from app.models.snmodels import Supernova
from app.services.supernova_filter_service import SupernovaFilterService

if TYPE_CHECKING:
    pass


class SupernovaSelectionService:
    """Service for selecting and sorting observable supernovae.

    This service coordinates the selection of supernovae based on observation
    parameters, applies visibility window constraints, and sorts results by
    observation time. It acts as a higher-level orchestrator that uses the
    SupernovaFilterService for the actual filtering logic.
    """

    def __init__(
        self,
        filter_service: Optional[SupernovaFilterService] = None,
        visibility_windows: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """Initialize the selection service.

        Args:
            filter_service: Optional filter service instance. If None, creates a new one.
            visibility_windows: Optional dictionary of named visibility window configs.
        """
        self.filter_service = (
            filter_service if filter_service is not None else SupernovaFilterService()
        )
        self.visibility_windows = visibility_windows or {}

    def get_visibility_window_params(
        self, visibility_window_name: Optional[str], fallback_min_latitude: float
    ) -> tuple[float, float, float, float]:
        """Extract visibility window parameters from configuration or fallback.

        Args:
            visibility_window_name: Name of the visibility window configuration
            fallback_min_latitude: Minimum latitude to use if no named window is found

        Returns:
            Tuple of (min_altitude, max_altitude, min_azimuth, max_azimuth)
        """
        # Try to get named visibility window configuration
        if visibility_window_name and visibility_window_name in self.visibility_windows:
            cfg = self.visibility_windows[visibility_window_name]
            try:
                min_alt = float(cfg.get("minAlt", fallback_min_latitude))
                max_alt = float(cfg.get("maxAlt", 90.0))
                min_az = float(cfg.get("minAz", 0.0))
                max_az = float(cfg.get("maxAz", 360.0))
                return (min_alt, max_alt, min_az, max_az)
            except (ValueError, TypeError, KeyError):
                pass

        # Fallback to latitude-based parameters
        return (fallback_min_latitude, 90.0, 0.0, 360.0)

    def select_and_sort_supernovae(
        self,
        supernova_list: List[SupernovaDTO],
        max_magnitude: float,
        observation_start: Time,
        observation_hours: int,
        from_date: str,
        site: EarthLocation,
        exclusion_list: set,
        visibility_window_name: Optional[str] = None,
        min_latitude: float = 0.0,
        visibility_factory=None,
    ) -> List[Supernova]:
        """Select and sort supernovae based on observation criteria.

        This is the main entry point for selecting observable supernovae. It:
        1. Determines visibility window parameters (from named config or fallback)
        2. Applies all filters using the filter service
        3. Sorts results by observation start time

        Args:
            supernova_list: List of supernova DTOs to filter
            max_magnitude: Maximum magnitude threshold
            observation_start: Start time of observation
            observation_hours: Duration of observation in hours
            from_date: Earliest discovery date to include (ISO format)
            site: Observer's location on Earth
            exclusion_list: Set of supernova names to exclude
            visibility_window_name: Optional name of visibility window configuration
            min_latitude: Minimum latitude/altitude if no named window
            visibility_factory: Optional factory for creating visibility calculators

        Returns:
            List of Supernova objects sorted by observation time
        """
        from datetime import timedelta

        # Calculate observation end time
        observation_end = observation_start + timedelta(hours=observation_hours)

        # Get visibility window parameters
        min_alt, max_alt, min_az, max_az = self.get_visibility_window_params(
            visibility_window_name, min_latitude
        )

        # Apply all filters using the filter service
        filtered_results = self.filter_service.apply_all_filters(
            supernovae=supernova_list,
            max_magnitude=max_magnitude,
            from_date=from_date,
            exclusion_list=exclusion_list,
            site=site,
            observation_start=observation_start,
            observation_end=observation_end,
            min_altitude=min_alt,
            max_altitude=max_alt,
            min_azimuth=min_az,
            max_azimuth=max_az,
            visibility_factory=visibility_factory,
        )

        # Convert to domain models
        supernovas = self.filter_service.convert_to_domain_models(filtered_results)

        # Sort by observation time
        supernovas = self.sort_by_observation_time(supernovas)

        return supernovas

    def sort_by_observation_time(self, supernovae: List[Supernova]) -> List[Supernova]:
        """Sort supernovae by their observation window start and end times.

        Sorts first by the start time of visibility (earliest first), then by
        end time (earliest first) as a tiebreaker. This ensures supernovae
        are ordered by when they become observable during the observation window.

        Args:
            supernovae: List of Supernova objects with visibility information

        Returns:
            Sorted list of supernovae
        """

        def get_observation_times(sn: Supernova) -> tuple[float, float]:
            """Extract start and end times from visibility data."""
            try:
                if (
                    sn.visibility
                    and hasattr(sn.visibility, "azCords")
                    and sn.visibility.azCords
                ):
                    az_coords = sn.visibility.azCords
                    if len(az_coords) > 0:
                        start_time = (
                            az_coords[0].time
                            if hasattr(az_coords[0], "time")
                            else float("inf")
                        )
                        end_time = (
                            az_coords[-1].time
                            if hasattr(az_coords[-1], "time")
                            else float("inf")
                        )
                        return (start_time, end_time)
            except (AttributeError, IndexError, TypeError):
                pass
            return (float("inf"), float("inf"))

        return sorted(supernovae, key=get_observation_times)

    def sort_by_max_altitude(
        self, supernovae: List[Supernova], reverse: bool = True
    ) -> List[Supernova]:
        """Sort supernovae by maximum altitude during observation window.

        Higher altitude generally means better observing conditions.

        Args:
            supernovae: List of Supernova objects with visibility information
            reverse: If True, sort highest altitude first (default)

        Returns:
            Sorted list of supernovae
        """

        def get_max_altitude(sn: Supernova) -> float:
            """Extract maximum altitude from visibility data."""
            try:
                if (
                    sn.visibility
                    and hasattr(sn.visibility, "azCords")
                    and sn.visibility.azCords
                ):
                    altitudes = []
                    for coord in sn.visibility.azCords:
                        if hasattr(coord, "coord") and hasattr(coord.coord, "alt"):
                            altitudes.append(coord.coord.alt.degree)

                    if altitudes:
                        return max(altitudes)
            except (AttributeError, IndexError, TypeError):
                pass
            return -999.0  # Below horizon

        return sorted(supernovae, key=get_max_altitude, reverse=reverse)

    def group_by_constellation(
        self, supernovae: List[Supernova]
    ) -> Dict[str, List[Supernova]]:
        """Group supernovae by constellation.

        This can be useful for planning observations or creating finding charts
        by constellation.

        Args:
            supernovae: List of Supernova objects

        Returns:
            Dictionary mapping constellation names to lists of supernovae
        """
        groups = {}
        for sn in supernovae:
            constellation = sn.constellation or "Unknown"
            if constellation not in groups:
                groups[constellation] = []
            groups[constellation].append(sn)

        return groups

    def filter_by_observation_quality(
        self,
        supernovae: List[Supernova],
        min_altitude: float = 30.0,
        min_observation_duration_minutes: float = 30.0,
    ) -> List[Supernova]:
        """Filter supernovae by observation quality criteria.

        This applies additional quality filters beyond basic visibility,
        such as minimum altitude and observation duration.

        Args:
            supernovae: List of Supernova objects to filter
            min_altitude: Minimum altitude in degrees
            min_observation_duration_minutes: Minimum observable duration in minutes

        Returns:
            Filtered list of high-quality observable supernovae
        """
        filtered = []
        for sn in supernovae:
            try:
                if not sn.visibility or not hasattr(sn.visibility, "azCords"):
                    continue

                az_coords = sn.visibility.azCords
                if not az_coords or len(az_coords) == 0:
                    continue

                # Check maximum altitude
                altitudes = []
                for coord in az_coords:
                    if hasattr(coord, "coord") and hasattr(coord.coord, "alt"):
                        altitudes.append(coord.coord.alt.degree)

                if not altitudes or max(altitudes) < min_altitude:
                    continue

                # Check observation duration
                if hasattr(az_coords[0], "time") and hasattr(az_coords[-1], "time"):
                    duration_minutes = (
                        (az_coords[-1].time - az_coords[0].time) * 60 * 24
                    )  # Convert days to minutes
                    if duration_minutes < min_observation_duration_minutes:
                        continue

                filtered.append(sn)
            except (AttributeError, IndexError, TypeError):
                continue

        return filtered
