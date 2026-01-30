from typing import List, Protocol, Iterable
import urllib.request
from bs4 import BeautifulSoup

from app.models.snmodels import Supernova, Visibility, AxCordInTime
from app.utils.snparser import _parse_row_safe


class ISupernovaProvider(Protocol):
    def fetch(self, source: str) -> List[Supernova]:
        """Fetch supernovae from `source` (URL or path) and return list of Supernova."""


class RochesterProvider:
    """Simple adapter that fetches Rochester HTML and parses rows into Supernova objects.

    Methods:
    - fetch(url_or_path): download or read the content and parse rows
    - parse_html(html): parse and return list of Supernova
    """

    def fetch(self, source: str) -> List[Supernova]:
        # support local file paths and URLs
        try:
            if source.startswith("http://") or source.startswith("https://"):
                with urllib.request.urlopen(source, timeout=20) as resp:
                    html = resp.read()
            else:
                with open(source, "rb") as fh:
                    html = fh.read()
        except Exception:
            # propagate error to caller
            raise

        return self.parse_html(html)

    def parse_html(self, html: bytes | str) -> List[Supernova]:
        if isinstance(html, bytes):
            try:
                html = html.decode("utf-8")
            except Exception:
                html = html.decode(errors="replace")

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        result: List[Supernova] = []
        for row in rows:
            parsed = _parse_row_safe(row)
            if not parsed:
                continue

            # Create an empty visibility placeholder (adapter doesn't compute visibility)
            visibility = Visibility(False, [])

            sn = Supernova(
                parsed.get("name", ""),
                parsed.get("date"),
                parsed.get("mag"),
                parsed.get("host"),
                parsed.get("ra"),
                parsed.get("decl"),
                parsed.get("link", "") or "",
                "",               # parsed.get("coord").get_constellation() if parsed.get("coord") else None,
                parsed.get("coord"),
                parsed.get("firstObserved"),
                parsed.get("maxMagnitude"),
                parsed.get("maxMagnitudeDate"),
                parsed.get("type"),
                visibility,
            )

            # attach parsed date objects if present
            try:
                sn.maxMagnitudeDate_obj = parsed.get("maxMagnitudeDate_obj")
                sn.firstObserved_obj = parsed.get("firstObserved_obj")
            except Exception:
                pass

            result.append(sn)

        return result


class NetworkRochesterProvider:
    """Network adapter that fetches Rochester HTML and returns parsed Supernovas
    and raw HTML rows. It uses `RochesterProvider.parse_html` to parse content.
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch(self, source: str):
        """Fetch from `source` (URL or local path). Returns (parsed_list, rows).

        parsed_list: List[Supernova]
        rows: ResultSet of <tr> elements (BeautifulSoup list)
        """
        import ssl
        try:
            if source.startswith("http://") or source.startswith("https://"):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(source, context=ctx, timeout=self.timeout) as resp:
                    html = resp.read()
            else:
                with open(source, "rb") as fh:
                    html = fh.read()
        except Exception:
            raise

        # parse using RochesterProvider
        parsed = RochesterProvider().parse_html(html)

        # also return raw rows so existing code can continue to use them
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        return parsed, rows

