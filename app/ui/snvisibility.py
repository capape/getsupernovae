from typing import List
from app.models.snmodels import AxCordInTime, Visibility
from astropy.coordinates import AltAz
from datetime import timedelta

# Use the pure visibility helpers to compute summary metadata (non-breaking)
from app.services.visibility import visibility_summary


class VisibilityWindow:
    def __init__(self, minAlt: float = 0, maxAlt: float = 90, minAz: float = 0, maxAz: float = 360):
        self.minAlt = minAlt
        self.maxAlt = maxAlt
        self.minAz = minAz
        self.maxAz = maxAz

    def getVisibility(self, site, coord, time1, time2):
        """
        Compute visibility samples for `coord` between `time1` and `time2` at `site`.

        Returns a `Visibility` object (from `snmodels`).
        """
        visible = False
        loopTime = time1
        azVisibles = []
        while loopTime < time2:
            altaz = coord.transform_to(AltAz(obstime=loopTime, location=site))
            if (
                altaz.alt.dms.d >= self.minAlt
                and altaz.alt.dms.d <= self.maxAlt
                and altaz.az.dms.d >= self.minAz
                and altaz.az.dms.d <= self.maxAz
            ):
                visible = True
                azVisibles.append(AxCordInTime(loopTime, altaz))
            loopTime = loopTime + timedelta(hours=0.5)

        azVisibles.sort(key=lambda x: x.time)

        # Compute optional summary and pass into Visibility constructor
        minAlt = maxAlt = minAz = maxAz = None
        try:
            summary = visibility_summary(azVisibles)
            if summary:
                minAlt = summary.get("minAlt")
                maxAlt = summary.get("maxAlt")
                minAz = summary.get("minAz")
                maxAz = summary.get("maxAz")
        except Exception:
            pass

        return Visibility(visible, azVisibles, minAlt=minAlt, maxAlt=maxAlt, minAz=minAz, maxAz=maxAz)
