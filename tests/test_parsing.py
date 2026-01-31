import os
import sys
import unittest
from bs4 import BeautifulSoup

# make the package root importable when running tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from getsupernovae import parse_magnitude, _parse_row_safe

class TestParsing(unittest.TestCase):
    def test_parse_magnitude_examples(self):
        self.assertEqual(parse_magnitude('15.3'), (15.3, None))
        self.assertEqual(parse_magnitude('>19'), (19.0, '>'))
        self.assertEqual(parse_magnitude('  -1.2'), (-1.2, None))
        self.assertEqual(parse_magnitude('17?'), (17.0, None))
        self.assertEqual(parse_magnitude(''), (None, None))
        self.assertEqual(parse_magnitude(None), (None, None))

    def test_parse_row_safe_basic(self):
        # build a table row with 12 tds matching expected page layout
        row_html = '''
        <tr>
            <td><a href="../snimages/sn2025abc.html">SN2025abc</a></td>
            <td>NGC 1234</td>
            <td>12:34:56</td>
            <td>+12:34:56</td>
            <td></td>
            <td>15.3</td>
            <td>2025/12/01</td>
            <td>Ia</td>
            <td></td>
            <td>14.8</td>
            <td>2025/12/03</td>
            <td>2025/11/30</td>
        </tr>
        '''
        soup = BeautifulSoup(row_html, 'html.parser')
        tr = soup.find('tr')
        parsed = _parse_row_safe(tr)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['name'], 'SN2025abc')
        self.assertTrue(parsed['link'].startswith('https://www.rochesterastronomy.org/'))
        self.assertEqual(parsed['host'], 'NGC 1234')
        self.assertAlmostEqual(parsed['mag'], 15.3)
        self.assertIsNone(parsed['mag_limit'])
        self.assertEqual(parsed['date'], '2025-12-01')
        # date objects should be present
        self.assertIsNotNone(parsed.get('date_obj'))
        self.assertEqual(parsed['type'], 'Ia')
        self.assertEqual(parsed['maxMagnitude'], '14.8')
        # maxMagnitudeDate and firstObserved should be normalized and have date objects
        self.assertEqual(parsed['maxMagnitudeDate'], '2025-12-03')
        self.assertIsNotNone(parsed.get('maxMagnitudeDate_obj'))
        self.assertEqual(parsed['firstObserved'], '2025-11-30')
        self.assertIsNotNone(parsed.get('firstObserved_obj'))

if __name__ == '__main__':
    unittest.main()
