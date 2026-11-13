from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
import requests
import responses

from custom_components.tryfi.pytryfi.common.query import (
    FRAGMENT_ACTIVITY_SUMMARY_DETAILS,
    FRAGMENT_BASE_DETAILS,
    FRAGMENT_BASE_PET_PROFILE,
    FRAGMENT_BREED_DETAILS,
    FRAGMENT_CONNECTION_STATE_DETAILS,
    FRAGMENT_DEVICE_DETAILS,
    FRAGMENT_LED_DETAILS,
    FRAGMENT_LOCATION_POINT,
    FRAGMENT_ONGOING_ACTIVITY_DETAILS,
    FRAGMENT_OPERATIONAL_DETAILS,
    FRAGMENT_PET_PROFILE,
    FRAGMENT_PHOTO_DETAILS,
    FRAGMENT_PLACE_DETAILS,
    FRAGMENT_POSITION_COORDINATES,
    FRAGMENT_REST_SUMMARY_DETAILS,
    FRAGMENT_USER_DETAILS,
    QUERY_GET_BASES,
    QUERY_PET_ACTIVE_DETAILS,
    QUERY_PET_ACTIVITY,
    QUERY_PET_CURRENT_LOCATION,
    QUERY_PET_DEVICE_DETAILS,
    QUERY_PET_REST,
    REQUEST_FRAGMENTS_PET_ALL_INFO,
    REQUEST_GET_HOUSEHOLDS,
    VAR_PET_ID,
    _execute,
    getBaseList,
    getCurrentPetLocation,
    getCurrentPetRestStats,
    getCurrentPetStats,
    getDevicedetails,
    getHouseHolds,
    getPetAllInfo,
    getPetHealthTrends,
    getWifiNetworks,
    query,
    setLedColor,
    setLostDogMode,
    turnOnOffLed,
    updatePetWeight,
    updateWifiNetwork,
)
from custom_components.tryfi.pytryfi.exceptions import (
    ApiNotAuthorizedError,
    RemoteApiError,
    TryFiError,
)
from tests.pytryfi.utils import GRAPHQL_BASE, mock_graphql, mock_response


@responses.activate
def test_query_error_handling():
    """When tryfi.com returns a non-200 response, the error gets bubbled up"""
    mock_graphql(query="test-query", status=500, response=None)

    # Test execute with HTTP error

    with pytest.raises(BaseException):
        query(requests.Session(), "test-query")


@responses.activate
def test_handle_empty_response():
    """Empty responses are treated as errors"""
    responses.add(
        method=responses.GET,
        url="https://api.tryfi.com/graphql?query=test-query",
        status=200,
        body="",
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


@responses.activate
def test_query_graphql_errors():
    """Test query GraphQL error handling."""
    responses.add(
        responses.GET,
        url="https://api.tryfi.com/graphql?query=test+query",
        status=200,
        json={"errors": [{"message": "GraphQL Error: Invalid query"}]},
    )
    with pytest.raises(RemoteApiError) as exc_info:
        query(requests.Session(), "test query")

    assert "GraphQL error" in str(exc_info.value)
    assert "Invalid query" in str(exc_info.value)


@responses.activate
def test_update_pet_weight():
    """Test updatePetWeight sends mutation and returns updated weight."""
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"updatePet": {"__typename": "BasePet", "weight": 15.5}}},
    )

    result = updatePetWeight(requests.Session(), "pet-123", 15.5)
    assert result == 15.5

    body = json.loads(responses.calls[0].request.body)
    assert body["variables"]["input"]["id"] == "pet-123"
    assert body["variables"]["input"]["weight"] == 15.5
    assert "UpdatePetInput" in body["query"]


@responses.activate
def test_get_base_list():
    """Test getBaseList retrieves household bases."""
    mock_graphql(
        query=QUERY_GET_BASES + FRAGMENT_BASE_DETAILS + FRAGMENT_POSITION_COORDINATES,
        status=200,
        response={
            "currentUser": {
                "userHouseholds": [{"household": {"bases": [GRAPHQL_BASE]}}]
            }
        },
    )
    result = getBaseList(requests.Session())
    assert len(result) == 1
    assert result[0]["household"]["bases"][0]["baseId"] == "BASEID-LR"


@responses.activate
def test_get_current_pet_location():
    """Test getCurrentPetLocation retrieves ongoing activity."""
    q_string = (
        QUERY_PET_CURRENT_LOCATION.replace(VAR_PET_ID, "pet-1")
        + FRAGMENT_ONGOING_ACTIVITY_DETAILS
        + FRAGMENT_LOCATION_POINT
        + FRAGMENT_PLACE_DETAILS
        + FRAGMENT_POSITION_COORDINATES
    )
    mock_graphql(
        query=q_string,
        status=200,
        response={
            "pet": {
                "ongoingActivity": {"__typename": "OngoingRest", "areaName": "Home"}
            }
        },
    )
    result = getCurrentPetLocation(requests.Session(), "pet-1")
    assert result["areaName"] == "Home"


@responses.activate
def test_get_pet_all_info():
    """Test getPetAllInfo retrieves full pet details."""
    q_string = (
        QUERY_PET_ACTIVE_DETAILS.replace(VAR_PET_ID, "pet-1")
        + REQUEST_FRAGMENTS_PET_ALL_INFO
    )
    mock_graphql(
        query=q_string,
        status=200,
        response={"pet": {"id": "pet-1", "name": "Buddy"}},
    )
    result = getPetAllInfo(requests.Session(), "pet-1")
    assert result["name"] == "Buddy"


@responses.activate
def test_get_current_pet_stats():
    """Test getCurrentPetStats retrieves activity statistics."""
    q_string = (
        QUERY_PET_ACTIVITY.replace(VAR_PET_ID, "pet-1")
        + FRAGMENT_ACTIVITY_SUMMARY_DETAILS
    )
    mock_graphql(
        query=q_string,
        status=200,
        response={"pet": {"dailyStat": {"totalSteps": 5000}}},
    )
    result = getCurrentPetStats(requests.Session(), "pet-1")
    assert result["dailyStat"]["totalSteps"] == 5000


@responses.activate
def test_get_current_pet_rest_stats():
    """Test getCurrentPetRestStats retrieves rest statistics."""
    q_string = (
        QUERY_PET_REST.replace(VAR_PET_ID, "pet-1") + FRAGMENT_REST_SUMMARY_DETAILS
    )
    mock_graphql(
        query=q_string,
        status=200,
        response={"pet": {"dailyStat": {"restSummaries": []}}},
    )
    result = getCurrentPetRestStats(requests.Session(), "pet-1")
    assert "dailyStat" in result


@responses.activate
def test_get_device_details():
    """Test getDevicedetails retrieves device information for pet."""
    q_string = (
        QUERY_PET_DEVICE_DETAILS.replace(VAR_PET_ID, "pet-1")
        + FRAGMENT_PET_PROFILE
        + FRAGMENT_BASE_PET_PROFILE
        + FRAGMENT_DEVICE_DETAILS
        + FRAGMENT_LED_DETAILS
        + FRAGMENT_OPERATIONAL_DETAILS
        + FRAGMENT_CONNECTION_STATE_DETAILS
        + FRAGMENT_USER_DETAILS
        + FRAGMENT_BREED_DETAILS
        + FRAGMENT_PHOTO_DETAILS
    )
    mock_graphql(
        query=q_string,
        status=200,
        response={"pet": {"device": {"id": "dev-1"}}},
    )
    result = getDevicedetails(requests.Session(), "pet-1")
    assert result["device"]["id"] == "dev-1"


@responses.activate
def test_get_pet_health_trends():
    """Test getPetHealthTrends retrieves pet health trends."""
    q_string = """
    query PetHealthTrends {
        getPetHealthTrendsForPet(petId: "pet-1", period: MONTH) {
            behaviorTrends {
                __typename
                id
                title
                summaryComponents {
                    __typename
                    eventsSummary
                    durationSummary
                }
            }
        }
    }
    """
    mock_graphql(
        query=q_string,
        status=200,
        response={"getPetHealthTrendsForPet": {"behaviorTrends": []}},
    )
    result = getPetHealthTrends(requests.Session(), "pet-1", "MONTH")
    assert result == {"behaviorTrends": []}


@responses.activate
def test_set_led_color():
    """Test setLedColor mutation."""
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={
            "data": {
                "setDeviceLed": {"id": "dev-1", "ledColor": {"name": "Red"}}
            }
        },
    )
    result = setLedColor(requests.Session(), "dev-1", 3)
    assert "setDeviceLed" in result
    body = json.loads(responses.calls[0].request.body)
    assert body["variables"]["moduleId"] == "dev-1"
    assert body["variables"]["ledColorCode"] == 3


@responses.activate
def test_turn_on_off_led():
    """Test turnOnOffLed mutation."""
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={
            "data": {
                "updateDeviceOperationParams": {
                    "id": "dev-1",
                    "operationParams": {"ledEnabled": True},
                }
            }
        },
    )
    result = turnOnOffLed(requests.Session(), "module-1", True)
    assert "updateDeviceOperationParams" in result
    body = json.loads(responses.calls[0].request.body)
    assert body["variables"]["input"]["moduleId"] == "module-1"
    assert body["variables"]["input"]["ledEnabled"] is True


@responses.activate
def test_set_lost_dog_mode():
    """Test setLostDogMode mutation for both lost (True) and normal (False) modes."""
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"updateDeviceOperationParams": {"id": "dev-1"}}},
    )
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"updateDeviceOperationParams": {"id": "dev-1"}}},
    )
    res_lost = setLostDogMode(requests.Session(), "module-1", True)
    assert res_lost == {"updateDeviceOperationParams": {"id": "dev-1"}}
    body1 = json.loads(responses.calls[0].request.body)
    assert body1["variables"]["input"]["mode"] == "LOST_DOG"

    res_norm = setLostDogMode(requests.Session(), "module-1", False)
    assert res_norm == {"updateDeviceOperationParams": {"id": "dev-1"}}
    body2 = json.loads(responses.calls[1].request.body)
    assert body2["variables"]["input"]["mode"] == "NORMAL"


@responses.activate
def test_get_wifi_networks():
    """Test getWifiNetworks mutation/query."""
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={
            "data": {
                "household": {
                    "wifiNetworks": {"networks": [{"ssid": "HomeWifi"}]}
                }
            }
        },
    )
    result = getWifiNetworks(requests.Session(), "house-1")
    assert result["networks"][0]["ssid"] == "HomeWifi"
    body = json.loads(responses.calls[0].request.body)
    assert body["variables"]["householdId"] == "house-1"


@responses.activate
def test_update_wifi_network():
    """Test updateWifiNetwork mutation."""
    responses.add(
        responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={
            "data": {
                "updateWifiNetwork": {
                    "ssid": "HomeWifi",
                    "state": "CONNECTED",
                }
            }
        },
    )
    result = updateWifiNetwork(requests.Session(), "house-1", "HomeWifi", 40.0, -73.0)
    assert result["ssid"] == "HomeWifi"
    body = json.loads(responses.calls[0].request.body)
    assert body["variables"]["input"]["householdId"] == "house-1"
    assert body["variables"]["input"]["ssid"] == "HomeWifi"
    assert body["variables"]["input"]["position"] == {
        "latitude": 40.0,
        "longitude": -73.0,
    }


@pytest.mark.parametrize("status_code", [401, 403])
@responses.activate
def test_query_auth_error_status_codes(status_code):
    """Test 401 and 403 HTTP status codes raise ApiNotAuthorizedError."""
    responses.add(
        responses.GET,
        url="https://api.tryfi.com/graphql?query=auth-test",
        status=status_code,
    )
    with pytest.raises(ApiNotAuthorizedError):
        query(requests.Session(), "auth-test")


@pytest.mark.parametrize(
    "auth_msg",
    ["unauthorized", "unauthenticated", "Authentication failed", "Forbidden access"],
)
@responses.activate
def test_query_graphql_auth_error_messages(auth_msg):
    """Test GraphQL error response containing auth keywords raises ApiNotAuthorizedError."""
    responses.add(
        responses.GET,
        url="https://api.tryfi.com/graphql?query=auth-msg-test",
        status=200,
        json={"errors": [{"message": f"Error: {auth_msg}"}]},
    )
    with pytest.raises(ApiNotAuthorizedError):
        query(requests.Session(), "auth-msg-test")


def test_execute_invalid_method():
    """Test _execute raises TryFiError when invalid HTTP method is provided."""
    session = Mock()
    with pytest.raises(TryFiError) as exc_info:
        _execute("https://api.tryfi.com/graphql", session, method="DELETE")  # type: ignore
    assert "Method Passed was invalid: DELETE" in str(exc_info.value)


@responses.activate
def test_query_500_warning(caplog):
    """Test query logs warning for 500 status code before raising error."""
    responses.add(
        responses.GET,
        url="https://api.tryfi.com/graphql?query=server-err",
        status=500,
        body="Internal Server Error detail",
    )
    with pytest.raises(RemoteApiError):
        query(requests.Session(), "server-err")
    assert "server error:" in caplog.text


@responses.activate
def test_get_households():
    """Test getHouseHolds retrieves current user details."""
    mock_graphql(
        query=REQUEST_GET_HOUSEHOLDS,
        status=200,
        response={"currentUser": {"email": "user@example.com"}},
    )
    result = getHouseHolds(requests.Session())
    assert result["email"] == "user@example.com"


