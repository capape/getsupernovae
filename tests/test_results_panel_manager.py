"""Tests for ResultsPanelManager

Tests the results panel UI manager functionality, including widget creation,
tree operations, and callback integration.
"""

import os
import sys

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from app.ui.results_panel_manager import ResultsPanelCallbacks, ResultsPanelManager


class TestResultsPanelManager(unittest.TestCase):
    """Test suite for ResultsPanelManager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create root window for tests
        self.root = tk.Tk()

        # Create mock callbacks
        self.callbacks = ResultsPanelCallbacks(
            on_sort_column=Mock(),
            on_double_click=Mock(),
            on_motion=Mock(),
            on_leave=Mock(),
            on_selection_change=Mock(),
            on_pdf=Mock(),
            on_txt=Mock(),
            on_refresh=Mock(),
            on_exit=Mock(),
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
        """Test ResultsPanelManager initialization."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        self.assertIsNotNone(manager)
        self.assertEqual(manager.parent, self.root)
        self.assertEqual(manager.callbacks, self.callbacks)
        self.assertEqual(manager.dark_mode, self.dark_mode)
        self.assertEqual(manager.widgets, {})
        self.assertEqual(manager.supernova_data, {})
        self.assertIsNone(manager.tooltip_window)
        self.assertIsNone(manager.tooltip_item)
        self.assertIsNone(manager.sort_column)
        self.assertFalse(manager.sort_reverse)

    def test_build_creates_all_components(self):
        """Test that build() creates all expected components."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Check that all expected widgets were created
        expected_widgets = [
            "label_results",
            "results_frame",
            "results_tree",
            "scrollbar_vertical",
            "scrollbar_horizontal",
            "button_pdf",
            "button_txt",
            "button_refresh",
            "button_exit",
            "progress_bar",
        ]

        for widget_name in expected_widgets:
            self.assertIn(widget_name, manager.widgets, f"Missing widget: {widget_name}")

    def test_results_label_created(self):
        """Test that results label is created."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        self.assertIn("label_results", manager.widgets)
        label = manager.widgets["label_results"]
        self.assertIsInstance(label, ttk.Label)

    def test_results_tree_created_with_columns(self):
        """Test that results tree is created with all columns."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        tree = manager.get_tree()
        self.assertIsNotNone(tree)
        self.assertIsInstance(tree, ttk.Treeview)

        # Check columns
        columns = tree["columns"]
        expected_columns = (
            "name",
            "type",
            "magnitude",
            "date",
            "observation_time",
            "host",
            "constellation",
            "ra",
            "dec",
            "rochester",
            "tns",
        )
        self.assertEqual(columns, expected_columns)

    def test_scrollbars_created(self):
        """Test that scrollbars are created and configured."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        self.assertIn("scrollbar_vertical", manager.widgets)
        self.assertIn("scrollbar_horizontal", manager.widgets)

    def test_action_buttons_created(self):
        """Test that all action buttons are created."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Check action buttons
        self.assertIn("button_pdf", manager.widgets)
        self.assertIn("button_txt", manager.widgets)
        self.assertIn("button_refresh", manager.widgets)
        self.assertIn("button_exit", manager.widgets)

    def test_progress_bar_created(self):
        """Test that progress bar is created."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        self.assertIn("progress_bar", manager.widgets)
        progress = manager.widgets["progress_bar"]
        self.assertIsInstance(progress, ttk.Progressbar)

    def test_pdf_button_calls_callback(self):
        """Test that PDF button triggers the callback."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets["button_pdf"]
        button.invoke()

        self.callbacks.on_pdf.assert_called_once()

    def test_txt_button_calls_callback(self):
        """Test that TXT button triggers the callback."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets["button_txt"]
        button.invoke()

        self.callbacks.on_txt.assert_called_once()

    def test_refresh_button_calls_callback(self):
        """Test that refresh button triggers the callback."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets["button_refresh"]
        button.invoke()

        self.callbacks.on_refresh.assert_called_once()

    def test_exit_button_calls_callback(self):
        """Test that exit button triggers the callback."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        button = manager.widgets["button_exit"]
        button.invoke()

        self.callbacks.on_exit.assert_called_once()

    def test_get_tree_returns_treeview(self):
        """Test that get_tree returns the treeview widget."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()
        tree = manager.get_tree()

        self.assertIsNotNone(tree)
        self.assertIsInstance(tree, ttk.Treeview)

    def test_clear_tree_removes_all_items(self):
        """Test that clear_tree removes all items from tree."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()
        tree = manager.get_tree()

        # Add some items
        tree.insert("", "end", values=("SN2024A", "Ia", "15.0"))
        tree.insert("", "end", values=("SN2024B", "II", "16.0"))

        # Add to supernova_data
        manager.supernova_data["item1"] = Mock()
        manager.supernova_data["item2"] = Mock()

        # Clear
        manager.clear_tree()

        # Verify cleared
        self.assertEqual(len(tree.get_children()), 0)
        self.assertEqual(len(manager.supernova_data), 0)

    def test_add_tree_item_adds_item(self):
        """Test that add_tree_item adds an item to the tree."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        values = (
            "SN2024A",
            "Ia",
            "15.0",
            "2024-01-01",
            "22:00",
            "NGC1234",
            "Leo",
            "10:20:30",
            "+12:34:56",
            "R",
            "T",
        )
        item_id = manager.add_tree_item(values, tags=("evenrow",))

        self.assertIsNotNone(item_id)

        tree = manager.get_tree()
        children = tree.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0], item_id)

    def test_set_button_state_enables_button(self):
        """Test that set_button_state can enable a button."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # PDF button is normal by default, let's disable then enable it
        button = manager.widgets["button_pdf"]
        manager.set_button_state("button_pdf", "disabled")
        self.assertEqual(str(button["state"]), "disabled")

        # Enable it
        manager.set_button_state("button_pdf", "normal")
        self.assertEqual(str(button["state"]), "normal")

    def test_set_button_state_disables_button(self):
        """Test that set_button_state can disable a button."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # PDF button is normal by default
        button = manager.widgets["button_pdf"]
        self.assertEqual(str(button["state"]), "normal")

        # Disable it
        manager.set_button_state("button_pdf", "disabled")
        self.assertEqual(str(button["state"]), "disabled")

    def test_start_progress_bar(self):
        """Test that start_progress_bar shows and starts animation."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Progress bar should not be visible initially
        progress = manager.widgets["progress_bar"]
        grid_info = progress.grid_info()
        self.assertEqual(grid_info, {})  # Not gridded

        # Start it
        manager.start_progress_bar()

        # Should now be gridded
        grid_info = progress.grid_info()
        self.assertNotEqual(grid_info, {})

    def test_stop_progress_bar(self):
        """Test that stop_progress_bar stops and hides animation."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Start progress bar first
        manager.start_progress_bar()
        progress = manager.widgets["progress_bar"]

        # Verify it's visible
        grid_info = progress.grid_info()
        self.assertNotEqual(grid_info, {})

        # Stop it
        manager.stop_progress_bar()

        # Should be hidden now
        grid_info = progress.grid_info()
        self.assertEqual(grid_info, {})

    def test_get_selection_returns_selected_items(self):
        """Test that get_selection returns selected items."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()
        tree = manager.get_tree()

        # Add items
        item1 = tree.insert("", "end", values=("SN2024A",))
        item2 = tree.insert("", "end", values=("SN2024B",))

        # Select first item
        tree.selection_set(item1)

        selection = manager.get_selection()
        self.assertEqual(len(selection), 1)
        self.assertEqual(selection[0], item1)

    def test_get_tree_children_returns_all_items(self):
        """Test that get_tree_children returns all items."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()
        tree = manager.get_tree()

        # Add items
        item1 = tree.insert("", "end", values=("SN2024A",))
        item2 = tree.insert("", "end", values=("SN2024B",))
        item3 = tree.insert("", "end", values=("SN2024C",))

        children = manager.get_tree_children()
        self.assertEqual(len(children), 3)
        self.assertIn(item1, children)
        self.assertIn(item2, children)
        self.assertIn(item3, children)

    def test_refresh_labels_updates_text(self):
        """Test that refresh_labels updates all label texts."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Mock the translation function
        with patch("app.ui.results_panel_manager._") as mock_translate:
            mock_translate.side_effect = lambda x: f"TRANSLATED: {x}"

            manager.refresh_labels()

            # Verify at least one label was updated
            label = manager.widgets["label_results"]
            text = label.cget("text")
            self.assertIn("TRANSLATED:", text)

    def test_update_idletasks_calls_update(self):
        """Test that update_idletasks updates widgets."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Should not raise exception
        manager.update_idletasks()

    def test_handles_missing_widgets_gracefully(self):
        """Test that methods handle missing widgets gracefully."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        # Don't build, so widgets don't exist
        # These should not raise exceptions
        manager.clear_tree()
        manager.add_tree_item(("test",))
        manager.set_button_state("button_pdf", "normal")
        manager.start_progress_bar()
        manager.stop_progress_bar()
        selection = manager.get_selection()
        self.assertEqual(selection, [])
        children = manager.get_tree_children()
        self.assertEqual(children, ())
        manager.refresh_labels()
        manager.update_idletasks()

    def test_tree_event_bindings(self):
        """Test that tree events are bound to callbacks."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()
        tree = manager.get_tree()

        # Verify bindings exist
        bindings = tree.bind()
        self.assertIn("<Double-Button-1>", bindings)
        self.assertIn("<Motion>", bindings)
        self.assertIn("<Leave>", bindings)
        self.assertIn("<<TreeviewSelect>>", bindings)

    def test_supernova_data_storage(self):
        """Test that supernova data can be stored and retrieved."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        manager.build()

        # Store some data
        mock_sn = Mock()
        manager.supernova_data["test_id"] = mock_sn

        # Retrieve it
        self.assertIn("test_id", manager.supernova_data)
        self.assertEqual(manager.supernova_data["test_id"], mock_sn)

    def test_sort_state_initialization(self):
        """Test that sort state is properly initialized."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        self.assertIsNone(manager.sort_column)
        self.assertFalse(manager.sort_reverse)

    def test_tooltip_state_initialization(self):
        """Test that tooltip state is properly initialized."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        self.assertIsNone(manager.tooltip_window)
        self.assertIsNone(manager.tooltip_item)

    def test_get_tree_returns_none_when_not_built(self):
        """Test that get_tree returns None when not built."""
        manager = ResultsPanelManager(
            parent=self.root, callbacks=self.callbacks, dark_mode=self.dark_mode
        )

        tree = manager.get_tree()
        self.assertIsNone(tree)


if __name__ == "__main__":
    unittest.main()
