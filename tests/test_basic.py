"""Basic tests for RemarkableSync."""


def test_dummy():
    """Dummy test to verify pytest is working."""
    assert True


def test_version_import():
    """Test that version module can be imported."""
    from src.__version__ import __repository__, __version__

    assert __version__ is not None
    assert __repository__ is not None
    assert isinstance(__version__, str)
    assert isinstance(__repository__, str)


def test_constants():
    """Test ReMarkable 2 constants."""
    # ReMarkable 2 dimensions
    REMARKABLE_WIDTH_PIXELS = 1404
    REMARKABLE_HEIGHT_PIXELS = 1872
    REMARKABLE_DPI = 226

    # Verify conversion to PDF points
    PIXELS_TO_POINTS = 72.0 / REMARKABLE_DPI
    REMARKABLE_WIDTH_POINTS = REMARKABLE_WIDTH_PIXELS * PIXELS_TO_POINTS
    REMARKABLE_HEIGHT_POINTS = REMARKABLE_HEIGHT_PIXELS * PIXELS_TO_POINTS

    # These should be approximately 447.3 and 596.4
    assert abs(REMARKABLE_WIDTH_POINTS - 447.3) < 0.1
    assert abs(REMARKABLE_HEIGHT_POINTS - 596.4) < 0.1
