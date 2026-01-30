import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.provider import NetworkRochesterProvider


class TestNetworkProvider(unittest.TestCase):
    def test_fetch_from_fixture_file(self):
        fixture = os.path.join(os.path.dirname(__file__), 'fixtures', 'snactive.html')
        provider = NetworkRochesterProvider(timeout=5)
        parsed, rows = provider.fetch(fixture)

        # Expect parsed list and rows to be non-empty and lengths to match
        self.assertIsInstance(parsed, list)
        self.assertIsInstance(rows, list)
        self.assertGreaterEqual(len(parsed), 2)
        self.assertGreaterEqual(len(rows), 2)

        # Basic checks on first parsed item
        first = parsed[0]
        self.assertTrue(hasattr(first, 'name'))
        self.assertEqual(first.name, 'SN2025abc')
        self.assertEqual(first.host, 'NGC 1234')


if __name__ == '__main__':
    unittest.main()
