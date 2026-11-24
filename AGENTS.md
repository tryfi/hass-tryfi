# AGENTS.md

## Commands

- **Run tests:** `uv run pytest -v`
- **Lint:** `uv run ruff check .`

## Architecture

- `custom_components/tryfi/` - Main HA integration code
  - `__init__.py` - Entry point, config flow, services
  - `coordinator.py` - Data update coordinator
  - `sensor.py`, `device_tracker.py`, `light.py`, etc. - Platform implementations
- `custom_components/tryfi/pytryfi/` - Embedded pytryfi library (API client)
- `tests/` - Integration and unit tests

## Key Patterns

- Uses Home Assistant's async/await pattern for all operations
- API calls are wrapped with `hass.async_add_executor_job` since pytryfi is synchronous
- Data flows through `TryFiDataUpdateCoordinator` for polling
- Platforms access data via `hass.data[DOMAIN][entry.entry_id]`
- Home Assistant Sensor classes should define config using the SensorEntityDescription pattern instead of using `if self._key == 'foo'`.

## Testing

- Most changes should be tested, however don't write low value test cases that aren't likely to ever catch an issue.