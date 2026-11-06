#!/usr/bin/bash
# C2q CI only: disposable Fedora Cloud guest with SELinux enforcing.
# This installs FAKE read-only service fixtures only inside the throwaway VM.
set -euo pipefail
unit=postapollo-connections-status.service
name=org.postapollo.ConnectionsStatus1
client=/root/c2q/BusPolicyClient.py
python=/opt/postapollo-c2o-venv/bin/python3

bad() {
  echo "C2R_FAIL // $*" >&2
  systemctl status "$unit" --no-pager -l 2>&1 | tail -n 35 || true
  journalctl -u "$unit" --no-pager -n 35 2>&1 || true
  exit 1
}
check() {
  local got
  got="$(runuser -u "$1" -- "$python" -I -B /opt/c2q/BusPolicyClient.py "$2")" \
    || bad "client invocation: user=$1 method=$2 response=$got"
  [[ "$got" == "$3" ]] || bad "user=$1 method=$2 expected=$3 got=$got"
}

echo "C2R_GUEST_OS // $(cat /etc/fedora-release)"
echo "C2R_GUEST_KERNEL // $(uname -r)"
[[ "$(getenforce)" == Enforcing ]] || bad "SELinux not Enforcing"
[[ "$(cat /sys/fs/selinux/enforce)" == 1 ]] || bad "SELinux kernel flag missing"
echo "C2R_PASS // REAL_GUEST_SELINUX_ENFORCING"

# Guest-only policy installation. No SELinux mode change and no permissive rule.
command -v semodule >/dev/null || bad "semodule unavailable in Fedora guest"
[[ -s /root/c2q/postapollo_connections.pp ]] || bad "missing compiled policy module"
semodule -i /root/c2q/postapollo_connections.pp || bad "SELinux module installation refused"
semodule -l | grep -Fq postapollo_connections || bad "custom policy module not loaded"
echo "C2R_PASS // CUSTOM_POLICY_MODULE_LOADED_WITH_ENFORCING_KERNEL"

# No persistent users, service, or OS changes outside this disposable guest.
groupadd --system postapollo-connections
groupadd --system postapollo-status-readers
groupadd --system c2q-test-clients
useradd --system --no-create-home --shell /usr/sbin/nologin \
  --gid postapollo-connections postapollo-connections
useradd --system --no-create-home --shell /usr/sbin/nologin \
  --gid c2q-test-clients --groups postapollo-status-readers c2q-reader
useradd --system --no-create-home --shell /usr/sbin/nologin \
  --gid c2q-test-clients c2q-outsider

# Offline install of a test-only pure Python wheel from the verified staging
# archive. No guest network and no package-server request.
python3 -m venv --without-pip /opt/postapollo-c2o-venv || bad "venv absent"
site="$("$python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
mkdir -p "$site"
"$python" -m zipfile -e /root/c2q/dbus_next.whl "$site"
"$python" -I -c 'import dbus_next; print("C2R_PYTHON_DBUS_PACKAGE_READY")' \
  || bad "offline dbus package unavailable"

install -D -o root -g root -m 0555 /root/c2q/FakeStatusHost.py \
  /usr/libexec/post-apollo/connections-status-host
install -D -o root -g root -m 0644 /root/c2q/status.service \
  /usr/lib/systemd/system/"$unit"
install -D -o root -g root -m 0644 /root/c2q/status.conf \
  /usr/share/dbus-1/system.d/"$name".conf
install -D -o root -g root -m 0644 /root/c2q/BusPolicyClient.py \
  /opt/c2q/BusPolicyClient.py
# World-readable dummy content; SELinux type, not Unix DAC, must deny it.
printf '%s\n' 'C2R_TEST_PUBLIC_DUMMY_NO_SECRETS' > /var/lib/postapollo-c2r-ci-denied
chmod 0644 /var/lib/postapollo-c2r-ci-denied
chcon -t shadow_t /var/lib/postapollo-c2r-ci-denied || bad "could not create shadow_t negative control"
[[ "$(stat -c %a /var/lib/postapollo-c2r-ci-denied)" == 644 ]] || bad "negative control not world readable"
echo "C2R_NEGATIVE_CONTROL // $(ls -Z /var/lib/postapollo-c2r-ci-denied)"

restorecon -F /usr/libexec/post-apollo/connections-status-host \
  /usr/lib/systemd/system/"$unit" \
  /usr/share/dbus-1/system.d/"$name".conf \
  /opt/c2q/BusPolicyClient.py \
  || bad "guest SELinux labels could not be restored"
label="$(ls -Z /usr/libexec/post-apollo/connections-status-host)"
[[ "$label" == *postapollo_connections_exec_t* ]] || bad "custom executable SELinux entrypoint label missing"
echo "C2R_PASS // DOMAIN_ENTRYPOINT_CUSTOM_LABEL_CONFIRMED"

# Hash check detects guest staging changes; this is NOT signed provenance.
sha256sum /root/c2q/FakeStatusHost.py /root/c2q/status.service \
  /root/c2q/status.conf /root/c2q/BusPolicyClient.py | \
  sed 's@/root/c2q/FakeStatusHost.py@/usr/libexec/post-apollo/connections-status-host@;
       s@/root/c2q/status.service@/usr/lib/systemd/system/postapollo-connections-status.service@;
       s@/root/c2q/status.conf@/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf@;
       s@/root/c2q/BusPolicyClient.py@/opt/c2q/BusPolicyClient.py@' \
  | sha256sum -c --status || bad "guest file hashes disagree"

for file in /usr/libexec/post-apollo/connections-status-host \
            /usr/lib/systemd/system/"$unit" \
            /usr/share/dbus-1/system.d/"$name".conf; do
  [[ "$(stat -c %u "$file")" == 0 ]] || bad "nonroot owner: $file"
  perm="$(stat -c %a "$file")"
  [[ $((8#$perm & 0022)) == 0 ]] || bad "group/other writable: $file"
  echo "C2R_FILE_CONTEXT // $(ls -Z "$file")"
done

systemctl daemon-reload
systemd-analyze verify "/usr/lib/systemd/system/$unit" || bad "systemd unit invalid"
[[ "$(systemctl is-enabled "$unit" 2>/dev/null || true)" == static ]] \
  || bad "unit unexpectedly enableable"
[[ "$(systemctl is-active "$unit" || true)" != active ]] \
  || bad "unit started without explicit action"

# Load the newly staged D-Bus policy before testing.
systemctl restart dbus-broker.service || bad "system bus policy reload failed"
busctl --system --no-pager list >/dev/null || bad "no guest system bus"
check c2q-reader claim OWN_REFUSED
check c2q-outsider claim OWN_REFUSED
echo "C2R_PASS // UNAUTHORIZED_NAME_OWNERS_DENIED"

systemctl start "$unit" || bad "enforcing SELinux refused service startup"
[[ "$(systemctl is-active "$unit")" == active ]] || bad "inactive service"
pid="$(systemctl show --value -p MainPID "$unit")"
[[ "$pid" =~ ^[1-9][0-9]*$ ]] || bad "no service PID"
[[ "$(ps -o user= -p "$pid" | xargs)" == postapollo-connections ]] \
  || bad "unexpected service Linux user"
grep -Eq '^NoNewPrivs:[[:space:]]*1$' "/proc/$pid/status" \
  || bad "NoNewPrivileges not applied"
context="$(cat "/proc/$pid/attr/current")"
echo "C2R_SERVICE_SELINUX_CONTEXT // $context"
[[ "$context" == *:postapollo_connections_t:* ]] || bad "SERVICE_NOT_CONFINED_IN_DEDICATED_SELINUX_DOMAIN"
journalctl -u "$unit" --no-pager | grep -Fq 'C2R_PASS // SELINUX_REFUSED_WORLD_READABLE_PROBE' \
  || bad "service did not prove SELinux denial of world-readable dummy file"
echo "C2R_PASS // DEDICATED_CONFINED_SERVICE_DOMAIN_AND_NEGATIVE_ACCESS_DENIAL"
[[ "$context" == *:*:*:* ]] || bad "service context not recorded"

check c2q-reader status OBSERVED_UNVERIFIED
check c2q-reader approve METHOD_REFUSED
check c2q-reader claim OWN_REFUSED
check c2q-outsider status METHOD_REFUSED
check c2q-outsider approve METHOD_REFUSED
check c2q-outsider claim OWN_REFUSED
echo "C2R_PASS // SYSTEMD_HOST_DBUS_UNDER_SELINUX_ENFORCING"

systemctl stop "$unit" || bad "service stop failed"
[[ "$(systemctl is-active "$unit" || true)" != active ]] \
  || bad "service remained active after stop"
if busctl --system --no-pager list | grep -Fq "$name"; then
  bad "D-Bus name persisted after service stop"
fi
echo "C2R_PASS // SERVICE_SHUTDOWN_RELEASES_DBUS_NAME"
echo "C2R_LIMITATION // CUSTOM_DOMAIN_EXPERIMENT_ONLY_NOT_SIGNED_PRODUCTION_PACKAGE"
echo "C2R_PASS // NO_CREDENTIALS_NO_NASA_NO_PRODUCTION_GRANTS"
