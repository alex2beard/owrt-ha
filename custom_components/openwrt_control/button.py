"""Button platform for OpenWrt Control."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OpenWrtControlRuntimeData
from .const import DOMAIN, ROUTER_NAME

_LOGGER = logging.getLogger(__name__)


def _get_path(data: dict[str, Any], *path: str) -> Any:
    """Safely retrieve a nested value from the coordinator payload."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


@dataclass(frozen=True, kw_only=True)
class OpenWrtButtonEntityDescription(ButtonEntityDescription):
    """Describe an OpenWrt button entity."""

    press_fn: Callable[[OpenWrtControlRuntimeData], Awaitable[dict[str, Any]]]
    enabled_by_default: bool = True
    refresh_after_press: bool = True


BUTTON_DESCRIPTIONS: tuple[OpenWrtButtonEntityDescription, ...] = (
    OpenWrtButtonEntityDescription(
        key="restart_passwall2",
        translation_key="restart_passwall2",
        press_fn=lambda runtime_data: runtime_data.client.async_restart_passwall2(),
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:restart",
    ),
    OpenWrtButtonEntityDescription(
        key="restart_dnsmasq",
        translation_key="restart_dnsmasq",
        press_fn=lambda runtime_data: runtime_data.client.async_restart_dnsmasq(),
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:restart",
    ),
    OpenWrtButtonEntityDescription(
        key="reload_firewall",
        translation_key="reload_firewall",
        press_fn=lambda runtime_data: runtime_data.client.async_reload_firewall(),
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-refresh",
    ),
    OpenWrtButtonEntityDescription(
        key="restart_vds_openconnect",
        translation_key="restart_vds_openconnect",
        press_fn=lambda runtime_data: runtime_data.client.async_restart_vds_openconnect(),
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:restart",
    ),
    OpenWrtButtonEntityDescription(
        key="reboot",
        translation_key="reboot",
        press_fn=lambda runtime_data: runtime_data.client.async_reboot(),
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        enabled_by_default=False,
        refresh_after_press=False,
        icon="mdi:power-cycle",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenWrt Control buttons."""
    runtime_data: OpenWrtControlRuntimeData = entry.runtime_data
    async_add_entities(
        OpenWrtButton(runtime_data, entry, description)
        for description in BUTTON_DESCRIPTIONS
    )


class OpenWrtButton(CoordinatorEntity, ButtonEntity):
    """Representation of an OpenWrt control action button."""

    _attr_has_entity_name = True
    entity_description: OpenWrtButtonEntityDescription

    def __init__(
        self,
        runtime_data: OpenWrtControlRuntimeData,
        entry: ConfigEntry,
        description: OpenWrtButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(runtime_data.coordinator)
        self._runtime_data = runtime_data
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_entity_registry_enabled_default = description.enabled_by_default

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the router."""
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=ROUTER_NAME,
            manufacturer="OpenWrt",
            model=_get_path(data, "system", "model"),
            sw_version=_get_path(data, "system", "version"),
            hw_version=_get_path(data, "system", "kernel"),
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Execute the button action."""
        result = await self.entity_description.press_fn(self._runtime_data)
        if not result.get("ok", False):
            stderr = str(result.get("stderr", "")).strip()
            stdout = str(result.get("stdout", "")).strip()
            message = stderr or stdout or f"Command failed with rc={result.get('rc')}"
            _LOGGER.error(
                "OpenWrt action %s failed: rc=%s stderr=%s stdout=%s",
                self.entity_description.key,
                result.get("rc"),
                stderr,
                stdout,
            )
            raise HomeAssistantError(message)

        if self.entity_description.refresh_after_press:
            await self.coordinator.async_request_refresh()
