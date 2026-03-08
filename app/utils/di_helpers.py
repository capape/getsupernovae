"""Dependency Injection helpers for factory initialization.

This module provides utilities for initializing factories with default fallbacks,
following the dependency injection pattern used throughout the application.
"""

from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


def default_if_none(value: Optional[T], default: T) -> T:
    """Return value if not None, otherwise return default.

    Args:
        value: The value to check
        default: The default value to use if value is None

    Returns:
        Either the value or the default
    """
    return value if value is not None else default


def initialize_rochester_factories(
    visibility_factory: Optional[Callable] = None,
    provider_factory: Optional[Callable] = None,
    reporter: Optional[Any] = None,
):
    """Initialize Rochester-related factories with defaults.

    This is a common pattern used across SearchCoordinator, RochesterSupernova,
    AsyncRochesterDownload, and initialization_builder.

    Args:
        visibility_factory: Factory for creating VisibilityWindow instances
        provider_factory: Factory for creating data providers
        reporter: Optional reporter for logging/reporting

    Returns:
        Tuple of (visibility_factory, provider_factory, reporter)
    """
    from app.services.provider import NetworkRochesterProvider
    from app.ui.snvisibility import VisibilityWindow

    return (
        default_if_none(visibility_factory, VisibilityWindow),
        default_if_none(provider_factory, NetworkRochesterProvider),
        reporter,
    )
