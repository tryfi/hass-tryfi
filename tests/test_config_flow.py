"""Test the TryFi config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.tryfi import config_flow
from custom_components.tryfi.config_flow import CannotConnect
from custom_components.tryfi.const import CONF_POLLING_RATE, DOMAIN


@pytest.fixture
def mock_setup_entry():
    """Mock setup entry."""
    with patch(
        "custom_components.tryfi.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_pytryfi():
    """Mock PyTryFi."""
    with patch("custom_components.tryfi.config_flow.PyTryFi") as mock_pytryfi:
        instance = mock_pytryfi.return_value
        instance.currentUser = AsyncMock()
        yield mock_pytryfi


async def test_form_user(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_pytryfi
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        return_value={"title": "test@email.com"},
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@email.com",
                CONF_PASSWORD: "test-password",
                CONF_POLLING_RATE: 30,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test@email.com"
    assert result2["data"] == {
        CONF_USERNAME: "test@email.com",
        CONF_PASSWORD: "test-password",
        CONF_POLLING_RATE: 30,
    }
    assert len(mock_setup_entry.mock_calls) == 1


def test_config_flow_does_not_declare_connection_class() -> None:
    """Test the flow leaves obsolete connection metadata to Home Assistant."""
    assert "CONNECTION_CLASS" not in vars(config_flow.ConfigFlow)


async def test_form_invalid_auth(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_pytryfi.side_effect = CannotConnect
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "wrong-password",
            CONF_POLLING_RATE: 30,
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_exception(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test we handle unexpected exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        side_effect=Exception("Boom"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@email.com",
                CONF_PASSWORD: "test-password",
                CONF_POLLING_RATE: 30,
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_options_flow_init(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test options flow initialization."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        minor_version=1,
        discovery_keys=None,
        unique_id="test",
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["description_placeholders"]["current_user"] == "test@email.com"


async def test_options_flow_change_polling_only(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test changing only the polling rate."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Update only polling rate (no credential validation should occur)
    with patch(
        "custom_components.tryfi.config_flow.validate_input",
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@email.com",  # Same as before
                CONF_PASSWORD: "test-password",  # Same as before
                CONF_POLLING_RATE: 60,  # Changed from 30 to 60
            },
        )

        # validate_input should NOT be called since credentials didn't change
        assert mock_validate.call_count == 0

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"] == {}
    # Check that config entry was updated
    assert entry.data[CONF_POLLING_RATE] == 60


async def test_options_flow_change_credentials_success(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test successfully changing credentials."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Update credentials
    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        return_value={"title": "new@email.com"},
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "new@email.com",  # Changed
                CONF_PASSWORD: "new-password",  # Changed
                CONF_POLLING_RATE: 45,  # Also changed
            },
        )

        # validate_input should be called since credentials changed
        assert mock_validate.call_count == 1
        mock_validate.assert_called_with(
            hass,
            {
                CONF_USERNAME: "new@email.com",
                CONF_PASSWORD: "new-password",
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"] == {}
    # Check that config entry was updated
    assert entry.data[CONF_USERNAME] == "new@email.com"
    assert entry.data[CONF_PASSWORD] == "new-password"
    assert entry.data[CONF_POLLING_RATE] == 45


async def test_options_flow_change_credentials_invalid(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test changing credentials with invalid new credentials."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Try to update with invalid credentials
    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "invalid@email.com",
                CONF_PASSWORD: "wrong-password",
                CONF_POLLING_RATE: 30,
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
    # Check that config entry was NOT updated
    assert entry.data[CONF_USERNAME] == "test@email.com"
    assert entry.data[CONF_PASSWORD] == "test-password"


async def test_options_flow_unexpected_exception(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test handling unexpected exception in options flow."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Try to update with exception
    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        side_effect=Exception("Unexpected error"),
    ):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "new@email.com",
                CONF_PASSWORD: "new-password",
                CONF_POLLING_RATE: 30,
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_options_flow_partial_update(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test partial update - only changing username."""
    # Create a config entry
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "test-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Update only username
    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        return_value={"title": "new@email.com"},
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "new@email.com",  # Changed
                CONF_PASSWORD: "test-password",  # Same
                CONF_POLLING_RATE: 30,  # Same
            },
        )

        # validate_input should be called since username changed
        assert mock_validate.call_count == 1

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # Check that only username was updated
    assert entry.data[CONF_USERNAME] == "new@email.com"
    assert entry.data[CONF_PASSWORD] == "test-password"
    assert entry.data[CONF_POLLING_RATE] == 30


async def test_options_flow_password_not_prefilled(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test the stored password is not exposed in the options form."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "secret-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    schema = result["data_schema"]
    # The stored secret must never appear in the schema payload
    assert "secret-password" not in repr(schema)
    assert "secret-password" not in str(schema)

    for key in schema.schema:
        if key == CONF_PASSWORD:
            assert key.default is vol.UNDEFINED
        elif key == CONF_USERNAME:
            assert key.default() == "test@email.com"
        elif key == CONF_POLLING_RATE:
            assert key.default() == 30


async def test_options_flow_blank_password_keeps_stored(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test submitting a blank password keeps the stored password."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "secret-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "custom_components.tryfi.config_flow.validate_input",
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@email.com",
                CONF_PASSWORD: "",
                CONF_POLLING_RATE: 60,
            },
        )

        # Credentials did not change, so no validation is needed
        assert mock_validate.call_count == 0

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_PASSWORD] == "secret-password"
    assert entry.data[CONF_POLLING_RATE] == 60


async def test_options_flow_omitted_credentials_keep_stored(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test omitting credentials entirely keeps the stored values."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "secret-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "custom_components.tryfi.config_flow.validate_input",
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_POLLING_RATE: 45},
        )

        assert mock_validate.call_count == 0

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_USERNAME] == "test@email.com"
    assert entry.data[CONF_PASSWORD] == "secret-password"
    assert entry.data[CONF_POLLING_RATE] == 45


async def test_options_flow_new_password_validated(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test a new password is validated and stored."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="test@email.com",
        data={
            CONF_USERNAME: "test@email.com",
            CONF_PASSWORD: "secret-password",
            CONF_POLLING_RATE: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "custom_components.tryfi.config_flow.validate_input",
        return_value={"title": "test@email.com"},
    ) as mock_validate:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "test@email.com",
                CONF_PASSWORD: "new-secret",
                CONF_POLLING_RATE: 30,
            },
        )

        assert mock_validate.call_count == 1
        mock_validate.assert_called_with(
            hass,
            {
                CONF_USERNAME: "test@email.com",
                CONF_PASSWORD: "new-secret",
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_PASSWORD] == "new-secret"
