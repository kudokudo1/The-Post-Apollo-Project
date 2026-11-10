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
# Read-only prerequisite for a genuine later rpm-ostree rollback --reboot.
# The booted system bus must still own login1 and answer ListInhibitors.
# This neither restarts logind/broker nor overrides reboot inhibitors.
check_logind_bus_health() {
  local checkpoint="$1"
  timeout --signal=TERM --kill-after=2s 8s \
    busctl --system --timeout=5s call \
      org.freedesktop.DBus /org/freedesktop/DBus \
      org.freedesktop.DBus GetNameOwner s org.freedesktop.login1 \
      >/dev/null || fail "LOGIND_DBUS_OWNER_UNAVAILABLE_$checkpoint"
  timeout --signal=TERM --kill-after=2s 8s \
    busctl --system --timeout=5s call \
      org.freedesktop.login1 /org/freedesktop/login1 \
      org.freedesktop.login1.Manager ListInhibitors \
      >/dev/null || fail "LOGIND_INHIBITOR_QUERY_UNRESPONSIVE_$checkpoint"
  echo "C4B_PASS // LOGIND_DBUS_RESPONSIVE_$checkpoint"
}
if [[ "$phase" == booted ]]; then
  [[ "$(cat /var/lib/c2v-transaction-stage)" == layer_pending ]] ||
    fail "WRONG_BOOT_PHASE"
  [[ ! -e "$donefile" &&
     -s "$assets/postapollo_connections.pp" &&
     -s "$assets/dbus_next.whl" &&
     -s "$assets/C3bOriginCheck.py" &&
     -s "$assets/BusPolicyClient.py" &&
     -s "$assets/c3d-status.rpm" ]] || fail "MISSING_OFFLINE_FIXTURES"
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
  # C3d-signed D-Bus policy was composed into immutable /usr BEFORE the
  # real Silverblue boot. Do not assume it was loaded by the running broker:
  # inspect the signed installed file then perform a non-disruptive config
  # reload. Restarting the whole system bus risks breaking login1 rollback.
  stage DBUS_BOOT_COMPOSED_POLICY_CHECK_BEGIN
  dbus_policy=/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf
  [[ -f "$dbus_policy" && ! -L "$dbus_policy" ]] ||
    fail "SIGNED_BOOT_COMPOSED_DBUS_POLICY_MISSING"
  [[ "$(rpm -qf --qf '%{NAME}\n' "$dbus_policy" 2>/dev/null || true)" == \
     postapollo-connections-c3d-ci-status ]] ||
    fail "DBUS_POLICY_NOT_OWNED_BY_SIGNED_C3D_RPM"
  [[ "$(stat -c '%u:%g:%a' "$dbus_policy")" == 0:0:644 ]] ||
    fail "SIGNED_DBUS_POLICY_FILE_UNSAFE"
  [[ "$(systemctl is-active dbus-broker.service)" == active ]] ||
    fail "BOOTED_DBUS_BROKER_NOT_ACTIVE"
  check_logind_bus_health BEFORE_C4B_POLICY_RELOAD
  broker_pid_before="$(systemctl show --value -p MainPID dbus-broker.service)"
  [[ "$broker_pid_before" =~ ^[1-9][0-9]*$ &&
     -r "/proc/$broker_pid_before/stat" ]] ||
    fail "BOOTED_DBUS_BROKER_PID_UNAVAILABLE"
  # /proc/PID/stat field 22 (start ticks) is field 20 after the ')' comm field.
  broker_start_before="$(sed 's/^.*) //' "/proc/$broker_pid_before/stat" | awk '{print $20}')"
  [[ "$broker_start_before" =~ ^[1-9][0-9]*$ ]] ||
    fail "BOOTED_DBUS_BROKER_START_UNAVAILABLE"
  login_owner_before="$(timeout --signal=TERM --kill-after=2s 8s \
    busctl --system --timeout=5s call \
      org.freedesktop.DBus /org/freedesktop/DBus \
      org.freedesktop.DBus GetNameOwner s org.freedesktop.login1)" ||
    fail "LOGIND_OWNER_PRE_RELOAD_UNAVAILABLE"
  stage DBUS_POLICY_GRACEFUL_RELOAD_BEGIN
  # The signed D-Bus policy arrived through the OSTree deployment; the
  # first boot's broker may not have loaded the new policy. Reload config
  # without stopping the bus or disconnecting logind/systemd clients.
  timeout --signal=TERM --kill-after=5s 45s systemctl reload dbus-broker.service ||
    fail "GUEST_ONLY_DBUS_CONFIG_RELOAD_FAILED"
  broker_pid_after="$(systemctl show --value -p MainPID dbus-broker.service)"
  [[ "$broker_pid_after" == "$broker_pid_before" &&
     -r "/proc/$broker_pid_after/stat" ]] ||
    fail "DBUS_BROKER_REPLACED_DURING_CONFIG_RELOAD"
  broker_start_after="$(sed 's/^.*) //' "/proc/$broker_pid_after/stat" | awk '{print $20}')"
  [[ "$broker_start_after" == "$broker_start_before" ]] ||
    fail "DBUS_BROKER_IDENTITY_CHANGED_ON_CONFIG_RELOAD"
  login_owner_after="$(timeout --signal=TERM --kill-after=2s 8s \
    busctl --system --timeout=5s call \
      org.freedesktop.DBus /org/freedesktop/DBus \
      org.freedesktop.DBus GetNameOwner s org.freedesktop.login1)" ||
    fail "LOGIND_OWNER_POST_RELOAD_UNAVAILABLE"
  [[ "$login_owner_after" == "$login_owner_before" ]] ||
    fail "LOGIND_OWNER_CHANGED_DURING_CONFIG_RELOAD"
  check_logind_bus_health AFTER_C4B_POLICY_RELOAD
  echo "C4B_PASS // SIGNED_DBUS_POLICY_RELOADED_WITHOUT_SYSTEM_BUS_RESTART"
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
  # Exact owner-controlled C3b Silverblue-44 opt-in mode. The signed C3d
  # executable and its /opt interpreter shebang stay byte-for-byte unchanged.
  # C3b independently verifies the canonical /opt -> var/opt link, all
  # protected physical directories, SELinux, D-Bus and OS process identity.
  # Any rejection remains fatal. No synthetic candidate or copied policy.
  if ! GITHUB_ACTIONS=true POST_APOLLO_C3B_TEST_GUEST=1 POST_APOLLO_C4B_TEST_GUEST=1 \
      timeout --signal=TERM --kill-after=5s 60s \
        "$python" -I -B "$assets/C3bOriginCheck.py" --verify-disposable-silverblue-opt; then
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
# Supplemental OS-layout evidence only: C3b still refuses the /opt link.
# Do not normalize, alter or substitute any origin evidence.
try:
    link_target = os.readlink("/opt")
    resolved = os.path.realpath("/opt")
    print("C4B_DIAG_C3B_OPT_LINK // "
          f"target={link_target!r} resolved={resolved!r}", flush=True)
    for path in dict.fromkeys(("/var", "/var/opt", resolved)):
        try:
            target_info = os.lstat(path)
            print("C4B_DIAG_C3B_OPT_CHAIN // "
                  f"path={path!r} uid={target_info.st_uid} "
                  f"mode={stat.S_IMODE(target_info.st_mode):04o} "
                  f"directory={stat.S_ISDIR(target_info.st_mode)} "
                  f"symlink={stat.S_ISLNK(target_info.st_mode)}",
                  flush=True)
        except OSError as exc:
            print("C4B_DIAG_C3B_OPT_CHAIN_STAT_REFUSED // "
                  f"path={path!r} error={type(exc).__name__}",
                  flush=True)
except OSError as exc:
    print("C4B_DIAG_C3B_OPT_LINK_READ_REFUSED // "
          f"error={type(exc).__name__}", flush=True)

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
  stage SIGNED_C3D_RUNNING_HOST_MEASUREMENT_BEGIN
  # The signed RPM is copied by C4b's prelayer gate after C4a independently
  # verifies it. Reverify its signature and signed file digests HERE, while
  # the exact C3b-verified systemd/D-Bus service is alive. No new signer,
  # transport, witness authority or production grant is created.
  #
  # C4d: capture the REAL producer's exact stdout in a single disposable
  # root-only file at generation time. The later diagnostic relay no longer
  # relies on searching a shared runtime log that omitted the original
  # C4B_OBSERVED record during genuine two-boot CI.
  c4d_record_dir=/run/postapollo-c4d-observation
  [[ ! -e "$c4d_record_dir" && ! -L "$c4d_record_dir" ]] ||
    fail "C4D_PRODUCER_RECORD_DIRECTORY_PREEXISTS"
  install -d -m 0700 "$c4d_record_dir" ||
    fail "C4D_PRODUCER_PRIVATE_DIRECTORY_FAILED"
  [[ "$(stat -c '%u:%g:%a:%h' "$c4d_record_dir")" == "0:0:700:2" ||
     "$(stat -c '%u:%g:%a' "$c4d_record_dir")" == "0:0:700" ]] ||
    fail "C4D_PRODUCER_DIRECTORY_UNSAFE"
  c4d_record="$c4d_record_dir/observation.txt"
  umask 077
  # Capture the verifier's REAL stdout into the protected 0600 file
  # directly, using noclobber so neither a pre-existing path nor a symlink
  # can be overwritten. The old extra tee pipeline yielded an empty record
  # in the real guest. The later strictly validating relay, not this shell,
  # decides what diagnostic bytes may reach ttyS0. The verifier's exit code
  # remains authoritative; an empty capture cannot grant host trust.
  [[ ! -e "$c4d_record" && ! -L "$c4d_record" ]] ||
    fail "C4D_PRODUCER_RECORD_PREEXISTS"
  (
    set -C
    GITHUB_ACTIONS=true POST_APOLLO_C4B_TEST_GUEST=1 \
      timeout --signal=TERM --kill-after=5s 60s "$python" -I -B - \
        "$pid" "$assets/c3d-status.rpm" > "$c4d_record" <<'C4B_RUNNING_HOST_PROBE'
  ) || fail "SIGNED_C3D_RUNNING_HOST_MEASUREMENT_REFUSED"
import grp, hashlib, json, os, pwd, re, stat, subprocess, sys
from pathlib import Path

HOST = "/usr/libexec/post-apollo/connections-status-host"
UNIT = "postapollo-connections-status.service"
BUS = "org.postapollo.ConnectionsStatus1"
PKG = "postapollo-connections-c3d-ci-status"
INTERPRETER = "/opt/postapollo-c2o-venv/bin/python3"
KEYDB = "/var/lib/c4a-test-only-rpm-keyring"
FILES = {HOST: 0o555,
         "/usr/lib/systemd/system/" + UNIT: 0o644,
         "/usr/share/dbus-1/system.d/" + BUS + ".conf": 0o644}

class Refused(Exception): pass

def refuse(code): raise Refused(code)

def command(*args):
    try:
        p = subprocess.run(args, input=b"", capture_output=True, timeout=12)
    except (OSError, subprocess.TimeoutExpired):
        refuse("OBSERVATION_COMMAND_UNAVAILABLE")
    if p.returncode or len(p.stdout) + len(p.stderr) > 32768:
        refuse("OBSERVATION_COMMAND_REFUSED")
    return (p.stdout + p.stderr).decode("utf-8", "strict").strip()

def start(pid):
    try:
        ticks = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[19]
    except (OSError, IndexError):
        refuse("PROCESS_START_UNAVAILABLE")
    if not ticks.isdecimal() or int(ticks) <= 0:
        refuse("PROCESS_START_INVALID")
    return ticks

def hash_root_file(path, expected_mode, limit):
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != expected_mode
                or not 0 < st.st_size <= limit):
            refuse("SIGNED_FILE_UNSAFE")
        h = hashlib.sha256()
        counted = 0
        while True:
            block = os.read(fd, 65536)
            if not block: break
            counted += len(block)
            if counted > limit: refuse("SIGNED_FILE_OVERSIZE")
            h.update(block)
        after = os.fstat(fd)
        if (counted != st.st_size or
                (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            refuse("SIGNED_FILE_CHANGED")
        return h.hexdigest(), st.st_dev, st.st_ino
    except OSError:
        refuse("SIGNED_FILE_OPEN_REFUSED")
    finally:
        if fd is not None: os.close(fd)

def observe():
    if (os.geteuid() != 0 or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_C4B_TEST_GUEST") != "1"
            or not Path("/run/ostree-booted").exists()):
        refuse("DISPOSABLE_SILVERBLUE_SCOPE_REFUSED")
    if len(sys.argv) != 3 or not sys.argv[1].isdecimal():
        refuse("PROCESS_ID_ARGUMENT_REFUSED")
    pid = int(sys.argv[1])
    rpm = sys.argv[2]
    if (pid <= 1 or rpm != "/var/lib/c4b-runtime-assets/c3d-status.rpm"
            or not Path(KEYDB).is_dir()
            or stat.S_IMODE(os.stat(KEYDB).st_mode) != 0o700
            or os.stat(KEYDB).st_uid != 0):
        refuse("SIGNED_RPM_OR_KEYRING_SCOPE_REFUSED")
    if command("systemctl", "show", "--value", "-p", "MainPID", UNIT) != str(pid):
        refuse("SYSTEMD_MAINPID_CHANGED")
    tick = start(pid)
    uid = pwd.getpwnam("postapollo-connections").pw_uid
    gid = grp.getgrnam("postapollo-connections").gr_gid
    status = Path(f"/proc/{pid}/status").read_text()
    if uid <= 0 or gid <= 0 or not re.search(r"^NoNewPrivs:\s*1$", status, re.M):
        refuse("SERVICE_IDENTITY_OR_NO_NEW_PRIVILEGES_REFUSED")
    for field, expected in (("Uid", uid), ("Gid", gid)):
        line = re.search(r"^" + field + r":\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$", status, re.M)
        if not line or any(int(v) != expected for v in line.groups()):
            refuse("KERNEL_PROCESS_UID_GID_MISMATCH")
    if ":postapollo_connections_t:" not in Path(f"/proc/{pid}/attr/current").read_text():
        refuse("KERNEL_SELINUX_SERVICE_DOMAIN_MISMATCH")
    owner = command("busctl", "--system", "--timeout=5s", "call",
                    "org.freedesktop.DBus", "/org/freedesktop/DBus",
                    "org.freedesktop.DBus", "GetNameOwner", "s", BUS)
    m = re.fullmatch(r's "(:[0-9]+\.[0-9]+)"', owner)
    if not m: refuse("DBUS_UNIQUE_OWNER_UNAVAILABLE")
    unique = m.group(1)
    base = ("busctl", "--system", "--timeout=5s", "call",
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus")
    if (command(*base, "GetConnectionUnixProcessID", "s", unique) != f"u {pid}"
            or command(*base, "GetConnectionUnixUser", "s", unique) != f"u {uid}"):
        refuse("KERNEL_SYSTEMD_DBUS_PROCESS_MISMATCH")
    package_sha, _, _ = hash_root_file(rpm, 0o600, 4 * 1024 * 1024)
    signature = command("rpmkeys", "--dbpath", KEYDB, "--checksig", "-v", rpm)
    if (not re.search(r"(Signature|RSA|PGP|Header).*\bOK\b", signature, re.I)
            or re.search(r"NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD", signature, re.I)):
        refuse("SIGNED_RPM_SIGNATURE_REFUSED")
    if command("rpm", "-qp", "--qf", "%{NAME} %{VERSION} %{ARCH}", rpm) != (
            PKG + " 0.1 noarch"):
        refuse("SIGNED_RPM_PACKAGE_IDENTITY_REFUSED")
    items = command("rpm", "-qp", "--qf", "[%{FILENAMES}\t%{FILEDIGESTS}\n]", rpm)
    signed = {}
    for line in items.splitlines():
        entry = line.split("\t")
        if (len(entry) != 2 or entry[0] in signed or
                not re.fullmatch(r"[a-f0-9]{64}", entry[1])):
            refuse("SIGNED_RPM_SHA256_HEADER_REFUSED")
        signed[entry[0]] = entry[1]
    if set(signed) != set(FILES): refuse("SIGNED_RPM_MEMBER_SET_REFUSED")
    for name, mode in FILES.items():
        if command("rpm", "-qf", "--qf", "%{NAME}", name) != PKG:
            refuse("INSTALLED_FILE_RPM_OWNERSHIP_REFUSED")
        if hash_root_file(name, mode, 128 * 1024)[0] != signed[name]:
            refuse("INSTALLED_FILE_DIFFERS_FROM_SIGNED_RPM")
    script_sha = signed[HOST]
    if Path(HOST).open("rb").readline() != b"#!/opt/postapollo-c2o-venv/bin/python3\n":
        refuse("SIGNED_PYTHON_SCRIPT_SHEBANG_REFUSED")
    exe = os.stat(f"/proc/{pid}/exe")
    interpreter = os.stat(INTERPRETER)
    if (exe.st_dev, exe.st_ino) != (interpreter.st_dev, interpreter.st_ino):
        refuse("RUNNING_KERNEL_INTERPRETER_INODE_REFUSED")
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    args = raw[:-1].split(b"\0") if raw.endswith(b"\0") and len(raw) <= 4096 else []
    if (len(args) != 3 or os.fsdecode(args[1]) != HOST or args[2] != b"--read-only"
            or os.path.realpath(os.fsdecode(args[0])) != os.path.realpath(INTERPRETER)):
        refuse("RUNNING_SERVICE_INVOCATION_REFUSED")
    # The interpreter is /proc/PID/exe, NOT the Python script's signed bytes.
    h = hashlib.sha256()
    fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        fst = os.fstat(fd)
        if (fst.st_dev, fst.st_ino) != (exe.st_dev, exe.st_ino):
            refuse("INTERPRETER_OPEN_IDENTITY_REFUSED")
        size = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk: break
            size += len(chunk)
            if size > 128 * 1024 * 1024: refuse("INTERPRETER_SIZE_REFUSED")
            h.update(chunk)
        if size != fst.st_size: refuse("INTERPRETER_CHANGED_DURING_READ")
    finally:
        os.close(fd)
    if (start(pid) != tick or
            command("systemctl", "show", "--value", "-p", "MainPID", UNIT) != str(pid)
            or Path(f"/proc/{pid}/cmdline").read_bytes() != raw or
            hash_root_file(rpm, 0o600, 4 * 1024 * 1024)[0] != package_sha):
        refuse("SIGNED_SERVICE_CHANGED_DURING_OBSERVATION")
    return dict(schema="postapollo.connections.c4b-booted-signed-host-observation.v1",
                signed_rpm_sha256=package_sha, signed_script_sha256=script_sha,
                running_script_sha256=script_sha, interpreter_sha256=h.hexdigest(),
                service_pid=pid, dbus_owner_pid=pid, process_start_ticks=tick,
                service_uid=uid, service_gid=gid, systemd_unit=UNIT,
                selinux_enforcing=True, signedGuestOriginAuthenticated=False,
                evidenceCryptographicallyAttested=False, hostAuthenticated=False,
                canApprove=False, credentialActionsEnabled=False,
                productionAuthority=False)

try:
    print("C4B_OBSERVED // " + json.dumps(observe(), sort_keys=True, separators=(",", ":")),
          flush=True)
except (Refused, OSError, KeyError, ValueError, UnicodeError) as exc:
    print("C4B_MEASUREMENT_REFUSED // " +
          (str(exc) if isinstance(exc, Refused) else type(exc).__name__), flush=True)
    sys.exit(2)
C4B_RUNNING_HOST_PROBE
  # Status-only diagnostics, never echo the producer's unvalidated bytes.
  # Distinguish a genuinely empty stdout capture from later file replacement.
  if [[ -s "$c4d_record" ]]; then
    echo "C4D_PRODUCER_DIAG // DIRECT_STDOUT_CAPTURE_PRESENT"
  else
    echo "C4D_PRODUCER_DIAG // DIRECT_STDOUT_CAPTURE_EMPTY"
  fi
  echo "C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED"

  stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN
  timeout --signal=TERM --kill-after=5s 60s systemctl stop "$unit" ||
    fail "SERVICE_STOP_FAILED"
  check_released
  echo "C4B_PASS // SERVICE_STOP_RELEASES_DBUS_NAME"
  rm -f -- /var/lib/postapollo-c2r-ci-denied /opt/c4b/BusPolicyClient.py
  rmdir /opt/c4b || fail "CLIENT_DIRECTORY_CLEANUP_FAILED"
  [[ -d /opt/postapollo-c2o-venv ]] ||
    fail "OFFLINE_VENV_MISSING_AT_CLEANUP"
  # C4d test-only export bridge: the signed-process observer's exact stdout
  # was captured into a root-only /run file at generation time. The runtime
  # log can be incomplete; a missing/unsafe producer capture must be REFUSED.
  # Emit one validated diagnostic line into the runtime log before the isolated
  # Python is deleted; the unchanged controller relays its final log tail.
  # Serial I/O is strictly best effort and must NEVER grant host authority or
  # change the signed service's acceptance/rollback lifecycle.
  if [[ -c /dev/ttyS0 ]]; then
    timeout --signal=TERM --kill-after=1s 6s "$python" -I -B - \
      "$c4d_record" /dev/ttyS0 <<'C4B_SINGLE_UART_RELAY' || true
import json, os, re, select, stat, sys, time

PREFIX = b"C4B_OBSERVED // "
SCHEMA = "postapollo.connections.c4b-booted-signed-host-observation.v1"
FIELDS = frozenset((
    "schema", "signed_rpm_sha256", "signed_script_sha256",
    "running_script_sha256", "interpreter_sha256", "service_pid",
    "dbus_owner_pid", "process_start_ticks", "service_uid", "service_gid",
    "systemd_unit", "selinux_enforcing", "signedGuestOriginAuthenticated",
    "evidenceCryptographicallyAttested", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
))
FALSE = ("signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
         "hostAuthenticated", "canApprove", "credentialActionsEnabled",
         "productionAuthority")

def unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("GUEST_OBSERVATION_DUPLICATE_KEY")
        obj[k] = v
    return obj

def selected_line(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        # Report only symbolic predicate failures. Never dump process IDs,
        # UID values, file bytes, filenames or digests to the host console.
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("GUEST_RECORD_NOT_REGULAR")
        if st.st_uid != os.geteuid():
            raise ValueError("GUEST_RECORD_OWNER_MISMATCH")
        if st.st_nlink != 1:
            raise ValueError("GUEST_RECORD_LINK_COUNT_INVALID")
        if st.st_size <= 0:
            raise ValueError("GUEST_RECORD_EMPTY")
        if st.st_size > 2 * 1024 * 1024:
            raise ValueError("GUEST_RECORD_OVERSIZE")
        # The original signed-service record may be farther back than the
        # last 16 KiB after teardown. Read the whole bounded, verified inode
        # instead of silently discarding a valid earlier observation.
        log = os.read(fd, st.st_size + 1)
        after = os.fstat(fd)
        if (len(log) != st.st_size or
                (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("GUEST_LOG_CHANGED")
    finally:
        os.close(fd)
    matched = [x.rstrip(b"\r") for x in log.split(b"\n")
               if x.startswith(PREFIX)]
    if not matched:
        raise ValueError("GUEST_OBSERVATION_MISSING")
    if len(matched) != 1:
        raise ValueError("GUEST_OBSERVATION_DUPLICATE")
    if len(matched[0]) > 2048:
        raise ValueError("GUEST_OBSERVATION_OVERSIZE")
    line = matched[0]
    try:
        doc = json.loads(line[len(PREFIX):].decode("utf-8"), object_pairs_hook=unique)
    except json.JSONDecodeError:
        raise ValueError("GUEST_OBSERVATION_JSON_INVALID") from None
    if (type(doc) is not dict or set(doc) != FIELDS or doc["schema"] != SCHEMA
            or doc["systemd_unit"] != "postapollo-connections-status.service"
            or doc["selinux_enforcing"] is not True
            or any(doc[k] is not False for k in FALSE)
            or doc["signed_script_sha256"] != doc["running_script_sha256"]):
        raise ValueError("GUEST_OBSERVATION_SCHEMA_INVALID")
    for k in ("signed_rpm_sha256", "signed_script_sha256",
              "running_script_sha256", "interpreter_sha256"):
        if type(doc[k]) is not str or re.fullmatch("[0-9a-f]{64}", doc[k]) is None:
            raise ValueError("GUEST_OBSERVATION_DIGEST_INVALID")
    for k in ("service_pid", "dbus_owner_pid", "service_uid", "service_gid"):
        if type(doc[k]) is not int or not 0 < doc[k] < 2147483648:
            raise ValueError("GUEST_OBSERVATION_PROCESS_INVALID")
    if doc["service_pid"] != doc["dbus_owner_pid"]:
        raise ValueError("GUEST_OBSERVATION_DBUS_PID_MISMATCH")
    ticks = doc["process_start_ticks"]
    if (type(ticks) is not str or not 1 <= len(ticks) <= 24
            or not ticks.isascii() or not ticks.isdecimal()
            or int(ticks) < 1 or str(int(ticks)) != ticks):
        raise ValueError("GUEST_OBSERVATION_START_INVALID")
    return line

def write_all_serial(fd, payload):
    # A real UART opened O_NONBLOCK can accept only part of an observation.
    # Never confuse a short write with a complete validated host record.
    deadline = time.monotonic() + 4.0
    sent = 0
    while sent < len(payload):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise ValueError("UART_WRITE_TIMEOUT")
        try:
            written = os.write(fd, payload[sent:sent + 128])
        except BlockingIOError:
            continue
        if written <= 0:
            raise ValueError("UART_WRITE_ZERO")
        sent += written
    return sent

phase = "LOG_PREP"
try:
    payload = selected_line(sys.argv[1]) + b"\n"
    # C2v already safely forwards the last 110 runtime-log lines after the
    # whole first-boot C4b phase. Mirror ONE validated self-observation at
    # that point; its separate guest serial is diagnostic only, never authority.
    print(payload.decode("ascii").rstrip("\n"), flush=True)
    phase = "UART_OPEN"
    fd = os.open(sys.argv[2], os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK |
                 os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        if not stat.S_ISCHR(os.fstat(fd).st_mode):
            raise ValueError("UART_NOT_CHARACTER_DEVICE")
        phase = "UART_WRITE"
        if write_all_serial(fd, payload) != len(payload):
            raise ValueError("UART_WRITE_INCOMPLETE")
        print("C4D_UART_DIAG // ONE_VALID_RECORD_WRITTEN_TO_UART", flush=True)
    finally:
        os.close(fd)
except (OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
    # Only source-defined symbolic statuses cross the diagnostic UART.
    # Arbitrary OS / JSON exceptions or guest log bytes are NEVER printed.
    # These statuses are hints, not acceptance evidence or authorization.
    allowed = frozenset((
        "GUEST_OBSERVATION_DUPLICATE_KEY",
        "GUEST_RECORD_NOT_REGULAR", "GUEST_RECORD_OWNER_MISMATCH",
        "GUEST_RECORD_LINK_COUNT_INVALID", "GUEST_RECORD_EMPTY",
        "GUEST_RECORD_OVERSIZE", "GUEST_LOG_CHANGED",
        "GUEST_OBSERVATION_MISSING", "GUEST_OBSERVATION_DUPLICATE",
        "GUEST_OBSERVATION_OVERSIZE", "GUEST_OBSERVATION_JSON_INVALID",
        "GUEST_OBSERVATION_SCHEMA_INVALID",
        "GUEST_OBSERVATION_DIGEST_INVALID",
        "GUEST_OBSERVATION_PROCESS_INVALID",
        "GUEST_OBSERVATION_DBUS_PID_MISMATCH",
        "GUEST_OBSERVATION_START_INVALID",
        "UART_NOT_CHARACTER_DEVICE", "UART_WRITE_TIMEOUT",
        "UART_WRITE_ZERO", "UART_WRITE_INCOMPLETE",
    ))
    reason = str(exc) if type(exc) is ValueError else ""
    if reason not in allowed:
        reason = phase + "_REFUSED"
    print("C4D_UART_DIAG // " + reason, flush=True)
C4B_SINGLE_UART_RELAY
  fi
  # The only first-boot record is now consumed. Check its inode before
  # deletion; no artifacts persist into the second boot or production host.
  [[ -f "$c4d_record" && ! -L "$c4d_record" &&
     "$(stat -c '%u:%g:%a:%h' "$c4d_record")" == "0:0:600:1" ]] ||
    fail "C4D_PRODUCER_CAPTURE_UNSAFE_AT_CLEANUP"
  rm -f -- "$c4d_record"
  rmdir -- "$c4d_record_dir" ||
    fail "C4D_PRODUCER_PRIVATE_DIRECTORY_CLEANUP_FAILED"
  rm -rf -- /opt/postapollo-c2o-venv
  userdel c4b-reader && userdel c4b-outsider &&
    userdel postapollo-connections || fail "TEST_USER_REMOVAL_FAILED"
  # Fedora shadow-utils may automatically remove the user's matching
  # private primary group during userdel. This is already the desired
  # result, not a failed cleanup. Other test groups must still be removed
  # explicitly, and every user/group must be absent after these commands.
  groupdel c4b-clients || fail "CLIENT_GROUP_REMOVAL_FAILED"
  groupdel postapollo-status-readers || fail "READER_GROUP_REMOVAL_FAILED"
  if getent group postapollo-connections >/dev/null; then
    groupdel postapollo-connections || fail "SERVICE_GROUP_REMOVAL_FAILED"
  else
    echo "C4B_DIAG // SERVICE_PRIMARY_GROUP_ALREADY_ABSENT_AFTER_USERDEL"
  fi
  check_accounts_absent
  echo "C4B_PASS // TEST_USERS_AND_GROUPS_FULLY_ABSENT"
  # The custom policy is part of the booted deployment and MUST NOT be
  # removed at runtime. Only the real OSTree rollback may remove it.
  stage COMPOSED_POLICY_RETAINED_FOR_ROLLBACK
  timeout 15s semodule -l | grep -Fq postapollo_connections ||
    fail "COMPOSED_POLICY_VANISHED_PREMATURELY"
  check_accounts_absent
  check_released
  check_logind_bus_health AFTER_C4B_RUNTIME_CLEANUP
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
