# OpenWrt Control for Home Assistant

`openwrt_control` is a Home Assistant custom integration for monitoring an OpenWrt router and running a small set of predefined control actions through `ubus/rpcd`.

It does not parse LuCI HTML, does not implement `device_tracker`, and does not track Wi-Fi clients. The project is intentionally aimed at router-style OpenWrt setups where monitoring and a few safe control actions are enough.

## What it does

- Monitors router availability.
- Exposes WAN state and WAN IP.
- Exposes OpenConnect state and OpenConnect IP.
- Exposes `passwall2`, `xray`, and `dnsmasq` running state.
- Exposes hostname, version, kernel, model, uptime, load, and available memory.
- Provides buttons to restart `passwall2`, restart `dnsmasq`, reload `firewall`, restart OpenConnect, and reboot OpenWrt.

## What it does not do

- No `device_tracker`.
- No Wi-Fi client tracking.
- No universal `exec`.
- No firewall rule editing.
- No `passwall2` config editing.
- No network config editing.
- No automatic OpenWrt-side provisioning from Home Assistant.

OpenWrt-side installation stays manual on purpose. Home Assistant does not create users, upload files, edit ACLs, or modify `/etc/openwrt-ha.conf`.

## Install with HACS

1. Make the GitHub repository public.
2. In Home Assistant open `HACS -> Custom repositories`.
3. Add the repository URL and choose type `Integration`.
4. Install `OpenWrt Control`.
5. Restart Home Assistant.

The custom component will be installed to:

```text
config/custom_components/openwrt_control/
```

## Install the OpenWrt rpcd plugin

Copy the OpenWrt-side files from the repository to the router:

```sh
scp custom_components/openwrt_control/openwrt/rpcd/openwrt-ha <router-admin>@<router-host>:/tmp/openwrt-ha
scp custom_components/openwrt_control/openwrt/acl/openwrt-ha.json <router-admin>@<router-host>:/tmp/openwrt-ha.json
```

Install them on OpenWrt:

```sh
ssh <router-admin>@<router-host>
install -m 0755 /tmp/openwrt-ha /usr/libexec/rpcd/openwrt.ha
install -m 0644 /tmp/openwrt-ha.json /usr/share/rpcd/acl.d/openwrt-ha.json
```

Important:

- The repository file is named `openwrt-ha`.
- It must be installed as `/usr/libexec/rpcd/openwrt.ha` so the ubus object name becomes `openwrt.ha`.

## Configure the OpenConnect interface on OpenWrt

Create `/etc/openwrt-ha.conf` manually:

```sh
cat >/etc/openwrt-ha.conf <<'EOF'
OPENCONNECT_INTERFACE="vpn"
EOF
```

If your OpenWrt logical OpenConnect interface is named differently, set that name instead:

```sh
OPENCONNECT_INTERFACE="myvpn"
```

Then restart `rpcd`:

```sh
/etc/init.d/rpcd restart
```

## Create a dedicated `/ubus` user

Example manual setup for a Home Assistant user:

```sh
adduser -D -H <ha-user>
passwd <ha-user>

uci add rpcd login
uci set rpcd.@login[-1].username='<ha-user>'
uci set rpcd.@login[-1].password='$p$<ha-user>'
uci add_list rpcd.@login[-1].read='openwrt-ha'
uci add_list rpcd.@login[-1].write='openwrt-ha'
uci commit rpcd

/etc/init.d/rpcd restart
/etc/init.d/uhttpd restart
```

Check login manually:

```sh
curl -s https://<router-host>/ubus \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"call","params":["00000000000000000000000000000000","session","login",{"username":"<ha-user>","password":"<ha-password>"}]}'
```

If the response includes `ubus_rpc_session`, authentication works.

## Set up in Home Assistant

Add the integration through `Settings -> Devices & Services -> Add Integration`.

Configuration fields:

- `host`
- `port`
- `use_https`
- `verify_ssl`
- `username`
- `password`
- `scan_interval`
- `openconnect_interface`

Safe neutral defaults used by the config flow:

- `host`: empty
- `port`: `443`
- `use_https`: `true`
- `verify_ssl`: `true`
- `username`: empty
- `password`: empty
- `scan_interval`: `30`
- `openconnect_interface`: `vpn`

`openconnect_interface` is the logical OpenWrt interface name, for example `vpn` or `myvpn`.

The same value should also be set on the router in `/etc/openwrt-ha.conf`.

## Entities

Binary sensors:

- `binary_sensor.openwrt_online`
- `binary_sensor.openwrt_wan_up`
- `binary_sensor.openwrt_openconnect_up`
- `binary_sensor.openwrt_passwall2_running`
- `binary_sensor.openwrt_xray_running`
- `binary_sensor.openwrt_dnsmasq_running`

Sensors:

- `sensor.openwrt_hostname`
- `sensor.openwrt_version`
- `sensor.openwrt_kernel`
- `sensor.openwrt_model`
- `sensor.openwrt_uptime`
- `sensor.openwrt_load_1m`
- `sensor.openwrt_load_5m`
- `sensor.openwrt_load_15m`
- `sensor.openwrt_memory_available`
- `sensor.openwrt_lan_ip`
- `sensor.openwrt_wan_ip`
- `sensor.openwrt_openconnect_ip`

Buttons:

- `button.openwrt_restart_passwall2`
- `button.openwrt_restart_dnsmasq`
- `button.openwrt_reload_firewall`
- `button.openwrt_restart_openconnect`
- `button.openwrt_reboot`

The reboot button remains a separate entity and is disabled by default in the entity registry because it is inherently risky. It is safer to call it through a Home Assistant script with confirmation.

## Expected ubus methods

After installing the rpcd file:

```sh
ubus -v list openwrt.ha
```

You should see:

- `status`
- `restart_passwall2`
- `restart_dnsmasq`
- `reload_firewall`
- `restart_openconnect`
- `reboot`

The deprecated alias `restart_vds_openconnect` may also appear for backward compatibility, but new setups should use `restart_openconnect`.

## Expected status payload

Run:

```sh
ubus call openwrt.ha status
```

The response should include:

- `system.load` as an array of 3 numbers
- `interfaces.lan.up`
- `interfaces.wan.up`
- `interfaces.openconnect.name`
- `interfaces.openconnect.up`
- `services.passwall2.running`
- `services.xray.running`
- `services.dnsmasq.running`

Example shape:

```json
{
  "interfaces": {
    "openconnect": {
      "name": "vpn",
      "up": true,
      "device": "vpn-vpn",
      "ipv4": "<openconnect-ip>"
    }
  }
}
```

## Troubleshooting

If Home Assistant cannot connect:

- Check `https://<router-host>/ubus` or `http://<router-host>/ubus`.
- Check that `rpcd` was restarted.
- Check `ubus -v list openwrt.ha`.
- Check login through `session.login`.
- Check that the `openwrt-ha` ACL is installed.

If OpenConnect state is empty:

- Check `/etc/openwrt-ha.conf`.
- Check that `OPENCONNECT_INTERFACE` matches the real logical OpenWrt interface name.
- Check `ubus call network.interface.<openconnect-interface> status`.

If service states are wrong:

- Check that `dnsmasq` returns `running` through `/etc/init.d/dnsmasq status`.
- Check that `xray` runs from `/tmp/etc/passwall2/bin/xray`.
- Check that `passwall2` processes are visible under `/usr/share/passwall2` or `/tmp/etc/passwall2`.

If a button fails:

- Check Home Assistant logs.
- Run the same command manually on the router.
- Check that `<ha-user>` has the `openwrt-ha` ACL.
