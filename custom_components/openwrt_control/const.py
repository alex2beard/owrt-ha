"""Constants for the OpenWrt Control integration."""

from homeassistant.const import Platform

DOMAIN = "openwrt_control"

DEFAULT_HOST = ""
DEFAULT_PORT = 443
DEFAULT_USE_HTTPS = True
DEFAULT_VERIFY_SSL = True
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_SESSION_TIMEOUT = 300
DEFAULT_OPENCONNECT_INTERFACE = "vpn"

CONF_OPENCONNECT_INTERFACE = "openconnect_interface"
CONF_USE_HTTPS = "use_https"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.BUTTON,
]

LOGGER_NAME = "custom_components.openwrt_control"
ROUTER_NAME = "OpenWrt"
