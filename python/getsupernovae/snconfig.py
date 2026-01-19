import os
import sys
import json
import shutil
from collections import OrderedDict
from astropy.coordinates import EarthLocation
import astropy.units as u


def load_old_supernovae(path=None):
    """Load old supernova names from a file (one per line). If the file
    is missing, returns an empty list."""
    candidates = []
    if path:
        candidates.append(path)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(os.path.join(xdg, "getsupernovae", "old_supernovae.txt"))
    else:
        candidates.append(os.path.expanduser("~/.config/getsupernovae/old_supernovae.txt"))
    # macOS
    candidates.append(os.path.expanduser("~/Library/Application Support/getsupernovae/old_supernovae.txt"))
    # Windows APPDATA
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "getsupernovae", "old_supernovae.txt"))
    # package-local fallback
    candidates.append(os.path.join(os.path.dirname(__file__), "old_supernovae.txt"))

    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                lines = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
            return lines
        except Exception:
            continue

    return []


def load_sites(path=None):
    """Load observing sites from a JSON file and return an OrderedDict of
    name -> EarthLocation. If missing, return reasonable defaults."""
    defaults = OrderedDict(
        [
            ("Sabadell", {"lat": 41.55, "lon": 2.09, "height": 224}),
            ("Sant Quirze", {"lat": 41.32, "lon": 2.04, "height": 196}),
            ("Requena", {"lat": 39.45, "lon": -1.21, "height": 587}),
        ]
    )

    candidates = []
    if path:
        candidates.append(path)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(os.path.join(xdg, "getsupernovae", "sites.json"))
    else:
        candidates.append(os.path.expanduser("~/.config/getsupernovae/sites.json"))
    candidates.append(os.path.expanduser("~/Library/Application Support/getsupernovae/sites.json"))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "getsupernovae", "sites.json"))
    candidates.append(os.path.join(os.path.dirname(__file__), "sites.json"))

    sites_conf = None
    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                sites_conf = json.load(fh)
            break
        except Exception:
            sites_conf = None
            continue

    result = OrderedDict()
    try:
        if isinstance(sites_conf, dict):
            items = sites_conf.items()
        else:
            items = defaults.items()
    except Exception:
        items = defaults.items()

    for name, v in items:
        try:
            if isinstance(v, dict):
                lat = float(v.get("lat", 0.0))
                lon = float(v.get("lon", 0.0))
                h = float(v.get("height", 0.0))
            else:
                # try EarthLocation-like
                lat = float(v.lat.value)
                lon = float(v.lon.value)
                h = float(v.height.value)
            result[name] = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=h * u.m)
        except Exception:
            continue

    return result


def load_visibility_windows(path=None):
    defaults = {"Default": {"minAlt": 0.0, "maxAlt": 90.0, "minAz": 0.0, "maxAz": 360.0}}
    candidates = []
    if path:
        candidates.append(path)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(os.path.join(xdg, "getsupernovae", "visibility_windows.json"))
    else:
        candidates.append(os.path.expanduser("~/.config/getsupernovae/visibility_windows.json"))
    candidates.append(os.path.join(os.path.dirname(__file__), "visibility_windows.json"))

    for p in candidates:
        try:
            if not p:
                continue
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except Exception:
            continue

    return defaults


def get_user_config_dir():
    """Return the user config directory for getsupernovae.

    Respects XDG on Linux, uses macOS Application Support, or APPDATA on Windows.
    """
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
    except Exception:
        return

    sites_path = os.path.join(cfg, "sites.json")
    old_path = os.path.join(cfg, "old_supernovae.txt")

    # default sites
    default_sites = {
        "Sabadell": {"lat": 41.55, "lon": 2.09, "height": 224}
    }

    # default old list
    default_old = []

    try:
        if not os.path.exists(sites_path):
            with open(sites_path, "w", encoding="utf-8") as fh:
                json.dump(default_sites, fh, indent=2)
    except Exception:
        pass

    try:
        if not os.path.exists(old_path):
            with open(old_path, "w", encoding="utf-8") as fh:
                for name in default_old:
                    fh.write(name + "\n")
    except Exception:
        pass

    # default visibility windows
    default_visibility = {
        "Default": {"minAlt": 0.0, "maxAlt": 90.0, "minAz": 0.0, "maxAz": 360.0}
    }
    vis_path = os.path.join(cfg, "visibility_windows.json")
    try:
        if not os.path.exists(vis_path):
            with open(vis_path, "w", encoding="utf-8") as fh:
                json.dump(default_visibility, fh, indent=2)
    except Exception:
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
                except Exception:
                    continue
    except Exception:
        pass
