"""Report coordinator for managing report generation (PDF and TXT).

This module coordinates report generation including:
- PDF report creation and file management
- TXT report creation
- Triggering searches when no data is available
- File opening dialogs
"""

import os
import subprocess
from typing import Callable, List, Optional

from app.models.snmodels import Supernova
from app.reports.report_pdf import createPdf
from app.reports.report_text import createText, createTextAsString
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class ReportCoordinator:
    """Coordinates report generation operations for PDF and TXT formats.

    Manages the complete report generation lifecycle including data validation,
    report creation, and user interaction for opening generated files.
    """

    def __init__(
        self,
        has_results: Callable[[], bool],
        get_results: Callable[[], Optional[List[Supernova]]],
        on_search_async: Callable[[object, str], None],
        on_results_text_update: Callable[[str], None],
        on_show_message: Optional[Callable[[str, str, str], bool]] = None,
        on_show_warning: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize report coordinator.

        Args:
            has_results: Callback to check if results are available
            get_results: Callback to get current results
            on_search_async: Callback to trigger async search (criteria, source)
            on_results_text_update: Callback to update results display text
            on_show_message: Callback to show yes/no message (title, message, type) -> bool
            on_show_warning: Callback to show warning message (title, message)
        """
        self.has_results = has_results
        self.get_results = get_results
        self.on_search_async = on_search_async
        self.on_results_text_update = on_results_text_update
        self.on_show_message = on_show_message
        self.on_show_warning = on_show_warning

    def generate_pdf_report(self, search_criteria):
        """Generate PDF report, triggering search if needed.

        Args:
            search_criteria: SupernovaCallBackData with search parameters
        """
        if search_criteria is None:
            return

        # If no results available, trigger search first
        if not self.has_results():
            try:
                self.on_search_async(search_criteria, "PDF")
            except Exception:
                log_exception(logger, "Failed to trigger search for PDF generation")
            return

        # Generate report with existing results
        try:
            results = self.get_results()
            if not results:
                log_exception(logger, "No results available for PDF generation")
                return

            # Generate text representation for display
            datatxt = createTextAsString(
                results,
                search_criteria.fromDate,
                search_criteria.observationDate,
                search_criteria.magnitude,
                search_criteria.site,
                float(search_criteria.minLatitude),
                getattr(search_criteria, "visibilityWindowName", None),
            )
            self.on_results_text_update(datatxt)

            # Generate PDF
            pdf_path = createPdf(
                results,
                search_criteria.fromDate,
                search_criteria.observationDate,
                search_criteria.magnitude,
                search_criteria.site,
                float(search_criteria.minLatitude),
                getattr(search_criteria, "visibilityWindowName", None),
            )

            # Show success message and offer to open file
            self._handle_pdf_success(pdf_path)

        except Exception:
            log_exception(logger, "Failed to generate PDF report")

    def generate_txt_report(self, search_criteria):
        """Generate TXT report, triggering search if needed.

        Args:
            search_criteria: SupernovaCallBackData with search parameters
        """
        if search_criteria is None:
            return

        # If no results available, trigger search first
        if not self.has_results():
            try:
                self.on_search_async(search_criteria, "TXT")
            except Exception:
                log_exception(logger, "Failed to trigger search for TXT generation")
            return

        # Generate report with existing results
        try:
            results = self.get_results()
            if not results:
                log_exception(logger, "No results available for TXT generation")
                return

            # Generate text representation
            datatxt = createTextAsString(
                results,
                search_criteria.fromDate,
                search_criteria.observationDate,
                search_criteria.magnitude,
                search_criteria.site,
                float(search_criteria.minLatitude),
                getattr(search_criteria, "visibilityWindowName", None),
            )
            self.on_results_text_update(datatxt)

            # Save to file
            createText(
                results,
                search_criteria.fromDate,
                search_criteria.observationDate,
                search_criteria.magnitude,
                search_criteria.site,
                float(search_criteria.minLatitude),
                getattr(search_criteria, "visibilityWindowName", None),
            )

        except Exception:
            log_exception(logger, "Failed to generate TXT report")

    def _handle_pdf_success(self, pdf_path: str):
        """Handle successful PDF generation.

        Shows success message and offers to open the file.

        Args:
            pdf_path: Path to the generated PDF file
        """
        if not self.on_show_message:
            return

        try:
            # Import here to avoid circular dependency with i18n
            from app.i18n import _

            msg = _("PDF report saved to:\n{path}").format(path=pdf_path)
            should_open = self.on_show_message(
                _("PDF Created"),
                msg + "\n\n" + _("Do you want to open it?"),
                "question",
            )

            if should_open:
                self._open_file(pdf_path)

        except Exception:
            log_exception(logger, "Failed to handle PDF success dialog")

    def _open_file(self, file_path: str):
        """Open file with system default application.

        Args:
            file_path: Path to the file to open
        """
        try:
            if os.name == "nt":  # Windows
                os.startfile(file_path)
            elif os.name == "posix":  # Linux/Mac
                if "linux" in os.sys.platform:
                    subprocess.run(["xdg-open", file_path])
                else:
                    subprocess.run(["open", file_path])
        except Exception as ex:
            if self.on_show_warning:
                from app.i18n import _

                self.on_show_warning(
                    _("Cannot open file"),
                    _(
                        "File saved but could not be opened automatically: {error}"
                    ).format(error=str(ex)),
                )
            else:
                log_exception(logger, f"Failed to open file {file_path}")
