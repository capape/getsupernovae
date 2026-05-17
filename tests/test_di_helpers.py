"""Unit tests for dependency injection helpers."""

from app.utils.di_helpers import default_if_none, initialize_rochester_factories


class TestDefaultIfNone:
    """Test the default_if_none utility function."""

    def test_returns_value_when_not_none(self):
        """Should return the value when it's not None."""
        assert default_if_none("test", "default") == "test"
        assert default_if_none(42, 99) == 42
        assert default_if_none([], ["default"]) == []

    def test_returns_default_when_none(self):
        """Should return the default when value is None."""
        assert default_if_none(None, "default") == "default"
        assert default_if_none(None, 42) == 42
        assert default_if_none(None, []) == []

    def test_works_with_falsy_values(self):
        """Should distinguish None from other falsy values."""
        assert default_if_none(0, 99) == 0
        assert default_if_none("", "default") == ""
        assert default_if_none(False, True) is False


class TestInitializeRochesterFactories:
    """Test the initialize_rochester_factories function."""

    def test_uses_defaults_when_all_none(self):
        """Should use default factories when all parameters are None."""
        from app.services.provider import NetworkRochesterProvider
        from app.ui.snvisibility import VisibilityWindow

        vis_factory, prov_factory, reporter = initialize_rochester_factories()

        assert vis_factory is VisibilityWindow
        assert prov_factory is NetworkRochesterProvider
        assert reporter is None

    def test_uses_provided_factories(self):
        """Should use provided factories when given."""

        class MockVisibility:
            pass

        class MockProvider:
            pass

        mock_reporter = "test_reporter"

        vis_factory, prov_factory, reporter = initialize_rochester_factories(
            visibility_factory=MockVisibility,
            provider_factory=MockProvider,
            reporter=mock_reporter,
        )

        assert vis_factory is MockVisibility
        assert prov_factory is MockProvider
        assert reporter == mock_reporter

    def test_mixes_provided_and_defaults(self):
        """Should mix provided factories with defaults."""
        from app.services.provider import NetworkRochesterProvider

        class MockVisibility:
            pass

        vis_factory, prov_factory, reporter = initialize_rochester_factories(
            visibility_factory=MockVisibility, provider_factory=None, reporter="test"
        )

        assert vis_factory is MockVisibility
        assert prov_factory is NetworkRochesterProvider
        assert reporter == "test"

    def test_returns_tuple_of_three(self):
        """Should always return a tuple of exactly 3 elements."""
        result = initialize_rochester_factories()
        assert isinstance(result, tuple)
        assert len(result) == 3
