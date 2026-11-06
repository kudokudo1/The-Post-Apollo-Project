#!/usr/bin/bash
# C2u: runs ONLY as a temporary service inside an installed, networkless
# Fedora Silverblue 44 VM. Never invoke on a user's system.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
failure() {
  echo "C2V_FAIL // $*"
  timeout --signal=TERM --kill-after=5s 15s rpm-ostree status 2>&1 | head -n 45 || true
  systemctl poweroff --no-block || true
  exit 1
}
trap 'rc=$?; if [[ "$rc" -ne 0 ]]; then echo "C2V_FAIL // SCRIPT_EXIT_$rc line $LINENO"; systemctl poweroff --no-block || true; fi' EXIT
stagefile=/var/lib/c2v-transaction-stage
pkg=postapollo-connections-c2t-fixture
data=/mnt/c2v-offline
echo "C2V_GUEST_BOOT // $(cat /etc/fedora-release) kernel=$(uname -r)"
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
    # Match the guest ISO volume label created by boot_official_silverblue.sh.
    # A mismatched C2u/C2v identifier previously blocked before rpm-ostree.
    media_label=C2VCI
    echo "C2V_OFFLINE_MEDIA_LABEL // $media_label"
    ls -l /dev/disk/by-label/ || true
    blkid || true
    mount -o ro "/dev/disk/by-label/$media_label" "$data" ||
      failure "OFFLINE_RPM_MEDIA_MISSING"
    [[ -f "$data/c2t-0.1.rpm" && -f "$data/c2t-artifact-manifest.sha256" ]] ||
      failure "OFFLINE_ARTIFACTS_MISSING"
    ( cd "$data" && sha256sum --check --status c2t-artifact-manifest.sha256 ) ||
      failure "SIGNED_TEST_ARTIFACT_CHECKSUM"
    echo "C2V_PASS // REAL_SILVERBLUE_FIRST_BOOT_BASELINE"
    echo staged > "$stagefile"
    # No guest network exists. Fedora's standard repos point to a metalink,
    # so prevent any metadata refresh by disabling them in this disposable VM.
    # Keep exact originals in /var and restore after the rebooted rollback.
    backup=/var/lib/c2v-original-yum-repos
    mkdir -p "$backup"
    shopt -s nullglob
    for file in /etc/yum.repos.d/*.repo; do
      cp -a "$file" "$backup/$(basename "$file")"
      sed -i -E 's/^[[:space:]]*enabled[[:space:]]*=[[:space:]]*[01][[:space:]]*$/enabled=0/' "$file"
    done
    echo "C2V_PASS // NO_REMOTE_RPM_REPOSITORIES_ENABLED_IN_OFFLINE_GUEST"
    # rpm-ostree must stage a new *pending* OSTree deployment without
    # fetching remote rpm-md. A local inert RPM has zero RPM dependencies.
    echo "C2V_INSTALL_STAGE_START // $(date --iso-8601=seconds)"
    echo "C2V_RPM_OSTREE_VERSION // $(rpm-ostree --version | head -n 1)"
    # This unbounded status --json pipeline was the last observed output in
    # previous CI: never allow a diagnostic to consume the entire guest budget.
    echo "C2V_STATUS_JSON_PRECHECK_BEGIN"
    statuslog=/var/tmp/c2v-preinstall-status.log
    if timeout --signal=TERM --kill-after=5s 15s \
        rpm-ostree status --json >"$statuslog" 2>&1; then
      echo "C2V_STATUS_JSON_PRECHECK_SUCCESS"
      head -c 600 "$statuslog" || true
      echo
    else
      rc="$?"
      echo "C2V_STATUS_JSON_PRECHECK_TIMEOUT_OR_ERROR // $rc"
      tail -n 18 "$statuslog" || true
      # A diagnostic must never turn a silent hang into a false success.
      # We still attempt the bounded actual local RPM operation to attribute
      # an rpm-ostreed failure separately.
    fi
    log=/var/tmp/c2v-rpm-ostree-install.log
    # Keep a useful progress message even if the process/daemon emits nothing.
    # The watchdog has a *shorter* limit than systemd or the host CI monitor.
    (
      while sleep 30; do
        echo "C2V_INSTALL_WATCHDOG // $(date --iso-8601=seconds)"
        tail -n 8 "$log" 2>/dev/null || true
        ps -eo pid,stat,etime,comm,args | grep -E '[r]pm-ostree|[r]pm-ostreed' | head -n 7 || true
        df -h /var | tail -n 1 || true
      done
    ) &
    monitor_pid="$!"
    echo "C2V_INSTALL_COMMAND_BEGIN // timeout=480s local RPM only"
    if timeout --signal=TERM --kill-after=20s 480s \
        rpm-ostree install --cache-only "$data/c2t-0.1.rpm" >"$log" 2>&1; then
      kill "$monitor_pid" 2>/dev/null || true
      wait "$monitor_pid" 2>/dev/null || true
      echo "C2V_INSTALL_RETURNED_SUCCESS"
      tail -n 50 "$log" || true
    else
      rc="$?"
      kill "$monitor_pid" 2>/dev/null || true
      wait "$monitor_pid" 2>/dev/null || true
      echo "C2V_INSTALL_FAILED_EXIT // $rc"
      tail -n 90 "$log" 2>/dev/null || true
      echo "C2V_RPM_OSTREED_JOURNAL"
      journalctl -b -u rpm-ostreed.service --no-pager -n 95 || true
      echo "C2V_RPM_OSTREE_STATUS"
      timeout 15s rpm-ostree status || true
      echo "C2V_DISK_SPACE"
      df -h /var /sysroot || true
      failure "OFFLINE_RPM_OSTREE_INSTALL_FAILED_$rc"
    fi
    echo "C2V_OSTREE_STATUS_AFTER_STAGE"
    rpm-ostree status | head -n 28
    rpm-ostree status | grep -q "$pkg" ||
      failure "NO_PENDING_LAYER_AFTER_RPM_OSTREE"
    echo "C2V_PASS // RPM_OSTREE_LAYER_STAGED_REBOOT_REQUIRED"
    echo layer_pending > "$stagefile"
    systemctl reboot --no-block
    ;;
  layer_pending)
    [[ "$(rpm -q --qf '%{VERSION}' "$pkg" 2>/dev/null || true)" == 0.1 ]] ||
      failure "LAYER_NOT_IN_BOOTED_RPMDB"
    [[ "$(cat /usr/share/post-apollo/c2t-fixture/fixture-version.txt)" == 0.1 ]] ||
      failure "LAYER_NOT_IN_BOOTED_USR"
    echo "C2V_PASS // LAYER_ACTIVE_ONLY_AFTER_REAL_REBOOT"
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
    for original in /var/lib/c2v-original-yum-repos/*.repo; do
      [[ -f "$original" ]] || continue
      cp -a "$original" "/etc/yum.repos.d/$(basename "$original")"
    done
    echo "C2V_PASS // OFFLINE_REPO_CONFIG_RESTORED_AFTER_ROLLBACK"
    echo "C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER"
    echo "C2V_PASS // NO_CONNECTIONS_SERVICE_OR_CREDENTIALS_ACTIVATED"
    echo complete > "$stagefile"
    systemctl poweroff --no-block
    ;;
  complete)
    echo "C2V_PASS // COMPLETE_ALREADY_VERIFIED"
    systemctl poweroff --no-block
    ;;
  *)
    failure "INVALID_STAGE_$stage"
    ;;
esac
