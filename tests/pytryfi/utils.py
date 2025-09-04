from unittest.mock import Mock

import responses
import urllib.parse



def mock_response(status_code: int) -> Mock:
    response = Mock()
    response.status_code = status_code
    if 200 <= status_code <= 299:
        response.raise_for_status.return_value = None
        response.ok.return_value = True
    else:
        response.raise_for_status.side_effect = Exception(
            f"Fake HTTP Status: {status_code}"
        )
        response.ok.return_value = False
    return response


def mock_graphql(query: str, status: int, response: dict):
    url = f"https://api.tryfi.com/graphql?query={urllib.parse.quote_plus(query)}"
    responses.add(method=responses.GET, url=url, status=status, json={"data": response})


def mock_login_requests():
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/auth/login",
        status=200,
        json={"userId": "userid", "sessionId": "sessionId"},
    )
