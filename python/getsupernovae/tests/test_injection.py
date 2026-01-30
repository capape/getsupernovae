import os
import sys

# Ensure package imports work when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from getsupernovae import AsyncRochesterDownload, RochesterSupernova, SupernovaCallBackData, sites


class DummyProvider:
    last_instance = None

    def __init__(self, timeout=None):
        DummyProvider.last_instance = self

    def fetch(self, source):
        # record that fetch was called and return empty parsed list and rows
        self.fetched = source
        return [], []


class DummyReporter:
    pass


def test_async_uses_injected_provider():
    # minimal valid callback data
    e = SupernovaCallBackData(
        magnitude="20",
        observationDate="2025-01-01",
        observationTime="00:00",
        observationHours="1",
        daysToSearch="1",
        site=sites[list(sites.keys())[0]],
        minLatitude="0",
    )

    # run downloader with dummy provider factory
    dl = AsyncRochesterDownload(e, visibility_factory=None, provider_factory=DummyProvider, reporter=None)
    # call run directly to avoid threading in tests
    dl.run()

    assert DummyProvider.last_instance is not None
    assert hasattr(DummyProvider.last_instance, "fetched")
    # result should be list (empty) and raw_rows should be set to rows (also empty list)
    assert isinstance(dl.result, list) or dl.result is None
    assert hasattr(dl, "raw_rows")


def test_reporter_propagation_to_rochester():
    dr = DummyReporter()
    rs = RochesterSupernova(visibility_factory=None, provider_factory=None, reporter=dr)
    assert getattr(rs, "reporter", None) is dr
