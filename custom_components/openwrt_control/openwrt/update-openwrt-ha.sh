#!/bin/sh

set -u

REPO="${OPENWRT_HA_REPO:-alex2beard/owrt-ha}"
TAG="${1:-}"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${TAG}"
RPCD_SOURCE="${BASE_URL}/custom_components/openwrt_control/openwrt/rpcd/openwrt-ha"
ACL_SOURCE="${BASE_URL}/custom_components/openwrt_control/openwrt/acl/openwrt-ha.json"
RPCD_TARGET="/usr/libexec/rpcd/openwrt.ha"
ACL_TARGET="/usr/share/rpcd/acl.d/openwrt-ha.json"
TMP_RPCD="/tmp/openwrt-ha.rpcd.$$"
TMP_ACL="/tmp/openwrt-ha.acl.$$"
BACKUP_DIR="/root/openwrt-ha-backup-$(date +%Y%m%d-%H%M%S)"

usage() {
    cat <<EOF
Usage:
  sh update-openwrt-ha.sh <tag>

Example:
  sh update-openwrt-ha.sh v0.2.3

Optional environment:
  OPENWRT_HA_REPO=owner/repo
EOF
}

fail() {
    echo "ERROR: $*" >&2
    rm -f "$TMP_RPCD" "$TMP_ACL"
    exit 1
}

info() {
    echo "=== $* ==="
}

[ -n "$TAG" ] || {
    usage
    exit 1
}

case "$TAG" in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) fail "tag must look like v0.2.3" ;;
esac

command -v wget >/dev/null 2>&1 || fail "wget not found"
command -v ubus >/dev/null 2>&1 || fail "ubus not found"

info "Download OpenWrt-side files from ${REPO} ${TAG}"
wget -O "$TMP_RPCD" "$RPCD_SOURCE" || fail "failed to download rpcd plugin"
wget -O "$TMP_ACL" "$ACL_SOURCE" || fail "failed to download ACL"

info "Downloaded files"
ls -l "$TMP_RPCD" "$TMP_ACL"

info "Validate downloaded rpcd plugin"
grep -q 'PLUGIN_VERSION=' "$TMP_RPCD" || fail "downloaded rpcd plugin does not contain PLUGIN_VERSION"
grep -q 'list_methods' "$TMP_RPCD" || fail "downloaded rpcd plugin does not look valid"
grep -q 'render_status' "$TMP_RPCD" || fail "downloaded rpcd plugin does not look valid"

DOWNLOADED_VERSION="$(grep '^PLUGIN_VERSION=' "$TMP_RPCD" | sed -n 's/^PLUGIN_VERSION="\(.*\)"/\1/p' | head -n 1)"
EXPECTED_VERSION="${TAG#v}"

[ "$DOWNLOADED_VERSION" = "$EXPECTED_VERSION" ] || fail "plugin version ${DOWNLOADED_VERSION:-unknown} does not match tag ${EXPECTED_VERSION}"

info "Validate downloaded ACL"
grep -q 'openwrt-ha' "$TMP_ACL" || fail "downloaded ACL does not look valid"
grep -q 'openwrt.ha' "$TMP_ACL" || fail "downloaded ACL does not look valid"

info "Backup current files to ${BACKUP_DIR}"
mkdir -p "$BACKUP_DIR" || fail "failed to create backup directory"
[ -f "$RPCD_TARGET" ] && cp "$RPCD_TARGET" "$BACKUP_DIR/openwrt.ha"
[ -f "$ACL_TARGET" ] && cp "$ACL_TARGET" "$BACKUP_DIR/openwrt-ha.json"
[ -f /etc/openwrt-ha.conf ] && cp /etc/openwrt-ha.conf "$BACKUP_DIR/openwrt-ha.conf"
ls -l "$BACKUP_DIR"

info "Install files"
cp "$TMP_RPCD" "$RPCD_TARGET" || fail "failed to install rpcd plugin"
chmod 0755 "$RPCD_TARGET" || fail "failed to chmod rpcd plugin"
cp "$TMP_ACL" "$ACL_TARGET" || fail "failed to install ACL"
chmod 0644 "$ACL_TARGET" || fail "failed to chmod ACL"

rm -f "$TMP_RPCD" "$TMP_ACL"

info "Restart rpcd"
/etc/init.d/rpcd restart || fail "failed to restart rpcd"
sleep 2

info "Installed ubus methods"
ubus -v list openwrt.ha || fail "openwrt.ha ubus object not found"

info "Installed status summary"
ubus call openwrt.ha status | grep -E '"plugin"|"version"|"wan"|"rx_mbps"|"tx_mbps"|"openconnect"' -A12 || ubus call openwrt.ha status

info "Done"
