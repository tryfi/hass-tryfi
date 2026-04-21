from custom_components.tryfi.pytryfi import FiPet, FiDevice
from .utils import mock_graphql, GRAPHQL_FIXTURE_PET_ALL_INFO, REQ_PET_ALL_INFO

import json
import requests
import responses
import urllib.parse


class TestParseBehaviorDuration:
    """Tests for _parseBehaviorDuration method - GitHub Issue #30."""

    def test_parse_minutes_only(self):
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("46min") == 46

    def test_parse_hours_decimal(self):
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("1.5hr") == 90

    def test_parse_less_than_minute(self):
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("<1min") == 0

    def test_parse_decimal_minutes(self):
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("10.1") == 10

    def test_parse_hours_and_minutes_with_space(self):
        """Test parsing 'Xhr Ymin' format (e.g., '1hr 5min') - GitHub Issue #30."""
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("1hr 5min") == 65

    def test_parse_hours_and_minutes_single_digits(self):
        """Test parsing 'Xhr Ymin' with single digit values - GitHub Issue #30."""
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("1hr 1min") == 61

    def test_parse_hours_and_minutes_multiple_hours(self):
        """Test parsing longer durations with multiple hours."""
        pet = FiPet("test-pet")
        assert pet._parseBehaviorDuration("6hr 20min") == 380
        assert pet._parseBehaviorDuration("7hr 28min") == 448


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
