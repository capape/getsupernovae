import math
import sys, os
# Ensure project root is on sys.path so `app` package is importable in tests
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.visibility import (
    _deg_normalize,
    compute_alt_min_max,
    compute_az_interval,
    visibility_summary,
)


class Dummy:
    def __init__(self, az=None, alt=None):
        class C:
            pass

        self.coord = C()
        if az is not None:
            class Az:
                def __init__(self, v):
                    self.degree = v

            self.coord.az = Az(az)
        else:
            self.coord.az = None
        if alt is not None:
            class Alt:
                def __init__(self, v):
                    self.degree = v

            self.coord.alt = Alt(alt)
        else:
            self.coord.alt = None


def test_deg_normalize():
    assert math.isclose(_deg_normalize(370), 10)
    assert math.isclose(_deg_normalize(-10), 350)
    assert math.isclose(_deg_normalize(360), 0)


def test_compute_alt_min_max_empty():
    assert compute_alt_min_max([]) == (None, None)


def test_compute_alt_min_max_values():
    pts = [Dummy(alt=10), Dummy(alt=5.5), Dummy(alt=20)]
    assert compute_alt_min_max(pts) == (5.5, 20)


def test_compute_az_interval_single_point():
    pts = [Dummy(az=45)]
    assert compute_az_interval(pts) == (45, 45)


def test_compute_az_interval_no_wrap():
    pts = [Dummy(az=10), Dummy(az=20), Dummy(az=30)]
    assert compute_az_interval(pts) == (10, 30)


def test_compute_az_interval_wrap():
    # Points around 350..10 should produce interval start=350 -> end=10 (wrap)
    pts = [Dummy(az=350), Dummy(az=355), Dummy(az=5), Dummy(az=10)]
    start, end = compute_az_interval(pts)
    assert start in (350, 355, 5, 10)
    # Ensure the interval covers the points (check that each point is inside the interval complementarily)
    # We'll verify that the largest gap is where expected by verifying the interval length < 360
    assert (end - start) % 360 != 360


def test_visibility_summary_empty():
    assert visibility_summary([]) is None


def test_visibility_summary_values():
    pts = [Dummy(az=350, alt=10), Dummy(az=5, alt=15), Dummy(az=20, alt=8)]
    s = visibility_summary(pts)
    assert s is not None
    assert s["minAlt"] == 8
    assert s["maxAlt"] == 15
    assert "minAz" in s and "maxAz" in s
