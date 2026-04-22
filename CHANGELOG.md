# Changelog

## 0.2.3 - 2026-04-22

### Added

- Added OpenWrt-side updater script: `custom_components/openwrt_control/openwrt/update-openwrt-ha.sh`.
- The updater accepts a release tag, downloads OpenWrt-side files from GitHub, validates them, backs up the current files, installs the new files, restarts `rpcd`, and prints a status summary.

## 0.2.2 - 2026-04-22

### Added

- Added OpenWrt-side rpcd plugin version to the status payload as `plugin.version`.
- Added disabled-by-default diagnostic sensor for the rpcd plugin version.

### Changed

- README now explicitly reminds users to update OpenWrt-side rpcd files after releases that modify `custom_components/openwrt_control/openwrt/`.

## 0.2.1 - 2026-04-22

### Added

- Added visible WAN RX/TX rate sensors in Mbit/s.
- Added `interfaces.wan.rx_mbps` and `interfaces.wan.tx_mbps` to the rpcd status payload.

### Changed

- WAN RX/TX byte counters are now diagnostic and disabled by default.
- Russian UI now uses `Скорость WAN RX` and `Скорость WAN TX` for visible WAN rate sensors.

## 0.2.0 - 2026-04-22

### Added

- CPU usage percent in the rpcd status payload: `system.cpu.usage_percent`.
- `sensor.openwrt_cpu_usage`.
- Memory used percent sensor.
- WAN RX/TX byte counters in the rpcd status payload.
- `sensor.openwrt_wan_rx` and `sensor.openwrt_wan_tx`.
- Human-readable uptime sensor.
- Disabled-by-default diagnostic raw uptime sensor.

### Changed

- Load average sensors are diagnostic and disabled by default.
- Raw available memory sensor is diagnostic and disabled by default.
- README installation now uses `cp` and `chmod` for minimal OpenWrt images.
- README and translations clarify that `openconnect_interface` is the logical OpenWrt network interface name.

### Removed

- Deprecated `restart_vds_openconnect` rpcd method alias.
- Deprecated `restart_vds_openconnect` from the rpcd ACL.

## 0.1.0 - 2026-04-21

### Added

- Initial Home Assistant custom integration.
- OpenWrt ubus/rpcd client.
- Aggregated `openwrt.ha status` rpcd method.
- WAN, LAN, OpenConnect, service, system, load, memory, and version sensors.
- Buttons for predefined OpenWrt service actions.
- Manual OpenWrt-side rpcd plugin and ACL installation flow.
