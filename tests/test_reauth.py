"""Test automatic re-authentication functionality."""
from __future__ import annotations

from unittest.mock import Mock, call, patch

import pytest

from custom_components.tryfi.pytryfi import PyTryFi
from custom_components.tryfi.pytryfi.exceptions import TryFiError


def test_update_with_auth_error_triggers_reauth():
    """Test that authentication errors trigger re-authentication."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi.login") as mock_login:
        with patch("custom_components.tryfi.pytryfi.PyTryFi.updateBases") as mock_update_bases:
            with patch("custom_components.tryfi.pytryfi.PyTryFi.updatePets") as mock_update_pets:
                # Create instance without going through __init__
                tryfi = object.__new__(PyTryFi)
                tryfi._username = "test@example.com"
                tryfi._password = "test-password"
                
                # First call fails with auth error
                mock_update_bases.side_effect = [
                    Exception("401 Unauthorized"),
                    None  # Success after re-auth
                ]
                mock_update_pets.side_effect = [
                    Exception("401 Unauthorized"),
                    None  # Success after re-auth
                ]
                
                # Should not raise - re-auth should fix it
                tryfi.update()
                
                # Verify login was called once
                mock_login.assert_called_once()
                
                # Verify updates were retried
                assert mock_update_bases.call_count == 2
                assert mock_update_pets.call_count == 2


def test_update_with_non_auth_error_no_reauth():
    """Test that non-authentication errors don't trigger re-authentication."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi.login") as mock_login:
        with patch("custom_components.tryfi.pytryfi.PyTryFi.updateBases") as mock_update_bases:
            with patch("custom_components.tryfi.pytryfi.PyTryFi.updatePets") as mock_update_pets:
                tryfi = object.__new__(PyTryFi)
                
                # Regular error (not auth)
                mock_update_bases.side_effect = Exception("Network timeout")
                mock_update_pets.side_effect = Exception("Invalid data")
                
                # Should raise without attempting re-auth
                with pytest.raises(Exception) as exc_info:
                    tryfi.update()
                
                assert "Network timeout" in str(exc_info.value)
                assert "Invalid data" in str(exc_info.value)
                
                # Login should not be called
                mock_login.assert_not_called()


def test_is_auth_error_detection():
    """Test authentication error detection."""
    tryfi = object.__new__(PyTryFi)
    
    # Auth errors
    assert tryfi._is_auth_error(Exception("401 Unauthorized"))
    assert tryfi._is_auth_error(Exception("403 Forbidden"))
    assert tryfi._is_auth_error(Exception("Authentication failed"))
    assert tryfi._is_auth_error(Exception("User is not authenticated"))
    assert tryfi._is_auth_error(TryFiError("Authentication error: Invalid token"))
    
    # Non-auth errors
    assert not tryfi._is_auth_error(Exception("Network timeout"))
    assert not tryfi._is_auth_error(Exception("Invalid data"))
    assert not tryfi._is_auth_error(Exception("Server error 500"))


def test_update_reauth_failure():
    """Test handling of re-authentication failure."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi.login") as mock_login:
        with patch("custom_components.tryfi.pytryfi.PyTryFi.updateBases") as mock_update_bases:
            with patch("custom_components.tryfi.pytryfi.PyTryFi.updatePets") as mock_update_pets:
                tryfi = object.__new__(PyTryFi)
                tryfi._username = "test@example.com"
                tryfi._password = "wrong-password"
                
                # Updates fail with auth error
                mock_update_bases.side_effect = Exception("401 Unauthorized")
                mock_update_pets.side_effect = Exception("401 Unauthorized")
                
                # Re-auth also fails
                mock_login.side_effect = Exception("Invalid credentials")
                
                # Should raise with all errors
                with pytest.raises(Exception) as exc_info:
                    tryfi.update()
                
                assert "Re-authentication failed" in str(exc_info.value)
                assert "Invalid credentials" in str(exc_info.value)


def test_query_auth_error_detection():
    """Test GraphQL authentication error detection."""
    from custom_components.tryfi.pytryfi.common.query import query
    
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "valid"
    response.status_code = 200
    
    # Test GraphQL auth error
    response.json.return_value = {
        "errors": [{"message": "User is not authenticated"}]
    }
    
    with patch("custom_components.tryfi.pytryfi.common.query.execute") as mock_execute:
        mock_execute.return_value = response
        
        with pytest.raises(TryFiError) as exc_info:
            query(session, "test query")
        
        assert "Authentication error" in str(exc_info.value)


def test_execute_http_auth_errors():
    """Test HTTP 401/403 error detection."""
    from custom_components.tryfi.pytryfi.common.query import execute
    
    session = Mock()
    
    # Test 401
    response = Mock()
    response.status_code = 401
    response.text = "Unauthorized"
    session.get.return_value = response
    
    with pytest.raises(TryFiError) as exc_info:
        execute("http://test.com", session, "GET")
    
    assert "Authentication error: HTTP 401" in str(exc_info.value)
    
    # Test 403
    response.status_code = 403
    session.get.return_value = response
    
    with pytest.raises(TryFiError) as exc_info:
        execute("http://test.com", session, "GET")
    
    assert "Authentication error: HTTP 403" in str(exc_info.value)


def test_partial_auth_failure():
    """Test when only one update has auth failure."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi.login") as mock_login:
        with patch("custom_components.tryfi.pytryfi.PyTryFi.updateBases") as mock_update_bases:
            with patch("custom_components.tryfi.pytryfi.PyTryFi.updatePets") as mock_update_pets:
                tryfi = object.__new__(PyTryFi)
                tryfi._username = "test@example.com"
                tryfi._password = "test-password"
                
                # Only bases fail with auth error
                mock_update_bases.side_effect = [
                    Exception("401 Unauthorized"),
                    None  # Success after re-auth
                ]
                mock_update_pets.return_value = None  # Always succeeds
                
                tryfi.update()
                
                # Should still trigger re-auth
                mock_login.assert_called_once()
                
                # Bases called twice, pets called once (then once more after re-auth)
                assert mock_update_bases.call_count == 2
                assert mock_update_pets.call_count == 2