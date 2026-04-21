"""Config flow for OpenWrt Control."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenWrtAuthError, OpenWrtClient, OpenWrtError
from .const import (
    CONF_USE_HTTPS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _async_validate_input(hass, user_input: dict[str, Any]) -> dict[str, str]:
    """Validate user-provided connection settings."""
    session = async_get_clientsession(
        hass,
        verify_ssl=user_input[CONF_VERIFY_SSL],
    )
    client = OpenWrtClient(
        session=session,
        host=user_input[CONF_HOST],
        port=user_input[CONF_PORT],
        username=user_input[CONF_USERNAME],
        password=user_input[CONF_PASSWORD],
        use_https=user_input[CONF_USE_HTTPS],
    )
    status = await client.async_test_connection()
    title = status.get("system", {}).get("hostname") or user_input[CONF_HOST]
    return {"title": str(title)}


def _build_unique_id(host: str, port: int, use_https: bool) -> str:
    """Build a stable unique id for an OpenWrt endpoint."""
    scheme = "https" if use_https else "http"
    return f"{scheme}://{host}:{port}"


class OpenWrtControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenWrt Control."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return OpenWrtControlOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = _build_unique_id(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USE_HTTPS],
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await _async_validate_input(self.hass, user_input)
            except OpenWrtAuthError:
                errors["base"] = "invalid_auth"
            except OpenWrtError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while validating OpenWrt Control")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def _get_schema(user_input: dict[str, Any] | None) -> vol.Schema:
        """Return the config form schema."""
        user_input = user_input or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=user_input.get(CONF_HOST, ""),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=user_input.get(CONF_PORT, ""),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(
                    CONF_USE_HTTPS,
                    default=user_input.get(CONF_USE_HTTPS, False),
                ): bool,
                vol.Required(
                    CONF_VERIFY_SSL,
                    default=user_input.get(CONF_VERIFY_SSL, False),
                ): bool,
                vol.Required(
                    CONF_USERNAME,
                    default=user_input.get(CONF_USERNAME, ""),
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=user_input.get(CONF_PASSWORD, ""),
                ): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        )


class OpenWrtControlOptionsFlow(config_entries.OptionsFlow):
    """Handle options for OpenWrt Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            merged_input = {**self._config_entry.data, **self._config_entry.options, **user_input}
            new_unique_id = _build_unique_id(
                merged_input[CONF_HOST],
                merged_input[CONF_PORT],
                merged_input[CONF_USE_HTTPS],
            )

            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == self._config_entry.entry_id:
                    continue
                if entry.unique_id == new_unique_id:
                    return self.async_abort(reason="already_configured")

            try:
                await _async_validate_input(
                    self.hass,
                    merged_input,
                )
            except OpenWrtAuthError:
                errors["base"] = "invalid_auth"
            except OpenWrtError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception(
                    "Unexpected error while validating OpenWrt Control options"
                )
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    unique_id=new_unique_id,
                )
                return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=OpenWrtControlConfigFlow._get_schema(current),
            errors=errors,
        )
