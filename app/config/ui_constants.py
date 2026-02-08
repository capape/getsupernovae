"""UI constants for the getsupernovae application.

This module centralizes all magic numbers and strings used throughout the UI,
making them easy to maintain and modify. Following SOLID principles, this
provides a single source of truth for UI-related constants.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ThemeColors:
    """Color scheme constants for light and dark themes.
    
    Using frozen=True to make these immutable and prevent accidental modification.
    """
    # Dark theme colors
    DARK_BG: str = "#2e2e2e"
    DARK_FG: str = "#eaeaea"
    DARK_ENTRY_BG: str = "#3a3a3a"
    DARK_BUTTON_BG: str = "#444444"
    DARK_TREE_BG: str = "#2b2b2b"
    DARK_SELECTION: str = "#5a5a5a"
    DARK_TOOLTIP_BG: str = "#3a3a3a"
    DARK_TOOLTIP_FG: str = "#eaeaea"
    DARK_EVEN_ROW: str = "#393838"
    DARK_ODD_ROW: str = "#262525"
    DARK_ROCHESTER_BG: str = "darkgray"
    
    # Light theme colors
    LIGHT_BG: str = "#9f9f9f"
    LIGHT_FG: str = "#000000"
    LIGHT_ENTRY_BG: str = "#eeeeee"
    LIGHT_BUTTON_BG: str = "#9f9f9f"
    LIGHT_TREE_BG: str = "#9f9f9f"
    LIGHT_SELECTION: str = "#cde"
    LIGHT_TOOLTIP_BG: str = "#ffffe0"
    LIGHT_TOOLTIP_FG: str = "#000000"
    LIGHT_EVEN_ROW: str = "#f0f0f0"
    LIGHT_ODD_ROW: str = "#ffffff"
    LIGHT_ROCHESTER_BG: str = "darkgray"
    
    # Highlight colors for bright supernovae (magnitude < 15)
    BRIGHT_FG_DARK: str = "#ff4444"
    BRIGHT_FG_LIGHT: str = "#cc0000"


@dataclass(frozen=True)
class UIConstants:
    """General UI layout and sizing constants."""
    
    # Window dimensions
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 1200
    
    # Tree view
    TREE_ROW_HEIGHT: int = 28
    
    # Column widths for results tree
    COL_WIDTH_NAME: int = 120
    COL_WIDTH_TYPE: int = 60
    COL_WIDTH_MAGNITUDE: int = 60
    COL_WIDTH_DATE: int = 100
    COL_WIDTH_OBS_TIME: int = 180
    COL_WIDTH_HOST: int = 150
    COL_WIDTH_CONSTELLATION: int = 80
    COL_WIDTH_RA: int = 90
    COL_WIDTH_DEC: int = 90
    COL_WIDTH_ROCHESTER: int = 80
    COL_WIDTH_TNS: int = 60
    
    # Progress bar
    PROGRESS_BAR_LENGTH: int = 400
    
    # Padding and spacing
    DEFAULT_PADX: int = 5
    DEFAULT_PADY: int = 5
    BUTTON_PADX: int = 6
    TOOLTIP_PADX: int = 8
    TOOLTIP_PADY: int = 6
    
    # Button sizes
    EDIT_BUTTON_WIDTH: int = 3
    
    # Grid row spacing
    MIN_ROW_SIZE: int = 30
    
    # Tooltip offset
    TOOLTIP_OFFSET_X: int = 10
    TOOLTIP_OFFSET_Y: int = 10
    
    # Rochester text widget
    ROCHESTER_TEXT_HEIGHT: int = 3
    ROCHESTER_TEXT_WIDTH: int = 60
    
    # Monitoring interval (milliseconds)
    MONITOR_INTERVAL_MS: int = 100


@dataclass(frozen=True)
class DefaultValues:
    """Default values for search filters and UI controls."""
    
    MAGNITUDE: str = "17"
    DAYS_TO_SEARCH: int = 21
    OBSERVATION_TIME: str = "21:00"
    OBSERVATION_HOURS: int = 5
    MIN_LATITUDE: float = 25.0
    LANGUAGE: str = "en"
    DARK_MODE: bool = True
    
    # Brightness threshold for highlighting
    BRIGHT_MAGNITUDE_THRESHOLD: float = 15.0


@dataclass(frozen=True)
class NetworkConstants:
    """Network-related constants."""
    
    TIMEOUT_SECONDS: int = 20
    
    # URLs
    ROCHESTER_BASE_URL: str = "https://www.rochesterastronomy.org/snimages/"
    TNS_OBJECT_URL: str = "https://www.wis-tns.org/object/"
    SIMBAD_QUERY_URL: str = "https://simbad.cds.unistra.fr/simbad/sim-sam"
    
    # SIMBAD query parameters
    SIMBAD_SEARCH_RADIUS: str = "30m 30m"  # 30 arcminutes box
    SIMBAD_MAX_VMAG: float = 17.0
    SIMBAD_MAIN_TYPE: str = "*"  # stellar objects
    SIMBAD_MAX_OBJECTS: int = 100


@dataclass(frozen=True)
class FileConstants:
    """File and directory related constants."""
    
    OLD_SUPERNOVAE_FILE: str = "old_supernovae.txt"
    SITES_CONFIG_FILE: str = "sites.json"
    VISIBILITY_WINDOWS_FILE: str = "visibility_windows.json"
    USER_PREFS_FILE: str = "user_prefs.json"
    
    # Icon files
    ICON_ICO: str = "app_icon.ico"
    ICON_PNG: str = "icon-256.png"
    ICON_SVG: str = "app_icon.svg"
    
    # Directories
    ICONS_DIR: str = "assets/icons"
    LOCALES_DIR: str = "locales"


@dataclass(frozen=True)
class UIStrings:
    """UI string constants (icons, symbols, etc.)."""
    
    # Unicode symbols
    EDIT_ICON: str = "✎"
    LINK_ICON: str = "🔗"
    
    # Tree view style name
    RESULTS_TREE_STYLE: str = "ResultsTreeview.Treeview"
    
    # Tag names for tree items
    TAG_EVEN_ROW: str = "evenrow"
    TAG_ODD_ROW: str = "oddrow"
    TAG_EVEN_ROW_BRIGHT: str = "evenrow_bright"
    TAG_ODD_ROW_BRIGHT: str = "oddrow_bright"


# Convenience instances for easy import
THEME_COLORS: Final[ThemeColors] = ThemeColors()
UI_CONSTANTS: Final[UIConstants] = UIConstants()
DEFAULT_VALUES: Final[DefaultValues] = DefaultValues()
NETWORK_CONSTANTS: Final[NetworkConstants] = NetworkConstants()
FILE_CONSTANTS: Final[FileConstants] = FileConstants()
UI_STRINGS: Final[UIStrings] = UIStrings()