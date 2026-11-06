#!/usr/bin/bash
# C2u: runs ONLY as a temporary service inside an installed, networkless
# Fedora Silverblue 44 VM. Never invoke on a user's system.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
failure() {
  echo "C2U_FAIL // $*"
  rpm-ostree status 2>&1 | head -n 45 || true
  systemctl poweroff --no-block || true
  exit 1
}
trap 'rc=$?; if [[ "$rc" -ne 0 ]]; then echo "C2U_FAIL // SCRIPT_EXIT_$rc line $LINENO"; systemctl poweroff --no-block || true; fi' EXIT
stagefile=/var/lib/c2u-transaction-stage
pkg=postapollo-connections-c2t-fixture
data=/mnt/c2u-offline
echo "C2U_GUEST_BOOT // $(cat /etc/fedora-release) kernel=$(uname -r)"
[[ -e /run/ostree-booted ]] || failure "NOT_BOOTED_OSTREE"
[[ "$(getenforce)" == Enforcing ]] || failure "SELINUX_NOT_ENFORCING"
command -v rpm-ostree || failure "NO_RPM_OSTREE"
command -v ostree || failure "NO_OSTREE"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] \
  || failure "GUEST_NETWORK_INTERFACE_PRESENT"
ostree admin status | head -n 18
rpm-ostree status | head -n 24

# Real, booted Silverblue OS identity; Fedora Cloud or a container cannot pass.
ostree admin status | grep -iq 'silverblue' || failure "NOT_SILVERBLUE_REF"
grep -Fq 'Fedora release 44' /etc/fedora-release || failure "WRONG_FEDORA_RELEASE"

stage="$(cat "$stagefile" 2>/dev/null || echo initial)"
case "$stage" in
  initial)
    [[ ! -e /usr/share/post-apollo/c2t-fixture ]] ||
      failure "PACKAGE_ALREADY_PRESENT_AT_BASELINE"
    rpm -q "$pkg" >/dev/null 2>&1 && failure "RPM_ALREADY_INSTALLED"
    mkdir -p "$data"
    mount -o ro /dev/disk/by-label/C2UCI "$data" ||
      failure "OFFLINE_RPM_MEDIA_MISSING"
    [[ -f "$data/c2t-0.1.rpm" && -f "$data/c2t-artifact-manifest.sha256" ]] ||
      failure "OFFLINE_ARTIFACTS_MISSING"
    ( cd "$data" && sha256sum --check --status c2t-artifact-manifest.sha256 ) ||
      failure "SIGNED_TEST_ARTIFACT_CHECKSUM"
    echo "C2U_PASS // REAL_SILVERBLUE_FIRST_BOOT_BASELINE"
    echo staged > "$stagefile"
    # No guest network exists. Fedora's standard repos point to a metalink,
    # so prevent any metadata refresh by disabling them in this disposable VM.
    # Keep exact originals in /var and restore after the rebooted rollback.
    backup=/var/lib/c2u-original-yum-repos
    mkdir -p "$backup"
    shopt -s nullglob
    for file in /etc/yum.repos.d/*.repo; do
      cp -a "$file" "$backup/$(basename "$file")"
      sed -i -E 's/^[[:space:]]*enabled[[:space:]]*=[[:space:]]*[01][[:space:]]*$/enabled=0/' "$file"
    done
    echo "C2U_PASS // NO_REMOTE_RPM_REPOSITORIES_ENABLED_IN_OFFLINE_GUEST"
    # rpm-ostree must stage a new *pending* OSTree deployment without
    # fetching remote rpm-md. A local inert RPM has zero RPM dependencies.
    rpm-ostree install --cache-only "$data/c2t-0.1.rpm" ||
      failure "OFFLINE_RPM_OSTREE_INSTALL_FAILED"
    echo "C2U_OSTREE_STATUS_AFTER_STAGE"
    rpm-ostree status | head -n 28
    rpm-ostree status | grep -q "$pkg" ||
      failure "NO_PENDING_LAYER_AFTER_RPM_OSTREE"
    echo "C2U_PASS // RPM_OSTREE_LAYER_STAGED_REBOOT_REQUIRED"
    echo layer_pending > "$stagefile"
    systemctl reboot --no-block
    ;;
  layer_pending)
    [[ "$(rpm -q --qf '%{VERSION}' "$pkg" 2>/dev/null || true)" == 0.1 ]] ||
      failure "LAYER_NOT_IN_BOOTED_RPMDB"
    [[ "$(cat /usr/share/post-apollo/c2t-fixture/fixture-version.txt)" == 0.1 ]] ||
      failure "LAYER_NOT_IN_BOOTED_USR"
    echo "C2U_PASS // LAYER_ACTIVE_ONLY_AFTER_REAL_REBOOT"
    echo rollback_pending > "$stagefile"
    rpm-ostree rollback --reboot || failure "RPM_OSTREE_ROLLBACK_FAILED"
    ;;
  rollback_pending)
    if rpm -q "$pkg" >/dev/null 2>&1; then
      failure "ROLLED_BACK_RPM_STILL_IN_BOOTED_DATABASE"
    fi
    [[ ! -e /usr/share/post-apollo/c2t-fixture ]] ||
      failure "ROLLED_BACK_USR_STILL_HAS_LAYER"
    [[ "$(getenforce)" == Enforcing ]] || failure "SELINUX_WEAKENED"
    [[ ! -e /usr/libexec/post-apollo/connections-status-host ]] ||
      failure "HOST_EXE_INSTALLED_BY_INERT_PACKAGE"
    [[ ! -e /usr/lib/systemd/system/postapollo-connections-status.service ]] ||
      failure "PRODUCTION_SERVICE_INSTALLED_BY_INERT_PACKAGE"
    # Restore repo config only in this disposable guest before discarding it.
    for original in /var/lib/c2u-original-yum-repos/*.repo; do
      [[ -f "$original" ]] || continue
      cp -a "$original" "/etc/yum.repos.d/$(basename "$original")"
    done
    echo "C2U_PASS // OFFLINE_REPO_CONFIG_RESTORED_AFTER_ROLLBACK"
    echo "C2U_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER"
    echo "C2U_PASS // NO_CONNECTIONS_SERVICE_OR_CREDENTIALS_ACTIVATED"
    echo complete > "$stagefile"
    systemctl poweroff --no-block
    ;;
  complete)
    echo "C2U_PASS // COMPLETE_ALREADY_VERIFIED"
    systemctl poweroff --no-block
    ;;
  *)
    failure "INVALID_STAGE_$stage"
    ;;
esac
