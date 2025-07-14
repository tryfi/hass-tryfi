"""Test manifest and configuration."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.tryfi import PLATFORMS
from homeassistant.const import Platform


def test_manifest_valid():
    """Test that manifest.json is valid."""
    manifest_path = (
        Path(__file__).parent.parent / "custom_components" / "tryfi" / "manifest.json"
    )

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Required fields
    assert manifest["domain"] == "tryfi"
    assert manifest["name"] == "TryFi"
    assert "version" in manifest
    assert manifest["config_flow"] is True
    assert manifest["documentation"]
    assert manifest["issue_tracker"]
    assert manifest["codeowners"] == ["@tryfi"]
    assert manifest["iot_class"] == "cloud_polling"
    assert manifest["requirements"] == []  # We embedded pytryfi

    # Version format
    version_parts = manifest["version"].split(".")
    assert len(version_parts) == 3
    assert all(part.isdigit() for part in version_parts)


def test_translations_exist():
    """Test that translation files exist."""
    translations_dir = (
        Path(__file__).parent.parent / "custom_components" / "tryfi" / "translations"
    )

    # At minimum, English should exist
    en_file = translations_dir / "en.json"
    assert en_file.exists()

    with open(en_file) as f:
        translations = json.load(f)

    # Check structure
    assert "config" in translations
    assert "step" in translations["config"]
    assert "user" in translations["config"]["step"]
    assert "error" in translations["config"]

    # Check required keys
    assert "cannot_connect" in translations["config"]["error"]
    assert "unknown" in translations["config"]["error"]


def test_all_platforms_imported():
    """Test that all platforms can be imported."""

    expected_platforms = [
        Platform.BINARY_SENSOR,
        Platform.DEVICE_TRACKER,
        Platform.LIGHT,
        Platform.NUMBER,
        Platform.SELECT,
        Platform.SENSOR,
        Platform.SWITCH,
    ]

    assert set(PLATFORMS) == set(expected_platforms)

    # Test each platform module can be imported
    for platform in PLATFORMS:
        module_name = f"custom_components.tryfi.{platform}"
        __import__(module_name)
