import datetime
import json
import requests
import responses
import urllib.parse
from unittest.mock import patch

from custom_components.tryfi.pytryfi import FiPet, FiDevice
from .utils import mock_graphql, GRAPHQL_FIXTURE_PET_ALL_INFO, GRAPHQL_PARTIAL_PET, REQ_PET_ALL_INFO


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


@responses.activate
def test_set_weight_success():
    """Test setWeight updates the pet's weight via the API."""
    responses.add(
        method=responses.POST,
        url="https://api.tryfi.com/graphql",
        status=200,
        json={"data": {"updatePet": {"__typename": "BasePet", "weight": 14.2}}},
    )

    pet = FiPet("test-pet")
    pet._name = "Buddy"
    result = pet.setWeight(requests.Session(), 14.2)

    assert result is True
    assert pet.weight == 14.2


def test_set_weight_failure():
    """Test setWeight returns False on API failure."""
    pet = FiPet("test-pet")
    pet._name = "Buddy"

    with patch(
        "custom_components.tryfi.pytryfi.common.query.updatePetWeight",
        side_effect=Exception("API error"),
    ):
        result = pet.setWeight(requests.Session(), 10.0)

    assert result is False


def test_pet_set_current_location_ongoing_walk():
    """Test setCurrentLocation with OngoingWalk activity."""
    pet = FiPet("test-pet")
    activity_json = {
        "__typename": "OngoingWalk",
        "areaName": "Downtown Park",
        "lastReportTimestamp": "2026-06-26T12:00:00.000Z",
        "start": "2026-06-26T11:30:00.000Z",
        "positions": [
            {
                "errorRadius": 5.5,
                "position": {"latitude": 37.7749, "longitude": -122.4194},
            }
        ],
        "place": {
            "name": "Dog Park",
            "address": "123 Bark St",
        },
    }
    pet.setCurrentLocation(activity_json)

    assert pet.activityType == "OngoingWalk"
    assert pet.areaName == "Downtown Park"
    assert pet.currLatitude == 37.7749
    assert pet.currLongitude == -122.4194
    assert pet.positionAccuracy == 5.5
    assert pet.currPlaceName == "Dog Park"
    assert pet.currPlaceAddress == "123 Bark St"
    assert pet.getCurrPlaceName() == "Dog Park"
    assert pet.getCurrPlaceAddress() == "123 Bark St"
    assert pet.getActivityType() == "OngoingWalk"


def test_pet_set_current_location_ongoing_rest_with_place():
    """Test setCurrentLocation with OngoingRest and place present."""
    pet = FiPet("test-pet-rest-place")
    pet._device = FiDevice("dev-id-2")
    activity_json = {
        "__typename": "OngoingRest",
        "areaName": "Home",
        "lastReportTimestamp": "2026-06-26T12:00:00.000Z",
        "start": "2026-06-26T11:30:00.000Z",
        "position": {"latitude": 37.0, "longitude": -122.0},
        "place": {
            "name": "Cozy Home",
            "address": "456 Home Rd",
            "radius": 15.0,
        },
    }
    pet.setCurrentLocation(activity_json)

    assert pet.activityType == "OngoingRest"
    assert pet.positionAccuracy == 15.0
    assert pet.currPlaceName == "Cozy Home"
    assert pet.currPlaceAddress == "456 Home Rd"
    assert pet.locationLastUpdate is not None


def test_pet_set_current_location_ongoing_rest_no_place():
    """Test setCurrentLocation with OngoingRest and no place."""
    pet = FiPet("test-pet")
    pet._device = FiDevice("dev-id")
    device_json = {
        "moduleId": "FC1001",
        "info": {"buildId": "1.0", "batteryPercent": "90"},
        "operationParams": {"ledOffAt": None, "ledEnabled": False, "mode": "NORMAL"},
        "ledColor": {"name": "Red", "hexCode": "#FF0000"},
        "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 80},
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
    }
    pet._device.setDeviceDetailsJSON(device_json)

    activity_json = {
        "__typename": "OngoingRest",
        "areaName": "Home",
        "lastReportTimestamp": "2026-06-26T12:00:00.000Z",
        "start": "2026-06-26T11:30:00.000Z",
        "position": {"latitude": 37.0, "longitude": -122.0},
        "place": None,
    }
    pet.setCurrentLocation(activity_json)

    assert pet.activityType == "OngoingRest"
    assert pet.positionAccuracy == 0
    assert pet.currPlaceName is None
    assert pet.currPlaceAddress is None

    # Test __str__
    str_repr = str(pet)
    assert "Pet ID: test-pet" in str_repr


def test_pet_set_stats_and_getters():
    """Test setStats with daily, weekly, and monthly data, and test getters."""
    pet = FiPet("test-pet")
    daily = {"stepGoal": "5000", "totalSteps": "4200", "totalDistance": "3100.5"}
    weekly = {"stepGoal": "35000", "totalSteps": "28000", "totalDistance": "21000.0"}
    monthly = {"stepGoal": "150000", "totalSteps": "120000", "totalDistance": "90000.0"}

    pet.setStats(daily, weekly, monthly)

    assert pet.dailyGoal == 5000
    assert pet.dailySteps == 4200
    assert pet.dailyTotalDistance == 3100.5
    assert pet.weeklyGoal == 35000
    assert pet.weeklySteps == 28000
    assert pet.weeklyTotalDistance == 21000.0
    assert pet.monthlyGoal == 150000
    assert pet.monthlySteps == 120000
    assert pet.monthlyTotalDistance == 90000.0

    # Getters
    assert pet.getDailySteps() == 4200
    assert pet.getDailyGoal() == 5000
    assert pet.getDailyDistance() == 3100.5
    assert pet.getWeeklySteps() == 28000
    assert pet.getWeeklyGoal() == 35000
    assert pet.getWeeklyDistance() == 21000.0
    assert pet.getMonthlySteps() == 120000
    assert pet.getMonthlyGoal() == 150000
    assert pet.getMonthlyDistance() == 90000.0


def test_pet_update_stats_success_and_failure():
    """Test updateStats success and exception paths."""
    pet = FiPet("test-pet")

    stats_response = {
        "dailyStat": {"stepGoal": "5000", "totalSteps": "1000", "totalDistance": "500.0"},
        "weeklyStat": None,
        "monthlyStat": None,
    }

    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetStats", return_value=stats_response):
        assert pet.updateStats(requests.Session()) is True
        assert pet.dailySteps == 1000
        assert getattr(pet, "_weeklyGoal", None) is None

    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetStats", side_effect=Exception("Error")):
        assert pet.updateStats(requests.Session()) is False


def test_pet_extract_sleep_missing_amounts():
    """Test _extractSleep returning None, None when sleepAmounts is missing."""
    pet = FiPet("test-pet")
    rest_obj = {"restSummaries": [{"data": {}}]}
    sleep, nap = pet._extractSleep(rest_obj)
    assert sleep is None
    assert nap is None


def test_pet_update_rest_stats_success_and_failure():
    """Test updateRestStats success and exception paths."""
    pet = FiPet("test-pet")

    rest_stats = {
        "dailyStat": {
            "restSummaries": [
                {
                    "data": {
                        "sleepAmounts": [
                            {"type": "SLEEP", "duration": 480},
                            {"type": "NAP", "duration": 60},
                        ]
                    }
                }
            ]
        },
        "weeklyStat": {
            "restSummaries": [
                {
                    "data": {
                        "sleepAmounts": [
                            {"type": "SLEEP", "duration": 3360},
                            {"type": "NAP", "duration": 420},
                        ]
                    }
                }
            ]
        },
        "monthlyStat": {
            "restSummaries": [
                {
                    "data": {
                        "sleepAmounts": [
                            {"type": "SLEEP", "duration": 14400},
                            {"type": "NAP", "duration": 1800},
                        ]
                    }
                }
            ]
        },
    }

    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetRestStats", return_value=rest_stats):
        assert pet.updateRestStats(requests.Session()) is True
        assert pet.dailySleep == 480
        assert pet.dailyNap == 60
        assert pet.weeklySleep == 3360
        assert pet.weeklyNap == 420
        assert pet.monthlySleep == 14400
        assert pet.monthlyNap == 1800

    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetRestStats", side_effect=Exception("Error")):
        assert pet.updateRestStats(requests.Session()) is False


def test_pet_update_pet_location_and_device_details():
    """Test updatePetLocation and updateDeviceDetails success and failure."""
    pet = FiPet("test-pet")
    device = FiDevice("dev-1")
    pet._device = device

    loc_response = {
        "__typename": "OngoingRest",
        "areaName": "Home",
        "lastReportTimestamp": "2026-06-26T12:00:00.000Z",
        "start": "2026-06-26T11:30:00.000Z",
        "position": {"latitude": 10.0, "longitude": 20.0},
    }
    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetLocation", return_value=loc_response):
        assert pet.updatePetLocation(requests.Session()) is True
        assert pet.currLatitude == 10.0

    with patch("custom_components.tryfi.pytryfi.common.query.getCurrentPetLocation", side_effect=Exception("Error")):
        assert pet.updatePetLocation(requests.Session()) is False

    device_response = {
        "device": {
            "moduleId": "FC1001",
            "info": {"buildId": "1.0", "batteryPercent": "90"},
            "operationParams": {"ledOffAt": None, "ledEnabled": False, "mode": "NORMAL"},
            "ledColor": {"name": "Red", "hexCode": "#FF0000"},
            "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 80},
            "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
        }
    }
    with patch("custom_components.tryfi.pytryfi.common.query.getDevicedetails", return_value=device_response):
        assert pet.updateDeviceDetails(requests.Session()) is True
        assert pet.device.moduleId == "FC1001"

    with patch("custom_components.tryfi.pytryfi.common.query.getDevicedetails", side_effect=Exception("Error")):
        assert pet.updateDeviceDetails(requests.Session()) is False


def test_pet_update_all_details_behavior_warning():
    """Test updateAllDetails when updateBehaviorStats raises a warning exception."""
    pet = FiPet("test-pet")
    pet._device = FiDevice("dev-series3")
    pet._device._moduleId = "FC3001"  # supports advanced behavior stats

    with patch("custom_components.tryfi.pytryfi.common.query.getPetAllInfo", return_value=GRAPHQL_PARTIAL_PET), \
         patch.object(pet, "updateBehaviorStats", side_effect=Exception("Behavior error")):
        pet.updateAllDetails(requests.Session())
        assert pet.currLatitude is not None


def test_pet_set_behavior_stats_from_trends_edge_cases():
    """Test setBehaviorStatsFromTrends with non-dict items and missing summaries."""
    pet = FiPet("test-pet")

    behavior_trends = [
        "invalid_string_item",  # Non-dict item
        {
            "id": "barking:DAY",
            "summaryComponents": {
                "eventsSummary": None,  # None eventsSummary
            },
        },
        {
            "id": "eating:DAY",
            "summaryComponents": {
                "eventsSummary": "5 events",
                "durationSummary": None,
            },
        },
    ]

    pet.setBehaviorStatsFromTrends(behavior_trends, "DAY")
    assert pet.dailyBarkingCount == 0
    assert pet.dailyEatingCount == 5
    assert pet.dailyEatingDuration == 0


def test_pet_update_behavior_stats_exception():
    """Test updateBehaviorStats exception logging during period iterations."""
    pet = FiPet("test-pet")
    with patch("custom_components.tryfi.pytryfi.common.query.getPetHealthTrends", side_effect=Exception("Trend error")):
        # Should not raise exception
        pet.updateBehaviorStats(requests.Session())


def test_pet_led_and_lost_mode_controls():
    """Test setLedColorCode, turnOnOffLed, and setLostDogMode success, inner warning, and outer exception."""
    pet = FiPet("test-pet")
    pet._device = FiDevice("dev-led")
    pet.device._moduleId = "FC3001"

    # setLedColorCode success
    with patch("custom_components.tryfi.pytryfi.common.query.setLedColor", return_value={"setDeviceLed": {
        "moduleId": "FC3001",
        "info": {"buildId": "1.0", "batteryPercent": "90"},
        "operationParams": {"ledOffAt": None, "ledEnabled": True, "mode": "NORMAL"},
        "ledColor": {"name": "Green", "hexCode": "#00FF00"},
        "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 80},
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
    }}):
        assert pet.setLedColorCode(requests.Session(), 2) is True

    # setLedColorCode inner exception (setDeviceDetailsJSON fail)
    with patch("custom_components.tryfi.pytryfi.common.query.setLedColor", return_value={"setDeviceLed": None}):
        assert pet.setLedColorCode(requests.Session(), 2) is True

    # setLedColorCode outer exception
    with patch("custom_components.tryfi.pytryfi.common.query.setLedColor", side_effect=Exception("API error")):
        assert pet.setLedColorCode(requests.Session(), 2) is False

    # turnOnOffLed success
    with patch("custom_components.tryfi.pytryfi.common.query.turnOnOffLed", return_value={"updateDeviceOperationParams": {
        "moduleId": "FC3001",
        "info": {"buildId": "1.0", "batteryPercent": "90"},
        "operationParams": {"ledOffAt": None, "ledEnabled": True, "mode": "NORMAL"},
        "ledColor": {"name": "Green", "hexCode": "#00FF00"},
        "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 80},
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
    }}):
        assert pet.turnOnOffLed(requests.Session(), True) is True

    # turnOnOffLed inner exception
    with patch("custom_components.tryfi.pytryfi.common.query.turnOnOffLed", return_value={"updateDeviceOperationParams": None}):
        assert pet.turnOnOffLed(requests.Session(), True) is True

    # turnOnOffLed outer exception
    with patch("custom_components.tryfi.pytryfi.common.query.turnOnOffLed", side_effect=Exception("API error")):
        assert pet.turnOnOffLed(requests.Session(), True) is False

    # setLostDogMode success
    with patch("custom_components.tryfi.pytryfi.common.query.setLostDogMode", return_value={"updateDeviceOperationParams": {
        "moduleId": "FC3001",
        "info": {"buildId": "1.0", "batteryPercent": "90"},
        "operationParams": {"ledOffAt": None, "ledEnabled": True, "mode": "LOST_DOG"},
        "ledColor": {"name": "Red", "hexCode": "#FF0000"},
        "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 80},
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
    }}):
        assert pet.setLostDogMode(requests.Session(), True) is True

    # setLostDogMode inner exception
    with patch("custom_components.tryfi.pytryfi.common.query.setLostDogMode", return_value={"updateDeviceOperationParams": None}):
        assert pet.setLostDogMode(requests.Session(), True) is True

    # setLostDogMode outer exception
    with patch("custom_components.tryfi.pytryfi.common.query.setLostDogMode", side_effect=Exception("API error")):
        assert pet.setLostDogMode(requests.Session(), True) is False


def test_pet_properties_and_getters_coverage():
    """Test remaining FiPet properties and getters."""
    pet = FiPet("test-pet-props")
    pet_json = {
        "name": "Max",
        "yearOfBirth": 2020,
        "monthOfBirth": 5,
        "dayOfBirth": 15,
        "gender": "MALE",
        "weight": 25.4,
        "breed": {"name": "Golden Retriever"},
        "photos": {"first": {"image": {"fullSize": "http://example.com/photo.jpg"}}},
        "device": {
            "id": "dev-999",
            "moduleId": "FC3001",
            "info": {"buildId": "1.0", "batteryPercent": "95"},
            "operationParams": {"ledOffAt": None, "ledEnabled": False, "mode": "NORMAL"},
            "ledColor": {"name": "Yellow", "hexCode": "#FFFF00"},
            "lastConnectionState": {"__typename": "ConnectedToCellular", "date": "2026-06-26T00:00:00.000Z", "signalStrengthPercent": 90},
            "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
        },
    }
    pet.setPetDetailsJSON(pet_json)

    assert pet.name == "Max"
    assert pet.yearOfBirth == 2020
    assert pet.monthOfBirth == 5
    assert pet.dayOfBirth == 15
    assert pet.getBirthDate() == datetime.datetime(2020, 5, 15)
    assert pet.gender == "MALE"
    assert pet.weight == 25.4
    assert pet.breed == "Golden Retriever"
    assert pet.photoLink == "http://example.com/photo.jpg"
    assert pet.locationNextEstimatedUpdate is not None
    assert pet.isLost is False
    pet._connectionSignalStrength = 90
    assert pet.signalStrength == 90

    # Test photo default when missing
    pet_json_no_photo = dict(pet_json)
    pet_json_no_photo["photos"] = {}
    pet.setPetDetailsJSON(pet_json_no_photo)
    assert pet.photoLink == ""

    # Test all behavior metric properties
    pet._weeklyBarkingCount = 10
    pet._weeklyBarkingDuration = 20
    pet._monthlyBarkingCount = 30
    pet._monthlyBarkingDuration = 60

    pet._weeklyLickingCount = 11
    pet._weeklyLickingDuration = 21
    pet._monthlyLickingCount = 31
    pet._monthlyLickingDuration = 61

    pet._weeklyScratchingCount = 12
    pet._weeklyScratchingDuration = 22
    pet._monthlyScratchingCount = 32
    pet._monthlyScratchingDuration = 62

    pet._weeklyEatingCount = 13
    pet._weeklyEatingDuration = 23
    pet._monthlyEatingCount = 33
    pet._monthlyEatingDuration = 63

    pet._weeklyDrinkingCount = 14
    pet._weeklyDrinkingDuration = 24
    pet._monthlyDrinkingCount = 34
    pet._monthlyDrinkingDuration = 64

    assert pet.weeklyBarkingCount == 10
    assert pet.weeklyBarkingDuration == 20
    assert pet.monthlyBarkingCount == 30
    assert pet.monthlyBarkingDuration == 60

    assert pet.weeklyLickingCount == 11
    assert pet.weeklyLickingDuration == 21
    assert pet.monthlyLickingCount == 31
    assert pet.monthlyLickingDuration == 61

    assert pet.weeklyScratchingCount == 12
    assert pet.weeklyScratchingDuration == 22
    assert pet.monthlyScratchingCount == 32
    assert pet.monthlyScratchingDuration == 62

    assert pet.weeklyEatingCount == 13
    assert pet.weeklyEatingDuration == 23
    assert pet.monthlyEatingCount == 33
    assert pet.monthlyEatingDuration == 63

    assert pet.weeklyDrinkingCount == 14
    assert pet.weeklyDrinkingDuration == 24
    assert pet.monthlyDrinkingCount == 34
    assert pet.monthlyDrinkingDuration == 64

