from src.version import APP_VERSION


def test_initial_app_version_matches_user_visible_contract():
    """Changing the initial displayed version must be an explicit product decision."""
    assert APP_VERSION == "0.1.0"
