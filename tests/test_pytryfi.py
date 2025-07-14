"""Test embedded pytryfi functionality."""

from __future__ import annotations


import pytest

from custom_components.tryfi.pytryfi import PyTryFi


def test_hex_to_rgb_edge_cases():
    """Test hex to RGB conversion edge cases."""
    from custom_components.tryfi.light import hex_to_rgb

    # Valid cases
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("000000") == (0, 0, 0)
    assert hex_to_rgb("#123456") == (18, 52, 86)

    # Edge cases that should raise
    with pytest.raises(ValueError):
        hex_to_rgb("#FFF")  # Too short

    with pytest.raises(ValueError):
        hex_to_rgb("#GGGGGG")  # Invalid hex

    with pytest.raises(ValueError):
        hex_to_rgb("")  # Empty string


def test_color_distance_calculation():
    """Test color distance calculation."""
    from custom_components.tryfi.light import calculate_distance

    # Same color
    assert calculate_distance((0, 0, 0), (0, 0, 0)) == 0

    # Maximum distance (black to white)
    distance = calculate_distance((0, 0, 0), (255, 255, 255))
    assert distance == pytest.approx(441.67, rel=0.01)

    # Partial distances
    assert calculate_distance((100, 100, 100), (150, 150, 150)) == pytest.approx(
        86.60, rel=0.01
    )


def test_find_closest_color_empty_map():
    """Test finding closest color with empty color map."""
    from custom_components.tryfi.light import find_closest_color_code

    # Empty color map should return default
    assert find_closest_color_code((255, 0, 0), {}) == 8  # Default white


def test_embedded_pytryfi_import():
    """Test that embedded pytryfi can be imported."""

    # Should be able to import without error
    assert PyTryFi is not None
