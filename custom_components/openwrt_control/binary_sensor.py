"""Binary sensor platform for OpenWrt Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OpenWrtControlRuntimeData
from .const import DOMAIN, ROUTER_NAME


def _get_path(data: dict[str, Any], *path: str) -> Any:
    """Safely retrieve a nested value from the coordinator payload."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


@dataclass(frozen=True, kw_only=True)
class OpenWrtBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an OpenWrt binary sensor."""

    value_fn: Callable[[dict[str, Any], bool], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[OpenWrtBinarySensorEntityDescription, ...] = (
    OpenWrtBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        value_fn=lambda _data, is_online: is_online,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:router-network",
    ),
    OpenWrtBinarySensorEntityDescription(
        key="wan_up",
        translation_key="wan_up",
        value_fn=lambda data, _is_online: bool(_get_path(data, "interfaces", "wan", "up")),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:web-check",
    ),
    OpenWrtBinarySensorEntityDescription(
        key="openconnect_up",
        translation_key="openconnect_up",
        value_fn=lambda data, _is_online: bool(
            _get_path(data, "interfaces", "openconnect", "up")
        ),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:shield-link-variant",
    ),
    OpenWrtBinarySensorEntityDescription(
        key="passwall2_running",
        translation_key="passwall2_running",
        value_fn=lambda data, _is_online: bool(
            _get_path(data, "services", "passwall2", "running")
        ),
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:rocket-launch-outline",
    ),
    OpenWrtBinarySensorEntityDescription(
        key="xray_running",
        translation_key="xray_running",
        value_fn=lambda data, _is_online: bool(_get_path(data, "services", "xray", "running")),
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:access-point-network",
    ),
    OpenWrtBinarySensorEntityDescription(
        key="dnsmasq_running",
        translation_key="dnsmasq_running",
        value_fn=lambda data, _is_online: bool(
            _get_path(data, "services", "dnsmasq", "running")
        ),
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:dns",
    ),
)


class OpenWrtEntity(CoordinatorEntity, BinarySensorEntity):
    """Base entity for OpenWrt Control."""

    _attr_has_entity_name = True

    def __init__(
        self,
        runtime_data: OpenWrtControlRuntimeData,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(runtime_data.coordinator)
        self._entry = entry

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


class OpenWrtOnlineBinarySensor(OpenWrtEntity):
    """Binary sensor that reflects overall router availability."""

    entity_description: OpenWrtBinarySensorEntityDescription

    def __init__(
        self,
        runtime_data: OpenWrtControlRuntimeData,
        entry: ConfigEntry,
        description: OpenWrtBinarySensorEntityDescription,
    ) -> None:
        """Initialize the online binary sensor."""
        super().__init__(runtime_data, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_available = True

    @property
    def available(self) -> bool:
        """Keep the online sensor available so it can go false on failures."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether the coordinator is currently online."""
        return self.coordinator.last_update_success


class OpenWrtBinarySensor(OpenWrtEntity):
    """Representation of a regular OpenWrt binary sensor."""

    entity_description: OpenWrtBinarySensorEntityDescription

    def __init__(
        self,
        runtime_data: OpenWrtControlRuntimeData,
        entry: ConfigEntry,
        description: OpenWrtBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(runtime_data, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the binary sensor state."""
        return self.entity_description.value_fn(
            self.coordinator.data or {},
            self.coordinator.last_update_success,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenWrt Control binary sensors."""
    runtime_data: OpenWrtControlRuntimeData = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    for description in BINARY_SENSOR_DESCRIPTIONS:
        if description.key == "online":
            entities.append(OpenWrtOnlineBinarySensor(runtime_data, entry, description))
        else:
            entities.append(OpenWrtBinarySensor(runtime_data, entry, description))

    async_add_entities(entities)
