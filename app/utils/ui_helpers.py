"""UI helper utilities for the application.

Provides common UI-related helper functions used across coordinators and managers.
"""

from typing import Any

from app.config.ui_constants import DEFAULT_VALUES, UI_STRINGS


def get_tree_row_tag(supernova: Any, row_index: int) -> str:
    """Determine the appropriate tree row tag for a supernova.

    Returns the tag name based on:
    - Whether the supernova is bright (magnitude < threshold)
    - Whether the row index is even or odd (for alternating colors)

    Args:
        supernova: Supernova object with 'mag' attribute
        row_index: Zero-based row index in the tree

    Returns:
        Tag string (e.g., 'even_row', 'odd_row_bright', etc.)
    """
    # Determine if supernova is bright
    mag = getattr(supernova, "mag", None)
    try:
        is_bright = (
            mag is not None
            and float(mag) < DEFAULT_VALUES.BRIGHT_MAGNITUDE_THRESHOLD
        )
    except (ValueError, TypeError):
        is_bright = False

    # Return appropriate tag based on brightness and row position
    if is_bright:
        return (
            UI_STRINGS.TAG_EVEN_ROW_BRIGHT
            if row_index % 2 == 0
            else UI_STRINGS.TAG_ODD_ROW_BRIGHT
        )
    return (
        UI_STRINGS.TAG_EVEN_ROW
        if row_index % 2 == 0
        else UI_STRINGS.TAG_ODD_ROW
    )
