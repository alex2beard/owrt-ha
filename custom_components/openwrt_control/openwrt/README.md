# OpenWrt-side files

This directory contains files that must be installed on the OpenWrt router manually.

## Files

- `rpcd/openwrt-ha` -> `/usr/libexec/rpcd/openwrt.ha`
- `acl/openwrt-ha.json` -> `/usr/share/rpcd/acl.d/openwrt-ha.json`
- `update-openwrt-ha.sh` -> helper updater script for OpenWrt

## One-command updater

Run on OpenWrt and pass the release tag:

```sh
wget -O /tmp/update-openwrt-ha.sh https://raw.githubusercontent.com/alex2beard/owrt-ha/v0.2.3/custom_components/openwrt_control/openwrt/update-openwrt-ha.sh
sh /tmp/update-openwrt-ha.sh v0.2.3
```

The updater:

- downloads the rpcd plugin and ACL from the requested GitHub tag;
- validates the downloaded files;
- checks that `PLUGIN_VERSION` matches the requested tag;
- backs up the current files to `/root/openwrt-ha-backup-YYYYMMDD-HHMMSS`;
- installs files to the proper OpenWrt paths;
- restarts `rpcd`;
- prints `ubus -v list openwrt.ha` and a status summary.

## Manual install

```sh
cp /tmp/openwrt-ha /usr/libexec/rpcd/openwrt.ha
chmod 0755 /usr/libexec/rpcd/openwrt.ha

cp /tmp/openwrt-ha.json /usr/share/rpcd/acl.d/openwrt-ha.json
chmod 0644 /usr/share/rpcd/acl.d/openwrt-ha.json

/etc/init.d/rpcd restart
```

## Check installed version

```sh
ubus call openwrt.ha status | grep -E '"plugin"|"version"' -A4
```

Expected example:

```json
"plugin": {
  "version": "0.2.3"
}
```
