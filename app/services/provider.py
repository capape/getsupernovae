"""Provider module for fetching supernova data from various sources."""

import urllib.request
from typing import List, Protocol

from bs4 import BeautifulSoup

from app.models.dto import SupernovaDTO
from app.utils.snparser import _parse_row_safe


class ISupernovaProvider(Protocol):
    """Protocol defining the interface for supernova data providers."""

    def fetch(self) -> List[SupernovaDTO]:
        """Fetch supernovae from provider and return list of SupernovaDTO."""


class RochesterProvider:
    """Abstract base class for Rochester providers."""

    def parse_html(self, html: bytes | str) -> List[SupernovaDTO]:
        html_str: str
        if isinstance(html, bytes):
            try:
                html_str = html.decode("utf-8")
            except UnicodeDecodeError:
                html_str = html.decode(errors="replace")
        else:
            html_str = html

        soup = BeautifulSoup(html_str, "html.parser")
        rows = soup.find_all("tr")
        result: List[SupernovaDTO] = []
        for row in rows:
            parsed = _parse_row_safe(row)
            if not parsed:
                continue

            sn = SupernovaDTO(
                parsed.get("name", ""),
                parsed.get("date"),
                parsed.get("date_obj"),
                parsed.get("mag"),
                parsed.get("host"),
                parsed.get("ra"),
                parsed.get("decl"),
                parsed.get("link", "") or "",
                parsed.get("coord"),
                parsed.get("first_observed"),
                parsed.get("max_magnitude"),
                parsed.get("max_magnitude_date"),
                parsed.get("type"),
                parsed.get("max_magnitude_date_obj"),
                parsed.get("first_observed_obj"),
            )
            result.append(sn)

        return result


class FileRochesterProvider(RochesterProvider):
    """Simple adapter that fetches Rochester HTML and parses rows into Supernova objects.

    Methods:
    - fetch(url_or_path): download or read the content and parse rows
    - parse_html(html): parse and return list of Supernova
    """

    def __init__(self, source: str, timeout: int = 20) -> None:
        self.timeout = timeout
        self.source = source

    def fetch(self) -> List[SupernovaDTO]:
        """Fetch supernova data from the source file."""
        # support local file paths and URLs
        try:
            with open(self.source, "rb") as fh:
                html = fh.read()
        except (OSError, IOError):
            # propagate error to caller
            raise

        return self.parse_html(html)


class NetworkRochesterProvider(RochesterProvider):
    """Network adapter that fetches Rochester HTML and returns parsed Supernovas
    and raw HTML rows. It uses `RochesterProvider.parse_html` to parse content.
    """

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.source = "https://www.rochesterastronomy.org/snimages/snactive.html"

    def fetch(self) -> List[SupernovaDTO]:
        """Fetch from `Rochester source` Returns (parsed_list, rows).

        parsed_list: List[Supernova]
        rows: ResultSet of <tr> elements (BeautifulSoup list)
        """
        import ssl

        source = self.source
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(source, context=ctx, timeout=self.timeout) as resp:
                html = resp.read()

        except (OSError, IOError, urllib.error.URLError):
            raise

        # parse using RochesterProvider
        return self.parse_html(html)
