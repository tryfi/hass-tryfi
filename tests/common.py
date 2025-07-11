"""Common test utilities for TryFi integration."""
from __future__ import annotations

from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry


class MockConfigEntry(ConfigEntry):
    """Helper to create a mock config entry."""
    
    def __init__(
        self,
        *,
        domain: str = "tryfi",
        data: dict | None = None,
        options: dict | None = None,
        entry_id: str = "test",
        **kwargs,
    ) -> None:
        """Initialize a mock config entry."""
        super().__init__(
            version=1,
            domain=domain,
            title="Mock Title",
            data=data or {},
            options=options or {},
            entry_id=entry_id,
            **kwargs,
        )
        self.add_to_hass = Mock()
        self.state = None


def mock_pet_data() -> dict:
    """Create mock pet data."""
    return {
        "id": "test_pet_id",
        "name": "Test Dog",
        "device": {
            "id": "test_device_id",
            "moduleId": "test_module_id", 
            "batteryPercent": 85,
            "isCharging": False,
            "ledOn": True,
            "ledColorCode": 3,
            "connectionState": "CONNECTED",
        },
        "breed": {"name": "Labrador"},
        "photo": {"url": "https://example.com/photo.jpg"},
    }


def mock_base_data() -> dict:
    """Create mock base data."""
    return {
        "baseId": "test_base_id",
        "name": "Test Base",
        "online": True,
        "position": {
            "latitude": 40.123456,
            "longitude": -74.123456,
        },
    }