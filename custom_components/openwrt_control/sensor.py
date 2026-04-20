"""Sensor platform for OpenWrt Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTime
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
class OpenWrtSensorEntityDescription(SensorEntityDescription):
    """Describe an OpenWrt sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[OpenWrtSensorEntityDescription, ...] = (
    OpenWrtSensorEntityDescription(
        key="hostname",
        translation_key="hostname",
        value_fn=lambda data: _get_path(data, "system", "hostname"),
        icon="mdi:router-network",
    ),
    OpenWrtSensorEntityDescription(
        key="version",
        translation_key="version",
        value_fn=lambda data: _get_path(data, "system", "version"),
        icon="mdi:label-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="kernel",
        translation_key="kernel",
        value_fn=lambda data: _get_path(data, "system", "kernel"),
        icon="mdi:chip",
    ),
    OpenWrtSensorEntityDescription(
        key="model",
        translation_key="model",
        value_fn=lambda data: _get_path(data, "system", "model"),
        icon="mdi:server-network",
    ),
    OpenWrtSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        value_fn=lambda data: _get_path(data, "system", "uptime"),
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:timer-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="load_1m",
        translation_key="load_1m",
        value_fn=lambda data: (_get_path(data, "system", "load") or [None])[0],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="load_5m",
        translation_key="load_5m",
        value_fn=lambda data: (_get_path(data, "system", "load") or [None, None])[1],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="load_15m",
        translation_key="load_15m",
        value_fn=lambda data: (_get_path(data, "system", "load") or [None, None, None])[2],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="memory_available",
        translation_key="memory_available",
        value_fn=lambda data: _get_path(data, "system", "memory", "available"),
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    ),
    OpenWrtSensorEntityDescription(
        key="lan_ip",
        translation_key="lan_ip",
        value_fn=lambda data: _get_path(data, "interfaces", "lan", "ipv4"),
        icon="mdi:ip-network",
    ),
    OpenWrtSensorEntityDescription(
        key="wan_ip",
        translation_key="wan_ip",
        value_fn=lambda data: _get_path(data, "interfaces", "wan", "ipv4"),
        icon="mdi:web",
    ),
    OpenWrtSensorEntityDescription(
        key="vds_openconnect_ip",
        translation_key="vds_openconnect_ip",
        value_fn=lambda data: _get_path(data, "interfaces", "vds_frolkin", "ipv4"),
        icon="mdi:shield-link-variant",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenWrt Control sensors."""
    runtime_data: OpenWrtControlRuntimeData = entry.runtime_data
    async_add_entities(
        OpenWrtSensor(runtime_data, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class OpenWrtEntity(CoordinatorEntity, SensorEntity):
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


class OpenWrtSensor(OpenWrtEntity):
    """Representation of an OpenWrt sensor."""

    entity_description: OpenWrtSensorEntityDescription

    def __init__(
        self,
        runtime_data: OpenWrtControlRuntimeData,
        entry: ConfigEntry,
        description: OpenWrtSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(runtime_data, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data or {})
