#!/usr/bin/bash
# C2o CI ONLY: runs as root inside ephemeral Fedora systemd container.
# No real connections broker, credentials, NASA traffic, or host installation.
set -euo pipefail

UNIT=postapollo-connections-status.service
NAME=org.postapollo.ConnectionsStatus1
PY=/opt/postapollo-c2o-venv/bin/python3
CLIENT=/opt/c2o/BusPolicyClient.py

die() { echo "C2O_FAIL // $*" >&2; exit 1; }
client() { runuser -u "$1" -- "$PY" -I -B "$CLIENT" "$2"; }
expect() {
  local got
  got="$(client "$1" "$2")" || die "client failed: $1 $2 => $got"
  [[ "$got" == "$3" ]] || die "expected $3, got $got ($1 $2)"
}

echo "C2O_FEDORA_VERSION // $(cat /etc/fedora-release)"
echo "C2O_SYSTEMD_VERSION // $(systemctl --version | head -1)"

# Root-owned fixture+policy are a disposable package imitation, NOT proof of
# a protected deployable package on the operator's workstation.
for file in /usr/lib/systemd/system/$UNIT \
  /usr/share/dbus-1/system.d/$NAME.conf \
  /usr/libexec/post-apollo/connections-status-host; do
  [[ "$(stat -c %u "$file")" == 0 ]] || die "non-root owner: $file"
  [[ $(( 8#$(stat -c %a "$file") & 0022 )) == 0 ]] || die "group/other writable: $file"
done

# This is a real Fedora systemd unit syntax check, not service-start proof.
systemd-analyze verify "/usr/lib/systemd/system/$UNIT" || die "systemd unit invalid"

# The template has no Install stanza, should not be enabled/autostarted.
[[ "$(systemctl is-enabled "$UNIT" 2>/dev/null || true)" == "static" ]] \
  || die "status host unexpectedly enabled or installable"
[[ "$(systemctl is-active "$UNIT" || true)" != "active" ]] \
  || die "unexpected automatic service start"

# Fedora's actual system bus and installed policy (not a synthesized Ubuntu
# policy-only daemon) are exercised by the calls below.
systemctl start dbus.socket || die "Fedora bus socket unavailable"
for i in $(seq 1 25); do
  if busctl --system --no-pager list >/dev/null 2>&1; then break; fi
  sleep 0.3
done
busctl --system --no-pager list >/dev/null || die "system bus missing"

# Inactive service cannot be claimed by a reader/outsider.
expect c2o-reader claim OWN_REFUSED
expect c2o-outsider claim OWN_REFUSED

# Explicit start is the only route in this CI fixture.
systemctl start "$UNIT" || {
  systemctl --no-pager --full status "$UNIT" || true
  journalctl -u "$UNIT" --no-pager -n 70 || true
  die "systemd refused status host"
}
[[ "$(systemctl is-active "$UNIT")" == "active" ]] || die "service not active"

pid="$(systemctl show --value -p MainPID "$UNIT")"
[[ "$pid" =~ ^[1-9][0-9]*$ ]] || die "no real host PID"
user="$(ps -o user= -p "$pid" | xargs)"
[[ "$user" == "postapollo-connections" ]] || die "wrong host principal: $user"
grep -Eq '^NoNewPrivs:[[:space:]]*1$' "/proc/$pid/status" \
  || die "systemd did not apply NoNewPrivileges"

expect c2o-reader status OBSERVED_UNVERIFIED
expect c2o-reader approve METHOD_REFUSED
expect c2o-reader claim OWN_REFUSED
expect c2o-outsider status METHOD_REFUSED
expect c2o-outsider approve METHOD_REFUSED
expect c2o-outsider claim OWN_REFUSED

echo "C2O_PASS // FEDORA_SYSTEMD_STARTED_STATIC_SERVICE_SEPARATE_UID"
echo "C2O_PASS // ROOT_OWNED_FILES_AND_BUS_POLICY_ENFORCED"

systemctl stop "$UNIT" || die "service did not stop"
[[ "$(systemctl is-active "$UNIT" || true)" != "active" ]] || die "service persisted"
# Prevent false success from a stale bus name.
if busctl --system --no-pager list | grep -Fq "$NAME"; then
  die "service bus name survived stop"
fi
echo "C2O_PASS // EXPLICIT_STOP_RELEASES_BUS_NAME"

# A Docker container on an Ubuntu runner typically lacks an enforcing
# SELinux host kernel. Report the actual state, never claim enforcement.
if command -v getenforce >/dev/null 2>&1; then
  state="$(getenforce 2>/dev/null || true)"
else
  state="UNKNOWN"
fi
if [[ "$state" == Enforcing ]]; then
  echo "C2O_SELINUX_CONTAINER_ENFORCING // LABEL_AND_AVC_REVIEW_STILL_REQUIRED"
else
  echo "C2O_SELINUX_NOT_VERIFIED // getenforce=$state"
fi
echo "C2O_PASS // NO_CREDENTIALS_NO_NASA_AND_NO_DESKTOP_CHANGES"
