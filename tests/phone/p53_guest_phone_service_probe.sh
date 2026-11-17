#!/usr/bin/bash
# P53 // Real installed signed PHONE STATUS-only service test in isolated
# offline Fedora Silverblue guest AFTER genuine rpm-ostree layered boot.
# This is not the operator's workstation, and not a C3e/C5 trust producer.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

pkg=post-apollo-phone-status-ci
unit=post-apollo-phone-personal-status-ci.service
name=postapollo-phone-status-ci
root=/run/postapollo-phone-status-test-only
marker="$root/explicit-test.marker"
launcher="$root/ci-python3"
socket=/run/postapollo-phone-status-ci/phone-personal-status-p47.sock
policy=/var/lib/postapollo-phone-ci-assets/postapollo_phone_ci.pp
dropin=/run/systemd/system/$unit.d
pid=0
user_created=0
policy_loaded=0
started=0

fail() {
  echo "P53_FAIL // PHONE_SERVICE_$1"
  exit 78
}
cleanup() {
  local rc=$?
  trap - EXIT ERR
  if (( started )); then
    timeout --signal=TERM --kill-after=2s 12s \
      systemctl stop "$unit" >/dev/null 2>&1 || true
  fi
  rm -f -- "$dropin/10-phone-ci-selinux.conf"
  rmdir -- "$dropin" >/dev/null 2>&1 || true
  systemctl daemon-reload >/dev/null 2>&1 || true
  if (( policy_loaded )); then
    timeout --signal=TERM --kill-after=4s 150s \
      semodule -r postapollo_phone_ci >/var/tmp/p53-selinux-unload.log 2>&1 ||
      { echo "P53_FAIL // POLICY_UNLOAD_REFUSED"; rc=78; }
  fi
  rm -f -- "$marker" "$launcher"
  rmdir -- "$root" >/dev/null 2>&1 || true
  if (( user_created )); then
    userdel "$name" >/dev/null 2>&1 ||
      { echo "P53_FAIL // TEMP_USER_DELETE_REFUSED"; rc=78; }
  fi
  if (( rc != 0 )); then echo "P53_FAIL // SERVICE_PROBE_EXIT_$rc"; fi
  exit "$rc"
}
trap cleanup EXIT

[[ -e /run/ostree-booted && "$(getenforce)" == Enforcing &&
   "$(cat /var/lib/postapollo-phone-ci-stage)" == layer_pending &&
   "$(rpm -q --qf '%{NAME}' "$pkg")" == "$pkg" ]] ||
  fail "NOT_LAYERED_ENFORCING_GUEST"
[[ ! -e "$root" && ! -e "$dropin" && ! -S "$socket" ]] ||
  fail "PREEXISTING_PRIVATE_PHONE_RUNTIME"
! getent passwd "$name" >/dev/null || fail "PREEXISTING_PHONE_STATUS_USER"
[[ -f "$policy" && ! -L "$policy" &&
   "$(stat -c '%u:%g:%a' "$policy")" == "0:0:600" ]] ||
  fail "OFFLINE_PHONE_SELINUX_POLICY_MISSING"

systemctl daemon-reload || fail "DAEMON_RELOAD"
systemctl start "$unit" || fail "UNIT_CONDITION_EVALUATION"
[[ "$(systemctl show "$unit" --property=MainPID --value)" == 0 &&
   "$(systemctl show "$unit" --property=ActiveState --value)" != active ]] ||
  fail "PHONE_SERVICE_ACTIVATED_WITHOUT_TEST_MARKER"
echo "P53_PASS // BOOTED_SIGNED_PHONE_UNIT_INERT_WITHOUT_TEST_MARKER"

! semodule -l | grep -Eq '^postapollo_phone_ci([[:space:]]|$)' ||
  fail "PHONE_SELINUX_TEST_MODULE_ALREADY_PRESENT"
echo "P53_STAGE // before_phone_selinux_install"
policy_rc=0
timeout --signal=TERM --kill-after=4s 150s semodule -i "$policy" \
  >/var/tmp/p53-selinux-load.log 2>&1 || policy_rc=$?
echo "P53_STAGE // after_phone_selinux_install rc=$policy_rc"
[[ "$policy_rc" == 0 ]] ||
  { sed -n '1,20p' /var/tmp/p53-selinux-load.log || true; fail "PHONE_SELINUX_MODULE_INSTALL"; }
policy_loaded=1
semodule -l | grep -Eq '^postapollo_phone_ci([[:space:]]|$)' ||
  fail "PHONE_SELINUX_MODULE_NOT_LOADED"
[[ "$(getenforce)" == Enforcing ]] || fail "SELINUX_NOT_ENFORCING"
echo "P53_PASS // DISTINCT_PHONE_SELINUX_TEST_DOMAIN_LOADED_ENFORCING"

useradd --system --no-create-home --home-dir /nonexistent \
  --shell /usr/sbin/nologin "$name" || fail "TEMP_USER_CREATE"
user_created=1
uid="$(id -u "$name")"
gid="$(id -g "$name")"
[[ "$uid" =~ ^[1-9][0-9]*$ && "$gid" =~ ^[1-9][0-9]*$ ]] ||
  fail "TEMP_USER_IS_ROOT"
install -d -m 0711 -o root -g root "$root"
printf 'P53 CI ONLY NO SAVE\n' > "$marker"
chmod 0600 "$marker"
install -m 0555 -o root -g root /usr/bin/python3 "$launcher"
cmp -s /usr/bin/python3 "$launcher" || fail "PYTHON_LAUNCHER_BYTE_DRIFT"
install -d -m 0700 -o "$uid" -g "$gid" /run/postapollo-phone-status-ci
chcon -t postapollo_phone_ci_run_t "$root" "$marker" /run/postapollo-phone-status-ci ||
  fail "PHONE_RUNTIME_CONTEXT"
chcon -t postapollo_phone_ci_exec_t "$launcher" ||
  fail "PHONE_PYTHON_EXEC_CONTEXT"
[[ "$(stat -c '%u:%g:%a' "$launcher")" == '0:0:555' ]] ||
  fail "PHONE_LAUNCHER_OWNER_MODE"
ls -Z "$launcher" | grep -Fq ':postapollo_phone_ci_exec_t:' ||
  fail "PHONE_LAUNCHER_SELINUX_TYPE"

mkdir -m 0755 "$dropin"
cat >"$dropin/10-phone-ci-selinux.conf" <<'PHONE_CI_OVERRIDE'
[Service]
ExecStart=
ExecStart=/run/postapollo-phone-status-test-only/ci-python3 -I -B /usr/libexec/post-apollo/phone/PhonePersonalStatusHostP49.py --private-status-dir /run/postapollo-phone-status-ci
PHONE_CI_OVERRIDE
chmod 0644 "$dropin/10-phone-ci-selinux.conf"
systemctl daemon-reload || fail "PHONE_OVERRIDE_RELOAD"
systemctl reset-failed "$unit" >/dev/null 2>&1 || true
systemctl start "$unit" || fail "CONFINED_PHONE_START"
started=1
for n in $(seq 1 60); do
  pid="$(systemctl show "$unit" --property=MainPID --value || echo 0)"
  [[ "$pid" =~ ^[1-9][0-9]+$ && -S "$socket" ]] && break
  sleep .2
done
[[ "$pid" =~ ^[1-9][0-9]+$ && -S "$socket" ]] ||
  { journalctl -b -u "$unit" -n 12 --no-pager -o cat || true; fail "PHONE_SOCKET_NOT_RUNNING"; }

actual_user="$(systemctl show "$unit" --property=User --value)"
actual_group="$(systemctl show "$unit" --property=Group --value)"
actual_cgroup="$(systemctl show "$unit" --property=ControlGroup --value)"
[[ "$actual_user" == "$name" && "$actual_group" == "$name" &&
   "$actual_cgroup" == "/system.slice/$unit" ]] ||
  fail "PHONE_SYSTEMD_MAINPID_OR_CGROUP_MISMATCH"
read -r u1 u2 u3 u4 < <(awk '/^Uid:/ {print $2,$3,$4,$5}' "/proc/$pid/status")
read -r g1 g2 g3 g4 < <(awk '/^Gid:/ {print $2,$3,$4,$5}' "/proc/$pid/status")
[[ "$u1:$u2:$u3:$u4" == "$uid:$uid:$uid:$uid" &&
   "$g1:$g2:$g3:$g4" == "$gid:$gid:$gid:$gid" &&
   "$(stat -c '%u:%g:%a' "$socket")" == "$uid:$gid:600" ]] ||
  fail "PHONE_KERNEL_UID_GID_OR_SOCKET_MODE"
lsm="$(cat "/proc/$pid/attr/current")"
[[ "$lsm" == "system_u:system_r:postapollo_phone_ci_t:s0" &&
   "$(getenforce)" == Enforcing ]] ||
  { echo "P53_STAGE // observed_selinux=$lsm"; fail "PHONE_DEDICATED_ENFORCING_DOMAIN_MISMATCH"; }
echo "P53_PASS // REAL_ENFORCING_PHONE_DOMAIN_AND_SYSTEMD_PROCESS_OBSERVED"

# Actual same-UID Linux client; P47 must still report zero authority.
runuser -u "$name" -- /usr/bin/python3 -I -B - <<'PY' ||
  fail "SAME_UID_PHONE_STATUS_DENIED"
import json, socket
path="/run/postapollo-phone-status-ci/phone-personal-status-p47.sock"
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
    conn.settimeout(3)
    conn.connect(path)
    conn.sendall(b'{"operation":"STATUS","schema":"post-apollo.phone.personal-host-status.p47.v1"}\n')
    response=json.loads(conn.recv(4096))
    assert response["status"] == "HOST_UNTRUSTED_STATUS_ONLY", response["status"]
    for name in ("installedIdentityVerified", "independentChallengeVerified",
                 "c5OneUseConsentVerified", "keyReadAuthorized", "productionEnabled",
                 "personalSaveAuthorized", "readbackTrusted", "retryAuthorized"):
        assert response[name] is False
PY
echo "P53_PASS // REAL_INSTALLED_PHONE_STATUS_RESPONSE_ALL_SAVE_FLAGS_FALSE"

# The root guest is a different real UID; even if DAC permits connecting,
# it must not obtain a valid STATUS or any private response.
python3 -I -B - <<'PY' || fail "CROSS_UID_PHONE_AUTHORITY"
import json, socket
path="/run/postapollo-phone-status-ci/phone-personal-status-p47.sock"
try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(3)
        conn.connect(path)
        conn.sendall(b'{"operation":"STATUS","schema":"post-apollo.phone.personal-host-status.p47.v1"}\n')
        out=json.loads(conn.recv(4096))
        assert out["status"] == "DENIED"
        assert out["personalSaveAuthorized"] is False
except (PermissionError, ConnectionRefusedError):
    # SELinux/DAC denial before socket acceptance is an even stricter refusal.
    pass
PY
echo "P53_PASS // CROSS_UID_HOST_ACCESS_REFUSED"

systemctl stop "$unit" || fail "STOP_PHONE_SERVICE"
started=0
for n in $(seq 1 30); do
  [[ ! -S "$socket" &&
     "$(systemctl show "$unit" --property=MainPID --value)" == 0 ]] && break
  sleep .2
done
[[ ! -S "$socket" &&
   "$(systemctl show "$unit" --property=MainPID --value)" == 0 ]] ||
  fail "SOCKET_OR_PID_REMAINS_AFTER_STOP"
cleanup
echo "P53_FAIL // UNREACHABLE_AFTER_CLEANUP"
