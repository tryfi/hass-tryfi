# TryFi Integration Tests

This directory contains the test suite for the TryFi Home Assistant integration.

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements_test.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=custom_components.tryfi --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test File
```bash
pytest tests/test_sensor.py
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Structure

- `conftest.py` - Shared fixtures for all tests
- `common.py` - Common test utilities and mock helpers
- `test_init.py` - Tests for integration setup and coordinator
- `test_config_flow.py` - Tests for configuration flow
- `test_sensor.py` - Tests for sensor entities
- `test_device_tracker.py` - Tests for device tracker entities (TODO)
- `test_binary_sensor.py` - Tests for binary sensor entities (TODO)
- `test_light.py` - Tests for light entities (TODO)
- `test_select.py` - Tests for select entities (TODO)

## Writing Tests

### Basic Test Structure
```python
async def test_my_feature(hass: HomeAssistant) -> None:
    """Test description."""
    # Arrange
    mock_data = create_mock_data()
    
    # Act
    result = await my_function(hass, mock_data)
    
    # Assert
    assert result == expected_value
```

### Using Fixtures
```python
async def test_with_fixture(
    hass: HomeAssistant,
    mock_pet,
    mock_coordinator
) -> None:
    """Test using fixtures."""
    # mock_pet and mock_coordinator are automatically injected
    assert mock_pet.name == "Test Dog"
```

## Coverage Goals

- Aim for >90% code coverage
- Test all entity types
- Test error conditions
- Test edge cases (missing data, invalid values)
- Test configuration flow validation

## Linting and Type Checking

Before submitting, ensure code passes all checks:

```bash
# Format code
black custom_components/tryfi tests

# Check linting
flake8 custom_components/tryfi tests

# Check types
mypy custom_components/tryfi
```