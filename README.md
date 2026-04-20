# OpenWrt Control for Home Assistant

## 1. Назначение интеграции

`openwrt_control` — это custom integration для Home Assistant, которая работает с OpenWrt через `ubus/rpcd`, а не через парсинг HTML LuCI. Интеграция предназначена для мониторинга состояния роутера и для ограниченного набора безопасных действий управления.

Она ориентирована на OpenWrt x86/router without Wi-Fi client tracking и особенно хорошо подходит для сценариев, где роутер используется как сетевой шлюз, VPN endpoint и точка запуска сервисов вроде PassWall2.

## 2. Что умеет интеграция

Интеграция умеет:

- проверять доступность OpenWrt;
- показывать состояние `wan` и `vds_frolkin`;
- показывать `WAN IP`, `LAN IP`, `OpenConnect IP`;
- показывать состояние `passwall2`, `xray`, `dnsmasq`;
- отображать `uptime`, `load average`, доступную память;
- отображать `hostname`, `OpenWrt version`, `kernel`, `model`;
- выполнять предопределенные действия: restart `passwall2`, restart `dnsmasq`, reload `firewall`, restart `vds_frolkin`, reboot роутера.

## 3. Что она не делает

Интеграция намеренно не делает следующее:

- не реализует `device_tracker`;
- не отслеживает Wi-Fi-клиентов;
- не парсит HTML LuCI;
- не предоставляет универсальный `exec`;
- не редактирует firewall rules;
- не редактирует конфигурацию `passwall2`;
- не редактирует network config.

Отдельно: `device_tracker` не реализован намеренно. Wi-Fi-клиенты не отслеживаются. Интеграция ориентирована на OpenWrt x86/router без Wi-Fi.

## 4. Установка OpenWrt-side rpcd plugin

В репозитории есть две OpenWrt-side части:

- [`openwrt/rpcd/openwrt-ha`](openwrt/rpcd/openwrt-ha)
- [`openwrt/acl/openwrt-ha.json`](openwrt/acl/openwrt-ha.json)

Скопируйте их на роутер:

```sh
scp openwrt/rpcd/openwrt-ha root@10.0.1.2:/tmp/openwrt-ha
scp openwrt/acl/openwrt-ha.json root@10.0.1.2:/tmp/openwrt-ha.json
```

Установите rpcd plugin и ACL:

```sh
ssh root@10.0.1.2
install -m 0755 /tmp/openwrt-ha /usr/libexec/rpcd/openwrt.ha
install -m 0644 /tmp/openwrt-ha.json /usr/share/rpcd/acl.d/openwrt-ha.json
/etc/init.d/rpcd restart
ubus -v list openwrt.ha
```

Важно: файл в репозитории называется `openwrt-ha`, но установить его нужно как `/usr/libexec/rpcd/openwrt.ha`, чтобы ubus object назывался именно `openwrt.ha`.

Проверка статуса:

```sh
ubus call openwrt.ha status
```

## 5. Создание пользователя `hass` и выдача ACL

По документации OpenWrt ACL для HTTP ubus задаются в `/usr/share/rpcd/acl.d/*.json`, а привязка логина к ACL-ролям делается через `/etc/config/rpcd`.

Пример настройки пользователя `hass`:

```sh
adduser -D -H hass
passwd hass

uci add rpcd login
uci set rpcd.@login[-1].username='hass'
uci set rpcd.@login[-1].password='$p$hass'
uci add_list rpcd.@login[-1].read='openwrt-ha'
uci add_list rpcd.@login[-1].write='openwrt-ha'
uci commit rpcd

/etc/init.d/rpcd restart
/etc/init.d/uhttpd restart
```

Здесь:

- `$p$hass` говорит `rpcd` брать пароль пользователя `hass` из `/etc/shadow`;
- `read/write openwrt-ha` привязывают пользователя к ACL-роли из файла `openwrt-ha.json`.

Проверка логина через `/ubus`:

```sh
curl -s http://10.0.1.2/ubus \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"call","params":["00000000000000000000000000000000","session","login",{"username":"hass","password":"YOUR_PASSWORD"}]}'
```

Если в ответе есть `ubus_rpc_session`, значит авторизация и ACL-связка настроены корректно.

## 6. Установка HA custom component

Скопируйте каталог [`custom_components/openwrt_control`](custom_components/openwrt_control) в директорию `config/custom_components/` Home Assistant.

Итоговый путь должен быть таким:

```text
config/custom_components/openwrt_control/
```

После копирования перезапустите Home Assistant.

## 7. Настройка через UI

В Home Assistant:

1. Откройте `Settings -> Devices & Services -> Add Integration`.
2. Найдите `OpenWrt Control`.
3. Укажите параметры:
   `host`, `port`, `use_https`, `verify_ssl`, `username`, `password`, `scan_interval`.

Значения по умолчанию:

- `host`: `10.0.1.2`
- `port`: `80`
- `use_https`: `false`
- `verify_ssl`: `false`
- `scan_interval`: `30`

После успешной настройки интеграция логинится через `session.login`, переиспользует ubus session и при ошибке авторизации пытается перелогиниться.

## 8. Пример entities

Создаются следующие сущности.

Binary sensors:

- `binary_sensor.openwrt_online`
- `binary_sensor.openwrt_wan_up`
- `binary_sensor.openwrt_vds_openconnect_up`
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
- `sensor.openwrt_vds_openconnect_ip`

Buttons:

- `button.openwrt_restart_passwall2`
- `button.openwrt_restart_dnsmasq`
- `button.openwrt_reload_firewall`
- `button.openwrt_restart_vds_openconnect`
- `button.openwrt_reboot`

Кнопку `reboot` лучше использовать не напрямую из UI, а через Home Assistant script с подтверждением.

Пример script:

```yaml
script:
  reboot_openwrt_confirmed:
    alias: Reboot OpenWrt (confirmed)
    sequence:
      - action: button.press
        target:
          entity_id: button.openwrt_reboot
```

## 9. Troubleshooting

Если интеграция не подключается:

- проверьте, что `/ubus` доступен по `http://<host>/ubus` или `https://<host>/ubus`;
- проверьте, что `rpcd` перезапущен после установки plugin и ACL;
- проверьте, что `ubus -v list openwrt.ha` показывает нужные методы;
- проверьте, что пользователь `hass` может выполнить `session.login`;
- проверьте ACL для `openwrt.ha`, `system`, `network.interface.*`.

Если не видно VPN/IP/service states:

- проверьте, что интерфейс называется именно `vds_frolkin`;
- проверьте, что процесс действительно определяется через `pgrep -f passwall2`, `pgrep -f xray`, `pgrep -f dnsmasq`;
- проверьте вывод `ubus call network.interface.vds_frolkin status`.

Если кнопки завершаются ошибкой:

- смотрите логи Home Assistant;
- проверьте, что соответствующие команды на роутере выполняются вручную;
- проверьте, что ACL установлен именно из `openwrt-ha.json`.
