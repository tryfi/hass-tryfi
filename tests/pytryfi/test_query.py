from __future__ import annotations

from unittest.mock import Mock

import pytest
import responses
import requests
import json

from custom_components.tryfi.pytryfi.exceptions import RemoteApiError
from custom_components.tryfi.pytryfi.common.query import query
from tests.pytryfi.utils import mock_response


def test_query_error_handling():
    """When tryfi.com returns a non-200 response, the error gets bubbled up"""

    session = Mock()

    # Test execute with HTTP error
    response = mock_response(500)
    session.get.return_value = response

    with pytest.raises(BaseException):
        query(session, "test-query")


@responses.activate
def test_handle_empty_response():
    """Empty responses are treated as errors"""
    responses.add(
        status=200
    )

    with pytest.raises(BaseException) as exc_info:
        query(requests.Session(), "test-query")

    assert "Empty response" in str(exc_info.value)


def test_query_json_parsing():
    """Test query JSON parsing error handling."""
    session = Mock()
    response = mock_response(200)
    response.text = "valid"
    response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
    session.get.return_value = response

    with pytest.raises(RemoteApiError) as exc_info:
        query(session, "test query")

    assert "Invalid JSON response" in str(exc_info.value)


def test_query_graphql_errors():
    """Test query GraphQL error handling."""
    responses.add(
        responses.GET,
        status=200,
        json={
            "errors": [{"message": "GraphQL Error: Invalid query"}]
        }
    )
    with pytest.raises(RemoteApiError) as exc_info:
        query(requests.Session(), "test query")

    assert "GraphQL error" in str(exc_info.value)
    assert "Invalid query" in str(exc_info.value)
