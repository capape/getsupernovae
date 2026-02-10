"""Unit tests for preferences_manager module."""

import unittest
import json
import tempfile
from pathlib import Path
from app.state.app_state import AppState, SearchState, UIState
from app.state.preferences_manager import (
    PreferencesManager,
    save_user_prefs,
    load_user_prefs,
    migrate_legacy_prefs,
)


class TestPreferencesManager(unittest.TestCase):
    """Tests for PreferencesManager class."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.manager = PreferencesManager(prefs_dir=self.temp_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        if self.temp_path.exists():
            for file in self.temp_path.glob('*'):
                file.unlink()
            self.temp_path.rmdir()
    
    def test_init_creates_directory(self):
        """Test that initialization creates preferences directory."""
        new_dir = self.temp_path / 'new_prefs'
        manager = PreferencesManager(prefs_dir=new_dir)
        self.assertTrue(new_dir.exists())
        new_dir.rmdir()
    
    def test_save_preferences(self):
        """Test saving preferences to file."""
        state = AppState(
            search=SearchState(magnitude="16.0", site="Test"),
            ui=UIState(language="es")
        )
        
        result = self.manager.save_preferences(state)
        
        self.assertTrue(result)
        self.assertTrue(self.manager.prefs_path.exists())
    
    def test_save_preserves_data(self):
        """Test saved data can be read back."""
        state = AppState(
            search=SearchState(
                magnitude="15.5",
                site="Observatory",
                visibility_window="Evening"
            ),
            ui=UIState(language="ca", dark_mode=True)
        )
        
        self.manager.save_preferences(state)
        
        # Read file directly
        with open(self.manager.prefs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data['search']['magnitude'], "15.5")
        self.assertEqual(data['search']['site'], "Observatory")
        self.assertEqual(data['search']['visibility_window'], "Evening")
        self.assertEqual(data['ui']['language'], "ca")
        self.assertTrue(data['ui']['dark_mode'])
    
    def test_load_preferences_nonexistent(self):
        """Test loading when file doesn't exist returns None."""
        result = self.manager.load_preferences()
        self.assertIsNone(result)
    
    def test_load_preferences(self):
        """Test loading preferences from file."""
        # Save first
        state = AppState(
            search=SearchState(magnitude="16.0", days_to_search="45"),
            ui=UIState(language="es")
        )
        self.manager.save_preferences(state)
        
        # Load
        loaded_state = self.manager.load_preferences()
        
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.search.magnitude, "16.0")
        self.assertEqual(loaded_state.search.days_to_search, "45")
        self.assertEqual(loaded_state.ui.language, "es")
    
    def test_get_preference_simple(self):
        """Test getting a simple preference value."""
        state = AppState(search=SearchState(magnitude="17.0"))
        self.manager.save_preferences(state)
        
        value = self.manager.get_preference('search.magnitude')
        self.assertEqual(value, "17.0")
    
    def test_get_preference_nested(self):
        """Test getting nested preference value."""
        state = AppState(ui=UIState(window_width=1024))
        self.manager.save_preferences(state)
        
        value = self.manager.get_preference('ui.window_width')
        self.assertEqual(value, 1024)
    
    def test_get_preference_not_found(self):
        """Test getting non-existent preference returns default."""
        value = self.manager.get_preference('search.nonexistent', default='default_value')
        self.assertEqual(value, 'default_value')
    
    def test_get_preference_no_file(self):
        """Test getting preference when no file exists returns default."""
        value = self.manager.get_preference('search.magnitude', default='18.0')
        self.assertEqual(value, '18.0')
    
    def test_set_preference_new_file(self):
        """Test setting preference creates new file if needed."""
        result = self.manager.set_preference('search.magnitude', '16.5')
        
        self.assertTrue(result)
        self.assertTrue(self.manager.prefs_path.exists())
        
        loaded = self.manager.load_preferences()
        self.assertEqual(loaded.search.magnitude, '16.5')
    
    def test_set_preference_existing_file(self):
        """Test setting preference updates existing file."""
        # Create initial state
        state = AppState(search=SearchState(magnitude="17.0", site="Old"))
        self.manager.save_preferences(state)
        
        # Update one preference
        self.manager.set_preference('search.site', 'New')
        
        # Verify
        loaded = self.manager.load_preferences()
        self.assertEqual(loaded.search.magnitude, "17.0")  # unchanged
        self.assertEqual(loaded.search.site, "New")  # changed
    
    def test_set_preference_invalid_key(self):
        """Test setting preference with invalid key returns False."""
        result = self.manager.set_preference('invalid', 'value')
        self.assertFalse(result)
    
    def test_clear_preferences(self):
        """Test clearing preferences deletes file."""
        # Create preferences
        state = AppState()
        self.manager.save_preferences(state)
        self.assertTrue(self.manager.prefs_path.exists())
        
        # Clear
        result = self.manager.clear_preferences()
        
        self.assertTrue(result)
        self.assertFalse(self.manager.prefs_path.exists())
    
    def test_clear_preferences_no_file(self):
        """Test clearing preferences when no file exists."""
        result = self.manager.clear_preferences()
        self.assertTrue(result)  # Should succeed even if nothing to delete
    
    def test_preferences_exist(self):
        """Test checking if preferences exist."""
        self.assertFalse(self.manager.preferences_exist())
        
        state = AppState()
        self.manager.save_preferences(state)
        
        self.assertTrue(self.manager.preferences_exist())


class TestLegacyFunctions(unittest.TestCase):
    """Tests for legacy compatibility functions."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        # Override default prefs dir for testing
        PreferencesManager.DEFAULT_PREFS_DIR = self.temp_path
    
    def tearDown(self):
        """Clean up temporary files."""
        if self.temp_path.exists():
            for file in self.temp_path.glob('*'):
                file.unlink()
            self.temp_path.rmdir()
    
    def test_save_user_prefs(self):
        """Test legacy save function."""
        result = save_user_prefs(
            site="Test Site",
            latitude=40.0,
            longitude=-3.0,
            magnitude="16.0",
            days="30",
            duration="6",
            language="es",
            min_latitude="20"
        )
        
        self.assertTrue(result)
        
        # Verify it was saved correctly
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = manager.load_preferences()
        
        self.assertEqual(state.search.site, "Test Site")
        # latitude/longitude are no longer stored
        self.assertEqual(state.search.magnitude, "16.0")
        self.assertEqual(state.search.days_to_search, "30")
        self.assertEqual(state.search.observation_duration, "6")
        self.assertEqual(state.search.min_latitude, "20")
        self.assertEqual(state.ui.language, "es")
    
    def test_save_user_prefs_no_location(self):
        """Test legacy save without location."""
        result = save_user_prefs(
            site="Test",
            latitude=None,
            longitude=None,
            magnitude="17.0",
            days="30",
            duration="6",
            language="en"
        )
        
        self.assertTrue(result)
        
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = manager.load_preferences()
        self.assertEqual(state.search.site, "Test")  # Site name still saved
    
    def test_load_user_prefs(self):
        """Test legacy load function."""
        # Save using new format
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = AppState(
            search=SearchState(
                site="Observatory",
                magnitude="15.5",
                days_to_search="45",
                observation_duration="8",
                min_latitude="25"
            ),
            ui=UIState(language="ca")
        )
        manager.save_preferences(state)
        
        # Load using legacy function
        prefs = load_user_prefs()
        
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs['site'], "Observatory")
        self.assertIsNone(prefs['latitude'])  # No longer stored
        self.assertIsNone(prefs['longitude'])  # No longer stored
        self.assertEqual(prefs['magnitude'], "15.5")
        self.assertEqual(prefs['days'], "45")
        self.assertEqual(prefs['duration'], "8")
        self.assertEqual(prefs['min_latitude'], "25")
        self.assertEqual(prefs['language'], "ca")
    
    def test_load_user_prefs_no_file(self):
        """Test legacy load when no file exists."""
        prefs = load_user_prefs()
        self.assertIsNone(prefs)
    
    def test_load_user_prefs_no_location(self):
        """Test legacy load with no location data."""
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = AppState(search=SearchState(site="Test"))
        manager.save_preferences(state)
        
        prefs = load_user_prefs()
        
        self.assertIsNone(prefs['latitude'])
        self.assertIsNone(prefs['longitude'])


class TestLegacyMigration(unittest.TestCase):
    """Tests for legacy preferences migration."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        PreferencesManager.DEFAULT_PREFS_DIR = self.temp_path
    
    def tearDown(self):
        """Clean up temporary files."""
        if self.temp_path.exists():
            for file in self.temp_path.glob('*'):
                file.unlink()
            self.temp_path.rmdir()
    
    def test_migrate_legacy_prefs(self):
        """Test migrating from legacy format."""
        # Create legacy config file
        legacy_path = self.temp_path / 'config.json'
        legacy_data = {
            'site': 'Old Site',
            'latitude': 40.5,
            'longitude': -3.5,
            'magnitude': '16.5',
            'days': '60',
            'duration': '7',
            'min_latitude': '15',
            'language': 'es'
        }
        with open(legacy_path, 'w', encoding='utf-8') as f:
            json.dump(legacy_data, f)
        
        # Migrate
        result = migrate_legacy_prefs(legacy_path)
        self.assertTrue(result)
        
        # Verify new format
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = manager.load_preferences()
        
        self.assertEqual(state.search.site, 'Old Site')
        # latitude/longitude no longer migrated
        self.assertEqual(state.search.magnitude, '16.5')
        self.assertEqual(state.search.days_to_search, '60')
        self.assertEqual(state.search.observation_duration, '7')
        self.assertEqual(state.search.min_latitude, '15')
        self.assertEqual(state.ui.language, 'es')
    
    def test_migrate_no_legacy_file(self):
        """Test migration when no legacy file exists."""
        legacy_path = self.temp_path / 'config.json'
        result = migrate_legacy_prefs(legacy_path)
        self.assertTrue(result)  # Should succeed (nothing to migrate)
    
    def test_migrate_partial_data(self):
        """Test migration with partial legacy data."""
        legacy_path = self.temp_path / 'config.json'
        legacy_data = {
            'site': 'Partial Site',
            'magnitude': '17.5'
        }
        with open(legacy_path, 'w', encoding='utf-8') as f:
            json.dump(legacy_data, f)
        
        result = migrate_legacy_prefs(legacy_path)
        self.assertTrue(result)
        
        manager = PreferencesManager(prefs_dir=self.temp_path)
        state = manager.load_preferences()
        
        self.assertEqual(state.search.site, 'Partial Site')
        self.assertEqual(state.search.magnitude, '17.5')
        # Other fields should have defaults
        self.assertEqual(state.search.days_to_search, '30')
        self.assertEqual(state.ui.language, 'en')


if __name__ == '__main__':
    unittest.main()
