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
    c3d_identity="$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$c3d_source")" ||
      die "SIGNED_C3D_MEASUREMENT_PACKAGE_QUERY_FAILED"
    [[ "$c3d_identity" == "postapollo-connections-c3d-ci-status 0.1 noarch" ]] ||
      die "SIGNED_C3D_MEASUREMENT_PACKAGE_MISMATCH"
    install -m 0600 "$c3d_source" "$c3d_saved" ||
      die "SIGNED_C3D_MEASUREMENT_COPY_REFUSED"
    c3d_source_sha="$(sha256sum "$c3d_source" | awk '{print $1}')"
    c3d_saved_sha="$(sha256sum "$c3d_saved" | awk '{print $1}')"
    [[ "$c3d_source_sha" == "$c3d_saved_sha" ]] ||
      die "SIGNED_C3D_MEASUREMENT_COPY_CHANGED"
    echo "C4B_PASS // SIGNED_C3D_PUBLIC_RPM_SNAPSHOT_RETAINED_FOR_RUNNING_OBSERVATION"
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
