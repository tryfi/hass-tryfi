from custom_components.tryfi.pytryfi import FiPet, FiDevice
from .utils import mock_graphql, GRAPHQL_FIXTURE_PET_ALL_INFO, REQ_PET_ALL_INFO

import json
import requests
import responses
import urllib.parse


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


@responses.activate
def test_update_behavior_stats():
    with open("tests/pytryfi/fixture_petHealthTrends.json", "r") as f:
        health_trends_fixture = json.load(f)

    behavior_trends_response = {
        "getPetHealthTrendsForPet": {"behaviorTrends": health_trends_fixture}
    }

    qString = """
    query PetHealthTrends {
        getPetHealthTrendsForPet(petId: "test-pet", period: DAY) {
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
    url = f"https://api.tryfi.com/graphql?query={urllib.parse.quote_plus(qString)}"
    responses.add(
        method=responses.GET,
        url=url,
        status=200,
        json={"data": behavior_trends_response},
    )

    pet = FiPet("test-pet")
    pet._device = FiDevice("device-id")
    pet.updateBehaviorStats(requests.Session())

    assert pet.dailyBarkingCount == 24
    assert pet.dailyBarkingDuration == 46
    assert pet.dailyEatingCount == 6
    assert pet.dailyEatingDuration == 6
    assert pet.dailyDrinkingCount == 3
    assert pet.dailyDrinkingDuration == 0
    assert pet.dailyLickingCount == 6
    assert pet.dailyLickingDuration == 6
    assert pet.dailyScratchingCount == 4
    assert pet.dailyScratchingDuration == 1
