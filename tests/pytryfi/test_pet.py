from custom_components.tryfi.pytryfi import FiPet, FiDevice
from .utils import mock_graphql, GRAPHQL_FIXTURE_PET_ALL_INFO, REQ_PET_ALL_INFO

import requests
import responses


@responses.activate
def test_load_location():
    mock_graphql(
        query=REQ_PET_ALL_INFO, status=200, response=GRAPHQL_FIXTURE_PET_ALL_INFO
    )

    pet = FiPet("test-pet")
    pet._device = FiDevice("device-id")
    pet.updateAllDetails(requests.Session())

    assert pet.currLatitude == -40
    assert pet.currLongitude == 16


@responses.activate
def test_get_sleep():
    mock_graphql(
        query=REQ_PET_ALL_INFO, status=200, response=GRAPHQL_FIXTURE_PET_ALL_INFO
    )

    pet = FiPet("test-pet")
    pet._device = FiDevice("device-id")
    pet.updateAllDetails(requests.Session())

    assert pet.dailySleep == 60
    assert pet.dailyNap == 30
