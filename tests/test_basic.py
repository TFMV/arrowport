"""Basic tests for Arrowport."""


from arrowport import __version__


def test_version():
    """Test version is string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"
