#!/usr/bin/bash
# Fedora 44 Cloud VM ONLY. RPM signing key is ephemeral, self-signed and
# imported ONLY to this throwaway VM. No service activation or real provider.
set -Eeuo pipefail
fail() { echo "C2T_FAIL // $*" >&2; exit 1; }
pkg=postapollo-connections-c2t-fixture
path=/usr/share/post-apollo/c2t-fixture
cd /root/c2t

[[ "$(getenforce)" == Enforcing && "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
  fail "Fedora guest kernel must enforce SELinux"
grep -Fq "Fedora release 44" /etc/fedora-release || fail "wrong Fedora version"
[[ "$(ls /sys/class/net | tr '\n' ' ')" == "lo " ]] || fail "guest is not offline"
[[ ! -e "$path" ]] || fail "fixture path unexpectedly present"
rpm -q "$pkg" >/dev/null 2>&1 && fail "package already installed"
[[ ! -e /usr/libexec/post-apollo/connections-status-host ]] ||
  fail "real service executable is unexpectedly installed"
[[ ! -e /usr/lib/systemd/system/postapollo-connections-status.service ]] ||
  fail "real systemd unit is unexpectedly installed"
[[ ! -e /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf ]] ||
  fail "real D-Bus policy is unexpectedly installed"
echo "C2T_PASS // CLEAN_ENFORCING_OFFLINE_GUEST_NO_LIVE_SERVICE"

sha256sum --check --status c2t-artifact-manifest.sha256 ||
  fail "RPM/pubkey input manifest mismatch"
[[ "$(grep -c '^' c2t-public-fingerprint.txt)" == 1 ]] ||
  fail "invalid public key fingerprint count"
echo "C2T_PASS // EXTERNAL_RPM_AND_PUBLIC_KEY_DIGESTS"

# The package's embedded RPM signature must be UNKNOWN before our test key
# is trusted. Do not mistake an untrusted signature for genuine provenance.
output="$(rpmkeys --checksig -v c2t-0.1.rpm 2>&1)" || true
printf 'C2T_UNTRUSTED_SIGNATURE_CHECK // %s\n' "$output"
printf '%s\n' "$output" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
  fail "test RPM was unexpectedly trusted before importing disposable public key"
echo "C2T_PASS // SIGNER_NOT_TRUSTED_BY_DEFAULT"

# Corrupt an RPM *before* any package installation or trusted key import.
cp c2t-0.1.rpm c2t-tampered.rpm
printf 'X' | dd of=c2t-tampered.rpm bs=1 seek=0 conv=notrunc status=none
if sha256sum -c --status <(
  sed 's/c2t-0.1.rpm/c2t-tampered.rpm/' c2t-artifact-manifest.sha256 |
  grep c2t-tampered.rpm
); then
  fail "tampered RPM passed pinned digest"
fi
if rpm -q "$pkg" >/dev/null 2>&1; then fail "tamper test installed RPM"; fi
echo "C2T_PASS // TAMPERED_RPM_REFUSED_BEFORE_MUTATION"

rpm -qa 'gpg-pubkey*' | sort > /root/c2t/keys-before.txt
rpm --import c2t-disposable-public.asc ||
  fail "could not import temporary CI signing public key into VM"
for ver in 0.1 0.2; do
  # Actual native RPM OpenPGP signature, not only SHA-256 manifest.
  output="$(rpmkeys --checksig -v "c2t-$ver.rpm" 2>&1)" ||
    fail "RPM signature verification failed for $ver"
  echo "$output" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
    fail "no cryptographic signature success for $ver"
  if echo "$output" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
    fail "RPM signature untrusted/invalid for $ver"
  fi
  echo "C2T_PASS // NATIVE_RPM_OPENPGP_SIGNATURE_VALID_$ver"
done

rpm -Uvh ./c2t-0.1.rpm || fail "Fedora RPM initial installation failed"
[[ "$(cat "$path/fixture-version.txt")" == "0.1" ]] ||
  fail "wrong installed v1 marker"
rpm -V "$pkg" || fail "rpmdb file verification failed after v1 installation"
echo "C2T_PASS // RPM_TRANSACTION_INSTALL_V1_VERIFIED"

rpm -Uvh ./c2t-0.2.rpm || fail "Fedora RPM upgrade failed"
[[ "$(cat "$path/fixture-version.txt")" == "0.2" ]] ||
  fail "upgrade did not replace version marker"
rpm -q --qf '%{VERSION}\n' "$pkg" | grep -Fxq 0.2 ||
  fail "RPM database version not upgraded"
rpm -V "$pkg" || fail "rpmdb file verification failed after upgrade"
echo "C2T_PASS // RPM_TRANSACTION_UPGRADE_V2_VERIFIED"

rpm -Uvh --oldpackage ./c2t-0.1.rpm ||
  fail "RPM downgrade/rollback failed"
[[ "$(cat "$path/fixture-version.txt")" == "0.1" ]] ||
  fail "rollback did not restore version marker"
rpm -q --qf '%{VERSION}\n' "$pkg" | grep -Fxq 0.1 ||
  fail "rollback did not restore rpmdb version"
rpm -V "$pkg" || fail "rpmdb file verification failed after rollback"
echo "C2T_PASS // RPM_TRANSACTION_DOWNGRADE_V1_VERIFIED"

rpm -e "$pkg" || fail "RPM erase failed"
rpm -q "$pkg" >/dev/null 2>&1 && fail "RPM still installed after erase"
[[ ! -e "$path" ]] || fail "package files persisted after erase"

# Clean up only the guest's temporary RPM signer trust record.
rpm -qa 'gpg-pubkey*' | sort > /root/c2t/keys-after-import.txt
comm -13 /root/c2t/keys-before.txt /root/c2t/keys-after-import.txt \
  > /root/c2t/keys-added.txt
[[ "$(wc -l < /root/c2t/keys-added.txt)" -eq 1 ]] ||
  fail "expected exactly one disposable signer key record"
added="$(cat /root/c2t/keys-added.txt)"
[[ "$added" == gpg-pubkey-* ]] || fail "unexpected key package"
rpm -e "$added" || fail "failed to remove disposable signer key"
rpm -qa 'gpg-pubkey*' | sort > /root/c2t/keys-after-cleanup.txt
cmp -s /root/c2t/keys-before.txt /root/c2t/keys-after-cleanup.txt ||
  fail "RPM trusted signer set not restored"

# Neither package version installs executable unit, accounts, D-Bus policy,
# SELinux policy, credentials, an active service or any real host.
[[ ! -e /usr/libexec/post-apollo/connections-status-host ]] ||
  fail "unexpected production executable after RPM transactions"
[[ ! -e /usr/lib/systemd/system/postapollo-connections-status.service ]] ||
  fail "unexpected production systemd unit after RPM transactions"
[[ ! -e /usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf ]] ||
  fail "unexpected production bus policy after RPM transactions"
if semodule -l | grep -Fq postapollo_connections; then
  fail "test RPM installed a custom SELinux module"
fi
if getent passwd postapollo-connections >/dev/null; then
  fail "test RPM created a production service account"
fi
[[ "$(getenforce)" == Enforcing ]] ||
  fail "RPM transactions weakened SELinux"
echo "C2T_PASS // RPM_ERASE_AND_TRUST_CLEANUP_COMPLETE"
echo "C2T_PASS // NO_SERVICE_START_NO_OS_ACCOUNTS_NO_CREDENTIALS"
echo "C2T_LIMITATION // TEMPORARY_CI_KEY_NOT_RELEASE_SIGNING_TRUST"
echo "C2T_LIMITATION // INERT_STAGING_RPM_NOT_PRODUCTION_SILVERBLUE_DEPLOYMENT"
