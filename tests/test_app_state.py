"""Unit tests for app_state module."""

import os
import sys
import unittest

# Make the package root importable when running tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.state.app_state import (
    AppState,
    AppStateManager,
    ResultsState,
    SearchState,
    UIState,
)


class TestSearchState(unittest.TestCase):
    """Tests for SearchState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = SearchState()
        self.assertEqual(state.magnitude, "17.5")
        self.assertEqual(state.days_to_search, "30")
        self.assertEqual(state.observation_date, "")
        self.assertEqual(state.observation_time, "")
        self.assertEqual(state.observation_duration, "6")
        self.assertIsNone(state.site)
        self.assertIsNone(state.visibility_window)
        self.assertEqual(state.min_latitude, "")

    def test_custom_values(self):
        """Test creating state with custom values."""
        state = SearchState(
            magnitude="16.0",
            days_to_search="60",
            observation_date="2024-01-15",
            observation_time="22:00",
            observation_duration="8",
            site="My Observatory",
            visibility_window="Evening",
            min_latitude="20",
        )
        self.assertEqual(state.magnitude, "16.0")
        self.assertEqual(state.days_to_search, "60")
        self.assertEqual(state.observation_date, "2024-01-15")
        self.assertEqual(state.observation_time, "22:00")
        self.assertEqual(state.observation_duration, "8")
        self.assertEqual(state.site, "My Observatory")
        self.assertEqual(state.visibility_window, "Evening")
        self.assertEqual(state.min_latitude, "20")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = SearchState(magnitude="16.0", site="Test Site", visibility_window="Evening")
        result = state.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["magnitude"], "16.0")
        self.assertEqual(result["site"], "Test Site")
        self.assertEqual(result["visibility_window"], "Evening")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "magnitude": "15.5",
            "days_to_search": "45",
            "site": "Observatory",
            "visibility_window": "Default",
            "observation_date": "2024-02-01",
        }
        state = SearchState.from_dict(data)

        self.assertEqual(state.magnitude, "15.5")
        self.assertEqual(state.days_to_search, "45")
        self.assertEqual(state.site, "Observatory")
        self.assertEqual(state.visibility_window, "Default")
        self.assertEqual(state.observation_date, "2024-02-01")

    def test_from_dict_handles_missing_keys(self):
        """Test from_dict uses defaults for missing keys."""
        data = {"magnitude": "18.0"}
        state = SearchState.from_dict(data)

        self.assertEqual(state.magnitude, "18.0")
        self.assertEqual(state.days_to_search, "30")  # default
        self.assertIsNone(state.site)  # default


class TestResultsState(unittest.TestCase):
    """Tests for ResultsState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = ResultsState()
        self.assertEqual(state.supernovas_found, 0)
        self.assertEqual(state.cached_dto_list, [])
        self.assertFalse(state.refreshing)
        self.assertIsNone(state.last_error)
        self.assertEqual(state.sort_column, 0)
        self.assertFalse(state.sort_reverse)
        self.assertEqual(state.selected_items, [])

    def test_clear_results(self):
        """Test clearing results."""
        state = ResultsState(
            supernovas_found=10,
            cached_dto_list=[{"name": "SN2024a"}],
            last_error="Some error",
            selected_items=["item1"],
        )

        state.clear_results()

        self.assertEqual(state.supernovas_found, 0)
        self.assertEqual(state.cached_dto_list, [])
        self.assertIsNone(state.last_error)
        self.assertEqual(state.selected_items, [])

    def test_has_results(self):
        """Test has_results method."""
        state = ResultsState()
        self.assertFalse(state.has_results())

        state.supernovas_found = 5
        self.assertTrue(state.has_results())

    def test_has_cached_data(self):
        """Test has_cached_data method."""
        state = ResultsState()
        self.assertFalse(state.has_cached_data())

        state.cached_dto_list = [{"name": "SN2024a"}]
        self.assertTrue(state.has_cached_data())


class TestUIState(unittest.TestCase):
    """Tests for UIState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = UIState()
        self.assertEqual(state.language, "en")
        self.assertFalse(state.dark_mode)
        self.assertIsNone(state.window_width)
        self.assertIsNone(state.window_height)
        self.assertIsNone(state.window_x)
        self.assertIsNone(state.window_y)

    def test_custom_values(self):
        """Test creating state with custom values."""
        state = UIState(
            language="es",
            dark_mode=True,
            window_width=1024,
            window_height=768,
            window_x=100,
            window_y=50,
        )
        self.assertEqual(state.language, "es")
        self.assertTrue(state.dark_mode)
        self.assertEqual(state.window_width, 1024)
        self.assertEqual(state.window_height, 768)
        self.assertEqual(state.window_x, 100)
        self.assertEqual(state.window_y, 50)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = UIState(language="ca", dark_mode=True, window_width=800)
        result = state.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["language"], "ca")
        self.assertTrue(result["dark_mode"])
        self.assertEqual(result["window_width"], 800)

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "language": "es",
            "dark_mode": True,
            "window_width": 1280,
            "window_height": 720,
        }
        state = UIState.from_dict(data)

        self.assertEqual(state.language, "es")
        self.assertTrue(state.dark_mode)
        self.assertEqual(state.window_width, 1280)
        self.assertEqual(state.window_height, 720)


class TestAppState(unittest.TestCase):
    """Tests for AppState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = AppState()
        self.assertIsInstance(state.search, SearchState)
        self.assertIsInstance(state.results, ResultsState)
        self.assertIsInstance(state.ui, UIState)

    def test_to_dict_excludes_results(self):
        """Test serialization excludes results state."""
        state = AppState()
        state.results.supernovas_found = 10
        state.search.magnitude = "16.0"
        state.ui.language = "es"

        result = state.to_dict()

        self.assertIn("search", result)
        self.assertIn("ui", result)
        self.assertNotIn("results", result)
        self.assertEqual(result["search"]["magnitude"], "16.0")
        self.assertEqual(result["ui"]["language"], "es")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "search": {"magnitude": "15.0", "site": "Test"},
            "ui": {"language": "ca", "dark_mode": True},
        }
        state = AppState.from_dict(data)

        self.assertEqual(state.search.magnitude, "15.0")
        self.assertEqual(state.search.site, "Test")
        self.assertEqual(state.ui.language, "ca")
        self.assertTrue(state.ui.dark_mode)


class TestAppStateManager(unittest.TestCase):
    """Tests for AppStateManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = AppStateManager()

    def test_initial_state(self):
        """Test manager starts with default state."""
        self.assertIsInstance(self.manager.state, AppState)
        self.assertEqual(self.manager.state.search.magnitude, "17.5")
        self.assertEqual(self.manager.state.ui.language, "en")

    def test_initial_custom_state(self):
        """Test manager can start with custom state."""
        custom_state = AppState(search=SearchState(magnitude="16.0"), ui=UIState(language="es"))
        manager = AppStateManager(initial_state=custom_state)

        self.assertEqual(manager.state.search.magnitude, "16.0")
        self.assertEqual(manager.state.ui.language, "es")

    def test_add_listener(self):
        """Test adding state change listeners."""
        callback_called = []

        def callback(state):
            callback_called.append(state)

        self.manager.add_listener("search", callback)
        self.manager.update_search_state(magnitude="16.0")

        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0].magnitude, "16.0")

    def test_multiple_listeners(self):
        """Test multiple listeners are notified."""
        calls = {"listener1": 0, "listener2": 0}

        def listener1(state):
            calls["listener1"] += 1

        def listener2(state):
            calls["listener2"] += 1

        self.manager.add_listener("search", listener1)
        self.manager.add_listener("search", listener2)
        self.manager.update_search_state(magnitude="16.0")

        self.assertEqual(calls["listener1"], 1)
        self.assertEqual(calls["listener2"], 1)

    def test_remove_listener(self):
        """Test removing listeners."""
        callback_called = []

        def callback(state):
            callback_called.append(state)

        self.manager.add_listener("search", callback)
        self.manager.update_search_state(magnitude="16.0")
        self.assertEqual(len(callback_called), 1)

        self.manager.remove_listener("search", callback)
        self.manager.update_search_state(magnitude="15.0")
        self.assertEqual(len(callback_called), 1)  # Not called again

    def test_listener_categories(self):
        """Test listeners only called for their category."""
        calls = {"search": 0, "results": 0, "ui": 0}

        def search_listener(state):
            calls["search"] += 1

        def results_listener(state):
            calls["results"] += 1

        def ui_listener(state):
            calls["ui"] += 1

        self.manager.add_listener("search", search_listener)
        self.manager.add_listener("results", results_listener)
        self.manager.add_listener("ui", ui_listener)

        self.manager.update_search_state(magnitude="16.0")
        self.assertEqual(calls["search"], 1)
        self.assertEqual(calls["results"], 0)
        self.assertEqual(calls["ui"], 0)

        self.manager.update_results_state(supernovas_found=10)
        self.assertEqual(calls["search"], 1)
        self.assertEqual(calls["results"], 1)
        self.assertEqual(calls["ui"], 0)

        self.manager.update_ui_state(language="es")
        self.assertEqual(calls["search"], 1)
        self.assertEqual(calls["results"], 1)
        self.assertEqual(calls["ui"], 1)

    def test_all_category_listener(self):
        """Test 'all' category listener is notified for any change."""
        call_count = 0

        def all_listener(category, state):
            nonlocal call_count
            call_count += 1

        self.manager.add_listener("all", all_listener)

        self.manager.update_search_state(magnitude="16.0")
        self.assertEqual(call_count, 1)

        self.manager.update_results_state(supernovas_found=5)
        self.assertEqual(call_count, 2)

        self.manager.update_ui_state(language="ca")
        self.assertEqual(call_count, 3)

    def test_update_search_state(self):
        """Test updating search state."""
        self.manager.update_search_state(magnitude="16.0", days_to_search="45", site="Observatory")

        self.assertEqual(self.manager.state.search.magnitude, "16.0")
        self.assertEqual(self.manager.state.search.days_to_search, "45")
        self.assertEqual(self.manager.state.search.site, "Observatory")

    def test_update_results_state(self):
        """Test updating results state."""
        self.manager.update_results_state(
            supernovas_found=15, refreshing=True, last_error="Test error"
        )

        self.assertEqual(self.manager.state.results.supernovas_found, 15)
        self.assertTrue(self.manager.state.results.refreshing)
        self.assertEqual(self.manager.state.results.last_error, "Test error")

    def test_update_ui_state(self):
        """Test updating UI state."""
        self.manager.update_ui_state(language="es", dark_mode=True, window_width=1024)

        self.assertEqual(self.manager.state.ui.language, "es")
        self.assertTrue(self.manager.state.ui.dark_mode)
        self.assertEqual(self.manager.state.ui.window_width, 1024)

    def test_clear_results(self):
        """Test clearing results through manager."""
        self.manager.update_results_state(
            supernovas_found=10, cached_dto_list=[{"name": "SN"}], last_error="Error"
        )

        self.manager.clear_results()

        self.assertEqual(self.manager.state.results.supernovas_found, 0)
        self.assertEqual(self.manager.state.results.cached_dto_list, [])
        self.assertIsNone(self.manager.state.results.last_error)

    def test_reset_to_defaults(self):
        """Test resetting state to defaults."""
        # Modify all states
        self.manager.update_search_state(magnitude="15.0", site="Test")
        self.manager.update_results_state(supernovas_found=20)
        self.manager.update_ui_state(language="es", dark_mode=True)

        # Reset
        self.manager.reset_to_defaults()

        # Verify defaults
        self.assertEqual(self.manager.state.search.magnitude, "17.5")
        self.assertIsNone(self.manager.state.search.site)
        self.assertEqual(self.manager.state.results.supernovas_found, 0)
        self.assertEqual(self.manager.state.ui.language, "en")
        self.assertFalse(self.manager.state.ui.dark_mode)

    def test_invalid_listener_category(self):
        """Test adding listener with invalid category raises error."""

        def callback(state):
            pass

        with self.assertRaises(ValueError):
            self.manager.add_listener("invalid_category", callback)


if __name__ == "__main__":
    unittest.main()
