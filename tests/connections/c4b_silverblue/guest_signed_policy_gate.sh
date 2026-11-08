#!/usr/bin/bash
# C4b: an OFFLINE, independently signed policy RPM must be composed with
# C3d's signed fake host. Only the disposable Silverblue CI guest may invoke.
set -Eeuo pipefail
[[ "$#" == 1 && "$1" =~ ^(prelayer|booted|rolledback)$ ]] ||
  { echo "C4B_POLICY_FAIL // INVALID_ARGUMENT"; exit 2; }
phase="$1"
media=/mnt/c2v-offline
rpmfile="$media/c4b-policy.rpm"
pkg=postapollo-connections-c4b-policy-ci
payload=/usr/share/selinux/packages/targeted/postapollo_connections.pp
host=/usr/libexec/post-apollo/connections-status-host
keydb=/var/lib/c4b-signed-policy-test-keyring
mode=/var/lib/c4b-runtime-ci-only
die() { echo "C4B_POLICY_FAIL // $*" >&2; exit 2; }
[[ "$(id -u)" == 0 && -e /run/ostree-booted &&
   -f /usr/local/libexec/c2v-ostree-cycle.sh &&
   -e /dev/disk/by-label/C2VCI ]] ||
  die "REFUSED_OUTSIDE_DISPOSABLE_SILVERBLUE"
[[ "$(getenforce)" == Enforcing && "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
  die "SELINUX_NOT_ENFORCING"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] ||
  die "NETWORK_DISABLED_GATE_FAILED"
[[ "$(cat /etc/fedora-release)" == *"Fedora release 44"* ]] ||
  die "WRONG_FEDORA_RELEASE"
ostree admin status | grep -iq silverblue || die "NOT_SILVERBLUE"
case "$phase" in
  prelayer)
    [[ -f "$media/c4b-opt-in.marker" && ! -e "$mode" &&
       -s "$rpmfile" && -s "$media/c4b-policy-public.asc" &&
       -s "$media/c4b-policy-fingerprint.txt" &&
       -s "$media/c4b-policy-artifact-manifest.sha256" ]] ||
      die "MISSING_EXPLICIT_SIGNED_POLICY_FIXTURES"
    [[ ! -e "$payload" && ! -e "$host" ]] ||
      die "COMPOSED_POLICY_OR_HOST_ALREADY_PRESENT"
    if rpm -q "$pkg" >/dev/null 2>&1; then
      die "POLICY_RPM_ALREADY_INSTALLED"
    fi
    if semodule -l | grep -Fq postapollo_connections; then
      die "POLICY_MODULE_ALREADY_PRESENT"
    fi
    (cd "$media" && sha256sum --check --status \
      c4b-policy-artifact-manifest.sha256) ||
      die "POLICY_MANIFEST_MISMATCH"
    [[ "$(cat "$media/c4b-policy-fingerprint.txt")" =~ ^[A-Fa-f0-9]{40}$ ]] ||
      die "BAD_DISPOSABLE_SIGNER_IDENTITY"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}\n' "$rpmfile")" == \
       "$pkg 0.1 noarch" ]] || die "UNEXPECTED_POLICY_RPM_IDENTITY"
    [[ "$(rpm -qpl "$rpmfile")" == "$payload" ]] ||
      die "POLICY_RPM_PAYLOAD_NOT_ALLOWLISTED"
    scripts="$(rpm -qp --scripts "$rpmfile")"
    [[ "$scripts" == *"/usr/sbin/semodule -i $payload"* &&
       "$scripts" == *"/usr/sbin/semodule -r postapollo_connections"* ]] ||
      die "POLICY_RPM_SCRIPTLET_NOT_ALLOWLISTED"
    [[ -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
      die "POLICY_RPM_UNEXPECTED_TRIGGERS"
    mkdir -m 0700 -p "$keydb"
    rpm --dbpath "$keydb" --initdb || die "TEST_KEYRING_INIT_REFUSED"
    before="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1 || true)"
    echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      die "SIGNER_PRETRUSTED_BEFORE_ISOLATED_IMPORT"
    rpmkeys --dbpath "$keydb" --import "$media/c4b-policy-public.asc" ||
      die "ISOLATED_POLICY_SIGNER_IMPORT_FAILED"
    after="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)" ||
      die "POLICY_RPM_OPENPGP_SIGNATURE_REJECTED"
    echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      die "POLICY_RPM_SIGNATURE_NOT_CONFIRMED"
    if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      die "INVALID_POLICY_SIGNATURE"
    fi
    echo "C4B_PASS // SIGNED_POLICY_VERIFIED_WITH_SEPARATE_TEST_ONLY_KEYRING"
    ;;
  booted)
    [[ -f "$mode" ]] || die "MISSING_RUNTIME_OPT_IN"
    [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}\n' "$pkg")" == \
       "$pkg 0.1 noarch" ]] || die "COMPOSED_POLICY_RPM_MISSING"
    [[ -f "$payload" && -f "$host" && ! -L "$payload" && ! -L "$host" ]] ||
      die "SIGNED_POLICY_OR_HOST_MISSING"
    [[ "$(rpm -qf --qf '%{NAME}\n' "$payload")" == "$pkg" ]] ||
      die "COMPOSED_POLICY_PAYLOAD_OWNERSHIP_INVALID"
    [[ "$(rpm -qf --qf '%{NAME}\n' "$host")" == \
       postapollo-connections-c3d-ci-status ]] ||
      die "SIGNED_HOST_OWNERSHIP_INVALID"
    semodule -l | grep -Fq postapollo_connections ||
      die "COMPOSED_POLICY_MODULE_NOT_LOADED"
    [[ "$(ls -Z "$host")" == *postapollo_connections_exec_t* ]] ||
      die "COMPOSED_OSTREE_HOST_ENTRYPOINT_LABEL_INVALID"
    echo "C4B_PASS // SIGNED_POLICY_RPM_COMPOSED_ENTRYPOINT_LABEL_BEFORE_REBOOT"
    ;;
  rolledback)
    [[ -f "$mode" ]] || die "MISSING_RUNTIME_OPT_IN_ON_ROLLBACK"
    if rpm -q "$pkg" >/dev/null 2>&1; then
      die "POLICY_RPM_SURVIVED_ROLLBACK"
    fi
    [[ ! -e "$payload" && ! -e "$host" ]] ||
      die "SIGNED_POLICY_PAYLOAD_OR_HOST_SURVIVED_ROLLBACK"
    if semodule -l | grep -Fq postapollo_connections; then
      die "COMPOSED_POLICY_MODULE_SURVIVED_ROLLBACK"
    fi
    [[ -d "$keydb" && "$keydb" == /var/lib/c4b-signed-policy-test-keyring ]] ||
      die "TEST_SIGNER_KEYRING_MISSING"
    rm -rf -- "$keydb"
    [[ ! -e "$keydb" ]] || die "TEST_SIGNER_KEYRING_NOT_REMOVED"
    echo "C4B_PASS // SIGNED_POLICY_RPM_AND_TEST_KEYRING_REMOVED_BY_ROLLBACK"
    ;;
esac
