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
from homeassistant.const import EntityCategory, UnitOfInformation, UnitOfTime
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


def _float_or_none(value: Any) -> float | None:
    """Return value as float, or None if conversion is not possible."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _memory_used_percent(data: dict[str, Any]) -> float | None:
    """Return memory utilization based on available and total memory."""
    total = _float_or_none(_get_path(data, "system", "memory", "total"))
    available = _float_or_none(_get_path(data, "system", "memory", "available"))

    if total is None or available is None or total <= 0:
        return None

    used_percent = (1 - available / total) * 100
    return round(min(max(used_percent, 0), 100), 1)


def _format_uptime(data: dict[str, Any], language: str | None) -> str | None:
    """Return uptime in a compact human-readable form."""
    uptime = _float_or_none(_get_path(data, "system", "uptime"))
    if uptime is None or uptime < 0:
        return None

    total_minutes = int(uptime) // 60
    days = total_minutes // 1440
    hours = (total_minutes % 1440) // 60
    minutes = total_minutes % 60

    if (language or "").startswith("ru"):
        if days:
            return f"{days} д {hours} ч {minutes} мин"
        if hours:
            return f"{hours} ч {minutes} мин"
        return f"{minutes} мин"

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@dataclass(frozen=True, kw_only=True)
class OpenWrtSensorEntityDescription(SensorEntityDescription):
    """Describe an OpenWrt sensor entity."""

    value_fn: Callable[[dict[str, Any], str | None], Any]
    enabled_by_default: bool = True


SENSOR_DESCRIPTIONS: tuple[OpenWrtSensorEntityDescription, ...] = (
    OpenWrtSensorEntityDescription(
        key="hostname",
        translation_key="hostname",
        value_fn=lambda data, language: _get_path(data, "system", "hostname"),
        icon="mdi:router-network",
    ),
    OpenWrtSensorEntityDescription(
        key="version",
        translation_key="version",
        value_fn=lambda data, language: _get_path(data, "system", "version"),
        icon="mdi:label-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="kernel",
        translation_key="kernel",
        value_fn=lambda data, language: _get_path(data, "system", "kernel"),
        icon="mdi:chip",
    ),
    OpenWrtSensorEntityDescription(
        key="model",
        translation_key="model",
        value_fn=lambda data, language: _get_path(data, "system", "model"),
        icon="mdi:server-network",
    ),
    OpenWrtSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        value_fn=_format_uptime,
        icon="mdi:timer-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="uptime_seconds",
        translation_key="uptime_seconds",
        value_fn=lambda data, language: _get_path(data, "system", "uptime"),
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_by_default=False,
        icon="mdi:timer-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        value_fn=lambda data, language: _get_path(
            data,
            "system",
            "cpu",
            "usage_percent",
        ),
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:cpu-64-bit",
    ),
    OpenWrtSensorEntityDescription(
        key="load_1m",
        translation_key="load_1m",
        value_fn=lambda data, language: (_get_path(data, "system", "load") or [None])[0],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_by_default=False,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="load_5m",
        translation_key="load_5m",
        value_fn=lambda data, language: (_get_path(data, "system", "load") or [None, None])[1],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_by_default=False,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="load_15m",
        translation_key="load_15m",
        value_fn=lambda data, language: (_get_path(data, "system", "load") or [None, None, None])[2],
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_by_default=False,
        icon="mdi:chart-line",
    ),
    OpenWrtSensorEntityDescription(
        key="memory_used_percent",
        translation_key="memory_used_percent",
        value_fn=lambda data, language: _memory_used_percent(data),
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:memory",
    ),
    OpenWrtSensorEntityDescription(
        key="memory_available",
        translation_key="memory_available",
        value_fn=lambda data, language: _get_path(data, "system", "memory", "available"),
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_by_default=False,
        icon="mdi:memory",
    ),
    OpenWrtSensorEntityDescription(
        key="lan_ip",
        translation_key="lan_ip",
        value_fn=lambda data, language: _get_path(data, "interfaces", "lan", "ipv4"),
        icon="mdi:ip-network",
    ),
    OpenWrtSensorEntityDescription(
        key="wan_ip",
        translation_key="wan_ip",
        value_fn=lambda data, language: _get_path(data, "interfaces", "wan", "ipv4"),
        icon="mdi:web",
    ),
    OpenWrtSensorEntityDescription(
        key="wan_rx",
        translation_key="wan_rx",
        value_fn=lambda data, language: _get_path(data, "interfaces", "wan", "rx_bytes"),
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:download-network-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="wan_tx",
        translation_key="wan_tx",
        value_fn=lambda data, language: _get_path(data, "interfaces", "wan", "tx_bytes"),
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:upload-network-outline",
    ),
    OpenWrtSensorEntityDescription(
        key="openconnect_ip",
        translation_key="openconnect_ip",
        value_fn=lambda data, language: _get_path(data, "interfaces", "openconnect", "ipv4"),
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
        self._attr_entity_registry_enabled_default = description.enabled_by_default

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        language = getattr(self.hass.config, "language", None) if self.hass else None
        return self.entity_description.value_fn(self.coordinator.data or {}, language)
