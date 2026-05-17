"""Unit tests for ObservationTimeService."""

import pytest

from app.services.observation_time_service import ObservationTimeService


class TestNormalizeTime:
    """Tests for normalize_time method."""

    def test_normalize_hour_only(self):
        """Test normalization of hour-only input."""
        assert ObservationTimeService.normalize_time("21") == "21:00"
        assert ObservationTimeService.normalize_time("0") == "00:00"
        assert ObservationTimeService.normalize_time("23") == "23:00"
        assert ObservationTimeService.normalize_time("9") == "09:00"

    def test_normalize_hour_minute(self):
        """Test normalization of HH:MM input."""
        assert ObservationTimeService.normalize_time("21:30") == "21:30"
        assert ObservationTimeService.normalize_time("0:0") == "00:00"
        assert ObservationTimeService.normalize_time("23:59") == "23:59"
        assert ObservationTimeService.normalize_time("12:45") == "12:45"

    def test_normalize_hour_minute_second(self):
        """Test normalization of HH:MM:SS input."""
        assert ObservationTimeService.normalize_time("21:30:45") == "21:30:45"
        assert ObservationTimeService.normalize_time("0:0:0") == "00:00:00"
        assert ObservationTimeService.normalize_time("23:59:59") == "23:59:59"
        assert ObservationTimeService.normalize_time("12:34:56") == "12:34:56"

    def test_normalize_with_whitespace(self):
        """Test normalization handles leading/trailing whitespace."""
        assert ObservationTimeService.normalize_time("  21  ") == "21:00"
        assert ObservationTimeService.normalize_time("  21:30  ") == "21:30"
        assert ObservationTimeService.normalize_time(" 21:30:45 ") == "21:30:45"

    def test_normalize_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Observation time is required"):
            ObservationTimeService.normalize_time("")

    def test_normalize_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Observation time is required"):
            ObservationTimeService.normalize_time("   ")

    def test_normalize_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="must be HH, HH:MM or HH:MM:SS"):
            ObservationTimeService.normalize_time("21:30:45:00")
        with pytest.raises(ValueError, match="must contain numeric values"):
            ObservationTimeService.normalize_time("not_a_time")

    def test_normalize_non_numeric_raises_error(self):
        """Test that non-numeric values raise ValueError."""
        with pytest.raises(ValueError, match="must contain numeric values"):
            ObservationTimeService.normalize_time("aa:bb")
        with pytest.raises(ValueError, match="must contain numeric values"):
            ObservationTimeService.normalize_time("21:xx")
        with pytest.raises(ValueError, match="must contain numeric values"):
            ObservationTimeService.normalize_time("21:30:xx")

    def test_normalize_hour_out_of_range_raises_error(self):
        """Test that hour out of range raises ValueError."""
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            ObservationTimeService.normalize_time("-1")
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            ObservationTimeService.normalize_time("24")
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            ObservationTimeService.normalize_time("25:00")

    def test_normalize_minute_out_of_range_raises_error(self):
        """Test that minute out of range raises ValueError."""
        with pytest.raises(ValueError, match="Minute must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:60")
        with pytest.raises(ValueError, match="Minute must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:-1")
        with pytest.raises(ValueError, match="Minute must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:99")

    def test_normalize_second_out_of_range_raises_error(self):
        """Test that second out of range raises ValueError."""
        with pytest.raises(ValueError, match="Second must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:30:60")
        with pytest.raises(ValueError, match="Second must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:30:-1")
        with pytest.raises(ValueError, match="Second must be between 0 and 59"):
            ObservationTimeService.normalize_time("21:30:99")

    def test_normalize_boundary_values(self):
        """Test boundary values for hour, minute, second."""
        # Minimum values
        assert ObservationTimeService.normalize_time("0:0:0") == "00:00:00"
        # Maximum values
        assert ObservationTimeService.normalize_time("23:59:59") == "23:59:59"
        # Mixed boundaries
        assert ObservationTimeService.normalize_time("0:59") == "00:59"
        assert ObservationTimeService.normalize_time("23:0") == "23:00"


class TestParseTimeComponents:
    """Tests for parse_time_components method."""

    def test_parse_hour_only(self):
        """Test parsing hour-only input."""
        assert ObservationTimeService.parse_time_components("21") == (21, 0, 0)
        assert ObservationTimeService.parse_time_components("0") == (0, 0, 0)
        assert ObservationTimeService.parse_time_components("23") == (23, 0, 0)

    def test_parse_hour_minute(self):
        """Test parsing HH:MM input."""
        assert ObservationTimeService.parse_time_components("21:30") == (21, 30, 0)
        assert ObservationTimeService.parse_time_components("0:0") == (0, 0, 0)
        assert ObservationTimeService.parse_time_components("23:59") == (23, 59, 0)

    def test_parse_hour_minute_second(self):
        """Test parsing HH:MM:SS input."""
        assert ObservationTimeService.parse_time_components("21:30:45") == (21, 30, 45)
        assert ObservationTimeService.parse_time_components("0:0:0") == (0, 0, 0)
        assert ObservationTimeService.parse_time_components("23:59:59") == (23, 59, 59)

    def test_parse_invalid_time_raises_error(self):
        """Test that invalid time raises ValueError."""
        with pytest.raises(ValueError):
            ObservationTimeService.parse_time_components("invalid")
        with pytest.raises(ValueError):
            ObservationTimeService.parse_time_components("25:00")


class TestValidateTime:
    """Tests for validate_time method."""

    def test_validate_valid_times(self):
        """Test that valid times return True."""
        assert ObservationTimeService.validate_time("21") is True
        assert ObservationTimeService.validate_time("21:30") is True
        assert ObservationTimeService.validate_time("21:30:45") is True
        assert ObservationTimeService.validate_time("0:0:0") is True
        assert ObservationTimeService.validate_time("23:59:59") is True

    def test_validate_invalid_times(self):
        """Test that invalid times return False."""
        assert ObservationTimeService.validate_time("") is False
        assert ObservationTimeService.validate_time("invalid") is False
        assert ObservationTimeService.validate_time("25:00") is False
        assert ObservationTimeService.validate_time("21:60") is False
        assert ObservationTimeService.validate_time("21:30:60") is False
        assert ObservationTimeService.validate_time("aa:bb") is False
        assert ObservationTimeService.validate_time("21:30:45:00") is False

    def test_validate_boundary_cases(self):
        """Test validation of boundary cases."""
        assert ObservationTimeService.validate_time("0") is True
        assert ObservationTimeService.validate_time("23") is True
        assert ObservationTimeService.validate_time("24") is False
        assert ObservationTimeService.validate_time("-1") is False


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_leading_zeros_accepted(self):
        """Test that leading zeros are properly handled."""
        assert ObservationTimeService.normalize_time("01") == "01:00"
        assert ObservationTimeService.normalize_time("01:02") == "01:02"
        assert ObservationTimeService.normalize_time("01:02:03") == "01:02:03"

    def test_single_digit_values(self):
        """Test single digit values are zero-padded."""
        assert ObservationTimeService.normalize_time("1") == "01:00"
        assert ObservationTimeService.normalize_time("1:2") == "01:02"
        assert ObservationTimeService.normalize_time("1:2:3") == "01:02:03"

    def test_midnight_representations(self):
        """Test various midnight representations."""
        assert ObservationTimeService.normalize_time("0") == "00:00"
        assert ObservationTimeService.normalize_time("0:0") == "00:00"
        assert ObservationTimeService.normalize_time("0:0:0") == "00:00:00"
        assert ObservationTimeService.normalize_time("00:00:00") == "00:00:00"

    def test_noon_representations(self):
        """Test noon representations."""
        assert ObservationTimeService.normalize_time("12") == "12:00"
        assert ObservationTimeService.normalize_time("12:0") == "12:00"
        assert ObservationTimeService.normalize_time("12:0:0") == "12:00:00"
