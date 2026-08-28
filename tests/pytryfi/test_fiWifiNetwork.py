from custom_components.tryfi.pytryfi.fiWifiNetwork import FiWifiNetwork


def test_wifi_network_with_position():
    wifi = FiWifiNetwork("MyHomeWifi", "household_123")
    assert wifi.ssid == "MyHomeWifi"
    assert wifi.householdId == "household_123"

    details = {
        "state": "ONLINE",
        "addressLabel": "123 Main St",
        "isHidden": True,
        "position": {
            "latitude": 37.7749,
            "longitude": -122.4194,
        },
    }
    wifi.setDetailsJSON(details)

    assert wifi.state == "ONLINE"
    assert wifi.addressLabel == "123 Main St"
    assert wifi.isHidden is True
    assert wifi.latitude == 37.7749
    assert wifi.longitude == -122.4194

    expected_str = (
        "WiFi Network: MyHomeWifi State: ONLINE "
        "Address: 123 Main St Hidden: True "
        "Location: 37.7749,-122.4194"
    )
    assert str(wifi) == expected_str


def test_wifi_network_without_position():
    wifi = FiWifiNetwork("GuestWifi", "household_456")
    details = {
        "state": "OFFLINE",
        "addressLabel": None,
        "position": None,
    }
    wifi.setDetailsJSON(details)

    assert wifi.state == "OFFLINE"
    assert wifi.addressLabel is None
    assert wifi.isHidden is False
    assert wifi.latitude is None
    assert wifi.longitude is None
