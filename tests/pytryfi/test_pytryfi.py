import json
from unittest.mock import patch

import pytest
import responses

from custom_components.tryfi.pytryfi import PyTryFi
from custom_components.tryfi.pytryfi.common.query import (
    FRAGMENT_BASE_DETAILS,
    FRAGMENT_POSITION_COORDINATES,
    QUERY_GET_BASES,
    REQUEST_GET_HOUSEHOLDS,
)
from tests.pytryfi.utils import (
    GRAPHQL_BASE,
    GRAPHQL_PARTIAL_PET,
    mock_graphql,
    mock_household_with_pets,
    mock_login_requests,
)


@responses.activate
def test_pet_with_no_collar():
    mock_login_requests()

    mock_household_with_pets(
        pets=[
            {
                "__typename": "Pet",
                "id": "testpetwithnodevice",
                "chip": None,
                "name": "Yolo",
                "device": None,
            }
        ]
    )

    tryfi = PyTryFi()

    assert tryfi.pets == []


@responses.activate
def test_generic_init():
    mock_login_requests()
    mock_household_with_pets(pets=[GRAPHQL_PARTIAL_PET])

    tryfi = PyTryFi()

    assert len(tryfi.pets) == 1

    assert tryfi.pets[0].petId == "test-pet"


def mock_multi_household_setup():
    mock_login_requests()
    mock_graphql(
        query=REQUEST_GET_HOUSEHOLDS,
        response={
            "currentUser": {
                "id": "user-123",
                "email": "user@example.com",
                "firstName": "John",
                "lastName": "Doe",
                "phoneNumber": "555-1234",
                "userHouseholds": [
                    {
                        "household": {
                            "id": "house-1",
                            "pets": [GRAPHQL_PARTIAL_PET],
                            "bases": [
                                GRAPHQL_BASE,
                                None,
                                {"baseId": "INVALID_BASE", "name": None},
                            ],
                        }
                    },
                    {
                        "household": {
                            "id": "house-2",
                            "pets": [],
                            "bases": [],
                        }
                    },
                ],
            }
        },
        status=200,
    )
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={
            "data": {
                "household": {
                    "wifiNetworks": {
                        "networks": [
                            {
                                "ssid": "HomeWifi",
                                "state": "CONNECTED",
                                "addressLabel": "Home",
                                "isHidden": False,
                                "position": {"latitude": 37.77, "longitude": -122.41},
                            }
                        ]
                    }
                }
            }
        },
    )
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"household": {"wifiNetworks": {"networks": []}}}},
    )


@responses.activate
def test_pytryfi_multi_household_properties():
    """Test PyTryFi instantiation with multiple households, pets, bases, and networks."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")

    assert tryfi.householdIds == ["house-1", "house-2"]
    assert len(tryfi.pets) == 1
    assert len(tryfi.bases) == 1
    assert len(tryfi.wifiNetworks) == 1
    assert tryfi.username == "user@example.com"
    assert tryfi.userID == "userid"
    assert tryfi.currentUser is not None
    assert tryfi.cookies is not None
    assert tryfi.session is not None


@responses.activate
def test_pytryfi_str_representation():
    """Test PyTryFi string representation."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")
    str_repr = str(tryfi)
    assert "Username: user@example.com" in str_repr
    assert "Pets in Home:" in str_repr
    assert "Bases In Home:" in str_repr


@responses.activate
def test_pytryfi_get_pet():
    """Test getPet returns pet or None when not found."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")
    pet = tryfi.getPet("test-pet")
    assert pet is not None
    assert pet.petId == "test-pet"
    assert tryfi.getPet("nonexistent-pet") is None


@responses.activate
def test_pytryfi_get_base():
    """Test getBase returns base or None when not found."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")
    base = tryfi.getBase("BASEID-LR")
    assert base is not None
    assert base.baseId == "BASEID-LR"
    assert tryfi.getBase("nonexistent-base") is None


@responses.activate
def test_pytryfi_update_bases():
    """Test updateBases updates base objects and handles null/invalid base data."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")
    mock_graphql(
        query=QUERY_GET_BASES + FRAGMENT_BASE_DETAILS + FRAGMENT_POSITION_COORDINATES,
        status=200,
        response={
            "currentUser": {
                "userHouseholds": [
                    {
                        "household": {
                            "bases": [
                                GRAPHQL_BASE,
                                None,
                                {"baseId": "BAD", "name": None},
                            ]
                        }
                    }
                ]
            }
        },
    )
    tryfi.updateBases()
    assert len(tryfi.bases) == 1
    assert tryfi.bases[0].baseId == "BASEID-LR"


@responses.activate
def test_pytryfi_wifi_networks():
    """Test WiFi network retrieval, lookup, and location updating."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")

    net = tryfi.getWifiNetwork("HomeWifi")
    assert net is not None
    assert net.ssid == "HomeWifi"
    assert tryfi.getWifiNetwork("UnknownWifi") is None

    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"updateWifiNetwork": {"ssid": "HomeWifi", "state": "CONNECTED"}}},
    )
    res = tryfi.setWifiNetworkLocation("HomeWifi", 37.8, -122.4)
    assert res["ssid"] == "HomeWifi"

    with pytest.raises(Exception) as exc_info:
        tryfi.setWifiNetworkLocation("NonExistent", 37.8, -122.4)
    assert "WiFi network not found: NonExistent" in str(exc_info.value)


@responses.activate
def test_pytryfi_update_wifi_networks_error(caplog):
    """Test updateWifiNetworks handles errors gracefully when fetching networks."""
    mock_login_requests()
    mock_graphql(
        query=REQUEST_GET_HOUSEHOLDS,
        response={
            "currentUser": {
                "email": "user@example.com",
                "firstName": "John",
                "lastName": "Doe",
                "phoneNumber": "555-1234",
                "userHouseholds": [
                    {"household": {"id": "house-1", "pets": [], "bases": []}}
                ],
            }
        },
        status=200,
    )
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=500,
        body="Internal error",
    )
    tryfi = PyTryFi("user@example.com", "password123")
    assert tryfi.wifiNetworks == []
    assert "failed to fetch WiFi networks for household house-1" in caplog.text


@responses.activate
def test_pytryfi_update_catches_exceptions(caplog):
    """Test update method handles errors in base/pet/wifi updates without crashing."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")

    with patch.object(tryfi, "updateBases", side_effect=Exception("base error")), patch.object(
        tryfi, "updatePets", side_effect=Exception("pet error")
    ), patch.object(
        tryfi, "updateWifiNetworks", side_effect=Exception("wifi error")
    ):
        tryfi.update()

    assert "failed to update base:" in caplog.text
    assert "failed to update pets:" in caplog.text
    assert "failed to update wifi networks:" in caplog.text


@responses.activate
def test_login_failure_json_error():
    """Test login raises exception when API returns error field in JSON."""
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/auth/login",
        status=200,
        json={"error": {"message": "Invalid password"}},
    )
    with pytest.raises(Exception) as exc_info:
        PyTryFi("user@example.com", "wrongpass")
    assert "TryFiLoginError" in str(exc_info.value)


@responses.activate
def test_login_failure_non_200():
    """Test login raises exception on non-200 HTTP status."""
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/auth/login",
        status=401,
        json={"message": "Unauthorized"},
    )
    with pytest.raises(Exception):
        PyTryFi("user@example.com", "wrongpass")


@responses.activate
def test_pytryfi_update_pets():
    """Test updatePets calls updateAllDetails on each pet."""
    mock_multi_household_setup()
    tryfi = PyTryFi("user@example.com", "password123")

    with patch.object(tryfi.pets[0], "updateAllDetails") as mock_update:
        tryfi.updatePets()
        mock_update.assert_called_once_with(tryfi.session)


