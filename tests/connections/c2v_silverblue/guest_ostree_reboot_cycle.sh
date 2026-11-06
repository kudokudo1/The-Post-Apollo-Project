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
    # Separate periodic diagnostic independent of the calling shell.
    # If this ticker goes silent, the guest may itself be stalled.
    echo "C2V_GUEST_PROBE_LAUNCHING"
    cat > /run/c2v-guest-probe.sh <<'PROBE'
#!/usr/bin/bash
set -u
echo "C2V_GUEST_PROBE_READY // $(date --iso-8601=seconds)" >/dev/ttyS0
for n in $(seq 1 36); do
  sleep 20
  {
    echo "C2V_GUEST_PROBE_TICK // $n $(date --iso-8601=seconds)"
    free -m | head -n 3
    df -h /var | tail -n 1
    ps -eo pid,stat,%cpu,rss,etime,comm | grep -E '[r]pm-ostree|[r]pm-ostreed|PID' | head -n 9 || true
    # Distinguish service cgroup freeze from CPU/RAM pressure.
    for unit in c2v-ostree-cycle.service c2v-rpm-layer-worker.service; do
      cg="$(systemctl show "$unit" --property=ControlGroup --value 2>/dev/null || true)"
      case "$cg" in
        /system.slice/*)
          echo "C2V_PROBE_UNIT_CGROUP // $unit $cg"
          for field in cgroup.freeze cgroup.events; do
            if [[ -r "/sys/fs/cgroup$cg/$field" ]]; then
              echo "C2V_PROBE_CGROUP_FIELD // $unit $field"
              head -n 4 "/sys/fs/cgroup$cg/$field" || true
            fi
          done
        ;;
      esac
    done
    tail -n 6 /var/tmp/c2v-rpm-ostree-install.log 2>/dev/null || true
  } >/dev/ttyS0 2>&1
done
PROBE
    chmod 0700 /run/c2v-guest-probe.sh
    systemd-run --quiet --unit=c2v-guest-probe --property=Type=exec \
      /usr/bin/bash /run/c2v-guest-probe.sh ||
      echo "C2V_GUEST_PROBE_START_FAILED"
    echo "C2V_GUEST_PROBE_START_RETURNED"
    # Worker and observer live in separate systemd cgroups. C2y verified
    # rpm-ostreed composed a pending deployment while the original oneshot
    # shell and its watchdog stopped reporting, so do not rely on its exit
    # alone. A pending deployment plus a booted-layer check are required.
    worker=/run/c2v-rpm-layer-worker.sh
    resultfile=/run/c2v-rpm-layer-worker-exit
    monitor=/run/c2v-rpm-layer-monitor.sh
    cat > "$monitor" <<'C2V_MONITOR'
#!/usr/bin/bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
echo "C2V_MONITOR_READY // $(date --iso-8601=seconds)"
echo ready > /run/c2v-monitor-ready
pkg=postapollo-connections-c2t-fixture
log=/var/tmp/c2v-rpm-ostree-install.log
resultfile=/run/c2v-rpm-layer-worker-exit
staged_json=/run/c2v-ostree-pending.json
fail() {
  echo "C2V_FAIL // INDEPENDENT_MONITOR_$*"
  tail -n 45 "$log" 2>/dev/null || true
  timeout --signal=TERM --kill-after=5s 15s rpm-ostree status || true
  systemctl poweroff --no-block || true
  exit 1
}
# Run in a separate transient systemd service, never in the original
# first-boot oneshot cgroup, which did not resume after staging the RPM.
for attempt in $(seq 1 50); do
  echo "C2V_INSTALL_WATCHDOG // independent-monitor-attempt=$attempt"
  tail -n 5 "$log" 2>/dev/null || true
  if timeout --signal=TERM --kill-after=5s 12s rpm-ostree status --json > "$staged_json" 2>/dev/null; then
    if python3 - "$staged_json" "$pkg" <<'C2V_PENDING_CHECK'
import json,sys
with open(sys.argv[1],encoding="utf-8") as fp:
    status=json.load(fp)
ds=status.get("deployments") or []
if len(ds)<2 or status.get("transaction") is not None:
    sys.exit(1)
d=ds[0]
pending=bool(d.get("staged") or d.get("pending")) or d.get("booted") is False
package_refs=json.dumps({"requested-local-packages":d.get("requested-local-packages",[]),"packages":d.get("packages",[])})
if not (pending and sys.argv[2] in package_refs):
    sys.exit(1)
print("C2V_PENDING_DEPLOYMENT_AUTHORITY // staged-or-pending, idle transaction, exact test RPM")
C2V_PENDING_CHECK
    then
      if [[ -e "$resultfile" ]]; then
        rc="$(cat "$resultfile")"
        [[ "$rc" == 0 ]] || fail "WORKER_REPORTED_NONZERO_INSTALL_EXIT_$rc"
        echo "C2V_INSTALL_RETURNED_SUCCESS"
      else
        echo "C2V_INSTALL_WORKER_EXIT_UNOBSERVED // pending deployment independently verified"
      fi
      echo "C2V_PASS // RPM_OSTREE_LAYER_STAGED_REBOOT_REQUIRED"
      echo layer_pending > /var/lib/c2v-transaction-stage
      sync
      echo "C2V_MONITOR_REBOOT_REQUESTED // verified pending deployment"
      systemctl reboot --no-block || fail "REBOOT_REQUEST_FAILED"
      exit 0
    fi
  fi
  if [[ -e "$resultfile" ]]; then
    rc="$(cat "$resultfile")"
    if [[ "$rc" != 0 ]]; then
      echo "C2V_INSTALL_FAILED_EXIT // $rc"
      journalctl -b -u rpm-ostreed.service --no-pager -n 45 || true
      fail "OFFLINE_RPM_OSTREE_INSTALL_FAILED_$rc"
    fi
  fi
  sleep 15
done
echo "C2V_INSTALL_PENDING_CHECK_TIMED_OUT"
journalctl -b -u rpm-ostreed.service --no-pager -n 65 || true
fail "NO_VERIFIED_PENDING_DEPLOYMENT_AFTER_INSTALL_WORKER"
C2V_MONITOR
    chmod 0700 "$monitor"
    echo "C2V_MONITOR_LAUNCHING // separate transient cgroup"
    timeout --signal=TERM --kill-after=5s 25s systemd-run --quiet \
      --unit=c2v-rpm-layer-monitor --property=Type=exec \
      --property=TimeoutStartSec=1120 /usr/bin/bash "$monitor" ||
      failure "MONITOR_UNIT_START_FAILED"
    # Do not initiate an RPM transaction until the independent monitor
    # confirms it is actually running, not merely accepted by systemd.
    monitor_ready=0
    for _ in $(seq 1 15); do
      if [[ -f /run/c2v-monitor-ready ]]; then monitor_ready=1; break; fi
      sleep 1
    done
    [[ "$monitor_ready" == 1 ]] || failure "MONITOR_DID_NOT_START"
    echo "C2V_MONITOR_STARTED_IN_SEPARATE_CGROUP"
    cat > "$worker" <<'C2V_WORKER'
#!/usr/bin/bash
set -u
log=/var/tmp/c2v-rpm-ostree-install.log
printf "C2V_WORKER_START // %s\n" "$(date --iso-8601=seconds)" >> "$log"
if timeout --signal=TERM --kill-after=20s 480s rpm-ostree install --cache-only /mnt/c2v-offline/c2t-0.1.rpm >> "$log" 2>&1; then
  printf "0\n" > /run/c2v-rpm-layer-worker-exit
else
  printf "%s\n" "$?" > /run/c2v-rpm-layer-worker-exit
fi
C2V_WORKER
    chmod 0700 "$worker"
    echo "C2V_INSTALL_COMMAND_BEGIN // detached transient unit; timeout=480s; local RPM only"
    timeout --signal=TERM --kill-after=5s 25s systemd-run --quiet \
      --unit=c2v-rpm-layer-worker --property=Type=exec \
      --property=TimeoutStartSec=600 /usr/bin/bash "$worker" ||
      failure "DETACHED_RPM_INSTALL_WORKER_START_FAILED"
    echo "C2V_INSTALL_WORKER_STARTED_IN_SEPARATE_CGROUP"
    # Important: the original one-shot service must EXIT instead of polling
    # rpm-ostreed. The independently running monitor is the sole owner of
    # pending-deployment verification, /var checkpoint and guest reboot.
    echo "C2V_MONITOR_HANDOFF_COMPLETE // first-boot controller exiting"
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
