#!/usr/bin/bash
# C2u: runs ONLY as a temporary service inside an installed, networkless
# Fedora Silverblue 44 VM. Never invoke on a user's system.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
# Separate C4b UART records top-level controller failure. Never acceptance.
c4b_controller_failure_relay() {
  [[ -f /var/lib/c4b-runtime-ci-only && -c /dev/ttyS1 ]] || return 0
  local reason="$1"
  timeout --signal=TERM --kill-after=1s 5s \
    /usr/bin/bash -c 'printf "C4B_DIAG_CONTROLLER_FATAL // %s\n" "$1" >/dev/ttyS1' \
    _ "$reason" || true
}
failure() {
  c4b_controller_failure_relay "$*"
  echo "C2V_FAIL // $*"
  timeout --signal=TERM --kill-after=5s 15s rpm-ostree status 2>&1 | head -n 45 || true
  systemctl poweroff --no-block || true
  exit 1
}
trap 'rc=$?; if [[ "$rc" -ne 0 ]]; then c4b_controller_failure_relay "SCRIPT_EXIT_$rc-line-$LINENO"; echo "C2V_FAIL // SCRIPT_EXIT_$rc line $LINENO"; systemctl poweroff --no-block || true; fi' EXIT
stagefile=/var/lib/c2v-transaction-stage
pkg=postapollo-connections-c2t-fixture
data=/mnt/c2v-offline
c4a_mode=/var/lib/c4a-signed-service-test
c4a_gate=/var/lib/c4a-guest-signed-status-gate.sh
c4b_mode=/var/lib/c4b-runtime-ci-only
c4b_gate=/var/lib/c4b-guest-confined-runtime.sh
c4b_assets=/var/lib/c4b-runtime-assets

# Independently observe C4b without controlling package/reboot authorization.
c4b_execute() {
  local phase="$1" rc
  [[ -s "$c4b_gate" ]] || failure "C4B_RUNTIME_GATE_MISSING_$phase"
  cat > /run/c4b-runtime-observer.sh <<'C4B_OBSERVER'
#!/usr/bin/bash
set -u
printf 'ready\n' > /run/c4b-runtime-observer-ready
for n in $(seq 1 65); do
  {
    echo "C4B_OBSERVER_TICK // n=$n $(date --iso-8601=seconds)"
    if [[ -r /var/tmp/c4b-runtime-stage ]]; then
      echo "C4B_OBSERVER_STAGE // $(cat /var/tmp/c4b-runtime-stage)"
    fi
    if [[ -r /var/tmp/c4b-runtime.log ]]; then
      echo "C4B_OBSERVER_GUEST_LOG_BEGIN"
      tail -n 12 /var/tmp/c4b-runtime.log || true
    fi
    timeout 4s ps -eo pid,stat,etime,comm |
      grep -E '[s]emodule|[r]estorecon|[s]ystemctl|[r]pm-ostree|PID' |
      head -n 12 || true
  } >/dev/ttyS0 2>&1 || true
  [[ -e /run/c4b-runtime-observer-finished ]] && break
  sleep 10
done
C4B_OBSERVER
  chmod 0700 /run/c4b-runtime-observer.sh
  rm -f /run/c4b-runtime-observer-finished /run/c4b-runtime-observer-ready
  echo "C4B_CONTROLLER_START // phase=$phase bounded=560s"
  timeout --signal=TERM --kill-after=5s 20s systemd-run --quiet \
    --unit=c4b-runtime-observer --property=Type=exec \
    /usr/bin/bash /run/c4b-runtime-observer.sh ||
    failure "C4B_INDEPENDENT_OBSERVER_START_FAILED"
  local observer_ready=0
  for _ in $(seq 1 8); do
    [[ -e /run/c4b-runtime-observer-ready ]] && { observer_ready=1; break; }
    sleep 1
  done
  [[ "$observer_ready" == 1 ]] ||
    failure "C4B_INDEPENDENT_OBSERVER_NOT_RUNNING"
  if timeout --signal=TERM --kill-after=15s 560s \
      /usr/bin/bash "$c4b_gate" "$phase"; then
    rc=0
  else
    rc="$?"
  fi
  echo complete > /run/c4b-runtime-observer-finished
  echo "C4B_CONTROLLER_EXIT // phase=$phase rc=$rc"
  echo "C4B_CONTROLLER_LAST_STAGE // $(cat /var/tmp/c4b-runtime-stage 2>/dev/null || echo absent)"
  echo "C4B_CONTROLLER_GUEST_LOG_BEGIN"
  tail -n 110 /var/tmp/c4b-runtime.log 2>/dev/null || true
  [[ "$rc" == 0 ]] || failure "C4B_RUNTIME_PHASE_FAILED_OR_TIMED_OUT_$rc"
}
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
    # Explicit C4a-only signed fake host; never enters the normal C2v test.
    if [[ -f "$data/c4a-opt-in.marker" ]]; then
      [[ -s "$data/c4a-guest-signed-status-gate.sh" ]] ||
        failure "C4A_GUEST_GATE_MISSING"
      install -m 0700 "$data/c4a-guest-signed-status-gate.sh" "$c4a_gate"
      /usr/bin/bash "$c4a_gate" prelayer ||
        failure "C4A_SIGNED_STATUS_PRELAYER_VERIFICATION_FAILED"
      printf '%s\n' signed-test-only > "$c4a_mode"
      echo "C4A_PASS // EXPLICIT_SILVERBLUE_SIGNED_SERVICE_MODE_ACCEPTED"
    fi
    # C4b only: preserve read-only ISO inputs in /var across the real boots.
    # The legacy C2v/C2x and signed-but-inactive C4a paths never enter here.
    if [[ -f "$data/c4b-opt-in.marker" ]]; then
      [[ -f "$c4a_mode" ]] || failure "C4B_REQUIRES_C4A_SIGNED_MODE"
      [[ -s "$data/c4b-guest-confined-runtime.sh" ]] ||
        failure "C4B_RUNTIME_GATE_NOT_STAGED"
      (cd "$data" && sha256sum --check --status c4b-runtime-manifest.sha256) ||
        failure "C4B_OFFLINE_ASSETS_FAILED_CHECKSUM"
      mkdir -m 0700 -p "$c4b_assets"
      for name in postapollo_connections.pp dbus_next.whl \
                  C3bOriginCheck.py BusPolicyClient.py; do
        install -m 0600 "$data/$name" "$c4b_assets/$name" ||
          failure "C4B_OFFLINE_ASSET_COPY_FAILED"
      done
      install -m 0700 "$data/c4b-guest-confined-runtime.sh" "$c4b_gate" ||
        failure "C4B_RUNTIME_SCRIPT_STAGING_FAILED"
      printf '%s\n' C4B_DISPOSABLE_VM_ONLY > "$c4b_mode"
      # This witness runs only when poweroff is requested inside disposable
      # C4b. It never initiates shutdown or authorizes a stage transition.
      cat > /var/lib/c4b-shutdown-witness.sh <<'C4B_SHUTDOWN_WITNESS'
#!/usr/bin/bash
set +e
[[ -f /var/lib/c4b-runtime-ci-only && -c /dev/ttyS1 ]] || exit 0
{
  echo "C4B_DIAG_POWEROFF_WITNESS // $(date --iso-8601=seconds)"
  for unit in c2v-ostree-cycle.service c2v-rpm-layer-monitor.service \
              c2v-rpm-layer-worker.service rpm-ostreed.service; do
    echo "C4B_DIAG_POWEROFF_UNIT // $unit"
    timeout 3s systemctl show "$unit" --no-pager \
      -p ActiveState -p SubState -p Result -p ExecMainStatus \
      -p MainPID -p NRestarts || true
  done
  echo "C4B_DIAG_POWEROFF_MONITOR_EXIT"
  tail -n 16 /var/tmp/c2v-monitor-exit.log 2>/dev/null || true
  echo "C4B_DIAG_POWEROFF_WORKER"
  cat /run/c2v-rpm-layer-worker-exit 2>/dev/null || echo not-observed
  echo "C4B_DIAG_POWEROFF_MONITOR_TAIL"
  tail -n 26 /var/tmp/c2v-monitor-output.log 2>/dev/null || true
  echo "C4B_DIAG_POWEROFF_WORKER_TAIL"
  tail -n 26 /var/tmp/c2v-rpm-ostree-install.log 2>/dev/null || true
  echo "C4B_DIAG_POWEROFF_JOURNAL"
  timeout 6s journalctl -b --no-pager -n 30 2>&1 || true
} > /var/tmp/c4b-shutdown-witness.log 2>&1
timeout --signal=TERM --kill-after=2s 10s \
  cat /var/tmp/c4b-shutdown-witness.log >/dev/ttyS1 2>&1 || true
exit 0
C4B_SHUTDOWN_WITNESS
      chmod 0700 /var/lib/c4b-shutdown-witness.sh
      cat > /etc/systemd/system/c4b-shutdown-witness.service <<'C4B_SHUTDOWN_UNIT'
[Unit]
Description=Disposable C4b poweroff diagnostic only
DefaultDependencies=no
Before=poweroff.target
ConditionPathExists=/var/lib/c4b-runtime-ci-only

[Service]
Type=oneshot
TimeoutStartSec=25
ExecStart=-/usr/bin/bash /var/lib/c4b-shutdown-witness.sh

[Install]
WantedBy=poweroff.target
C4B_SHUTDOWN_UNIT
      systemctl daemon-reload || failure "C4B_DIAG_WITNESS_SYSTEMD_RELOAD_FAILED"
      systemctl enable c4b-shutdown-witness.service ||
        failure "C4B_DIAG_WITNESS_ENABLE_FAILED"
      # UART1 exists only in C4b's disposable QEMU; diagnostic-only channel.
      if [[ -c /dev/ttyS1 ]]; then
        timeout --signal=TERM --kill-after=1s 4s \
          /usr/bin/bash -c 'printf "%s\n" "C4B_DIAG_UART1_READY // first_boot" >/dev/ttyS1' || true
      fi
      echo "C4B_PASS // SIGNED_C4A_LAYER_HAS_EXPLICIT_OFFLINE_RUNTIME_OPT_IN"
    fi
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
for n in $(seq 1 72); do
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
    # Independent evidence channel: the monitor's serial ERR/EXIT traps were
    # absent even though systemd recorded ExecMainStatus=1. Read its journal
    # and on-disk exit marker from the still-live resource probe.
    if [[ -f /var/tmp/c2v-monitor-output.log ]]; then
      echo "C2V_PROBE_MONITOR_OUTPUT_BEGIN"
      tail -n 18 /var/tmp/c2v-monitor-output.log || true
    fi
    if [[ -f /var/tmp/c2v-monitor-exit.log ]]; then
      echo "C2V_PROBE_MONITOR_EXIT_FILE_BEGIN"
      tail -n 12 /var/tmp/c2v-monitor-exit.log || true
    fi
    if [[ -f /var/tmp/c2v-monitor-shell-trace.log ]]; then
      echo "C2V_PROBE_MONITOR_SHELL_TRACE_BEGIN"
      tail -n 26 /var/tmp/c2v-monitor-shell-trace.log || true
    fi
    if (( n <= 12 || n % 6 == 0 )); then
      echo "C2V_PROBE_MONITOR_SYSTEMD_PROPERTIES_BEGIN"
      timeout --signal=TERM --kill-after=2s 6s systemctl show c2v-rpm-layer-monitor.service \
        --property=Type --property=TimeoutStartUSec --property=RuntimeMaxUSec \
        --property=ExecMainCode --property=ExecMainStatus --property=Result \
        --property=KillMode --property=OOMPolicy --no-pager 2>&1 || \
        echo "C2V_PROBE_MONITOR_PROPERTIES_UNAVAILABLE"
    fi
    if (( n <= 12 || n % 6 == 0 )); then
      echo "C2V_PROBE_MONITOR_JOURNAL_BEGIN"
      timeout --signal=TERM --kill-after=2s 6s journalctl -b -u c2v-rpm-layer-monitor.service --no-pager -n 16 2>&1 ||
        echo "C2V_PROBE_MONITOR_JOURNAL_UNAVAILABLE"
    fi
    # The last two CI runs showed both transient units disappear or stop
    # reporting while this separate resource probe stayed active. Capture
    # actual systemd unit lifetime and read-only libostree state, without
    # scheduling any reboots or weakening the acceptance gate.
    if (( n <= 12 || n % 6 == 0 )); then
      for unit in c2v-ostree-cycle.service c2v-rpm-layer-monitor.service c2v-rpm-layer-worker.service rpm-ostreed.service; do
        echo "C2V_PROBE_UNIT_STATE_BEGIN // $unit"
        timeout --signal=TERM --kill-after=2s 5s systemctl show "$unit" \
          --property=ActiveState --property=SubState --property=Result \
          --property=MainPID --property=ExecMainStatus --no-pager 2>&1 ||
          echo "C2V_PROBE_UNIT_STATE_QUERY_BLOCKED // $unit"
        cg="/sys/fs/cgroup/system.slice/$unit"
        if [[ -r "$cg/cgroup.events" ]]; then
          echo "C2V_PROBE_CGROUP_EVENTS // $unit"
          head -n 5 "$cg/cgroup.events" || true
          if [[ -r "$cg/cgroup.freeze" ]]; then
            echo "C2V_PROBE_CGROUP_FREEZE // $unit $(cat "$cg/cgroup.freeze")"
          fi
        else
          echo "C2V_PROBE_CGROUP_ABSENT // $unit"
        fi
      done
      echo "C2V_PROBE_OSTREE_ADMIN_STATUS_BEGIN"
      if timeout --signal=TERM --kill-after=2s 6s \
          ostree admin status --json > /run/c2v-probe-ostree-status.json 2>&1; then
        echo "C2V_PROBE_OSTREE_ADMIN_STATUS_SUCCESS"
        head -c 700 /run/c2v-probe-ostree-status.json || true
        echo
      else
        echo "C2V_PROBE_OSTREE_ADMIN_STATUS_TIMEOUT_OR_ERROR"
        tail -n 8 /run/c2v-probe-ostree-status.json || true
      fi
    fi
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
# Serial is diagnostic-only and can reject writes in the disposable VM.
# A failed serial echo previously triggered errexit after the first sleep.
# Persist monitor output independently; the guest probe relays it to serial
# without making that channel part of reboot authorization.
exec >>/var/tmp/c2v-monitor-output.log 2>&1
# Trace to an independent guest-local file: stdout/ERR/EXIT traps have not
# survived the observed first poll. The resource probe collects this file.
exec 9>>/var/tmp/c2v-monitor-shell-trace.log
export BASH_XTRACEFD=9
PS4='+C2V_TRACE line=${LINENO} rc=$? '
set -x
# Preserve the exact first failing command and exit status; a successful
# systemd-run start does not prove its later transient unit stayed healthy.
trap 'rc=$?; msg="C2V_MONITOR_ERR // rc=$rc line=$LINENO command=$BASH_COMMAND"; echo "$msg"; printf "%s\n" "$msg" >> /var/tmp/c2v-monitor-exit.log' ERR
trap 'rc=$?; msg="C2V_MONITOR_EXIT // rc=$rc"; echo "$msg"; printf "%s\n" "$msg" >> /var/tmp/c2v-monitor-exit.log; if [[ "$rc" -ne 0 ]] && declare -F c4b_emergency_relay >/dev/null; then c4b_emergency_relay "MONITOR_ABNORMAL_EXIT_$rc"; fi' EXIT
echo "C2V_MONITOR_READY // $(date --iso-8601=seconds)"
echo ready > /run/c2v-monitor-ready
pkg=postapollo-connections-c2t-fixture
log=/var/tmp/c2v-rpm-ostree-install.log
resultfile=/run/c2v-rpm-layer-worker-exit
staged_json=/run/c2v-ostree-pending.json
# Opt-in C4b-only evidence relay. The monitor's normal stdout is a private
# guest-local file; when it intentionally powers off a failed test, the
# periodic probe may not get another tick to relay the reason.
# Relay is best-effort, bounded, and NEVER authorizes a reboot or success.
c4b_emergency_relay() {
  [[ -f /var/lib/c4b-runtime-ci-only ]] || return 0
  local reason="$1"
  {
    printf 'C4B_DIAG_MONITOR_FATAL // %s\n' "$reason"
    printf 'C4B_DIAG_WORKER_EXIT // %s\n' \
      "$(cat /run/c2v-rpm-layer-worker-exit 2>/dev/null || echo unobserved)"
    echo 'C4B_DIAG_MONITOR_OUTPUT_BEGIN'
    tail -n 45 /var/tmp/c2v-monitor-output.log 2>/dev/null || true
    echo 'C4B_DIAG_RPM_OSTREE_WORKER_LOG_BEGIN'
    tail -n 45 /var/tmp/c2v-rpm-ostree-install.log 2>/dev/null || true
  } > /var/tmp/c4b-monitor-fatal-summary.log 2>&1 || true
  # ttyS1 is a second independent C4b-only UART. Its output is NEVER an
  # acceptance signal. Keep the old ttyS0 best-effort path for comparison.
  if [[ -c /dev/ttyS1 ]]; then
    timeout --signal=TERM --kill-after=2s 9s \
      cat /var/tmp/c4b-monitor-fatal-summary.log >/dev/ttyS1 2>&1 || true
  fi
  timeout --signal=TERM --kill-after=2s 9s \
    cat /var/tmp/c4b-monitor-fatal-summary.log >/dev/ttyS0 2>&1 || true
  return 0
}
fail() {
  echo "C2V_FAIL // INDEPENDENT_MONITOR_$*"
  c4b_emergency_relay "INDEPENDENT_MONITOR_$*"
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
    echo "C2V_MONITOR_STATUS_QUERY_OK // attempt=$attempt bytes=$(wc -c < "$staged_json")"
    if python3 - "$staged_json" "$pkg" <<'C2V_PENDING_CHECK'
import json,sys,os
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
# C4a requires BOTH exact signed-test NEVRAs as LOCAL requested layers,
# never substring matches in unrelated package names or JSON fields.
if os.path.isfile("/var/lib/c4a-signed-service-test"):
    import re
    local_refs=d.get("requested-local-packages") or []
    expected=(
        "postapollo-connections-c2t-fixture-0.1-1.fc44.noarch",
        "postapollo-connections-c3d-ci-status-0.1-1.fc44.noarch",
    )
    if not isinstance(local_refs,list) or not all(
        any(isinstance(ref,str) and (
            ref==nevra or
            re.fullmatch(r"sha256:[a-fA-F0-9]{64}:"+re.escape(nevra),ref)
        ) for ref in local_refs) for nevra in expected
    ):
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
    else
      echo "C2V_MONITOR_PENDING_JSON_REJECTED // attempt=$attempt"
      # Read-only, bounded observation at early denied polls, independent of
      # the authoritative C2v/C4a pending-deployment check above.
      if [[ -f /var/lib/c4b-runtime-ci-only && -c /dev/ttyS1 ]] &&
         (( attempt == 2 || attempt == 3 || attempt % 6 == 0 )); then
        {
          echo "C4B_DIAG_PENDING_REJECTED // attempt=$attempt"
          python3 - "$staged_json" <<'C4B_PENDING_DIAG'
import json,sys
try:
    with open(sys.argv[1],encoding="utf-8") as fp:
        s=json.load(fp)
    deployments=s.get("deployments") or []
    d=deployments[0] if deployments else {}
    print("C4B_DIAG_PENDING_HEAD // "+
          json.dumps({"transaction":s.get("transaction"),
                      "staged":d.get("staged"),"pending":d.get("pending"),
                      "booted":d.get("booted"),
                      "requested-local-packages":d.get("requested-local-packages"),
                      "packages":d.get("packages")},sort_keys=True)[:2500])
except Exception as exc:
    print("C4B_DIAG_PENDING_PARSE_FAILED // "+type(exc).__name__)
C4B_PENDING_DIAG
          echo "C4B_DIAG_WORKER_EXIT // $(cat "$resultfile" 2>/dev/null || echo unobserved)"
          tail -n 8 "$log" 2>/dev/null || true
        } >/var/tmp/c4b-pending-diag.log 2>&1 || true
        timeout --signal=TERM --kill-after=1s 5s \
          cat /var/tmp/c4b-pending-diag.log >/dev/ttyS1 2>&1 || true
      fi
    fi
  else
    echo "C2V_MONITOR_STATUS_QUERY_FAILED // attempt=$attempt"
  fi
  if [[ -e "$resultfile" ]]; then
    rc="$(cat "$resultfile")"
    if [[ "$rc" != 0 ]]; then
      echo "C2V_INSTALL_FAILED_EXIT // $rc"
      journalctl -b -u rpm-ostreed.service --no-pager -n 45 || true
      fail "OFFLINE_RPM_OSTREE_INSTALL_FAILED_$rc"
    fi
  fi
  echo "C2V_MONITOR_ITERATION_DONE // attempt=$attempt"
  echo "C2V_MONITOR_SLEEP_BEGIN // attempt=$attempt"
  if sleep 15; then
    echo "C2V_MONITOR_SLEEP_COMPLETED // attempt=$attempt"
  else
    rc="$?"
    echo "C2V_MONITOR_SLEEP_FAILED // attempt=$attempt rc=$rc"
    fail "POLL_SLEEP_FAILED_$rc"
  fi
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
set -- /mnt/c2v-offline/c2t-0.1.rpm
if [[ -f /var/lib/c4a-signed-service-test ]]; then
  set -- "$@" /mnt/c2v-offline/c3d-status.rpm
  if [[ ! -s /mnt/c2v-offline/c3d-status.rpm ]]; then
    printf '2\n' > /run/c2v-rpm-layer-worker-exit
    exit 2
  fi
fi
if timeout --signal=TERM --kill-after=20s 480s rpm-ostree install --cache-only "$@" >> "$log" 2>&1; then
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
    if [[ -f "$c4a_mode" ]]; then
      [[ -s "$c4a_gate" ]] || failure "C4A_GATE_LOST_AFTER_FIRST_REBOOT"
      /usr/bin/bash "$c4a_gate" booted ||
        failure "C4A_SIGNED_SERVICE_NOT_VALID_AFTER_REBOOT"
    fi
    if [[ -f "$c4b_mode" ]]; then
      [[ -s "$c4b_gate" ]] || failure "C4B_RUNTIME_GATE_LOST_AFTER_REBOOT"
      c4b_execute booted ||
        failure "C4B_CONFINED_RUNTIME_NOT_VERIFIED"
    fi
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
    if [[ -f "$c4a_mode" ]]; then
      [[ -s "$c4a_gate" ]] || failure "C4A_GATE_LOST_AFTER_ROLLBACK"
      /usr/bin/bash "$c4a_gate" rolledback ||
        failure "C4A_SIGNED_SERVICE_ROLLBACK_NOT_VERIFIED"
    fi
    if [[ -f "$c4b_mode" ]]; then
      [[ -s "$c4b_gate" ]] || failure "C4B_RUNTIME_GATE_LOST_AFTER_ROLLBACK"
      c4b_execute rolledback ||
        failure "C4B_RUNTIME_CLEANUP_OR_ROLLBACK_NOT_VERIFIED"
    fi
    # Remove test-only poweroff witness following successful real rollback.
    if [[ -e /etc/systemd/system/c4b-shutdown-witness.service ]]; then
      systemctl disable c4b-shutdown-witness.service ||
        failure "C4B_DIAG_WITNESS_DISABLE_FAILED"
      rm -f -- /etc/systemd/system/c4b-shutdown-witness.service \
        /var/lib/c4b-shutdown-witness.sh
      systemctl daemon-reload || failure "C4B_DIAG_WITNESS_CLEANUP_RELOAD_FAILED"
      [[ ! -e /var/lib/c4b-shutdown-witness.sh &&
         ! -e /etc/systemd/system/c4b-shutdown-witness.service ]] ||
        failure "C4B_DIAG_WITNESS_CLEANUP_FAILED"
    fi
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
