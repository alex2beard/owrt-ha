"""Constants for the OpenWrt Control integration."""

from homeassistant.const import Platform

DOMAIN = "openwrt_control"

DEFAULT_HOST = "10.0.1.2"
DEFAULT_PORT = 80
DEFAULT_USE_HTTPS = False
DEFAULT_VERIFY_SSL = False
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_SESSION_TIMEOUT = 300

CONF_USE_HTTPS = "use_https"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.BUTTON,
]

LOGGER_NAME = "custom_components.openwrt_control"
ROUTER_NAME = "OpenWrt"
