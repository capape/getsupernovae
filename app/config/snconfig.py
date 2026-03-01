"""Configuration loading utilities for the Get Supernovae application.

This module provides functions to load configuration from various sources:
- Old supernova names from text files
- Observing sites from JSON files
- Visibility windows for observations
- Bootstrap configuration and directory management
"""

import json
import os
import shutil
import sys
from collections import OrderedDict

import astropy.units as u
from astropy.coordinates import EarthLocation


def load_old_supernovae(path: str | None = None):
    """Load old supernova names from a file (one per line). If the file
    is missing, returns an empty list."""

    candidates = get_config_candidates(path, "old_supernovae.txt")

    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                lines = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
            return lines
        except (OSError, IOError, UnicodeDecodeError):
            continue

    return []


def load_sites(path: str | None = None):
    """Load observing sites from a JSON file and return an OrderedDict of
    name -> EarthLocation. If missing, return reasonable defaults."""
    defaults = OrderedDict(
        [
            ("Sabadell", {"lat": 41.55, "lon": 2.09, "height": 224}),
            ("Sant Quirze", {"lat": 41.32, "lon": 2.04, "height": 196}),
            ("Requena", {"lat": 39.45, "lon": -1.21, "height": 587}),
        ]
    )

    candidates = get_config_candidates(path, "sites.json")

    sites_conf = None
    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                sites_conf = json.load(fh)
            break
        except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
            sites_conf = None
            continue

    # Start with defaults and then overlay any user-provided sites so that
    # canonical defaults like 'Sabadell' remain available unless explicitly
    # overridden by the user. This avoids breaking tests or code that expects
    # the default sites to always be present.
    result = OrderedDict()
    try:
        for name, v in defaults.items():
            try:
                lat = float(v.get("lat", 0.0))
                lon = float(v.get("lon", 0.0))
                h = float(v.get("height", 0.0))
                result[name] = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=h * u.m)  # type: ignore[operator] # pylint: disable=no-member
            except (ValueError, TypeError, KeyError, AttributeError):
                continue

        if isinstance(sites_conf, dict):
            for name, v in sites_conf.items():
                try:
                    if isinstance(v, dict):
                        lat = float(v.get("lat", 0.0))
                        lon = float(v.get("lon", 0.0))
                        h = float(v.get("height", 0.0))
                    else:
                        lat = float(v.lat.value)
                        lon = float(v.lon.value)
                        h = float(v.height.value)
                    result[name] = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=h * u.m)  # type: ignore[operator] # pylint: disable=no-member
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue
    except (ValueError, TypeError, KeyError, AttributeError):
        # On any unexpected error, fall back to defaults already populated.
        pass

    return result


def get_config_candidates(path: str | None, config_file: str):
    """Get list of candidate paths for config file."""
    candidates = []
    if path:
        candidates.append(path)
    config_path = get_user_config_dir()
    candidates.append(os.path.join(config_path, config_file))
    # Note: XDG_CONFIG_HOME support could be added here if needed
    return candidates


def load_visibility_windows(path: str | None = None):
    """Load visibility windows from config file."""
    defaults = {"Default": {"min_alt": 0.0, "max_alt": 90.0, "min_az": 0.0, "max_az": 360.0}}

    candidates = get_config_candidates(path, "visibility_windows.json")

    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
            continue

    return defaults


def get_user_config_dir():
    """Return the user config directory for getsupernovae.

    Respects XDG on Linux, uses macOS Application Support, or APPDATA on Windows.
    """
    # Allow overriding config dir via env var (useful for tests)
    env = os.environ.get("GETSUPERNOVAE_CONFIG_DIR")
    if env:
        return env
    # When running under pytest, prefer a workspace-local test config dir to
    # avoid reading or mutating the real user's config during automated tests.
    # Checking for the `pytest` module in sys.modules catches the test runner
    # during import/collection time as well as per-test execution.
    if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
        return os.path.join(os.getcwd(), ".getsupernovae_test_config")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "getsupernovae")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/getsupernovae")
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "getsupernovae")
    return os.path.expanduser("~/.config/getsupernovae")


def bootstrap_config():
    """Create user config dir and write default config files if missing."""
    cfg = get_user_config_dir()
    try:
        os.makedirs(cfg, exist_ok=True)
    except OSError:
        return

    sites_path = os.path.join(cfg, "sites.json")
    old_path = os.path.join(cfg, "old_supernovae.txt")

    # default sites
    default_sites = {"Sabadell": {"lat": 41.55, "lon": 2.09, "height": 224}}

    # default old list
    default_old = []

    try:
        if not os.path.exists(sites_path):
            with open(sites_path, "w", encoding="utf-8") as fh:
                json.dump(default_sites, fh, indent=2)
    except (OSError, IOError):
        pass

    try:
        if not os.path.exists(old_path):
            with open(old_path, "w", encoding="utf-8") as fh:
                for name in default_old:
                    fh.write(name + "\n")
    except (OSError, IOError):
        pass


def load_user_prefs():
    """Load persisted UI prefs from user config dir, return {} on error."""
    try:
        cfg = get_user_config_dir()
        os.makedirs(cfg, exist_ok=True)
        p = os.path.join(cfg, "prefs.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    # fallback: try package-local prefs file
    try:
        p = os.path.join(os.path.dirname(__file__), "prefs.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {}


def save_user_prefs(prefs: dict):
    """Save prefs dict to user config dir; best-effort, ignore failures."""
    try:
        cfg = get_user_config_dir()
        os.makedirs(cfg, exist_ok=True)
        p = os.path.join(cfg, "prefs.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(prefs, fh, indent=2)
        return
    except (OSError, IOError, TypeError):
        pass
    # last resort: write next to module
    try:
        p = os.path.join(os.path.dirname(__file__), "prefs.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(prefs, fh, indent=2)
    except (OSError, IOError, TypeError):
        pass

    # default visibility windows
    default_visibility = {
        "Default": {"min_alt": 0.0, "max_alt": 90.0, "min_az": 0.0, "max_az": 360.0}
    }
    vis_path = os.path.join(cfg, "visibility_windows.json")
    try:
        if not os.path.exists(vis_path):
            with open(vis_path, "w", encoding="utf-8") as fh:
                json.dump(default_visibility, fh, indent=2)
    except (OSError, IOError, TypeError):
        pass

    # Ensure a bundled font exists in package fonts/ for deterministic embedding on export
    try:
        package_fonts = os.path.join(os.path.dirname(__file__), "fonts")
        os.makedirs(package_fonts, exist_ok=True)
        bundled = os.path.join(package_fonts, "DejaVuSans.ttf")
        if not os.path.exists(bundled):
            sys_candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]
            for sc in sys_candidates:
                try:
                    if sc and os.path.exists(sc):
                        shutil.copyfile(sc, bundled)
                        break
                except (OSError, IOError, shutil.Error):
                    continue
    except (OSError, IOError):
        pass
