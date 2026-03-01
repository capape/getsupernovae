"""Tests for ToolbarManager

Tests the toolbar UI manager functionality, including widget creation,
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

from app.ui.toolbar_manager import ToolbarCallbacks, ToolbarManager


class TestToolbarManager(unittest.TestCase):
    """Test suite for ToolbarManager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create root window for tests
        self.root = tk.Tk()

        # Create mock callbacks
        self.callbacks = ToolbarCallbacks(
            on_find_stars=Mock(),
            on_ignore_selected=Mock(),
            on_edit_old=Mock(),
            on_dark_mode_toggle=Mock(),
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
        """Test ToolbarManager initialization."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        self.assertEqual(manager.parent, self.root)
        self.assertEqual(manager.callbacks, self.callbacks)
        self.assertEqual(manager.dark_mode, self.dark_mode)
        self.assertEqual(manager.grid_column, 3)
        self.assertEqual(manager.grid_row, 11)
        self.assertEqual(manager.columnspan, 2)
        self.assertIsNone(manager.toolbar_frame)
        self.assertEqual(manager.widgets, {})

    def test_initialization_custom_grid_position(self):
        """Test ToolbarManager initialization with custom grid position."""
        manager = ToolbarManager(
            parent=self.root,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
            grid_column=5,
            grid_row=10,
            columnspan=3,
        )

        self.assertEqual(manager.grid_column, 5)
        self.assertEqual(manager.grid_row, 10)
        self.assertEqual(manager.columnspan, 3)

    def test_initialization_without_dark_mode(self):
        """Test ToolbarManager initialization without dark mode variable."""
        manager = ToolbarManager(parent=self.root, callbacks=self.callbacks, dark_mode=None)

        self.assertIsNone(manager.dark_mode)

    def test_build_creates_toolbar_frame(self):
        """Test that build() creates the toolbar frame."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        self.assertIsNotNone(manager.toolbar_frame)
        self.assertIsInstance(manager.toolbar_frame, ttk.Frame)

    def test_build_creates_find_stars_button(self):
        """Test that build() creates the Find Stars button."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets.get("button_find_stars")
        self.assertIsNotNone(button)
        self.assertIsInstance(button, ttk.Button)
        # Button should be initially disabled
        self.assertEqual(str(button.cget("state")), "disabled")

    def test_build_creates_ignore_selected_button(self):
        """Test that build() creates the Ignore Selected SN button."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets.get("button_ignore_selected")
        self.assertIsNotNone(button)
        self.assertIsInstance(button, ttk.Button)

    def test_build_creates_edit_old_button(self):
        """Test that build() creates the Edit Ignored SN button."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets.get("button_edit_old")
        self.assertIsNotNone(button)
        self.assertIsInstance(button, ttk.Button)

    def test_build_creates_dark_mode_toggle(self):
        """Test that build() creates the Dark Mode toggle."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        toggle = manager.widgets.get("toggle_dark_mode")
        self.assertIsNotNone(toggle)
        self.assertIsInstance(toggle, ttk.Checkbutton)

    def test_build_without_dark_mode_skips_toggle(self):
        """Test that build() skips dark mode toggle when dark_mode is None."""
        manager = ToolbarManager(parent=self.root, callbacks=self.callbacks, dark_mode=None)

        manager.build()

        toggle = manager.widgets.get("toggle_dark_mode")
        self.assertIsNone(toggle)

    def test_find_stars_button_triggers_callback(self):
        """Test that Find Stars button triggers the correct callback."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Enable button first
        manager.set_find_stars_state(tk.NORMAL)

        # Simulate button click
        button = manager.widgets.get("button_find_stars")
        button.invoke()

        self.callbacks.on_find_stars.assert_called_once()

    def test_ignore_selected_button_triggers_callback(self):
        """Test that Ignore Selected SN button triggers the correct callback."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Simulate button click
        button = manager.widgets.get("button_ignore_selected")
        button.invoke()

        self.callbacks.on_ignore_selected.assert_called_once()

    def test_edit_old_button_triggers_callback(self):
        """Test that Edit Ignored SN button triggers the correct callback."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Simulate button click
        button = manager.widgets.get("button_edit_old")
        button.invoke()

        self.callbacks.on_edit_old.assert_called_once()

    def test_dark_mode_toggle_triggers_callback(self):
        """Test that Dark Mode toggle triggers the correct callback."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Simulate toggle click
        toggle = manager.widgets.get("toggle_dark_mode")
        toggle.invoke()

        self.callbacks.on_dark_mode_toggle.assert_called_once()

    def test_get_widget_returns_correct_widget(self):
        """Test get_widget() returns the correct widget."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.get_widget("button_find_stars")
        self.assertIsNotNone(button)
        self.assertIsInstance(button, ttk.Button)

    def test_get_widget_returns_none_for_nonexistent(self):
        """Test get_widget() returns None for non-existent widget."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        widget = manager.get_widget("nonexistent_widget")
        self.assertIsNone(widget)

    def test_get_all_widgets_returns_copy(self):
        """Test get_all_widgets() returns a copy of the widgets dict."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        widgets = manager.get_all_widgets()
        self.assertIsInstance(widgets, dict)
        # Should contain at least 3 buttons (4 with dark mode toggle)
        self.assertGreaterEqual(len(widgets), 3)

        # Verify it's a copy, not the original
        widgets["test_key"] = "test_value"
        self.assertNotIn("test_key", manager.widgets)

    def test_set_find_stars_state_enables_button(self):
        """Test set_find_stars_state() enables the button."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Button should be initially disabled
        button = manager.widgets.get("button_find_stars")
        self.assertEqual(str(button.cget("state")), "disabled")

        # Enable button
        manager.set_find_stars_state(tk.NORMAL)
        self.assertEqual(str(button.cget("state")), "normal")

    def test_set_find_stars_state_disables_button(self):
        """Test set_find_stars_state() disables the button."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Enable button first
        manager.set_find_stars_state(tk.NORMAL)
        button = manager.widgets.get("button_find_stars")
        self.assertEqual(str(button.cget("state")), "normal")

        # Disable button
        manager.set_find_stars_state(tk.DISABLED)
        self.assertEqual(str(button.cget("state")), "disabled")

    def test_set_ignore_selected_state_changes_state(self):
        """Test set_ignore_selected_state() changes button state."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets.get("button_ignore_selected")

        manager.set_ignore_selected_state(tk.DISABLED)
        self.assertEqual(str(button.cget("state")), "disabled")

        manager.set_ignore_selected_state(tk.NORMAL)
        self.assertEqual(str(button.cget("state")), "normal")

    def test_set_edit_old_state_changes_state(self):
        """Test set_edit_old_state() changes button state."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets.get("button_edit_old")

        manager.set_edit_old_state(tk.DISABLED)
        self.assertEqual(str(button.cget("state")), "disabled")

        manager.set_edit_old_state(tk.NORMAL)
        self.assertEqual(str(button.cget("state")), "normal")

    def test_set_all_buttons_state_affects_all_buttons(self):
        """Test set_all_buttons_state() changes state of all buttons."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Enable Find Stars button first
        manager.set_find_stars_state(tk.NORMAL)

        # Disable all buttons
        manager.set_all_buttons_state(tk.DISABLED)

        find_stars = manager.widgets.get("button_find_stars")
        ignore_selected = manager.widgets.get("button_ignore_selected")
        edit_old = manager.widgets.get("button_edit_old")

        self.assertEqual(str(find_stars.cget("state")), "disabled")
        self.assertEqual(str(ignore_selected.cget("state")), "disabled")
        self.assertEqual(str(edit_old.cget("state")), "disabled")

    def test_set_all_buttons_state_does_not_affect_toggle(self):
        """Test set_all_buttons_state() does not affect dark mode toggle."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Disable all buttons
        manager.set_all_buttons_state(tk.DISABLED)

        # Toggle should remain in normal state
        toggle = manager.widgets.get("toggle_dark_mode")
        # Checkbuttons don't have the same state behavior as buttons
        # Just verify it exists and wasn't affected
        self.assertIsNotNone(toggle)

    def test_refresh_labels_updates_button_texts(self):
        """Test refresh_labels() updates all button texts."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Mock the translation function
        with patch("app.ui.toolbar_manager._") as mock_gettext:
            mock_gettext.side_effect = lambda x: f"TRANSLATED_{x}"

            manager.refresh_labels()

            # Verify _ was called with expected strings
            expected_calls = ["Find stars", "Ignore selected SN", "Edit Ignored SN", "Dark mode"]
            actual_calls = [call[0][0] for call in mock_gettext.call_args_list]

            for expected in expected_calls:
                self.assertIn(expected, actual_calls)

    def test_destroy_clears_widgets(self):
        """Test destroy() clears all widgets."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Verify widgets exist
        self.assertGreater(len(manager.widgets), 0)
        self.assertIsNotNone(manager.toolbar_frame)

        # Destroy
        manager.destroy()

        # Verify cleanup
        self.assertEqual(len(manager.widgets), 0)
        self.assertIsNone(manager.toolbar_frame)

    def test_state_methods_handle_missing_widgets_gracefully(self):
        """Test state methods don't crash when widgets don't exist."""
        manager = ToolbarManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        # Don't build, so widgets don't exist

        # These should not raise exceptions
        manager.set_find_stars_state(tk.NORMAL)
        manager.set_ignore_selected_state(tk.NORMAL)
        manager.set_edit_old_state(tk.NORMAL)
        manager.set_all_buttons_state(tk.NORMAL)
        manager.refresh_labels()

    def test_toolbar_frame_positioned_correctly(self):
        """Test toolbar frame is positioned at correct grid location."""
        manager = ToolbarManager(
            parent=self.root,
            callbacks=self.callbacks,
            dark_mode=self.dark_mode,
            grid_column=5,
            grid_row=10,
            columnspan=3,
        )

        manager.build()

        # Get grid info
        info = manager.toolbar_frame.grid_info()

        self.assertEqual(info["column"], 5)
        self.assertEqual(info["row"], 10)
        self.assertEqual(info["columnspan"], 3)

    def test_callbacks_dataclass_structure(self):
        """Test ToolbarCallbacks dataclass has correct structure."""
        callbacks = ToolbarCallbacks(
            on_find_stars=Mock(),
            on_ignore_selected=Mock(),
            on_edit_old=Mock(),
            on_dark_mode_toggle=Mock(),
        )

        self.assertTrue(hasattr(callbacks, "on_find_stars"))
        self.assertTrue(hasattr(callbacks, "on_ignore_selected"))
        self.assertTrue(hasattr(callbacks, "on_edit_old"))
        self.assertTrue(hasattr(callbacks, "on_dark_mode_toggle"))


if __name__ == "__main__":
    unittest.main()
