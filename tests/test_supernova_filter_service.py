"""Tests for SupernovaFilterService.

This module tests the filtering logic for supernovae including magnitude,
date range, exclusion list, and visibility filtering.
"""

import os
import sys
from datetime import datetime, timedelta

import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

# Ensure package imports work when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.dto import SupernovaDTO
from app.models.snmodels import AxCordInTime, Supernova, Visibility
from app.services.supernova_filter_service import SupernovaFilterService


# Mock visibility factory for testing
class MockVisibilityFactory:
    """Mock visibility calculator that returns configurable results."""

    def __init__(self, minAlt, maxAlt, minAz, maxAz):
        self.minAlt = minAlt
        self.maxAlt = maxAlt
        self.minAz = minAz
        self.maxAz = maxAz
        self.calls = []

    def getVisibility(self, site, coord, t1, t2):
        """Return mock visibility - visible for coords with RA > 12h."""
        self.calls.append((site, coord, t1, t2))

        # Make objects with RA > 12h visible
        ra_hours = coord.ra.hour
        is_visible = ra_hours > 12.0

        if is_visible:
            return Visibility(
                True, [AxCordInTime(t1, None), AxCordInTime(t1 + timedelta(hours=1), None)]
            )
        else:
            return Visibility(False, [])


def create_test_supernova_dto(name, mag, date_str, ra="12:00:00", dec="+45:00:00"):
    """Helper to create test supernova DTOs."""
    coords = SkyCoord(ra, dec, frame="icrs", unit=(u.hourangle, u.deg))
    date_obj = datetime.strptime(date_str, "%Y/%m/%d").date()

    return SupernovaDTO(
        name=name,
        host=f"Host of {name}",
        ra=ra,
        decl=dec,
        mag=mag,
        date=date_str,
        date_obj=date_obj,
        coordinates=coords,
        type="Ia",
        firstObserved=date_str,
        maxMagnitude=mag,
        maxMagnitudeDate=date_str,
        link=f"http://example.com/{name}",
        firstObserved_obj=date_obj,
        maxMagnitudeDate_obj=date_obj,
    )


def test_filter_by_magnitude():
    """Test magnitude filtering."""
    service = SupernovaFilterService()

    supernovae = [
        create_test_supernova_dto("SN2025a", 14.5, "2025/01/01"),
        create_test_supernova_dto("SN2025b", 15.5, "2025/01/02"),
        create_test_supernova_dto("SN2025c", 16.5, "2025/01/03"),
    ]

    # Filter with threshold 15.0
    filtered = service.filter_by_magnitude(supernovae, 15.0)

    assert len(filtered) == 1
    assert filtered[0].name == "SN2025a"
    assert filtered[0].mag == 14.5


def test_filter_by_magnitude_inclusive():
    """Test that magnitude filter includes objects at the threshold."""
    service = SupernovaFilterService()

    supernovae = [
        create_test_supernova_dto("SN2025a", 15.0, "2025/01/01"),
        create_test_supernova_dto("SN2025b", 15.1, "2025/01/02"),
    ]

    filtered = service.filter_by_magnitude(supernovae, 15.0)

    assert len(filtered) == 1
    assert filtered[0].name == "SN2025a"


def test_filter_by_date_range():
    """Test date range filtering."""
    service = SupernovaFilterService()

    supernovae = [
        create_test_supernova_dto("SN2025a", 15.0, "2025/01/01"),
        create_test_supernova_dto("SN2025b", 15.0, "2025/01/15"),
        create_test_supernova_dto("SN2025c", 15.0, "2025/01/30"),
    ]

    # Filter to get only after Jan 10
    filtered = service.filter_by_date_range(supernovae, "2025-01-10")

    assert len(filtered) == 2
    assert filtered[0].name == "SN2025b"
    assert filtered[1].name == "SN2025c"


def test_filter_by_exclusion_list():
    """Test exclusion list filtering."""
    service = SupernovaFilterService()

    supernovae = [
        create_test_supernova_dto("SN2025a", 15.0, "2025/01/01"),
        create_test_supernova_dto("SN2025b", 15.0, "2025/01/02"),
        create_test_supernova_dto("SN2025c", 15.0, "2025/01/03"),
    ]

    exclusion_list = {"SN2025a", "SN2025c"}
    filtered = service.filter_by_exclusion_list(supernovae, exclusion_list)

    assert len(filtered) == 1
    assert filtered[0].name == "SN2025b"


def test_filter_by_visibility():
    """Test visibility filtering."""
    service = SupernovaFilterService(visibility_factory=MockVisibilityFactory)

    # Create supernovae with different RAs (> 12h will be visible in mock)
    supernovae = [
        create_test_supernova_dto("SN2025a", 15.0, "2025/01/01", ra="10:00:00"),  # Not visible
        create_test_supernova_dto("SN2025b", 15.0, "2025/01/02", ra="14:00:00"),  # Visible
        create_test_supernova_dto("SN2025c", 15.0, "2025/01/03", ra="18:00:00"),  # Visible
    ]

    site = EarthLocation(lat=41.5 * u.deg, lon=2.0 * u.deg, height=200 * u.m)
    obs_start = Time("2025-01-01T21:00:00")
    obs_end = Time("2025-01-01T23:00:00")

    visible = service.filter_by_visibility(
        supernovae,
        site,
        obs_start,
        obs_end,
        min_altitude=0,
        max_altitude=90,
        min_azimuth=0,
        max_azimuth=360,
    )

    assert len(visible) == 2
    assert visible[0][0].name == "SN2025b"
    assert visible[1][0].name == "SN2025c"

    # Check visibility objects are included
    assert visible[0][1].visible is True
    assert visible[1][1].visible is True


def test_apply_all_filters():
    """Test applying all filters in sequence."""
    service = SupernovaFilterService(visibility_factory=MockVisibilityFactory)

    supernovae = [
        create_test_supernova_dto("SN2025a", 14.0, "2025/01/01", ra="14:00:00"),  # Pass all
        create_test_supernova_dto("SN2025b", 16.0, "2025/01/02", ra="14:00:00"),  # Fail mag
        create_test_supernova_dto("SN2025c", 14.0, "2024/12/01", ra="14:00:00"),  # Fail date
        create_test_supernova_dto("SN2025d", 14.0, "2025/01/03", ra="10:00:00"),  # Fail visibility
        create_test_supernova_dto("SN2025e", 14.0, "2025/01/04", ra="14:00:00"),  # Excluded
    ]

    site = EarthLocation(lat=41.5 * u.deg, lon=2.0 * u.deg, height=200 * u.m)
    obs_start = Time("2025-01-01T21:00:00")
    obs_end = Time("2025-01-01T23:00:00")

    visible = service.apply_all_filters(
        supernovae=supernovae,
        max_magnitude=15.0,
        from_date="2024-12-31",
        exclusion_list={"SN2025e"},
        site=site,
        observation_start=obs_start,
        observation_end=obs_end,
        min_altitude=0,
        max_altitude=90,
        min_azimuth=0,
        max_azimuth=360,
    )

    # Only SN2025a should pass all filters
    assert len(visible) == 1
    assert visible[0][0].name == "SN2025a"


def test_convert_to_domain_models():
    """Test conversion from DTO to domain model."""
    service = SupernovaFilterService()

    dto = create_test_supernova_dto("SN2025a", 14.5, "2025/01/01", ra="14:00:00")
    visibility = Visibility(True, [AxCordInTime(Time.now(), None)])

    filtered_results = [(dto, visibility)]
    supernovae = service.convert_to_domain_models(filtered_results)

    assert len(supernovae) == 1
    sn = supernovae[0]

    assert isinstance(sn, Supernova)
    assert sn.name == "SN2025a"
    assert sn.mag == "14.5"
    assert sn.host == "Host of SN2025a"
    assert sn.visibility == visibility


def test_is_bright_supernova():
    """Test brightness classification."""
    service = SupernovaFilterService()

    assert service.is_bright_supernova(14.0) is True
    assert service.is_bright_supernova(14.9) is True
    assert service.is_bright_supernova(15.0) is False
    assert service.is_bright_supernova(16.0) is False
    assert service.is_bright_supernova(None) is False


def test_sort_by_magnitude():
    """Test sorting by magnitude."""
    service = SupernovaFilterService()

    # Create domain model supernovae
    dto1 = create_test_supernova_dto("SN2025a", 16.0, "2025/01/01")
    dto2 = create_test_supernova_dto("SN2025b", 14.0, "2025/01/02")
    dto3 = create_test_supernova_dto("SN2025c", 15.0, "2025/01/03")

    visibility = Visibility(True, [AxCordInTime(Time.now(), None)])

    supernovae = service.convert_to_domain_models(
        [(dto1, visibility), (dto2, visibility), (dto3, visibility)]
    )

    sorted_sn = service.sort_by_magnitude(supernovae)

    assert sorted_sn[0].name == "SN2025b"  # 14.0
    assert sorted_sn[1].name == "SN2025c"  # 15.0
    assert sorted_sn[2].name == "SN2025a"  # 16.0


def test_sort_by_magnitude_reverse():
    """Test reverse sorting by magnitude."""
    service = SupernovaFilterService()

    dto1 = create_test_supernova_dto("SN2025a", 14.0, "2025/01/01")
    dto2 = create_test_supernova_dto("SN2025b", 16.0, "2025/01/02")

    visibility = Visibility(True, [AxCordInTime(Time.now(), None)])
    supernovae = service.convert_to_domain_models([(dto1, visibility), (dto2, visibility)])

    sorted_sn = service.sort_by_magnitude(supernovae, reverse=True)

    assert sorted_sn[0].mag == "16.0"  # Dimmest first
    assert sorted_sn[1].mag == "14.0"


def test_empty_input_handling():
    """Test that service handles empty inputs gracefully."""
    service = SupernovaFilterService()

    assert service.filter_by_magnitude([], 15.0) == []
    assert service.filter_by_date_range([], "2025-01-01") == []
    assert service.filter_by_exclusion_list([], set()) == []
    assert service.convert_to_domain_models([]) == []
    assert service.sort_by_magnitude([]) == []
    assert service.sort_by_date([]) == []


def test_filter_with_invalid_magnitude():
    """Test filtering handles invalid magnitude values."""
    service = SupernovaFilterService()

    # Create DTO with invalid magnitude (will be caught during filtering)
    supernovae = [
        create_test_supernova_dto("SN2025a", 14.5, "2025/01/01"),
    ]
    supernovae[0].mag = None  # Set to invalid value

    filtered = service.filter_by_magnitude(supernovae, 15.0)

    # Should skip the invalid one
    assert len(filtered) == 0


if __name__ == "__main__":
    # Run tests
    test_filter_by_magnitude()
    test_filter_by_magnitude_inclusive()
    test_filter_by_date_range()
    test_filter_by_exclusion_list()
    test_filter_by_visibility()
    test_apply_all_filters()
    test_convert_to_domain_models()
    test_is_bright_supernova()
    test_sort_by_magnitude()
    test_sort_by_magnitude_reverse()
    test_empty_input_handling()
    test_filter_with_invalid_magnitude()

    print("All SupernovaFilterService tests passed!")
