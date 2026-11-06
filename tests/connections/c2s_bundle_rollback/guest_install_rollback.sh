#!/usr/bin/bash
# C2s disposable Fedora guest only. Test-only package fixture, not RPM/release.
# Nothing here is run on the user's computer.
set -Eeuo pipefail
fail() { printf 'C2S_FAIL // %s\n' "$*" >&2; exit 1; }
unit=postapollo-connections-status.service
name=org.postapollo.ConnectionsStatus1
host=/usr/libexec/post-apollo/connections-status-host
unit_path=/usr/lib/systemd/system/$unit
policy_path=/usr/share/dbus-1/system.d/$name.conf

[[ "$(getenforce)" == Enforcing ]] || fail "SELinux not enforcing"
[[ "$(cat /sys/fs/selinux/enforce)" == 1 ]] || fail "guest kernel is not enforcing"
[[ ! -e "$host" && ! -e "$unit_path" && ! -e "$policy_path" ]] ||
    fail "guest was not clean before package test"
if semodule -l | grep -Fq postapollo_connections; then
    fail "custom SELinux module preinstalled"
fi
if getent passwd postapollo-connections >/dev/null; then
    fail "service account preinstalled"
fi
[[ "$(ls /sys/class/net | tr '\n' ' ')" == "lo " ]] ||
    fail "guest should have no network interface other than lo"
echo "C2S_PASS // OFFLINE_GUEST_CLEAN_INSTALL_BASELINE"

# Verify the archive against an external checksum, and the manifest inside it
# before performing a single OS/account/policy write.
cd /root/c2s
sha256sum --check --status bundle.sha256 ||
    fail "bundle integrity check failed"
expect="$(printf '%s\n' BusPolicyClient.py FakeStatusHost.py SHA256SUMS \
    dbus_next.whl postapollo_connections.pp status.conf status.service | sort)"
got="$(tar -tzf bundle.tar.gz | sort)" || fail "archive listing error"
[[ "$got" == "$expect" ]] ||
    fail "unexpected bundle path, directory, executable, link or missing file"
# Archive entries are restricted to seven flat known file names, no directories.
echo "C2S_PASS // ALLOWLISTED_BUNDLE_SHA256_VERIFIED"

# Negative test: a changed archive must fail BEFORE any service files exist.
mkdir -m 0700 /root/c2s/forged
cp bundle.tar.gz /root/c2s/forged/bundle.tar.gz
cp bundle.sha256 /root/c2s/forged/bundle.sha256
printf 'X' | dd of=/root/c2s/forged/bundle.tar.gz bs=1 seek=0 conv=notrunc status=none
if (cd /root/c2s/forged && sha256sum --check --status bundle.sha256); then
    fail "tampered package was accepted"
fi
[[ ! -e "$host" && ! -e "$unit_path" && ! -e "$policy_path" ]] ||
    fail "tamper test modified the guest"
echo "C2S_PASS // TAMPERED_PACKAGE_REFUSED_BEFORE_INSTALL"

mkdir -m 0700 /root/c2q
tar -xzf /root/c2s/bundle.tar.gz -C /root/c2q --no-same-owner ||
    fail "fixture extraction failed"
(cd /root/c2q && sha256sum --check --status SHA256SUMS) ||
    fail "internal file digest mismatch"
echo "C2S_PASS // INTERNAL_CONTENT_DIGESTS_VERIFIED"

# The C2r test is the install/start/permission/stop sequence. Reuse the
# already-reviewed exact code instead of creating a second implementation.
bash /root/c2s/c2r-guest-smoke.sh ||
    fail "C2r confined-service regression failed"

[[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
    fail "host still active before rollback"
echo "C2S_PASS // EXPLICIT_START_ONLY_AND_SHUTDOWN"

# Rollback *only* the known synthetic files/accounts/policy in this VM.
# There is no user task source, keyring, password or provider connection.
systemctl stop "$unit" >/dev/null 2>&1 || true
rm -f "$host" "$unit_path" "$policy_path" /opt/c2q/BusPolicyClient.py \
    /var/lib/postapollo-c2r-ci-denied
semodule -r postapollo_connections ||
    fail "custom SELinux policy module removal failed"
systemctl daemon-reload
systemctl restart dbus-broker.service ||
    fail "system D-Bus reload after rollback failed"
rm -rf /opt/postapollo-c2o-venv /opt/c2q
for u in c2q-reader c2q-outsider postapollo-connections; do
    userdel "$u" || fail "failed to remove disposable $u account"
done
for g in c2q-test-clients postapollo-status-readers postapollo-connections; do
    groupdel "$g" || fail "failed to remove disposable $g group"
done

[[ ! -e "$host" && ! -e "$unit_path" && ! -e "$policy_path" ]] ||
    fail "service files remained after rollback"
if semodule -l | grep -Fq postapollo_connections; then
    fail "SELinux module persisted after rollback"
fi
for u in postapollo-connections c2q-reader c2q-outsider; do
    if getent passwd "$u" >/dev/null; then fail "account $u remained"; fi
done
for g in postapollo-connections postapollo-status-readers c2q-test-clients; do
    if getent group "$g" >/dev/null; then fail "group $g remained"; fi
done
if busctl --system --no-pager list | grep -Fq "$name"; then
    fail "D-Bus name still owned after rollback"
fi
[[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
    fail "service still active after rollback"
[[ "$(getenforce)" == Enforcing ]] ||
    fail "SELinux was weakened during test"
[[ "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
    fail "kernel enforcement changed"
echo "C2S_PASS // ROLLBACK_REMOVED_SERVICE_POLICY_USERS_AND_BUS_NAME"
echo "C2S_PASS // ENFORCING_SELINUX_PRESERVED_AND_NO_GUEST_NETWORK"
echo "C2S_LIMITATION // UNSIGNED_TEST_BUNDLE_NO_RPM_TRANSACTION_NO_PRODUCTION_AUTH"
echo "C2S_PASS // NO_KEYRING_NO_CREDENTIALS_NO_REAL_PROVIDER_GRANTS"
