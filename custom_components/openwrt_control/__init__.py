"""The OpenWrt Control integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenWrtClient
from .const import (
    CONF_USE_HTTPS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import OpenWrtControlDataUpdateCoordinator


@dataclass(slots=True)
class OpenWrtControlRuntimeData:
    """Runtime objects stored on the config entry."""

    client: OpenWrtClient
    coordinator: OpenWrtControlDataUpdateCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenWrt Control from a config entry."""
    config = {**entry.data, **entry.options}
    session = async_get_clientsession(
        hass,
        verify_ssl=config.get(CONF_VERIFY_SSL, False),
    )
    client = OpenWrtClient(
        session=session,
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        use_https=config.get(CONF_USE_HTTPS, False),
    )
    coordinator = OpenWrtControlDataUpdateCoordinator(
        hass=hass,
        client=client,
        scan_interval=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = OpenWrtControlRuntimeData(
        client=client,
        coordinator=coordinator,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None
    return unload_ok
