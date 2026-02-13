"""Service for handling observation time validation and normalization.

This service provides utilities for processing and validating observation
time inputs from users, ensuring they conform to formats accepted by astropy.Time.
"""

from typing import Tuple


class ObservationTimeService:
    """Service for observation time validation and normalization.

    Handles conversion of various time formats (HH, HH:MM, HH:MM:SS) to
    standardized formats suitable for astronomical calculations.
    """

    @staticmethod
    def normalize_time(observation_time: str) -> str:
        """Normalize observation time to HH:MM or HH:MM:SS format.

        Accepts flexible input formats:
        - "21" -> "21:00"
        - "21:30" -> "21:30"
        - "21:30:45" -> "21:30:45"

        Args:
            observation_time: Time string in HH, HH:MM, or HH:MM:SS format

        Returns:
            Normalized time string in HH:MM or HH:MM:SS format

        Raises:
            ValueError: If time format is invalid or values are out of range
        """
        text = str(observation_time).strip()
        if not text:
            raise ValueError("Observation time is required")

        parts = text.split(":")
        if len(parts) not in (1, 2, 3):
            raise ValueError("Observation time must be HH, HH:MM or HH:MM:SS")

        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) >= 2 else 0
            second = int(parts[2]) if len(parts) == 3 else None
        except (TypeError, ValueError):
            raise ValueError("Observation time must contain numeric values")

        if hour < 0 or hour > 23:
            raise ValueError("Hour must be between 0 and 23")
        if minute < 0 or minute > 59:
            raise ValueError("Minute must be between 0 and 59")

        if second is None:
            return f"{hour:02d}:{minute:02d}"

        if second < 0 or second > 59:
            raise ValueError("Second must be between 0 and 59")
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    @staticmethod
    def parse_time_components(observation_time: str) -> Tuple[int, int, int]:
        """Parse observation time into hour, minute, second components.

        Args:
            observation_time: Time string in HH, HH:MM, or HH:MM:SS format

        Returns:
            Tuple of (hour, minute, second) as integers

        Raises:
            ValueError: If time format is invalid or values are out of range
        """
        normalized = ObservationTimeService.normalize_time(observation_time)
        parts = normalized.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
        return hour, minute, second

    @staticmethod
    def validate_time(observation_time: str) -> bool:
        """Check if observation time is valid without raising exceptions.

        Args:
            observation_time: Time string to validate

        Returns:
            True if time is valid, False otherwise
        """
        try:
            ObservationTimeService.normalize_time(observation_time)
            return True
        except ValueError:
            return False
