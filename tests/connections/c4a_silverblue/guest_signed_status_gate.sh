#!/usr/bin/bash
# C4a: signed, inert status-service RPM evidence across REAL Silverblue boots.
# This is only a disposable test gate, not a workstation installer or a
# production trust root. The service must never be started in this test.
set -Eeuo pipefail
phase="$1"
root=/mnt/c2v-offline
rpmfile="$root/c3d-status.rpm"
pkg=postapollo-connections-c3d-ci-status
unit=postapollo-connections-status.service
host=/usr/libexec/post-apollo/connections-status-host
unitpath=/usr/lib/systemd/system/postapollo-connections-status.service
buspolicy=/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf
keydb=/var/lib/c4a-test-only-rpm-keyring
mode=/var/lib/c4a-signed-service-test
die() { echo "C4A_FAIL // $*" >&2; exit 2; }

[[ "$#" -eq 1 && "$phase" =~ ^(prelayer|booted|rolledback)$ ]] ||
  die "INVALID_PHASE"
[[ "$(id -u)" -eq 0 && -e /run/ostree-booted &&
   -e /dev/disk/by-label/C2VCI &&
   -f /usr/local/libexec/c2v-ostree-cycle.sh ]] ||
  die "REFUSED_OUTSIDE_DISPOSABLE_SILVERBLUE"
[[ "$(getenforce)" == Enforcing && "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
  die "SELINUX_NOT_ENFORCING"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] ||
  die "GUEST_NETWORK_INTERFACE_PRESENT"
[[ "$(cat /etc/fedora-release)" == *"Fedora release 44"* ]] ||
  die "NOT_FEDORA_44"
ostree admin status | grep -iq silverblue || die "NOT_SILVERBLUE"

check_inactive() {
  if systemctl is-active --quiet "$unit"; then
    die "FAKE_SERVICE_ACTIVE"
  fi
  # This reference unit intentionally has no [Install] section, so
  # systemd may report "static" with a successful is-enabled exit code.
  # Accept static/disabled ONLY; fail closed on actual enablement or drift.
  if [[ -e "$unitpath" ]]; then
    enablement="$(systemctl is-enabled "$unit" 2>&1 || true)"
    case "$enablement" in
      static|disabled) ;;
      *) die "FAKE_SERVICE_ENABLED_OR_INDETERMINATE" ;;
    esac
  fi
  if busctl --system get-name-owner org.postapollo.ConnectionsStatus1 >/dev/null 2>&1; then
    die "FAKE_DBUS_NAME_OWNED"
  fi
}

check_installed() {
  [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}\n' "$pkg")" == \
     "$pkg 0.1 noarch" ]] ||
    die "WRONG_INSTALLED_PACKAGE"
  rpm -V "$pkg" || die "RPMDB_CONTENT_INTEGRITY_FAILED"
  for item in "$host" "$unitpath" "$buspolicy"; do
    [[ -f "$item" && ! -L "$item" ]] ||
      die "MISSING_OR_SYMLINKED_PACKAGE_FILE"
    [[ "$(rpm -qf --qf '%{NAME}\n' "$item")" == "$pkg" ]] ||
      die "FILE_NOT_OWNED_BY_SIGNED_TEST_RPM"
  done
  check_inactive
}

case "$phase" in
  prelayer)
    [[ -f "$root/c4a-opt-in.marker" &&
       -f "$rpmfile" &&
       -f "$root/c3d-disposable-public.asc" &&
       -f "$root/c3d-public-fingerprint.txt" &&
       -f "$root/c3d-artifact-manifest.sha256" ]] ||
      die "MISSING_EXPLICIT_SIGNED_TEST_ARTIFACTS"
    [[ ! -e "$mode" ]] || die "ALREADY_IN_C4A_MODE"
    [[ ! -e "$host" && ! -e "$unitpath" && ! -e "$buspolicy" ]] ||
      die "FAKE_SERVICE_FILES_PRESENT_BEFORE_LAYER"
    if rpm -q "$pkg" >/dev/null 2>&1; then
      die "FAKE_STATUS_PACKAGE_ALREADY_INSTALLED"
    fi
    (cd "$root" && sha256sum --check --status c3d-artifact-manifest.sha256) ||
      die "SIGNED_ARTIFACT_MANIFEST_MISMATCH"
    [[ "$(cat "$root/c3d-public-fingerprint.txt")" =~ ^[A-Fa-f0-9]{40}$ ]] ||
      die "BAD_DISPOSABLE_SIGNER_FINGERPRINT"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}\n' "$rpmfile")" == \
       "$pkg 0.1 noarch" ]] || die "UNRECOGNIZED_SIGNED_FIXTURE"
    [[ -z "$(rpm -qp --scripts "$rpmfile")" &&
       -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
      die "SIGNED_PACKAGE_HAS_SCRIPTLETS_OR_TRIGGERS"
    expected="$(printf '%s\n' "$host" "$unitpath" "$buspolicy" | sort)"
    actual="$(rpm -qpl "$rpmfile" | sort)" ||
      die "SIGNED_PACKAGE_PATH_QUERY_FAILED"
    [[ "$actual" == "$expected" ]] ||
      die "SIGNED_PACKAGE_PAYLOAD_PATH_ALLOWLIST_FAILED"
    echo "C4A_PASS // SIGNED_FAKE_RPM_EXACT_PAYLOAD_AND_NO_SCRIPTLETS"

    # Silverblue's booted rpmdb is immutable; NEVER import a test signer there.
    # Use an isolated, disposable test keyring in /var, not a release identity.
    mkdir -m 0700 -p "$keydb"
    rpm --dbpath "$keydb" --initdb ||
      die "ISOLATED_KEYRING_INIT_FAILED"
    before="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1 || true)"
    echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      die "TEST_SIGNER_ALREADY_TRUSTED_BEFORE_IMPORT"
    echo "C4A_PASS // TEST_SIGNER_UNTRUSTED_BEFORE_EXPLICIT_IMPORT"
    rpmkeys --dbpath "$keydb" --import "$root/c3d-disposable-public.asc" ||
      die "ISOLATED_PUBLIC_KEY_IMPORT_FAILED"
    after="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)" ||
      die "SIGNED_FIXTURE_OPENPGP_VERIFICATION_FAILED"
    echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      die "SIGNED_FIXTURE_SIGNATURE_NOT_CONFIRMED"
    if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      die "UNTRUSTED_OR_BAD_SIGNATURE_AFTER_IMPORT"
    fi
    echo "C4A_PASS // TEST_ONLY_RPM_SIGNATURE_VERIFIED_ISOLATED_FROM_BOOTED_RPMDB"
    check_inactive
    echo "C4A_PASS // SERVICE_NOT_ACTIVE_BEFORE_OSTREE_LAYER"
    ;;
  booted)
    [[ -f "$mode" ]] || die "MODE_MARKER_ABSENT_AFTER_FIRST_REBOOT"
    check_installed
    echo "C4A_PASS // SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT"
    echo "C4A_PASS // FAKE_SERVICE_NEVER_STARTED_OR_ENABLED"
    ;;
  rolledback)
    [[ -f "$mode" ]] || die "MODE_MARKER_ABSENT_AFTER_ROLLBACK"
    if rpm -q "$pkg" >/dev/null 2>&1; then
      die "SIGNED_FAKE_RPM_REMAINS_AFTER_ROLLBACK"
    fi
    [[ ! -e "$host" && ! -e "$unitpath" && ! -e "$buspolicy" ]] ||
      die "SIGNED_SERVICE_FILES_REMAIN_AFTER_ROLLBACK"
    check_inactive
    [[ -d "$keydb" && "$keydb" == /var/lib/c4a-test-only-rpm-keyring ]] ||
      die "ISOLATED_KEYRING_PATH_INVALID"
    rm -rf -- "$keydb"
    [[ ! -e "$keydb" ]] || die "ISOLATED_KEYRING_CLEANUP_FAILED"
    echo "C4A_PASS // SIGNED_FAKE_SERVICE_REMOVED_BY_REAL_BOOTED_ROLLBACK"
    echo "C4A_PASS // ISOLATED_TEST_SIGNER_KEYRING_REMOVED"
    echo "C4A_LIMITATION // EPHEMERAL_SIGNER_NOT_INDEPENDENT_PRODUCTION_TRUST"
    ;;
esac
