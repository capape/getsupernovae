"""Pure visibility calculation helpers.

These functions accept a sequence of objects with a `.coord` attribute
where `.coord.alt.degree` and `.coord.az.degree` are numeric (astropy
Angle/Quantity or simple numbers). They return min/max altitude and
an azimuth interval that correctly handles wrap-around across 0/360°.
"""
from typing import Iterable, List, Tuple, Optional


def _deg_normalize(az: float) -> float:
    """Normalize azimuth to [0, 360)."""
    try:
        a = float(az) % 360.0
        if a < 0:
            a += 360.0
        return a
    except Exception:
        raise


def compute_alt_min_max(az_coords: Iterable) -> Tuple[Optional[float], Optional[float]]:
    """Return (min_alt_deg, max_alt_deg) in degrees, or (None, None) if empty.

    Each element of `az_coords` is expected to expose `coord.alt.degree`.
    """
    alts: List[float] = []
    for c in az_coords:
        try:
            a = getattr(getattr(c, "coord", c), "alt", None)
            if a is None:
                continue
            # support astropy Quantity/Angle with .degree
            val = getattr(a, "degree", None)
            if val is None:
                val = float(a)
            alts.append(float(val))
        except Exception:
            continue

    if not alts:
        return None, None
    return min(alts), max(alts)


def compute_az_interval(az_coords: Iterable) -> Tuple[Optional[float], Optional[float]]:
    """Compute a minimal covering azimuth interval (minAz, maxAz) in degrees.

    The returned interval may wrap (minAz > maxAz) to indicate e.g. 350..10°.
    Returns (None, None) if no azimuths available.
    """
    azs: List[float] = []
    for c in az_coords:
        try:
            a = getattr(getattr(c, "coord", c), "az", None)
            if a is None:
                continue
            val = getattr(a, "degree", None)
            if val is None:
                val = float(a)
            azs.append(_deg_normalize(float(val)))
        except Exception:
            continue

    if not azs:
        return None, None

    # Sort unique values
    azs = sorted(set(azs))

    # If only one point, return that point as degenerate interval
    if len(azs) == 1:
        return azs[0], azs[0]

    # Find largest gap between consecutive azimuths (including wrap)
    gaps: List[Tuple[float, int]] = []  # (gap_size, index_of_first)
    for i in range(len(azs)):
        a1 = azs[i]
        a2 = azs[(i + 1) % len(azs)]
        gap = (a2 - a1) if i + 1 < len(azs) else (azs[0] + 360.0 - azs[-1])
        gaps.append((gap, i))

    # largest gap index
    largest_gap, idx = max(gaps, key=lambda x: x[0])

    # interval is complement of largest gap: from next element to current
    start = azs[(idx + 1) % len(azs)]
    end = azs[idx]
    # start..end is the minimal covering interval; may wrap if start > end
    return start, end


def visibility_summary(az_coords: Iterable) -> Optional[dict]:
    """Return a dict with keys: minAlt, maxAlt, minAz, maxAz, visible.

    Returns None if no valid coordinates are present.
    """
    min_alt, max_alt = compute_alt_min_max(az_coords)
    min_az, max_az = compute_az_interval(az_coords)
    if min_alt is None and min_az is None:
        return None
    return {
        "minAlt": min_alt,
        "maxAlt": max_alt,
        "minAz": min_az,
        "maxAz": max_az,
        "visible": True if (min_alt is not None or min_az is not None) else False,
    }
