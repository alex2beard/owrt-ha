"""Data update coordinator for OpenWrt Control."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenWrtAuthError, OpenWrtClient, OpenWrtError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenWrtControlDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator responsible for periodic OpenWrt status refreshes."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenWrtClient,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from OpenWrt."""
        try:
            return await self.client.async_get_status()
        except OpenWrtAuthError as err:
            raise ConfigEntryAuthFailed from err
        except OpenWrtError as err:
            raise UpdateFailed(str(err)) from err
