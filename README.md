# OpenWrt Control for Home Assistant

`openwrt_control` — custom integration для Home Assistant, которая работает с OpenWrt через `ubus/rpcd`, а не через HTML LuCI.

Интеграция рассчитана на OpenWrt x86/router и даёт безопасный базовый мониторинг плюс несколько заранее заданных действий управления.

## Что умеет

- показывает доступность OpenWrt;
- показывает состояние `wan` и `vds_frolkin`;
- показывает `WAN IP`, `LAN IP`, `OpenConnect IP`;
- показывает состояние `passwall2`, `xray`, `dnsmasq`;
- показывает `uptime`, `load`, память, `hostname`, `version`, `kernel`, `model`;
- умеет restart `passwall2`, restart `dnsmasq`, reload `firewall`, restart `vds_frolkin`, reboot.

## Что не делает

- не реализует `device_tracker`;
- не отслеживает Wi-Fi-клиентов;
- не даёт универсальный `exec`;
- не редактирует firewall rules, `passwall2` config или network config.

`device_tracker` и Wi-Fi client tracking не реализованы намеренно. Интеграция ориентирована на OpenWrt x86/router без Wi-Fi.

## Установка через HACS

Это основной способ установки из GitHub.

1. Убедитесь, что репозиторий public.
2. В Home Assistant откройте `HACS -> 3 dots -> Custom repositories`.
3. Добавьте URL:

```text
https://github.com/alex2beard/owrt-ha
```

4. Выберите тип `Integration`.
5. Установите `OpenWrt Control`.
6. Перезапустите Home Assistant.

После установки компонент будет находиться в:

```text
config/custom_components/openwrt_control/
```

Важно:

- GitHub workflow для HACS не обязателен для установки как `Custom repository`;
- private GitHub repositories HACS не поддерживает.

OpenWrt-side файлы после установки будут лежать здесь:

- `config/custom_components/openwrt_control/openwrt/rpcd/openwrt-ha`
- `config/custom_components/openwrt_control/openwrt/acl/openwrt-ha.json`

## Установка OpenWrt-side plugin

Скопируйте файлы на роутер:

```sh
scp custom_components/openwrt_control/openwrt/rpcd/openwrt-ha <router-admin>@<router-host>:/tmp/openwrt-ha
scp custom_components/openwrt_control/openwrt/acl/openwrt-ha.json <router-admin>@<router-host>:/tmp/openwrt-ha.json
```

Установите rpcd plugin и ACL:

```sh
ssh <router-admin>@<router-host>
install -m 0755 /tmp/openwrt-ha /usr/libexec/rpcd/openwrt.ha
install -m 0644 /tmp/openwrt-ha.json /usr/share/rpcd/acl.d/openwrt-ha.json
/etc/init.d/rpcd restart
ubus -v list openwrt.ha
ubus call openwrt.ha status
```

Важно: файл в репозитории называется `openwrt-ha`, но устанавливать его нужно как `/usr/libexec/rpcd/openwrt.ha`, чтобы ubus object назывался `openwrt.ha`.

## Пользователь для `/ubus`

Пример настройки отдельного пользователя для Home Assistant:

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

Проверка логина:

```sh
curl -s http://<router-host>/ubus \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"call","params":["00000000000000000000000000000000","session","login",{"username":"<ha-user>","password":"<ha-password>"}]}'
```

Если в ответе есть `ubus_rpc_session`, значит авторизация настроена корректно.

## Настройка в Home Assistant

После установки:

1. Откройте `Settings -> Devices & Services -> Add Integration`.
2. Найдите `OpenWrt Control`.
3. Заполните параметры подключения.

Поля подключения:

- `host`
- `port`
- `use_https`
- `verify_ssl`
- `username`
- `password`
- `scan_interval`

По умолчанию в коде оставлен только `scan_interval = 30`. Адрес роутера, порт и TLS-параметры нужно указать вручную.

Интеграция использует `session.login`, переиспользует ubus session и при истечении сессии логинится заново.

## Сущности

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

Кнопка `reboot` остаётся отдельной сущностью, но по умолчанию отключена в entity registry. Это сделано намеренно, потому что действие опасное и может оборвать доступ к роутеру. Использовать её лучше через script с подтверждением.

## Troubleshooting

Если интеграция не подключается:

- проверьте доступность `http://<host>/ubus` или `https://<host>/ubus`;
- проверьте, что `rpcd` перезапущен;
- проверьте `ubus -v list openwrt.ha`;
- проверьте логин выделенного пользователя через `session.login`;
- проверьте ACL для `openwrt.ha`, `system`, `network.interface.*`.

Если не видны статусы сервисов или VPN:

- проверьте, что интерфейс называется `vds_frolkin`;
- проверьте, что `passwall2` и `dnsmasq` возвращают `running` через init.d;
- проверьте, что `xray` запущен из `/tmp/etc/passwall2/bin/xray`;
- проверьте вывод `ubus call network.interface.vds_frolkin status`.

Если команды из кнопок завершаются ошибкой:

- смотрите логи Home Assistant;
- проверьте выполнение команд вручную на роутере;
- проверьте, что ACL установлен из `openwrt-ha.json`.

## Проверка репозитория

В репозитории оставлен `.github/workflows/hassfest.yml`, который проверяет структуру integration-репозитория и метаданные Home Assistant.
