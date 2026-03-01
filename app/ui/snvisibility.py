"""Visibility window calculations for supernova observations."""

from datetime import timedelta

from astropy.coordinates import AltAz

from app.models.snmodels import AxCordInTime, Visibility

# Use the pure visibility helpers to compute summary metadata (non-breaking)
from app.services.visibility import visibility_summary


class VisibilityWindow:
    def __init__(
        self,
        min_alt: float = 0,
        max_alt: float = 90,
        min_az: float = 0,
        max_az: float = 360,
    ):
        self.min_alt = min_alt
        self.max_alt = max_alt
        self.min_az = min_az
        self.max_az = max_az

    def get_visibility(self, site, coord, time1, time2):
        """
        Compute visibility samples for `coord` between `time1` and `time2` at `site`.

        Returns a `Visibility` object (from `snmodels`).
        """
        visible = False
        loop_time = time1
        az_visibles = []
        while loop_time < time2:
            altaz = coord.transform_to(AltAz(obstime=loop_time, location=site))
            if (
                altaz.alt.dms.d >= self.min_alt
                and altaz.alt.dms.d <= self.max_alt
                and altaz.az.dms.d >= self.min_az
                and altaz.az.dms.d <= self.max_az
            ):
                visible = True
                az_visibles.append(AxCordInTime(loop_time, altaz))
            loop_time = loop_time + timedelta(hours=0.5)

        az_visibles.sort(key=lambda x: x.time)

        # Compute optional summary and pass into Visibility constructor
        min_alt = max_alt = min_az = max_az = None
        try:
            summary = visibility_summary(az_visibles)
            if summary:
                min_alt = summary.get("min_alt")
                max_alt = summary.get("max_alt")
                min_az = summary.get("min_az")
                max_az = summary.get("max_az")
        except (AttributeError, TypeError, KeyError, ValueError):
            pass

        return Visibility(
            visible, az_visibles, min_alt=min_alt, max_alt=max_alt, min_az=min_az, max_az=max_az
        )
