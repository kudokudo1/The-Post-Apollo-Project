#!/usr/bin/bash
# C4b disposable Fedora Silverblue runtime probe. NEVER a host installer.
set -Eeuo pipefail
[[ "$#" == 1 ]] || { echo "C4B_FAIL // INVALID_ARGUMENTS"; exit 2; }
phase="$1"
# Do not let the guest serial device govern runtime authorization. C2z
# already demonstrated that ttyS0 writes may fail despite successful work.
# A separate systemd observer and the controller relay this test-only log.
exec >>/var/tmp/c4b-runtime.log 2>&1
stage() {
  echo "C4B_STAGE // phase=$phase step=$1"
  printf '%s\n' "$phase/$1" > /var/tmp/c4b-runtime-stage
}
trap 'rc=$?; echo "C4B_EXIT // phase=$phase rc=$rc step=$(cat /var/tmp/c4b-runtime-stage 2>/dev/null || echo unavailable)"' EXIT
stage ENTER
mode=/var/lib/c4b-runtime-ci-only
assets=/var/lib/c4b-runtime-assets
donefile=/var/lib/c4b-runtime-cleaned
unit=postapollo-connections-status.service
bus=org.postapollo.ConnectionsStatus1
host=/usr/libexec/post-apollo/connections-status-host
python=/opt/postapollo-c2o-venv/bin/python3
fail() {
  echo "C4B_FAIL // $*" >&2
  timeout 5s systemctl status "$unit" --no-pager -l 2>&1 | tail -n 20 || true
  timeout 5s journalctl -b -u "$unit" --no-pager -n 18 2>&1 || true
  exit 2
}
[[ "$phase" == booted || "$phase" == rolledback ]] || fail "INVALID_PHASE"
[[ "$(id -u)" == 0 && -e /run/ostree-booted &&
   -f "$mode" && -f /var/lib/c4a-signed-service-test &&
   -f /usr/local/libexec/c2v-ostree-cycle.sh ]] ||
  fail "REFUSED_OUTSIDE_DISPOSABLE_C4A"
[[ "$(getenforce)" == Enforcing &&
   "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
  fail "SELINUX_NOT_ENFORCING"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] ||
  fail "GUEST_HAS_NETWORK_INTERFACE"
[[ "$(cat /etc/fedora-release)" == *"Fedora release 44"* ]] || fail "NOT_FEDORA_44"
ostree admin status | grep -iq silverblue || fail "NOT_SILVERBLUE"
check_released() {
  [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
    fail "SERVICE_REMAINS_ACTIVE"
  if busctl --system get-name-owner "$bus" >/dev/null 2>&1; then
    fail "BUS_NAME_REMAINS_OWNED"
  fi
}
check_accounts_absent() {
  for user in postapollo-connections c4b-reader c4b-outsider; do
    getent passwd "$user" >/dev/null && fail "USER_REMAINS_$user"
  done
  for group in postapollo-connections postapollo-status-readers c4b-clients; do
    getent group "$group" >/dev/null && fail "GROUP_REMAINS_$group"
  done
  return 0
}
client_check() {
  local result
  result="$(runuser -u "$1" -- "$python" -I -B /opt/c4b/BusPolicyClient.py "$2")" ||
    fail "CLIENT_INVOCATION_FAILED"
  [[ "$result" == "$3" ]] || fail "CLIENT_RESPONSE_MISMATCH"
}
if [[ "$phase" == booted ]]; then
  [[ "$(cat /var/lib/c2v-transaction-stage)" == layer_pending ]] ||
    fail "WRONG_BOOT_PHASE"
  [[ ! -e "$donefile" &&
     -s "$assets/postapollo_connections.pp" &&
     -s "$assets/dbus_next.whl" &&
     -s "$assets/C3bOriginCheck.py" &&
     -s "$assets/BusPolicyClient.py" ]] || fail "MISSING_OFFLINE_FIXTURES"
  echo "58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b  $assets/dbus_next.whl" |
    sha256sum --check --status || fail "PINNED_DBUS_WHEEL_HASH_MISMATCH"
  stage BASELINE_CHECKS
  check_accounts_absent
  check_released
  # This policy must already be present in the signed, offline layered
  # deployment. Runtime relabel of immutable /usr is not possible on Silverblue.
  stage COMPOSED_POLICY_VERIFICATION_BEGIN
  command -v semodule >/dev/null || fail "SEMODULE_UNAVAILABLE"
  [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}\n' \
    postapollo-connections-c4b-policy-ci 2>/dev/null || true)" == \
    "postapollo-connections-c4b-policy-ci 0.1 noarch" ]] ||
    fail "SIGNED_POLICY_RPM_NOT_COMPOSED"
  timeout 15s semodule -l | grep -Fq postapollo_connections ||
    fail "COMPOSED_SELINUX_POLICY_NOT_LOADED"
  [[ "$(getenforce)" == Enforcing ]] || fail "ENFORCING_WEAKENED"
  echo "C4B_PASS // SELINUX_POLICY_LOADED_WITH_ENFORCING_KERNEL"
  stage COMPOSED_IMMUTABLE_EXECUTABLE_LABEL_CHECK
  [[ "$(ls -Z "$host")" == *postapollo_connections_exec_t* ]] ||
    fail "SIGNED_OSTREE_EXECUTABLE_NOT_LABELED"
  echo "C4B_PASS // SIGNED_SILVERBLUE_EXECUTABLE_CONFINED_ENTRYPOINT"

  stage SERVICE_IDENTITY_SETUP_BEGIN
  groupadd --system postapollo-connections || fail "SERVICE_GROUP_FAILED"
  groupadd --system postapollo-status-readers || fail "READER_GROUP_FAILED"
  groupadd --system c4b-clients || fail "CLIENT_GROUP_FAILED"
  useradd --system --no-create-home --shell /usr/sbin/nologin \
    --gid postapollo-connections postapollo-connections || fail "SERVICE_USER_FAILED"
  useradd --system --no-create-home --shell /usr/sbin/nologin \
    --gid c4b-clients --groups postapollo-status-readers c4b-reader ||
    fail "READER_USER_FAILED"
  useradd --system --no-create-home --shell /usr/sbin/nologin \
    --gid c4b-clients c4b-outsider || fail "OUTSIDER_USER_FAILED"
  stage PINNED_OFFLINE_PYTHON_SETUP_BEGIN
  timeout --signal=TERM --kill-after=5s 90s python3 -m venv --without-pip /opt/postapollo-c2o-venv ||
    fail "OFFLINE_VENV_UNAVAILABLE"
  site="$("$python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" ||
    fail "VENV_SITE_NOT_FOUND"
  mkdir -p "$site" /opt/c4b
  "$python" -m zipfile -e "$assets/dbus_next.whl" "$site" ||
    fail "PINNED_WHEEL_UNPACK_REFUSED"
  "$python" -I -c 'import dbus_next' || fail "OFFLINE_DBUS_MODULE_IMPORT_FAILED"
  install -m 0644 "$assets/BusPolicyClient.py" /opt/c4b/BusPolicyClient.py
  printf '%s\n' C4B_WORLD_READABLE_FAKE_NON_SECRET \
    > /var/lib/postapollo-c2r-ci-denied
  chmod 0644 /var/lib/postapollo-c2r-ci-denied
  chcon -t shadow_t /var/lib/postapollo-c2r-ci-denied ||
    fail "NEGATIVE_SELINUX_FIXTURE_LABEL_FAILED"
  [[ "$(stat -c %a /var/lib/postapollo-c2r-ci-denied)" == 644 ]] ||
    fail "NEGATIVE_FIXTURE_NOT_WORLD_READABLE"
  stage SIGNED_SYSTEMD_UNIT_VALIDATION_BEGIN
  timeout 30s systemctl daemon-reload || fail "GUEST_SYSTEMD_RELOAD_TIMED_OUT"
  timeout 30s systemd-analyze verify "/usr/lib/systemd/system/$unit" ||
    fail "SIGNED_UNIT_VERIFICATION_FAILED"
  [[ "$(systemctl is-enabled "$unit" 2>&1 || true)" == static ]] ||
    fail "SIGNED_SERVICE_MUST_BE_STATIC"
  check_released
  stage DBUS_POLICY_RELOAD_BEGIN
  timeout --signal=TERM --kill-after=5s 45s systemctl restart dbus-broker.service ||
    fail "GUEST_ONLY_DBUS_POLICY_RELOAD_FAILED"
  client_check c4b-reader claim OWN_REFUSED
  client_check c4b-outsider claim OWN_REFUSED
  echo "C4B_PASS // UNAUTHORIZED_DBUS_OWNERSHIP_REFUSED"

  stage EXPLICIT_SIGNED_FAKE_SERVICE_START_BEGIN
  timeout --signal=TERM --kill-after=5s 75s systemctl start "$unit" ||
    fail "EXPLICIT_FAKE_SERVICE_START_FAILED"
  [[ "$(systemctl is-active "$unit")" == active ]] ||
    fail "FAKE_SERVICE_DID_NOT_REMAIN_ACTIVE"
  pid="$(systemctl show --value -p MainPID "$unit")"
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || fail "MISSING_SERVICE_PID"
  [[ "$(ps -o user= -p "$pid" | xargs)" == postapollo-connections ]] ||
    fail "SERVICE_UID_NOT_DEDICATED"
  grep -Eq '^NoNewPrivs:[[:space:]]*1$' "/proc/$pid/status" ||
    fail "NO_NEW_PRIVILEGES_MISSING"
  [[ "$(cat "/proc/$pid/attr/current")" == *:postapollo_connections_t:* ]] ||
    fail "SERVICE_NOT_SELINUX_CONFINED"
  journalctl -u "$unit" --no-pager |
    grep -Fq 'C2R_PASS // SELINUX_REFUSED_WORLD_READABLE_PROBE' ||
    fail "CONFINED_SERVICE_DID_NOT_REFUSE_DUMMY_FILE"
  echo "C4B_PASS // REAL_SELINUX_SERVICE_DOMAIN_AND_NEGATIVE_FILE_DENIAL"
  stage C3B_OS_ORIGIN_VERIFICATION_BEGIN
  if ! GITHUB_ACTIONS=true POST_APOLLO_C3B_TEST_GUEST=1 \
      timeout --signal=TERM --kill-after=5s 60s \
        "$python" -I -B "$assets/C3bOriginCheck.py" --verify-disposable; then
    # Read-only diagnostic on rejection. Import the exact staged C3b probe
    # rather than inventing a second list of protected directories. Report
    # only ancestor attributes that violate its existing strict predicate.
    # Never permit a symlink or writable directory as a workaround.
    stage C3B_REJECTED_ORIGIN_ANCESTOR_DIAG_BEGIN
    timeout --signal=TERM --kill-after=3s 12s "$python" -I -B - \
      "$assets/C3bOriginCheck.py" <<'C4B_C3B_DIR_DIAG' || true
import importlib.util
import os
import stat
import sys

probe_path = sys.argv[1]
spec = importlib.util.spec_from_file_location("c4b_exact_c3b_probe", probe_path)
if spec is None or spec.loader is None:
    print("C4B_DIAG_C3B_PROBE_UNAVAILABLE", flush=True)
    raise SystemExit(1)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
violations = 0
for path in probe.PROTECTED_DIRS:
    try:
        info = os.lstat(path)
        owner = info.st_uid
        mode = stat.S_IMODE(info.st_mode)
        directory = stat.S_ISDIR(info.st_mode)
        symlink = stat.S_ISLNK(info.st_mode)
        if owner != 0 or mode & 0o022 or not directory or symlink:
            violations += 1
            print("C4B_DIAG_C3B_UNPROTECTED_DIRECTORY // "
                  f"path={path!r} uid={owner} mode={mode:04o} "
                  f"directory={directory} symlink={symlink}",
                  flush=True)
    except OSError as exc:
        violations += 1
        print("C4B_DIAG_C3B_ANCESTOR_STAT_REFUSED // "
              f"path={path!r} error={type(exc).__name__}", flush=True)
print(f"C4B_DIAG_C3B_ANCESTOR_VIOLATION_COUNT // {violations}", flush=True)
C4B_C3B_DIR_DIAG
    fail "DBUS_SYSTEMD_PID_UID_SELINUX_ORIGIN_REJECTED"
  fi
  client_check c4b-reader status OBSERVED_UNVERIFIED
  client_check c4b-reader approve METHOD_REFUSED
  client_check c4b-reader claim OWN_REFUSED
  client_check c4b-outsider status METHOD_REFUSED
  client_check c4b-outsider approve METHOD_REFUSED
  client_check c4b-outsider claim OWN_REFUSED
  echo "C4B_PASS // EXACT_RUNTIME_ORIGIN_AND_DENY_ONLY_CLIENT_CALLS"

  stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN
  timeout --signal=TERM --kill-after=5s 60s systemctl stop "$unit" ||
    fail "SERVICE_STOP_FAILED"
  check_released
  echo "C4B_PASS // SERVICE_STOP_RELEASES_DBUS_NAME"
  rm -f -- /var/lib/postapollo-c2r-ci-denied /opt/c4b/BusPolicyClient.py
  rmdir /opt/c4b || fail "CLIENT_DIRECTORY_CLEANUP_FAILED"
  [[ -d /opt/postapollo-c2o-venv ]] ||
    fail "OFFLINE_VENV_MISSING_AT_CLEANUP"
  rm -rf -- /opt/postapollo-c2o-venv
  userdel c4b-reader && userdel c4b-outsider &&
    userdel postapollo-connections || fail "TEST_USER_REMOVAL_FAILED"
  groupdel c4b-clients && groupdel postapollo-status-readers &&
    groupdel postapollo-connections || fail "TEST_GROUP_REMOVAL_FAILED"
  # The custom policy is part of the booted deployment and MUST NOT be
  # removed at runtime. Only the real OSTree rollback may remove it.
  stage COMPOSED_POLICY_RETAINED_FOR_ROLLBACK
  timeout 15s semodule -l | grep -Fq postapollo_connections ||
    fail "COMPOSED_POLICY_VANISHED_PREMATURELY"
  check_accounts_absent
  check_released
  stage BOOTED_RUNTIME_ACCEPTED
  echo complete > "$donefile"
  echo "C4B_PASS // RUNTIME_USERS_VENV_CLEANED_POLICY_RETAINED_FOR_ROLLBACK"
else
  stage ROLLBACK_RECHECK_BEGIN
  [[ "$(cat /var/lib/c2v-transaction-stage)" == rollback_pending ]] ||
    fail "WRONG_ROLLBACK_PHASE"
  [[ "$(cat "$donefile" 2>/dev/null || true)" == complete ]] ||
    fail "RUNTIME_TEST_NOT_COMPLETED_BEFORE_ROLLBACK"
  check_accounts_absent
  check_released
  [[ ! -e "$host" &&
     ! -e /usr/lib/systemd/system/postapollo-connections-status.service &&
     ! -e /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf &&
     ! -e /opt/postapollo-c2o-venv && ! -e /opt/c4b &&
     ! -e /var/lib/postapollo-c2r-ci-denied ]] ||
    fail "SIGNED_PACKAGE_OR_TEST_FILES_SURVIVED_ROLLBACK"
  if semodule -l | grep -Fq postapollo_connections; then
    fail "TEST_SELINUX_POLICY_REMAINS_AFTER_ROLLBACK"
  fi
  if rpm -q postapollo-connections-c4b-policy-ci >/dev/null 2>&1; then
    fail "SIGNED_COMPOSED_POLICY_RPM_REMAINS_AFTER_ROLLBACK"
  fi
  rm -f -- "$donefile" "$mode"
  rm -rf -- "$assets"
  [[ ! -e "$donefile" && ! -e "$mode" && ! -e "$assets" ]] ||
    fail "TEST_ARTIFACT_CLEANUP_INCOMPLETE"
  echo "C4B_PASS // SIGNED_CONFINED_FAKE_HOST_STOPPED_AND_REAL_SILVERBLUE_ROLLBACK"
  echo "C4B_LIMITATION // DISPOSABLE_OFFLINE_VM_NOT_PRODUCTION_HOST"
fi
