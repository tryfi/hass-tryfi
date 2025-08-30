from unittest.mock import Mock

import responses
import urllib.parse

from custom_components.tryfi.pytryfi.common.query import (
    FRAGMENT_USER_DETAILS,
    QUERY_CURRENT_USER,
    QUERY_PET_ACTIVE_DETAILS,
    REQUEST_FRAGMENTS_PET_ALL_INFO,
    REQUEST_GET_HOUSEHOLDS,
    VAR_PET_ID,
)


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
    mock_graphql(
        QUERY_CURRENT_USER + FRAGMENT_USER_DETAILS,
        status=200,
        response={
            "currentUser": {
                "email": "email",
                "firstName": "John",
                "lastName": "Smith",
                "phoneNumber": "phone",
            }
        },
    )


def mock_household_with_pets(pets: list[dict] = [], bases: list[dict] = []):
    mock_graphql(
        query=REQUEST_GET_HOUSEHOLDS,
        response={
            "currentUser": {
                "userHouseholds": [{"household": {"pets": pets, "bases": bases}}]
            }
        },
        status=200,
    )
    mock_graphql(
        query=REQ_PET_ALL_INFO, status=200, response=GRAPHQL_FIXTURE_PET_ALL_INFO
    )


REQ_PET_ALL_INFO = (
    QUERY_PET_ACTIVE_DETAILS.replace(VAR_PET_ID, "test-pet")
    + REQUEST_FRAGMENTS_PET_ALL_INFO
)

GRAPHQL_PARTIAL_DEVICE_VALUE = {
    "device": {
        "__typename": "Device",
        "id": "DEVICEID",
        "moduleId": "DEVICEID",
        "info": {
            "batteryPercent": 92,
            "buildId": "4.16.61-d8fcd9279-fc3_f3-prod",
        },
        "operationParams": {
            "__typename": "OperationParams",
            "mode": "NORMAL",
            "ledEnabled": None,
            "ledOffAt": None,
        },
        "ledColor": {
            "__typename": "LedColor",
            "ledColorCode": 8,
            "hexCode": "ffffff",
            "name": "White",
        },
        "lastConnectionState": {
            "__typename": "ConnectedToBase",
            "date": "2025-06-17T01:25:41.705Z",
            "chargingBase": {"__typename": "ChargingBase", "id": "FB33A514868"},
        },
        "nextLocationUpdateExpectedBy": "2025-06-17T01:32:35.504Z",
    }
}

GRAPHQL_PARTIAL_PET = {
    "id": "test-pet",
    "yearOfBirth": 2020,
    "monthOfBirth": 10,
    "dayOfBirth": 5,
    "gender": "Female",
    "weight": 12,
    "name": "Buddy",
    "breed": {
        "name": "Golden Retriever",
    },
    "device": {
        "__typename": "Device",
        "id": "DEVICEID",
        "moduleId": "DEVICEID",
        "info": {
            "batteryPercent": 92,
            "buildId": "1.2.3",
        },
        "operationParams": {
            "__typename": "OperationParams",
            "mode": "NORMAL",
            "ledEnabled": None,
            "ledOffAt": None,
        },
        "ledColor": {
            "__typename": "LedColor",
            "ledColorCode": 8,
            "hexCode": "ffffff",
            "name": "White",
        },
        "lastConnectionState": {
            "__typename": "ConnectedToBase",
            "date": "2025-06-17T01:25:41.705Z",
            "chargingBase": {"__typename": "ChargingBase", "id": "FB33A514868"},
        },
        "nextLocationUpdateExpectedBy": "2025-06-17T01:32:35.504Z",
    },
    "ongoingActivity": {
        "__typename": "OngoingRest",
        "areaName": "FooArea",
        "lastReportTimestamp": "2025-06-17T01:30:00.000Z",
        "position": {
            "latitude": -40,
            "longitude": 16,
        },
        "start": "2025-06-17T01:00:00.000Z",
    },
    "dailyStepStat": {
        "stepGoal": 5000,
        "totalSteps": 4000,
        "totalDistance": 54,
    },
    "weeklyStepStat": {},
    "monthlyStepStat": {},
    "dailySleepStat": {
        "restSummaries": [
            {
                "data": {
                    "sleepAmounts": [
                        {"type": "SLEEP", "duration": 60},
                        {"type": "NAP", "duration": 30},
                    ]
                }
            }
        ]
    },
    "monthlySleepStat": {"restSummaries": [{"data": {}}]},
}

GRAPHQL_BASE = {
    "baseId": "BASEID-LR",
    "name": "Living Room Base",
    "online": True,
    "onlineQuality": "Online",
    "infoLastUpdated": "2025-08-29T00:00:00Z",
    "networkName": "NETWORKNAME",
    "position": {
        "latitude": 80,
        "longitude": -47,
    },
}

GRAPHQL_FIXTURE_PET_ALL_INFO = {"pet": GRAPHQL_PARTIAL_PET}

GRAPHQL_RESP_GET_HOUSEHOLDS = {
    "currentUser": {
        "userHouseholds": [
            {"household": {"pets": [GRAPHQL_PARTIAL_PET], "bases": [GRAPHQL_BASE]}}
        ]
    }
}
