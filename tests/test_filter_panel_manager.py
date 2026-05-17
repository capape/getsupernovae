"""Tests for FilterPanelManager

Tests the filter panel UI manager functionality, including widget creation,
state management, and callback integration.
"""

import os
import sys

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from app.ui.filter_panel_manager import FilterPanelCallbacks, FilterPanelManager


class TestFilterPanelManager(unittest.TestCase):
    """Test suite for FilterPanelManager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create root window for tests
        self.root = tk.Tk()

        # Create mock variables
        self.variables = {
            "magnitude": tk.StringVar(value="15.0"),
            "days_to_search": tk.StringVar(value="30"),
            "observation_date": tk.StringVar(value="2024-01-01"),
            "observation_time": tk.StringVar(value="20:00"),
            "observation_duration": tk.StringVar(value="8"),
            "site": tk.StringVar(value="Test Site"),
            "visibility_window": tk.StringVar(value=""),
            "min_latitude": tk.StringVar(value="30"),
        }

        # Mock sites and visibility windows
        self.sites = {
            "Test Site": Mock(),
            "Another Site": Mock(),
        }

        self.visibility_windows = {
            "Night Window": {
                "min_alt": 30.0,
                "max_alt": 85.0,
                "min_az": 0.0,
                "max_az": 360.0,
            }
        }

        # Create mock callbacks
        self.callbacks = FilterPanelCallbacks(
            on_clear_results=Mock(),
            on_persist_prefs=Mock(),
            on_update_visibility_ui=Mock(),
            on_language_change=Mock(),
            on_add_site=Mock(),
            on_add_visibility_window=Mock(),
        )

        # Create dark mode variable
        self.dark_mode = tk.BooleanVar(value=False)

    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_initialization(self):
        """Test FilterPanelManager initialization."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        self.assertIsNotNone(manager)
        self.assertEqual(manager.parent, self.root)
        self.assertEqual(manager.variables, self.variables)
        self.assertEqual(manager.sites, self.sites)
        self.assertEqual(manager.visibility_windows, self.visibility_windows)
        self.assertEqual(manager.callbacks, self.callbacks)
        self.assertEqual(manager.dark_mode, self.dark_mode)
        self.assertIsNone(manager.frame)
        self.assertEqual(manager.widgets, {})

    def test_build_creates_frame(self):
        """Test that build() creates and returns a frame."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        frame = manager.build()

        self.assertIsNotNone(frame)
        self.assertIsInstance(frame, ttk.Frame)
        self.assertEqual(manager.frame, frame)

    def test_build_creates_all_widgets(self):
        """Test that build() creates all expected widgets."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        # Check that all expected widgets were created
        expected_widgets = [
            "label_magnitude",
            "entry_magnitude",
            "label_days_to_search",
            "entry_days_to_search",
            "label_observation_date",
            "entry_observation_date",
            "label_init_time",
            "entry_init_time",
            "label_duration",
            "entry_duration",
            "label_site",
            "combobox_site",
            "button_add_site",
            "label_visibility",
            "combobox_visibility",
            "button_add_visibility",
            "label_min_latitude",
            "entry_min_latitude",
            "label_visibility_values",
            "label_language",
            "combobox_language",
        ]

        for widget_name in expected_widgets:
            self.assertIn(widget_name, manager.widgets, f"Missing widget: {widget_name}")

    def test_magnitude_entry_linked_to_variable(self):
        """Test that magnitude entry is properly linked to its variable."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        # Change variable and verify entry updates
        self.variables["magnitude"].set("18.5")
        self.root.update()

        entry = manager.widgets["entry_magnitude"]
        self.assertEqual(entry.get(), "18.5")

    def test_site_combobox_has_correct_values(self):
        """Test that site combobox is populated with site names."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        combobox = manager.widgets["combobox_site"]
        values = combobox["values"]

        self.assertIn("Test Site", values)
        self.assertIn("Another Site", values)

    def test_visibility_window_combobox_has_correct_values(self):
        """Test that visibility window combobox includes empty option."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        combobox = manager.widgets["combobox_visibility"]
        values = combobox["values"]

        # Should have empty string first
        self.assertEqual(values[0], "")
        self.assertIn("Night Window", values)

    def test_add_site_button_calls_callback(self):
        """Test that add site button triggers the callback."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        button = manager.widgets["button_add_site"]
        button.invoke()

        self.callbacks.on_add_site.assert_called_once()

    def test_add_visibility_window_button_calls_callback(self):
        """Test that add visibility window button triggers the callback."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        button = manager.widgets["button_add_visibility"]
        button.invoke()

        self.callbacks.on_add_visibility_window.assert_called_once()

    def test_update_visibility_values_label(self):
        """Test updating the visibility values label."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        test_text = "min_alt: 30.0° max_alt: 85.0°"
        manager.update_visibility_values_label(test_text)

        label = manager.widgets["label_visibility_values"]
        self.assertEqual(label.cget("text"), test_text)

    def test_set_min_latitude_state_disabled(self):
        """Test disabling the min latitude entry."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        manager.set_min_latitude_state("disabled")

        entry = manager.widgets["entry_min_latitude"]
        self.assertEqual(str(entry.cget("state")), "disabled")

    def test_set_min_latitude_state_normal(self):
        """Test enabling the min latitude entry."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        # First disable, then enable
        manager.set_min_latitude_state("disabled")
        manager.set_min_latitude_state("normal")

        entry = manager.widgets["entry_min_latitude"]
        self.assertEqual(str(entry.cget("state")), "normal")

    def test_update_site_values(self):
        """Test updating site combobox values."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        new_sites = ["New Site 1", "New Site 2", "New Site 3"]
        manager.update_site_values(new_sites)

        combobox = manager.widgets["combobox_site"]
        values = combobox["values"]

        self.assertEqual(list(values), new_sites)

    def test_update_visibility_window_values(self):
        """Test updating visibility window combobox values."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        new_windows = ["", "Window 1", "Window 2"]
        manager.update_visibility_window_values(new_windows)

        combobox = manager.widgets["combobox_visibility"]
        values = combobox["values"]

        self.assertEqual(list(values), new_windows)

    def test_refresh_labels_updates_text(self):
        """Test that refresh_labels updates all label texts."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        # Mock the translation function
        with patch("app.ui.filter_panel_manager._") as mock_translate:
            mock_translate.side_effect = lambda x: f"TRANSLATED: {x}"

            manager.refresh_labels()

            # Verify at least one label was updated
            label = manager.widgets["label_magnitude"]
            text = label.cget("text")
            self.assertIn("TRANSLATED:", text)

    def test_apply_theme_light_mode(self):
        """Test applying light theme."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        manager.apply_theme(dark_mode=False)

        # Verify Rochester text has light background
        if "text_rochester" in manager.widgets:
            text_widget = manager.widgets["text_rochester"]
            bg = text_widget.cget("background")
            # Should be light color (not dark)
            self.assertIsNotNone(bg)

    def test_apply_theme_dark_mode(self):
        """Test applying dark theme."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        manager.apply_theme(dark_mode=True)

        # Verify Rochester text has dark background
        if "text_rochester" in manager.widgets:
            text_widget = manager.widgets["text_rochester"]
            bg = text_widget.cget("background")
            self.assertIsNotNone(bg)

    def test_variable_traces_trigger_callbacks(self):
        """Test that changing variables triggers appropriate callbacks."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()
        self.root.update()

        # Reset mocks to ignore setup calls
        self.callbacks.on_clear_results.reset_mock()
        self.callbacks.on_persist_prefs.reset_mock()

        # Change magnitude variable
        self.variables["magnitude"].set("17.0")
        self.root.update()

        # Should trigger clear and persist callbacks
        self.assertTrue(self.callbacks.on_clear_results.called)
        self.assertTrue(self.callbacks.on_persist_prefs.called)

    def test_visibility_window_change_triggers_update_ui(self):
        """Test that changing visibility window triggers UI update callback."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()
        self.root.update()

        # Reset mock to ignore setup calls
        self.callbacks.on_update_visibility_ui.reset_mock()

        # Change visibility window variable
        self.variables["visibility_window"].set("Night Window")
        self.root.update()

        # Should trigger update visibility UI callback
        self.assertTrue(self.callbacks.on_update_visibility_ui.called)

    def test_handles_missing_widgets_gracefully(self):
        """Test that methods handle missing widgets gracefully."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        # Don't build, so widgets don't exist
        # These should not raise exceptions
        manager.update_visibility_values_label("test")
        manager.set_min_latitude_state("disabled")
        manager.update_site_values(["test"])
        manager.update_visibility_window_values(["test"])
        manager.refresh_labels()
        manager.apply_theme(False)

    def test_safe_trace_add_handles_exceptions(self):
        """Test that _safe_trace_add handles exceptions gracefully."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        # Create a mock variable that raises exception on trace_add
        bad_var = Mock()
        bad_var.trace_add.side_effect = AttributeError("Test exception")

        # Should not raise exception
        manager._safe_trace_add(bad_var, lambda: None)

    def test_language_combobox_created_with_available_languages(self):
        """Test that language combobox is created with available languages."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        manager.build()

        combobox = manager.widgets["combobox_language"]
        values = combobox["values"]

        # Should always have 'en'
        self.assertIn("en", values)

    def test_empty_sites_dict_handled_gracefully(self):
        """Test that empty sites dictionary is handled gracefully."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites={},  # Empty sites
            visibility_windows=self.visibility_windows,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        # Should not raise exception
        frame = manager.build()
        self.assertIsNotNone(frame)

    def test_empty_visibility_windows_dict_handled_gracefully(self):
        """Test that empty visibility windows dictionary is handled gracefully."""
        manager = FilterPanelManager(
            parent=self.root,
            variables=self.variables,
            sites=self.sites,
            visibility_windows={},  # Empty visibility windows
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
        )

        # Should not raise exception
        frame = manager.build()
        self.assertIsNotNone(frame)

        # Should have empty string as first option
        combobox = manager.widgets["combobox_visibility"]
        values = combobox["values"]
        self.assertEqual(values[0], "")


if __name__ == "__main__":
    unittest.main()
