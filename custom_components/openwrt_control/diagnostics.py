"""Diagnostics support for OpenWrt Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import OpenWrtControlRuntimeData

_REDACT_KEYS = {
    "password",
    "session_id",
    "token",
    "cookie",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data: OpenWrtControlRuntimeData | None = entry.runtime_data

    diagnostics = {
        "entry": async_redact_data(dict(entry.data), _REDACT_KEYS),
        "options": async_redact_data(dict(entry.options), _REDACT_KEYS),
        "coordinator": {
            "last_update_success": runtime_data.coordinator.last_update_success
            if runtime_data
            else None,
            "data": runtime_data.coordinator.data if runtime_data else None,
        },
    }

    return async_redact_data(diagnostics, _REDACT_KEYS)
