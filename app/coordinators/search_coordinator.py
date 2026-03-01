"""Search coordinator for managing async supernova searches and results.

This module coordinates the search process including:
- Async downloading and parsing of Rochester supernova data
- Managing search state and progress
- Refiltering cached results
- Coordinating UI updates (button states, progress bar)
"""

from threading import Thread
from typing import Any, Callable, List, Optional

from app.models.dto import SupernovaDTO
from app.models.snmodels import Supernova
from app.services.provider import NetworkRochesterProvider
from app.ui.snvisibility import VisibilityWindow
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class AsyncRochesterDownload(Thread):
    """Background thread for downloading and filtering supernova data.

    Downloads Rochester supernova list and applies filtering/sorting
    based on provided search criteria.
    """

    def __init__(
        self,
        search_criteria: Any,
        rochester_supernova,
        visibility_factory=None,
        provider_factory=None,
        reporter=None,
    ):
        """Initialize async download thread.

        Args:
            search_criteria: Search parameters and observation settings (SupernovaCallBackData)
            rochester_supernova: RochesterSupernova instance for filtering
            visibility_factory: Factory for creating visibility windows
            provider_factory: Factory for creating data providers
            reporter: Optional reporter for DI
        """
        super().__init__()
        self.result = None
        self.error = None
        self.config = search_criteria
        self.rochester_supernova = rochester_supernova
        self.visibility_factory = visibility_factory
        self.provider_factory = (
            provider_factory
            if provider_factory is not None
            else NetworkRochesterProvider
        )
        self.reporter = reporter
        self.dto_list = None

    def run(self):
        """Execute the download and filtering in background thread."""
        try:
            # Use the injected provider factory to download and parse content
            try:
                provider = self.provider_factory(timeout=20)
            except TypeError:
                # provider_factory may be a class that doesn't accept timeout
                provider = self.provider_factory()

            supernovae_list = provider.fetch()

            # Apply selection/filtering logic
            self.result = self.rochester_supernova.selectAndSortSupernovas(
                self.config, supernovae_list
            )
            # Keep raw rows so the app can re-filter without re-downloading
            self.dto_list = supernovae_list

        except (AttributeError, TypeError, ValueError, OSError, IOError) as ex:
            # Record the error for the main thread to show
            try:
                self.error = str(ex)
            except (AttributeError, TypeError, ValueError):
                self.error = "unknown error"
            self.result = None


class SearchCoordinator:
    """Coordinates supernova search operations and UI updates.

    Manages the complete search lifecycle including async downloads,
    progress tracking, caching, and UI state management.
    """

    def __init__(
        self,
        rochester_supernova,
        visibility_factory=None,
        provider_factory=None,
        reporter=None,
        on_results_updated: Optional[Callable[[List[Supernova], str], None]] = None,
        on_button_state_change: Optional[Callable[[str, str], None]] = None,
        on_progress_start: Optional[Callable[[], None]] = None,
        on_progress_end: Optional[Callable[[], None]] = None,
        on_pdf_invoke: Optional[Callable[[], None]] = None,
        on_txt_invoke: Optional[Callable[[], None]] = None,
        after_callback: Optional[Callable[[int, Callable], None]] = None,
    ):
        """Initialize search coordinator.

        Args:
            rochester_supernova: RochesterSupernova instance for data processing
            visibility_factory: Factory for creating visibility windows
            provider_factory: Factory for creating data providers
            reporter: Optional reporter for DI
            on_results_updated: Callback when results are ready (results, source)
            on_button_state_change: Callback to change button state (button_name, state)
            on_progress_start: Callback to start progress indicator
            on_progress_end: Callback to stop progress indicator
            on_pdf_invoke: Callback to invoke PDF generation
            on_txt_invoke: Callback to invoke TXT generation
            after_callback: Callback for scheduling delayed execution (delay_ms, callback)
        """
        self.rochester_supernova = rochester_supernova
        self.visibility_factory = (
            visibility_factory if visibility_factory is not None else VisibilityWindow
        )
        self.provider_factory = (
            provider_factory
            if provider_factory is not None
            else NetworkRochesterProvider
        )
        self.reporter = reporter

        # UI callbacks
        self.on_results_updated = on_results_updated
        self.on_button_state_change = on_button_state_change
        self.on_progress_start = on_progress_start
        self.on_progress_end = on_progress_end
        self.on_pdf_invoke = on_pdf_invoke
        self.on_txt_invoke = on_txt_invoke
        self.after_callback = after_callback

        # State
        self.refreshing = False
        self.last_rows: Optional[List[SupernovaDTO]] = None
        self.current_results: Optional[List[Supernova]] = None

    def search_async(self, search_criteria: Any, source: str = "SEARCH"):
        """Start an async search operation.

        Args:
            search_criteria: Search parameters (SupernovaCallBackData)
            source: Source of the search ("SEARCH", "PDF", "TXT", "REFRESH")
        """
        try:
            # Disable buttons during search
            self._set_button_state("pdf", "disabled")
            self._set_button_state("txt", "disabled")
            self._set_button_state("refresh", "disabled")

            # Start progress indicator
            if self.on_progress_start:
                self.on_progress_start()

            # Create and start download thread
            download_thread = AsyncRochesterDownload(
                search_criteria=search_criteria,
                rochester_supernova=self.rochester_supernova,
                visibility_factory=self.visibility_factory,
                provider_factory=self.provider_factory,
                reporter=self.reporter,
            )
            download_thread.start()

            # Monitor thread completion
            self._monitor_thread(download_thread, source)

        except (AttributeError, TypeError, RuntimeError):
            log_exception(logger, f"Failed to start async search for source={source}")
            self._cleanup_after_search(source)

    def refresh_search(self, search_criteria: Any):
        """Refresh search results.

        Args:
            search_criteria: Search parameters (SupernovaCallBackData)
        """
        if not self.refreshing:
            self.refreshing = True
            self._set_button_state("refresh", "disabled")
            self.search_async(search_criteria, "REFRESH")

    def refilter_from_cache(self, search_criteria: Any, source: str = "REFRESH"):
        """Re-run selection/filtering on cached data without downloading.

        Args:
            search_criteria: Search parameters (SupernovaCallBackData)
            source: Source of the refilter request
        """
        if not self.last_rows:
            # No cache available - do full search
            try:
                self.refreshing = True
                self.search_async(search_criteria, source)
            except (AttributeError, TypeError, RuntimeError):
                log_exception(logger, "Failed to fallback to full search")
            return

        try:
            # Apply filtering to cached data
            new_results = self.rochester_supernova.selectAndSortSupernovas(
                search_criteria, self.last_rows
            )
            self.current_results = new_results

            # Update UI based on source
            if self.on_results_updated:
                self.on_results_updated(new_results, source)

            # Handle post-filter actions
            if source == "PDF":
                self._set_button_state("pdf", "normal")
                if self.on_pdf_invoke:
                    self.on_pdf_invoke()
                self._set_button_state("txt", "normal")
                self._set_button_state("refresh", "normal")
            else:
                # Default to text output
                self._set_button_state("txt", "normal")
                if self.on_txt_invoke:
                    self.on_txt_invoke()
                self._set_button_state("pdf", "normal")
                self._set_button_state("refresh", "normal")

        except (AttributeError, TypeError, ValueError, KeyError):
            log_exception(logger, "Failed to refilter from cache")
            # Fallback to network refresh
            try:
                self.refreshing = True
                self.search_async(search_criteria, source)
            except (AttributeError, TypeError, RuntimeError):
                log_exception(logger, "Failed to fallback to network refresh")

    def _monitor_thread(self, thread: AsyncRochesterDownload, source: str):
        """Monitor background thread and update UI when complete.

        Args:
            thread: The download thread to monitor
            source: Source of the search operation
        """
        if thread.is_alive():
            # Check thread every 100ms
            if self.after_callback:
                self.after_callback(100, lambda: self._monitor_thread(thread, source))
        else:
            # Thread completed - process results
            self._handle_thread_completion(thread, source)

    def _handle_thread_completion(self, thread: AsyncRochesterDownload, source: str):
        """Handle completed download thread.

        Args:
            thread: The completed download thread
            source: Source of the search operation
        """
        try:
            self.current_results = thread.result

            # Update UI with results or error
            if self.on_results_updated:
                if thread.result is None:
                    error_msg = getattr(thread, "error", None)
                    if error_msg:
                        error_text = f"ERROR: Failed to fetch/parse data - {error_msg}"
                    else:
                        error_text = "ERROR: Failed to fetch data (no details)"
                    self.on_results_updated(None, error_text)
                else:
                    self.on_results_updated(thread.result, "")

            # Handle source-specific UI updates
            if source == "PDF":
                self._set_button_state("pdf", "normal")
                if self.on_pdf_invoke:
                    self.on_pdf_invoke()
                self._set_button_state("txt", "normal")
                self._set_button_state("refresh", "normal")
            elif source == "TXT":
                self._set_button_state("txt", "normal")
                if self.on_txt_invoke:
                    self.on_txt_invoke()
                self._set_button_state("pdf", "normal")
                self._set_button_state("refresh", "normal")
            elif source == "REFRESH":
                self._set_button_state("txt", "normal")
                if self.on_txt_invoke:
                    self.on_txt_invoke()
                self.refreshing = False
                self._set_button_state("pdf", "normal")
                self._set_button_state("refresh", "normal")
                # Cache raw rows for later refiltering
                try:
                    self.last_rows = getattr(thread, "dto_list", None)
                except (AttributeError, TypeError):
                    log_exception(logger, "Failed to cache downloaded rows")
                    self.last_rows = None
            else:
                # Default case
                self._cleanup_after_search(source)

        except (AttributeError, TypeError, KeyError):
            log_exception(
                logger, f"Failed to handle thread completion for source={source}"
            )
            self._cleanup_after_search(source)
        finally:
            # Always stop progress indicator
            if self.on_progress_end:
                self.on_progress_end()

    def _set_button_state(self, button: str, state: str):
        """Set UI button state.

        Args:
            button: Button identifier ("pdf", "txt", "refresh")
            state: Button state ("normal", "disabled")
        """
        if self.on_button_state_change:
            try:
                self.on_button_state_change(button, state)
            except (AttributeError, TypeError):
                log_exception(logger, f"Failed to set {button} button to {state}")

    def _cleanup_after_search(self, source: str):
        """Re-enable buttons after search completion.

        Args:
            source: Source of the search operation
        """
        try:
            self._set_button_state("pdf", "normal")
            self._set_button_state("txt", "normal")
            self._set_button_state("refresh", "normal")
            if source == "REFRESH":
                self.refreshing = False
        except (AttributeError, TypeError):
            log_exception(logger, "Failed to cleanup after search")

    def get_current_results(self) -> Optional[List[Supernova]]:
        """Get the current search results.

        Returns:
            List of supernovae or None if no results
        """
        return self.current_results

    def has_cached_data(self) -> bool:
        """Check if cached data is available for refiltering.

        Returns:
            True if cached data exists, False otherwise
        """
        return self.last_rows is not None

    def clear_cache(self):
        """Clear cached search data."""
        self.last_rows = None
