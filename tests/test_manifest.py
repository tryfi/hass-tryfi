"""Test manifest and configuration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_manifest_valid():
    """Test that manifest.json is valid."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "tryfi" / "manifest.json"
    
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
    translations_dir = Path(__file__).parent.parent / "custom_components" / "tryfi" / "translations"
    
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
    from custom_components.tryfi import PLATFORMS
    from homeassistant.const import Platform
    
    expected_platforms = [
        Platform.BINARY_SENSOR,
        Platform.DEVICE_TRACKER,
        Platform.LIGHT,
        Platform.SELECT,
        Platform.SENSOR,
    ]
    
    assert set(PLATFORMS) == set(expected_platforms)
    
    # Test each platform module can be imported
    for platform in PLATFORMS:
        module_name = f"custom_components.tryfi.{platform}"
        __import__(module_name)


def test_constants():
    """Test constants are properly defined."""
    from custom_components.tryfi.const import (
        CONF_PASSWORD,
        CONF_POLLING_RATE,
        CONF_USERNAME,
        DEFAULT_POLLING_RATE,
        DOMAIN,
        MANUFACTURER,
        MODEL,
        SENSOR_STATS_BY_TIME,
        SENSOR_STATS_BY_TYPE,
    )
    
    assert DOMAIN == "tryfi"
    assert CONF_USERNAME == "username"
    assert CONF_PASSWORD == "password"
    assert CONF_POLLING_RATE == "polling"
    assert DEFAULT_POLLING_RATE == 10
    assert MANUFACTURER == "TryFi"
    assert MODEL == "Smart Dog Collar"
    
    assert SENSOR_STATS_BY_TIME == ["DAILY", "WEEKLY", "MONTHLY"]
    assert SENSOR_STATS_BY_TYPE == ["STEPS", "DISTANCE", "SLEEP", "NAP"]


def test_all_files_have_docstrings():
    """Test that all Python files have module docstrings."""
    import ast
    
    src_path = Path(__file__).parent.parent / "custom_components" / "tryfi"
    
    for py_file in src_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        with open(py_file) as f:
            try:
                tree = ast.parse(f.read())
                docstring = ast.get_docstring(tree)
                assert docstring is not None, f"{py_file} is missing module docstring"
            except SyntaxError:
                pytest.fail(f"Syntax error in {py_file}")


def test_no_print_statements():
    """Test that there are no print statements in the code."""
    import ast
    
    src_path = Path(__file__).parent.parent / "custom_components" / "tryfi"
    
    class PrintChecker(ast.NodeVisitor):
        def __init__(self):
            self.has_print = False
            
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                self.has_print = True
            self.generic_visit(node)
    
    for py_file in src_path.rglob("*.py"):
        if "__pycache__" in str(py_file) or "test_" in str(py_file):
            continue
            
        with open(py_file) as f:
            tree = ast.parse(f.read())
            checker = PrintChecker()
            checker.visit(tree)
            assert not checker.has_print, f"{py_file} contains print statements"