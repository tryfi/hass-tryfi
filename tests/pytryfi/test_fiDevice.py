"""Tests for FiDevice.setConnectedTo — especially null name handling."""

from __future__ import annotations

from custom_components.tryfi.pytryfi.fiDevice import FiDevice


def _make_device() -> FiDevice:
    """Create a bare FiDevice for testing setConnectedTo."""
    return FiDevice("test-device-id")


def test_connected_to_user_both_names():
    """ConnectedToUser with both firstName and lastName present."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToUser",
        "date": "2026-06-26T00:00:00.000Z",
        "user": {
            "id": "user123",
            "firstName": "John",
            "lastName": "Smith",
        },
    })
    assert result == "John Smith"
    assert dev.connectionSignalStrength is None


def test_connected_to_user_null_last_name():
    """ConnectedToUser where lastName is None (the bug we fixed).

    The TryFi API sometimes returns the account email as firstName
    with lastName=null.  The old code did ``firstName + " " + lastName``
    which raised TypeError when lastName was None.
    """
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToUser",
        "date": "2026-06-26T00:00:00.000Z",
        "user": {
            "id": "user456",
            "firstName": "user@example.com",
            "lastName": None,
        },
    })
    assert result == "user@example.com"
    assert dev.connectionSignalStrength is None


def test_connected_to_user_null_first_name():
    """ConnectedToUser where firstName is None."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToUser",
        "date": "2026-06-26T00:00:00.000Z",
        "user": {
            "id": "user789",
            "firstName": None,
            "lastName": "Smith",
        },
    })
    assert result == "Smith"


def test_connected_to_user_both_null():
    """ConnectedToUser where both names are None."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToUser",
        "date": "2026-06-26T00:00:00.000Z",
        "user": {
            "id": "user000",
            "firstName": None,
            "lastName": None,
        },
    })
    assert result == ""


def test_connected_to_user_missing_keys():
    """ConnectedToUser where firstName and lastName keys are absent."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToUser",
        "date": "2026-06-26T00:00:00.000Z",
        "user": {
            "id": "user111",
        },
    })
    assert result == ""


def test_connected_to_cellular():
    """ConnectedToCellular sets signal strength and returns 'Cellular'."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToCellular",
        "date": "2026-06-26T00:00:00.000Z",
        "signalStrengthPercent": 75,
    })
    assert result == "Cellular"
    assert dev.connectionSignalStrength == 75


def test_connected_to_base():
    """ConnectedToBase returns base ID string."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "ConnectedToBase",
        "date": "2026-06-26T00:00:00.000Z",
        "chargingBase": {
            "__typename": "ChargingBase",
            "id": "FB33A514868",
        },
    })
    assert result == "Base ID - FB33A514868"
    assert dev.connectionSignalStrength is None


def test_connected_to_unknown_type():
    """Unknown connection type returns None."""
    dev = _make_device()
    result = dev.setConnectedTo({
        "__typename": "SomeNewType",
        "date": "2026-06-26T00:00:00.000Z",
    })
    assert result is None
    assert dev.connectionSignalStrength is None


def test_device_details_json_and_properties():
    """Test setDeviceDetailsJSON parsing and property accessors."""
    dev = FiDevice("device-123")
    assert dev.deviceId == "device-123"

    device_json = {
        "moduleId": "FC3001",
        "info": {
            "buildId": "1.2.3",
            "batteryPercent": "85",
            "isCharging": True,
            "temperature": 2500,  # float(2500)/100 = 25.0
        },
        "operationParams": {
            "ledOffAt": "2099-01-01T00:00:00.000Z",
            "ledEnabled": True,
            "mode": "LOST_DOG",
        },
        "ledColor": {
            "name": "Red",
            "hexCode": "#FF0000",
        },
        "lastConnectionState": {
            "__typename": "ConnectedToCellular",
            "date": "2026-06-26T00:00:00.000Z",
            "signalStrengthPercent": 90,
        },
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
        "availableLedColors": [
            {"ledColorCode": "1", "hexCode": "#FF0000", "name": "Red"},
            {"ledColorCode": "2", "hexCode": "#00FF00", "name": "Green"},
        ],
    }

    dev.setDeviceDetailsJSON(device_json)

    assert dev.moduleId == "FC3001"
    assert dev.buildId == "1.2.3"
    assert dev.batteryPercent == 85
    assert dev.isCharging is True
    assert dev.temperature == 25.0
    assert dev.mode == "LOST_DOG"
    assert dev.isLost is True
    assert dev.ledOn is True
    assert dev.ledColor == "Red"
    assert dev.ledColorHex == "#FF0000"
    assert dev.connectedTo == "Cellular"
    assert dev.connectionStateType == "ConnectedToCellular"
    assert dev.connectionSignalStrength == 90
    assert dev._nextLocationUpdatedExpectedBy is not None
    assert dev.lastUpdated is not None
    assert len(dev.availableLedColors) == 2
    assert dev.availableLedColors[0].name == "Red"

    # Test __str__
    str_repr = str(dev)
    assert "Device ID: device-123" in str_repr
    assert "Device Mode: LOST_DOG" in str_repr
    assert "Battery Left: 85%" in str_repr


def test_device_details_non_numeric_battery_and_v2_charging():
    """Test fallback when batteryPercent is invalid and isCharging is missing."""
    dev = FiDevice("device-456")
    device_json = {
        "moduleId": "FC1001",
        "info": {
            "buildId": "1.0.0",
            "batteryPercent": "invalid",
        },
        "operationParams": {
            "ledOffAt": None,
            "ledEnabled": False,
            "mode": "NORMAL",
        },
        "ledColor": {
            "name": "Blue",
            "hexCode": "#0000FF",
        },
        "lastConnectionState": {
            "__typename": "ConnectedToUser",
            "date": "2026-06-26T00:00:00.000Z",
            "user": {"firstName": "Jane", "lastName": "Doe"},
        },
        "nextLocationUpdateExpectedBy": "2026-06-26T01:00:00.000Z",
    }

    dev.setDeviceDetailsJSON(device_json)
    assert dev.batteryPercent is None
    assert dev.isCharging is None
    assert dev.temperature is None
    assert dev.availableLedColors is None
    assert dev.isLost is False
    assert dev.ledOn is False


def test_supports_advanced_behavior_stats():
    """Test module ID checks for advanced behavior stats support."""
    dev = FiDevice("dev1")

    # None moduleId
    assert dev.supportsAdvancedBehaviorStats() is False

    # FC1, FC2, M1 series -> False
    dev._moduleId = "FC123"
    assert dev.supportsAdvancedBehaviorStats() is False
    dev._moduleId = "FC245"
    assert dev.supportsAdvancedBehaviorStats() is False
    dev._moduleId = "M1001"
    assert dev.supportsAdvancedBehaviorStats() is False

    # FC3, S3, etc -> True
    dev._moduleId = "FC3001"
    assert dev.supportsAdvancedBehaviorStats() is True


def test_get_accurate_led_status_and_set_led_off_at_date():
    """Test LED status calculations based on current time vs ledOffAt."""
    dev = FiDevice("dev2")

    # None ledOffAt
    now_utc = dev.setLedOffAtDate(None)
    assert now_utc is not None

    # LED status False input
    assert dev.getAccurateLEDStatus(False) is False

    # LED status True with past ledOffAt -> returns False
    dev._ledOffAt = dev.setLedOffAtDate("2000-01-01T00:00:00.000Z")
    assert dev.getAccurateLEDStatus(True) is False

    # LED status True with future ledOffAt -> returns True
    dev._ledOffAt = dev.setLedOffAtDate("2099-01-01T00:00:00.000Z")
    assert dev.getAccurateLEDStatus(True) is True