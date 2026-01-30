import os
import sys
import unittest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.provider import RochesterProvider


class TestProvider(unittest.TestCase):
    def test_parse_html_minimal_row(self):
        # minimal HTML row matching expected structure
        row_html = '''
        <table>
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
        </table>
        '''
        provider = RochesterProvider()
        result = provider.parse_html(row_html)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        sn = result[0]
        self.assertEqual(sn.name, 'SN2025abc')
        self.assertEqual(sn.host, 'NGC 1234')
        self.assertAlmostEqual(sn.mag, 15.3)
        self.assertEqual(sn.type, 'Ia')


if __name__ == '__main__':
    unittest.main()
