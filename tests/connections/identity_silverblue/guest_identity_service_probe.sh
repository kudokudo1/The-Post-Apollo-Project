#!/usr/bin/bash
# C4b Identity Silverblue: disposable *running* installed gateway probe.
# Runs only INSIDE the actual offline official Silverblue VM, after the signed
# RPM and installed-file checks. No operator desktop or production credentials.
set -Eeuo pipefail
[[ "$(id -u)" == 0 && -e /run/ostree-booted &&
   "$(getenforce)" == Enforcing && -f /var/lib/postapollo-id-ci-stage &&
   "$(cat /var/lib/postapollo-id-ci-stage)" == layer_pending ]] ||
  { echo "C4B_ID_FAIL // IDENTITY_SERVICE_PROBE_WRONG_GUEST_OR_STAGE"; exit 2; }

pkg=post-apollo-identity-silverblue-ci
unit=post-apollo-identity-silverblue-ci.service
name=postapollo-identity-ci
base=/run/postapollo-identity-silverblue-ci-only
runtime=$base/native
signer=$base/signer.ed25519
socket=$runtime/identity-command-v0.sock
pid=0
user_created=0

cleanup() {
  # Never preserve user, runtime or ephemeral private signing key into rollback.
  timeout --signal=TERM --kill-after=2s 12s systemctl stop "$unit" >/dev/null 2>&1 || true
  rm -rf -- "$base"
  if [[ "$user_created" == 1 ]]; then
    userdel "$name" >/dev/null 2>&1 || true
  fi
  systemctl reset-failed "$unit" >/dev/null 2>&1 || true
}
trap cleanup EXIT
fail() {
  echo "C4B_ID_FAIL // IDENTITY_SERVICE_$1"
  journalctl -b -u "$unit" --no-pager -n 24 2>&1 |
    sed -E 's/^/C4B_ID_SERVICE_JOURNAL \/\//g' | head -n 24 || true
  exit 2
}

[[ "$(rpm -q --qf '%{NAME}' "$pkg")" == "$pkg" &&
    ! -e "$base" && ! -S "$socket" ]] ||
  fail "PREREQUISITES_OR_PREEXISTING_RUNTIME"
if getent passwd "$name" >/dev/null; then
  fail "NON_DISPOSABLE_USER_PREEXISTS"
fi

# Explicitly probe the unit's negative activation condition in the real guest.
systemctl daemon-reload || fail "DAEMON_RELOAD_DENIED"
timeout --signal=TERM --kill-after=2s 12s systemctl start "$unit" ||
  fail "MISSING_MARKER_SYSTEMCTL_UNEXPECTED_ERROR"
pre_pid="$(systemctl show "$unit" --property=MainPID --value)"
pre_active="$(systemctl show "$unit" --property=ActiveState --value)"
[[ "$pre_pid" == 0 && "$pre_active" != active ]] ||
  fail "UNIT_ACTIVATED_WITHOUT_CI_MARKER"
echo "C4B_ID_PASS // REAL_SYSTEMD_UNIT_REFUSED_WITHOUT_MARKER"

# This fixture requires Fedora's system Python Ed25519 support. Never pip
# install a mutable dependency into the offline guest or weaken import pins.
if ! /usr/bin/python3 -I -B -c 'from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey'; then
  fail "OS_PINNED_ED25519_PYTHON_DEPENDENCY_ABSENT"
fi
useradd --system --no-create-home --home-dir /nonexistent \
  --shell /usr/sbin/nologin "$name" || fail "CI_SYSTEM_USER_CREATE"
user_created=1
uid="$(id -u "$name")"
gid="$(id -g "$name")"
[[ "$uid" =~ ^[1-9][0-9]*$ && "$gid" =~ ^[1-9][0-9]*$ ]] ||
  fail "NONROOT_SERVICE_IDENTITY_INVALID"

mkdir -m 0711 "$base"
mkdir -m 0700 "$runtime"
chown "$uid:$gid" "$runtime"
chmod 0700 "$runtime"
# An ephemeral random 32-byte Ed25519 seed; not a production receipt signer.
# Use no network, persistent host key, real provider account or C5 approval.
python3 -I -B - "$signer" <<'PY'
import os,sys
fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
    os.write(fd,os.urandom(32))
finally:
    os.close(fd)
PY
chown "$uid:$gid" "$signer"
chmod 0600 "$signer"
printf '%s\n' \
  "POST_APOLLO_ID_CI_RUNTIME=$runtime" \
  "POST_APOLLO_ID_CI_SIGNING_KEY=$signer" >"$base/runtime.env"
chmod 0600 "$base/runtime.env"
printf '%s\n' 'CI-ONLY-SUPERVISED-NATIVE-IDENTITY-GATE' >"$base/authorized-test.marker"
chmod 0444 "$base/authorized-test.marker"
chown root:root "$base" "$base/runtime.env" "$base/authorized-test.marker"
chmod 0711 "$base"

systemctl reset-failed "$unit" >/dev/null 2>&1 || true
timeout --signal=TERM --kill-after=2s 12s systemctl start "$unit" ||
  fail "ACTUAL_SIGNED_INSTALLED_SERVICE_START_REFUSED"
for i in $(seq 1 70); do
  pid="$(systemctl show "$unit" --property=MainPID --value || echo 0)"
  if [[ "$pid" =~ ^[1-9][0-9]+$ && -S "$socket" ]]; then break; fi
  sleep .2
done
[[ "$pid" =~ ^[1-9][0-9]+$ && -S "$socket" ]] ||
  fail "ACTUAL_SIGNED_INSTALLED_SERVICE_SOCKET_UNAVAILABLE"
active="$(systemctl show "$unit" --property=ActiveState --value)"
identity_user="$(systemctl show "$unit" --property=User --value)"
cgroup="$(systemctl show "$unit" --property=ControlGroup --value)"
[[ "$active" == active && "$identity_user" == "$name" &&
   "$cgroup" == "/system.slice/$unit" ]] ||
  fail "SUPERVISOR_IDENTITY_MISMATCH"
[[ "$(stat -c '%u:%g:%a' "$socket")" == "$uid:$gid:600" ]] ||
  fail "KERNEL_SOCKET_OWNERSHIP_OR_MODE_MISMATCH"
read -r u1 u2 u3 u4 < <(awk '/^Uid:/ {print $2,$3,$4,$5}' "/proc/$pid/status")
read -r g1 g2 g3 g4 < <(awk '/^Gid:/ {print $2,$3,$4,$5}' "/proc/$pid/status")
[[ "$u1:$u2:$u3:$u4" == "$uid:$uid:$uid:$uid" &&
   "$g1:$g2:$g3:$g4" == "$gid:$gid:$gid:$gid" ]] ||
  fail "KERNEL_PROCESS_UID_GID_MISMATCH"
tr '\0' ' ' <"/proc/$pid/cmdline" |
  grep -Fq '/usr/libexec/post-apollo/identity/identity-gateway-ci' ||
  fail "KERNEL_PROCESS_COMMAND_MISMATCH"
selinux="$(cat "/proc/$pid/attr/current")"
[[ -n "$selinux" && "$selinux" != "unconfined_t" ]] ||
  fail "KERNEL_SELINUX_CONTEXT_MISSING"
printf 'C4B_ID_SERVICE_OBSERVED // pid=%s uid=%s gid=%s cgroup=%s selinux=%s\n' \
  "$pid" "$uid" "$gid" "$cgroup" "$selinux"
echo "C4B_ID_PASS // REAL_SYSTEMD_IDENTITY_GATEWAY_SOCKET_AND_PROCESS_OBSERVED"

# The real installed gateway, not an imitation server, must sign four
# UNAVAILABLE receipts. The verifier sees the disposable signer public key
# from its own test-only seed; this is NOT independently enrolled host trust.
python3 -I -B - "$socket" "$signer" <<'PY'
import secrets,socket,sys
from pathlib import Path
sys.path.insert(0,"/usr/libexec/post-apollo/identity")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from signed_command_receipt_v0 import build_request,verify_receipt
key=Ed25519PrivateKey.from_private_bytes(Path(sys.argv[2]).read_bytes()).public_key()
for action in ("BEGIN","STATUS","CANCEL","RECOVER"):
    nonce=secrets.token_urlsafe(32)
    rid=None if action=="BEGIN" else "CI_NO_LOGIN_REQUEST_01234567"
    request=build_request(action,rid,nonce)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
        conn.settimeout(3)
        conn.connect(sys.argv[1])
        conn.sendall(request)
        out=b""
        while not out.endswith(b"\n"):
            fragment=conn.recv(1024)
            if not fragment:break
            out+=fragment
            if len(out)>1024:raise RuntimeError("oversize signed receipt")
    receipt=verify_receipt(out,pinned_key=key,action=action,
                           command_request_id=rid,client_nonce=nonce)
    if receipt["state"]!="UNAVAILABLE" or receipt["requestId"] is not None:
        raise RuntimeError("identity command was not denied")
    print(f"C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_{action}")
PY
if [[ -e "$runtime/identity-display-v0.sock" ]]; then
  fail "UNAPPROVED_BROWSER_HOST_SOCKET_EXISTS"
fi

# Verify teardown of the *running* service before rpm-ostree rollback.
systemctl stop "$unit" || fail "SERVICE_STOP_REFUSED"
for i in $(seq 1 30); do
  [[ ! -S "$socket" && "$(systemctl show "$unit" --property=MainPID --value)" == 0 ]] && break
  sleep .2
done
[[ ! -S "$socket" && "$(systemctl show "$unit" --property=MainPID --value)" == 0 ]] ||
  fail "SOCKET_OR_PROCESS_REMAINS_AFTER_STOP"
cleanup
trap - EXIT
[[ ! -e "$base" ]] && ! getent passwd "$name" >/dev/null ||
  fail "TEMPORARY_USER_OR_PRIVATE_KEY_REMAINS"
echo "C4B_ID_PASS // REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP"
echo "C4B_ID_LIMITATION // NO_PRODUCTION_RELEASE_ENROLLMENT_OR_C5_OPERATOR_CONSENT"
