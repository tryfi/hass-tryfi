"""Test embedded pytryfi functionality."""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from custom_components.tryfi.pytryfi import PyTryFi
from custom_components.tryfi.pytryfi.exceptions import TryFiError


@pytest.fixture
def mock_session():
    """Create a mock session."""
    session = Mock()
    session.post = Mock()
    session.get = Mock()
    return session


@pytest.fixture
def mock_query_module():
    """Mock the query module."""
    with patch("custom_components.tryfi.pytryfi.common.query") as mock_query:
        yield mock_query


def test_pytryfi_update_error_handling():
    """Test PyTryFi update method error handling."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi.updateBases") as mock_update_bases:
        with patch("custom_components.tryfi.pytryfi.PyTryFi.updatePets") as mock_update_pets:
            # Create instance without going through __init__
            tryfi = object.__new__(PyTryFi)
            
            # Test both updates failing
            mock_update_bases.side_effect = Exception("Base update failed")
            mock_update_pets.side_effect = Exception("Pet update failed")
            
            with pytest.raises(Exception) as exc_info:
                tryfi.update()
            
            assert "Base update failed" in str(exc_info.value)
            assert "Pet update failed" in str(exc_info.value)
            
            # Test only base update failing
            mock_update_bases.side_effect = Exception("Base update failed")
            mock_update_pets.side_effect = None
            
            with pytest.raises(Exception) as exc_info:
                tryfi.update()
            
            assert "Base update failed" in str(exc_info.value)
            
            # Test only pet update failing
            mock_update_bases.side_effect = None
            mock_update_pets.side_effect = Exception("Pet update failed")
            
            with pytest.raises(Exception) as exc_info:
                tryfi.update()
            
            assert "Pet update failed" in str(exc_info.value)
            
            # Test both succeed
            mock_update_bases.side_effect = None
            mock_update_pets.side_effect = None
            
            # Should not raise
            tryfi.update()


def test_query_error_handling():
    """Test query module error handling."""
    from custom_components.tryfi.pytryfi.common.query import execute
    
    session = Mock()
    
    # Test execute with HTTP error
    response = Mock()
    response.raise_for_status.side_effect = Exception("HTTP Error")
    session.get.return_value = response
    
    with pytest.raises(TryFiError) as exc_info:
        execute("http://test.com", session, "GET")
    
    assert "API request failed" in str(exc_info.value)
    
    # Test execute with empty response
    response = Mock()
    response.text = ""
    response.raise_for_status.return_value = None
    session.get.return_value = response
    
    with pytest.raises(TryFiError) as exc_info:
        execute("http://test.com", session, "GET")
    
    assert "Empty response" in str(exc_info.value)
    
    # Test invalid method
    with pytest.raises(TryFiError) as exc_info:
        execute("http://test.com", session, "INVALID")
    
    assert "Method Passed was invalid" in str(exc_info.value)


def test_query_json_parsing():
    """Test query JSON parsing error handling."""
    from custom_components.tryfi.pytryfi.common.query import query
    
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "valid"
    response.json.side_effect = ValueError("Invalid JSON")
    
    with patch("custom_components.tryfi.pytryfi.common.query.execute") as mock_execute:
        mock_execute.return_value = response
        
        with pytest.raises(TryFiError) as exc_info:
            query(session, "test query")
        
        assert "Invalid JSON response" in str(exc_info.value)


def test_query_graphql_errors():
    """Test query GraphQL error handling."""
    from custom_components.tryfi.pytryfi.common.query import query
    
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "valid"
    response.json.return_value = {
        "errors": [{"message": "GraphQL Error: Invalid query"}]
    }
    
    with patch("custom_components.tryfi.pytryfi.common.query.execute") as mock_execute:
        mock_execute.return_value = response
        
        with pytest.raises(TryFiError) as exc_info:
            query(session, "test query")
        
        assert "GraphQL error" in str(exc_info.value)
        assert "Invalid query" in str(exc_info.value)


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
    
    with pytest.raises(IndexError):
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
    assert calculate_distance((100, 100, 100), (150, 150, 150)) == pytest.approx(86.60, rel=0.01)


def test_find_closest_color_empty_map():
    """Test finding closest color with empty color map."""
    from custom_components.tryfi.light import find_closest_color_code
    
    # Empty color map should return default
    assert find_closest_color_code((255, 0, 0), {}) == 8  # Default white


def test_embedded_pytryfi_import():
    """Test that embedded pytryfi can be imported."""
    from custom_components.tryfi.pytryfi import PyTryFi
    
    # Should be able to import without error
    assert PyTryFi is not None