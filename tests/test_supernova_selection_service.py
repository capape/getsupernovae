"""Tests for SupernovaSelectionService.

This module tests the selection and sorting logic for observable supernovae,
including visibility window parameter extraction and observation time sorting.
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
from app.services.supernova_selection_service import SupernovaSelectionService


# Mock visibility factory for testing
class MockVisibilityFactory:
    """Mock visibility calculator with configurable start times."""

    def __init__(self, min_alt, max_alt, min_az, max_az):
        self.min_alt = min_alt
        self.max_alt = max_alt
        self.min_az = min_az
        self.max_az = max_az

    def get_visibility(self, site, coord, t1, t2):
        """Return mock visibility with staggered observation times."""
        # Create different start times based on RA
        ra_hours = coord.ra.hour

        if ra_hours > 12.0:
            # Calculate offset based on RA
            offset_hours = (ra_hours - 12.0) / 2.0
            start_time = t1.datetime + timedelta(hours=offset_hours)
            end_time = start_time + timedelta(hours=1)

            return Visibility(True, [AxCordInTime(start_time, None), AxCordInTime(end_time, None)])
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
        last_observed_date=date_str,
        date_obj=date_obj,
        coordinates=coords,
        type="Ia",
        first_observed=date_str,
        max_magnitude=mag,
        max_magnitude_date=date_str,
        link=f"http://example.com/{name}",
        first_observed_obj=date_obj,
        max_magnitude_date_obj=date_obj,
    )


def test_get_visibility_window_params_fallback():
    """Test visibility window parameter extraction with fallback."""
    service = SupernovaSelectionService()

    params = service.get_visibility_window_params(None, 25.0)

    assert params == (25.0, 90.0, 0.0, 360.0)


def test_get_visibility_window_params_named():
    """Test visibility window parameter extraction from named config."""
    visibility_windows = {
        "MyWindow": {"min_alt": 30.0, "max_alt": 85.0, "min_az": 45.0, "max_az": 315.0}
    }

    service = SupernovaSelectionService(visibility_windows=visibility_windows)
    params = service.get_visibility_window_params("MyWindow", 25.0)

    assert params == (30.0, 85.0, 45.0, 315.0)


def test_get_visibility_window_params_missing_window():
    """Test fallback when named window doesn't exist."""
    visibility_windows = {"OtherWindow": {"min_alt": 30.0}}

    service = SupernovaSelectionService(visibility_windows=visibility_windows)
    params = service.get_visibility_window_params("NonExistent", 25.0)

    # Should fall back to default values
    assert params == (25.0, 90.0, 0.0, 360.0)


def test_select_and_sort_supernovae():
    """Test full selection and sorting workflow."""
    filter_service = SupernovaFilterService(visibility_factory=MockVisibilityFactory)
    service = SupernovaSelectionService(filter_service=filter_service)

    # Create test data with different RAs (affects observation time in mock)
    supernovae = [
        create_test_supernova_dto("SN2025a", 14.0, "2025/01/01", ra="14:00:00"),  # Later start
        create_test_supernova_dto("SN2025b", 14.0, "2025/01/02", ra="16:00:00"),  # Latest start
        create_test_supernova_dto("SN2025c", 14.0, "2025/01/03", ra="13:00:00"),  # Earlier start
    ]

    site = EarthLocation(lat=41.5 * u.deg, lon=2.0 * u.deg, height=200 * u.m)
    obs_start = Time("2025-01-01T21:00:00")

    result = service.select_and_sort_supernovae(
        supernova_list=supernovae,
        max_magnitude=15.0,
        observation_start=obs_start,
        observation_hours=5,
        from_date="2024-12-31",
        site=site,
        exclusion_list=set(),
        visibility_window_name=None,
        min_latitude=0.0,
        visibility_factory=MockVisibilityFactory,
    )

    assert len(result) == 3
    # Should be sorted by observation start time
    # RA 13h starts earliest, then 14h, then 16h
    assert result[0].name == "SN2025c"
    assert result[1].name == "SN2025a"
    assert result[2].name == "SN2025b"


def test_select_and_sort_with_named_window():
    """Test selection with named visibility window."""
    visibility_windows = {
        "HighAltitude": {"min_alt": 40.0, "max_alt": 85.0, "min_az": 0.0, "max_az": 360.0}
    }

    filter_service = SupernovaFilterService(visibility_factory=MockVisibilityFactory)
    service = SupernovaSelectionService(
        filter_service=filter_service, visibility_windows=visibility_windows
    )

    supernovae = [create_test_supernova_dto("SN2025a", 14.0, "2025/01/01", ra="14:00:00")]

    site = EarthLocation(lat=41.5 * u.deg, lon=2.0 * u.deg, height=200 * u.m)
    obs_start = Time("2025-01-01T21:00:00")

    result = service.select_and_sort_supernovae(
        supernova_list=supernovae,
        max_magnitude=15.0,
        observation_start=obs_start,
        observation_hours=5,
        from_date="2024-12-31",
        site=site,
        exclusion_list=set(),
        visibility_window_name="HighAltitude",
        min_latitude=25.0,
        visibility_factory=MockVisibilityFactory,
    )

    # Should use the named window parameters (not the fallback min_latitude)
    assert len(result) == 1


def test_sort_by_observation_time():
    """Test sorting supernovae by observation time."""
    service = SupernovaSelectionService()

    # Create mock supernovae with different observation times
    sn1 = Supernova(
        name="SN2025a",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host1",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                AxCordInTime(datetime(2025, 1, 1, 22, 0, 0), None),
                AxCordInTime(datetime(2025, 1, 1, 23, 0, 0), None),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    sn2 = Supernova(
        name="SN2025b",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host2",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                AxCordInTime(datetime(2025, 1, 1, 21, 0, 0), None),
                AxCordInTime(datetime(2025, 1, 1, 22, 30, 0), None),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    sn3 = Supernova(
        name="SN2025c",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host3",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                AxCordInTime(datetime(2025, 1, 1, 23, 0, 0), None),
                AxCordInTime(datetime(2025, 1, 2, 0, 0, 0), None),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    supernovae = [sn1, sn2, sn3]
    sorted_sn = service.sort_by_observation_time(supernovae)

    # Should be sorted by start time
    assert sorted_sn[0].name == "SN2025b"  # 21:00
    assert sorted_sn[1].name == "SN2025a"  # 22:00
    assert sorted_sn[2].name == "SN2025c"  # 23:00


def test_sort_by_max_altitude():
    """Test sorting by maximum altitude."""
    service = SupernovaSelectionService()

    # Mock coordinate with altitude
    class MockCoord:
        def __init__(self, alt_deg):
            self.alt = type("obj", (object,), {"degree": alt_deg})

    class MockAxCord:
        def __init__(self, time, alt_deg):
            self.time = time
            self.coord = MockCoord(alt_deg)

    sn1 = Supernova(
        name="SN2025a",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host1",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                MockAxCord(datetime.now(), 45.0),
                MockAxCord(datetime.now(), 50.0),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    sn2 = Supernova(
        name="SN2025b",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host2",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                MockAxCord(datetime.now(), 70.0),
                MockAxCord(datetime.now(), 75.0),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    supernovae = [sn1, sn2]
    sorted_sn = service.sort_by_max_altitude(supernovae, reverse=True)

    # Should be sorted by max altitude (highest first)
    assert sorted_sn[0].name == "SN2025b"  # max 75
    assert sorted_sn[1].name == "SN2025a"  # max 50


def test_group_by_constellation():
    """Test grouping supernovae by constellation."""
    service = SupernovaSelectionService()

    sn1 = Supernova(
        name="SN2025a",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host1",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=None,
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    sn2 = Supernova(
        name="SN2025b",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host2",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Virgo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=None,
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    sn3 = Supernova(
        name="SN2025c",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host3",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=None,
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    supernovae = [sn1, sn2, sn3]
    grouped = service.group_by_constellation(supernovae)

    assert len(grouped) == 2
    assert len(grouped["Leo"]) == 2
    assert len(grouped["Virgo"]) == 1
    assert grouped["Leo"][0].name in ["SN2025a", "SN2025c"]
    assert grouped["Virgo"][0].name == "SN2025b"


def test_filter_by_observation_quality():
    """Test filtering by observation quality criteria."""
    service = SupernovaSelectionService()

    # Mock coordinate with altitude
    class MockCoord:
        def __init__(self, alt_deg):
            self.alt = type("obj", (object,), {"degree": alt_deg})

    class MockAxCord:
        def __init__(self, time, alt_deg):
            self.time = time
            self.coord = MockCoord(alt_deg)

    # Low altitude - should be filtered out
    sn1 = Supernova(
        name="SN2025a",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host1",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                MockAxCord(0.0, 20.0),
                MockAxCord(0.1, 25.0),
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    # Good altitude and duration
    sn2 = Supernova(
        name="SN2025b",
        last_observed_date="2025/01/01",
        mag="14.0",
        host="Host2",
        ra="12:00:00",
        decl="+45:00:00",
        link="",
        constellation="Leo",
        coordinates=None,
        first_observed=None,
        max_magnitude=None,
        max_magnitude_date=None,
        type="Ia",
        visibility=Visibility(
            True,
            [
                MockAxCord(0.0, 45.0),
                MockAxCord(0.05, 50.0),  # ~1 hour duration
            ],
        ),
        max_magnitude_date_obj=None,
        first_observed_obj=None,
    )

    supernovae = [sn1, sn2]
    filtered = service.filter_by_observation_quality(
        supernovae, min_altitude=30.0, min_observation_duration_minutes=30.0
    )

    assert len(filtered) == 1
    assert filtered[0].name == "SN2025b"


def test_empty_list_handling():
    """Test that service handles empty lists gracefully."""
    service = SupernovaSelectionService()

    assert service.sort_by_observation_time([]) == []
    assert service.sort_by_max_altitude([]) == []
    assert service.group_by_constellation([]) == {}
    assert service.filter_by_observation_quality([]) == []


if __name__ == "__main__":
    # Run tests
    test_get_visibility_window_params_fallback()
    test_get_visibility_window_params_named()
    test_get_visibility_window_params_missing_window()
    test_select_and_sort_supernovae()
    test_select_and_sort_with_named_window()
    test_sort_by_observation_time()
    test_sort_by_max_altitude()
    test_group_by_constellation()
    test_filter_by_observation_quality()
    test_empty_list_handling()

    print("All SupernovaSelectionService tests passed!")
