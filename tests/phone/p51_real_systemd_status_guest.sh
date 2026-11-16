#!/usr/bin/env bash
# P51: Actual disposable Linux systemd SOURCE-STAGED STATUS service.
# Intentionally NOT a signed Fedora RPM, installed production host or SAVE API.
set -Eeuo pipefail

if [[ "$(id -u)" != 0 || "$GITHUB_ACTIONS" != "true" ||
      "$RUNNER_ENVIRONMENT" != "github-hosted" || "$(uname -s)" != "Linux" ]]; then
  echo "P51_REFUSED // ONLY_ROOT_ON_DISPOSABLE_GITHUB_RUNNER" >&2
  exit 78
fi

user="postapollo-phone-status-ci"
unit="post-apollo-phone-personal-status-ci.service"
bundle="/usr/libexec/post-apollo/phone"
unit_target="/run/systemd/system/$unit"
marker_dir="/run/postapollo-phone-status-test-only"
marker="$marker_dir/explicit-test.marker"
sock="/run/postapollo-phone-status-ci/phone-personal-status-p47.sock"
worktree="$(pwd)"
origin="$worktree/services/phone"
observer="$origin/PhonePersonalSystemdOriginP51.py"

if [[ ! -f "$observer" || ! -f "$origin/PhonePersonalStatusHostP49.py" ||
      -e "$bundle" || -e "$unit_target" || -e "$marker_dir" ]] ||
      getent passwd "$user" >/dev/null ||
      getent group "$user" >/dev/null; then
  echo "P51_REFUSED // EXISTING_RESOURCES_OR_MISSING_SOURCE" >&2
  exit 78
fi
if [[ ! -x /usr/bin/systemctl || ! -x /usr/sbin/groupadd ||
      ! -x /usr/sbin/useradd || ! -x /usr/sbin/runuser ||
      ! -x /usr/bin/python3 ]]; then
  echo "P51_REFUSED // MISSING_OS_TOOLS" >&2
  exit 78
fi
if ! /usr/bin/systemctl --system is-system-running >/dev/null 2>&1; then
  # systemd may report "degraded" on disposable runner; verify via D-Bus.
  [[ "$(/usr/bin/systemctl --system show -p Version --value 2>/dev/null)" != "" ]] ||
    { echo "P51_REFUSED // NO_SUPERVISOR"; exit 78; }
fi

user_made=0
group_made=0
bundle_made=0
unit_made=0
marker_made=0

cleanup() {
  local prior=$?
  trap - EXIT
  if (( unit_made )); then
    /usr/bin/timeout 8s /usr/bin/systemctl --system stop "$unit" >/dev/null 2>&1 || true
    rm -f -- "$unit_target"
    /usr/bin/systemctl --system daemon-reload >/dev/null 2>&1 || true
  fi
  if (( marker_made )); then
    rm -f -- "$marker"
    rmdir -- "$marker_dir" >/dev/null 2>&1 || true
  fi
  if (( bundle_made )); then
    for name in PhonePersonalHostSocketP47.py PhonePersonalPeerEvidenceP48.py PhonePersonalStatusHostP49.py PhonePersonalInstalledReleaseP50.py; do
      rm -f -- "$bundle/$name"
    done
    rm -f -- "$bundle/systemd/$unit"
    rmdir -- "$bundle/systemd" >/dev/null 2>&1 || true
    rmdir -- "$bundle" >/dev/null 2>&1 || true
  fi
  if (( user_made )); then /usr/sbin/userdel "$user" >/dev/null 2>&1 || true; fi
  if (( group_made )); then /usr/sbin/groupdel "$user" >/dev/null 2>&1 || true; fi
  # Leave no running PHONE service on the CI runner.
  exit "$prior"
}
trap cleanup EXIT

/usr/sbin/groupadd --system "$user"
group_made=1
/usr/sbin/useradd --system --no-create-home --home-dir /nonexistent \
  --shell /usr/sbin/nologin --gid "$user" "$user"
user_made=1

/usr/bin/install -d -o root -g root -m 0555 "$bundle" "$bundle/systemd"
bundle_made=1
for name in PhonePersonalHostSocketP47.py PhonePersonalPeerEvidenceP48.py PhonePersonalStatusHostP49.py PhonePersonalInstalledReleaseP50.py; do
  /usr/bin/install -o root -g root -m 0555 "$origin/$name" "$bundle/$name"
done
/usr/bin/install -o root -g root -m 0644 \
  "$origin/systemd/$unit" "$bundle/systemd/$unit"
/usr/bin/install -o root -g root -m 0644 \
  "$origin/systemd/$unit" "$unit_target"
unit_made=1

/usr/bin/install -d -o root -g root -m 0700 "$marker_dir"
printf 'P51 STATUS TEST ONLY\n' >"$marker"
chmod 0600 "$marker"
marker_made=1

/usr/bin/systemctl --system daemon-reload
/usr/bin/systemctl --system start "$unit"
for attempt in $(seq 1 50); do
  if [[ -S "$sock" ]]; then break; fi
  if ! /usr/bin/systemctl --system is-active --quiet "$unit"; then
    echo "P51_REFUSED // SERVICE_EXITED" >&2
    exit 1
  fi
  sleep 0.1
done
[[ -S "$sock" ]] || { echo "P51_REFUSED // NO_REAL_SOCKET" >&2; exit 1; }

/usr/bin/python3 -I -B -c '
import sys
sys.path.insert(0, "services/phone")
import PhonePersonalSystemdOriginP51 as p
seen = p.observe_installed_status_candidate()
assert seen == p.OBSERVED, "real systemd/kernel candidate refused"
assert not any(seen[x] for x in (
    "installedHostVerified", "signedReleaseIndependentlyEnrolled",
    "selinuxEnforcingVerified", "logindSeatVerified",
    "c3eChallengeConsumed", "c5HumanConsentVerified",
    "keyReleaseAuthorized", "personalSaveAuthorized"))
print("P51_PASS // REAL_SYSTEMD_CANDIDATE_OBSERVED_NO_TRUST")
'

# Actual client under the dedicated service UID should get STATUS only.
/usr/sbin/runuser -u "$user" -- /usr/bin/python3 -I -B -c '
import json, socket
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.settimeout(2)
s.connect("/run/postapollo-phone-status-ci/phone-personal-status-p47.sock")
s.sendall(b"{\"operation\":\"STATUS\",\"schema\":\"post-apollo.phone.personal-host-status.p47.v1\"}\n")
data=s.recv(2048)
s.close()
j=json.loads(data)
assert j["status"]=="HOST_UNTRUSTED_STATUS_ONLY"
assert j["personalSaveAuthorized"] is False
assert j["keyReadAuthorized"] is False
'

# A different UID can neither claim STATUS authority nor read private socket.
# Root can pass DAC but P47 checks real SO_PEERCRED and must DENY.
 /usr/bin/python3 -I -B -c '
import json, socket
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.settimeout(2)
s.connect("/run/postapollo-phone-status-ci/phone-personal-status-p47.sock")
s.sendall(b"{\"operation\":\"STATUS\",\"schema\":\"post-apollo.phone.personal-host-status.p47.v1\"}\n")
data=s.recv(2048)
s.close()
j=json.loads(data)
assert j["status"]=="DENIED"
assert j["personalSaveAuthorized"] is False
'

# A running unit with a changed source file must fail the observer, without
# pretending that a process already loaded into memory was automatically safe.
chmod 0755 "$bundle/PhonePersonalStatusHostP49.py"
/usr/bin/python3 -I -B -c '
import sys
sys.path.insert(0, "services/phone")
import PhonePersonalSystemdOriginP51 as p
assert p.observe_installed_status_candidate() == p.REFUSED
'
chmod 0555 "$bundle/PhonePersonalStatusHostP49.py"

/usr/bin/python3 -I -B -c '
import sys
sys.path.insert(0, "services/phone")
import PhonePersonalSystemdOriginP51 as p
assert p.observe_installed_status_candidate() == p.OBSERVED
'
/usr/bin/systemctl --system stop "$unit"
[[ ! -e "$sock" ]] || { echo "P51_REFUSED // SOCKET_LEFT_BEHIND"; exit 1; }
/usr/bin/python3 -I -B -c '
import sys
sys.path.insert(0, "services/phone")
import PhonePersonalSystemdOriginP51 as p
assert p.observe_installed_status_candidate() == p.REFUSED
'
echo "P51_PASS // STOP_CLEANUP_CONFIRMED_AND_AUTHORITY_FALSE"
