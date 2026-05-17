"""Rochester Supernova Service - Main class for fetching and selecting supernovae.

This service coordinates supernova selection, filtering, and sorting operations
using the Rochester catalog data.
"""

from datetime import datetime, timedelta
from typing import List

from astropy.coordinates import EarthLocation
from astropy.time import Time

from app.models.dto import SupernovaDTO
from app.services.supernova_filter_service import SupernovaFilterService
from app.services.supernova_selection_service import SupernovaSelectionService
from app.utils.di_helpers import initialize_rochester_factories


class RochesterSupernova:
    """Main class for fetching and selecting supernovae from Rochester catalog."""

    def __init__(
        self,
        visibility_factory=None,
        provider_factory=None,
        reporter=None,
        filter_service=None,
        selection_service=None,
        old_supernovae=None,
        visibility_windows=None,
    ):
        """Initialize RochesterSupernova service.

        Args:
            visibility_factory: Factory for creating VisibilityWindow instances
            provider_factory: Factory for creating data providers
            reporter: Optional reporter for logging/reporting
            filter_service: Service for filtering supernovae
            selection_service: Service for selecting and sorting supernovae
            old_supernovae: Set of supernova names to exclude
            visibility_windows: Dict of named visibility windows
        """
        # Initialize factories with defaults using DI helper
        (
            self.visibility_factory,
            self.provider_factory,
            self.reporter,
        ) = initialize_rochester_factories(visibility_factory, provider_factory, reporter)

        # Store old supernovae and visibility windows
        self.old_supernovae = old_supernovae if old_supernovae is not None else set()
        self.visibility_windows = visibility_windows if visibility_windows is not None else {}

        # filter_service handles all filtering logic
        self.filter_service = (
            filter_service
            if filter_service is not None
            else SupernovaFilterService(visibility_factory=self.visibility_factory)
        )
        # selection_service coordinates selection and sorting
        self.selection_service = (
            selection_service
            if selection_service is not None
            else SupernovaSelectionService(
                filter_service=self.filter_service, visibility_windows=self.visibility_windows
            )
        )

    def select_and_sort_supernovae(self, callback_data, supernovae_list: List[SupernovaDTO]):
        """Select and sort supernovae using the selection service.

        This method now delegates to SupernovaSelectionService for all
        selection, filtering, and sorting logic.

        Args:
            callback_data: SupernovaCallBackData with search parameters
            supernovae_list: List of supernova DTOs to filter

        Returns:
            List of selected and sorted supernovae
        """
        # Convert magnitude to float
        try:
            max_magnitude = float(callback_data.magnitude)
        except (ValueError, TypeError):
            max_magnitude = float(str(callback_data.magnitude))

        # Use selection service to coordinate the entire selection process
        supernovas = self.selection_service.select_and_sort_supernovae(
            supernova_list=supernovae_list,
            max_magnitude=max_magnitude,
            observation_start=callback_data.observation_start,
            observation_hours=int(callback_data.observation_hours),
            from_date=callback_data.from_date,
            site=callback_data.site,
            exclusion_list=self.old_supernovae,
            visibility_window_name=getattr(callback_data, "visibility_window_name", None),
            min_latitude=float(callback_data.min_latitude),
            visibility_factory=self.visibility_factory,
        )

        return supernovas

    def select_supernovae(
        self,
        supernovae_list: List[SupernovaDTO],
        max_mag: str,
        observation_day: datetime,
        local_start_time: str,
        hours_observation: int,
        from_date: str,
        site: EarthLocation,
        min_alt: float = 0,
        max_alt: float = 90,
        min_az: float = 0,
        max_az: float = 360,
    ):
        """Select supernovae using the filter service.

        Legacy method kept for backward compatibility. Delegates to filter service.
        For new code, prefer using select_and_sort_supernovae with SupernovaCallBackData.

        Args:
            supernovae_list: List of supernova DTOs
            max_mag: Maximum magnitude threshold
            observation_day: Observation date
            local_start_time: Start time string
            hours_observation: Duration in hours
            from_date: Earliest date to consider
            site: Earth location for observation
            min_alt: Minimum altitude (default: 0)
            max_alt: Maximum altitude (default: 90)
            min_az: Minimum azimuth (default: 0)
            max_az: Maximum azimuth (default: 360)

        Returns:
            List of filtered supernovae
        """
        observation_start = observation_day.strftime("%Y-%m-%d") + "T" + local_start_time + "Z"

        time1 = Time(observation_start)
        time2 = time1 + timedelta(hours=hours_observation)

        # Convert maxMag to float
        try:
            max_mag_threshold = float(max_mag)
        except (ValueError, TypeError):
            max_mag_threshold = float(str(max_mag))

        # Use filter service to apply all filters and get results
        filtered_results = self.filter_service.apply_all_filters(
            supernovae=supernovae_list,
            max_magnitude=max_mag_threshold,
            from_date=from_date,
            exclusion_list=self.old_supernovae,
            site=site,
            observation_start=time1,
            observation_end=time2,
            min_altitude=min_alt,
            max_altitude=max_alt,
            min_azimuth=min_az,
            max_azimuth=max_az,
            visibility_factory=self.visibility_factory,
        )

        # Convert to domain models
        supernovas = self.filter_service.convert_to_domain_models(filtered_results)

        return supernovas
