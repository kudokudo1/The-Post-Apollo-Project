#!/usr/bin/bash
# C3d test-only. Signed RPM provenance of a fake, networkless status host.
# The guest's ephemeral signing key is never a production trust anchor.
set -Eeuo pipefail
if [[ "$#" -ne 1 || ! "$1" =~ ^(preinstall|installed|cleanup)$ ||
      ! -v GITHUB_ACTIONS || "$GITHUB_ACTIONS" != true ||
      ! -v POST_APOLLO_C3D_DISPOSABLE_GUEST ||
      "$POST_APOLLO_C3D_DISPOSABLE_GUEST" != 1 ||
      ! -f /root/c2q/c3d-status.rpm ]]; then
  echo "C3D_REFUSED_NOT_DISPOSABLE_GUEST"
  exit 2
fi
phase="$1"
pkg=postapollo-connections-c3d-ci-status
unit=postapollo-connections-status.service
host=/usr/libexec/post-apollo/connections-status-host
unitpath=/usr/lib/systemd/system/postapollo-connections-status.service
buspolicy=/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf
root=/root/c2q
die() { echo "C3D_FAIL // $*" >&2; exit 2; }
check_installed() {
  [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}\n' "$pkg")" == \
       "$pkg 0.1 noarch" ]] || die "unexpected rpmdb package identity"
  rpm -V "$pkg" || die "installed package content/metadata drift"
  [[ -z "$(rpm -q --scripts "$pkg")" ]] || die "unexpected installed scriptlet"
  [[ -z "$(rpm -q --triggers "$pkg")" ]] || die "unexpected installed trigger"
  for path in "$host" "$unitpath" "$buspolicy"; do
    [[ -f "$path" && ! -L "$path" ]] || die "package file missing or symlinked: $path"
    [[ "$(rpm -qf --qf '%{NAME}\n' "$path")" == "$pkg" ]] ||
      die "installed file not owned by exact signed test package: $path"
  done
}

[[ "$(getenforce)" == Enforcing &&
   "$(cat /sys/fs/selinux/enforce)" == 1 ]] ||
  die "SELinux not enforcing"
[[ "$(ls /sys/class/net | tr '\n' ' ')" == "lo " ]] ||
  die "guest network unexpectedly available"
[[ -f "$root/c3d-disposable-public.asc" &&
   -f "$root/c3d-public-fingerprint.txt" &&
   -f "$root/c3d-artifact-manifest.sha256" ]] ||
  die "missing signed fixture input"
cd "$root"
case "$phase" in
  preinstall)
    [[ ! -e "$host" && ! -e "$unitpath" && ! -e "$buspolicy" ]] ||
      die "service already installed before RPM verification"
    rpm -q "$pkg" >/dev/null 2>&1 &&
      die "package unexpectedly preinstalled"
    sha256sum --check --status c3d-artifact-manifest.sha256 ||
      die "signed fixture artifact digest mismatch"
    # C3e-B independently root-authorized the RPM outside this guest.
    # The guest must verify those same bytes BEFORE any key import or install.
    if [[ -f c3eb-approved.sha256 ]]; then
      [[ "$(wc -l <c3eb-approved.sha256)" -eq 1 ]] ||
        die "root-approved RPM digest was not a single entry"
      grep -Eq '^[0-9a-f]{64}  c3d-status[.]rpm
      die "bad public signer fingerprint format"
    [[ "$(cat c3d-public-fingerprint.txt)" =~ ^[A-Fa-f0-9]{40}$ ]] ||
      die "unexpected public signer fingerprint syntax"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}\n' c3d-status.rpm)" == \
         "$pkg 0.1 noarch" ]] ||
      die "unrecognized RPM payload identity"
    [[ -z "$(rpm -qp --scripts c3d-status.rpm)" ]] ||
      die "RPM contains scriptlets"
    [[ -z "$(rpm -qp --triggers c3d-status.rpm)" ]] ||
      die "RPM contains triggers"
    expected_files="$(printf '%s\n' "$host" "$unitpath" "$buspolicy" | sort)"
    observed_files="$(rpm -qpl c3d-status.rpm | sort)" ||
      die "RPM payload file listing failed"
    [[ "$observed_files" == "$expected_files" ]] ||
      die "unexpected or missing signed RPM payload path"
    echo "C3D_PASS // SIGNED_RPM_PAYLOAD_PATH_ALLOWLIST"
    # Refuse unknown signing identities until the test public key is imported.
    before="$(rpmkeys --checksig -v c3d-status.rpm 2>&1)" || true
    echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      die "CI signer unexpectedly trusted before ephemeral public key import"
    echo "C3D_PASS // SIGNER_NOT_TRUSTED_BEFORE_TEST_IMPORT"

    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-before.txt"
    rpm --import "$root/c3d-disposable-public.asc" ||
      die "ephemeral test signer public key import rejected"
    after="$(rpmkeys --checksig -v c3d-status.rpm 2>&1)" ||
      die "native RPM signature invalid after importing test key"
    echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      die "no validated OpenPGP signature in RPM header"
    if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      die "signature still untrusted"
    fi
    echo "C3D_PASS // TEST_ONLY_RPM_SIGNATURE_ACCEPTED"

    # Never activate the fake host during package installation.
    rpm -Uvh "$root/c3d-status.rpm" ||
      die "install of signed fake RPM failed"
    [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
      die "install started service without operator action"
    check_installed
    echo "C3D_PASS // RPMDB_OWNS_AND_VERIFIES_FAKE_SERVICE_FILES"

    # Negative integrity test before service startup. A modified executable
    # must produce a failed native rpm -V, then be restored by reinstall.
    printf '\n# C3D_SYNTHETIC_TAMPER_ONLY\n' >> "$host"
    if rpm -V "$pkg" > "$root/c3d-tamper-result.txt" 2>&1; then
      die "modified fake executable incorrectly passed RPM verification"
    fi
    grep -Fq "$host" "$root/c3d-tamper-result.txt" ||
      die "RPM verification failure did not identify the altered executable"
    echo "C3D_PASS // MODIFIED_FAKE_SERVICE_REFUSED_BY_RPM_VERIFY"
    rpm -Uvh --replacepkgs "$root/c3d-status.rpm" ||
      die "signed package repair failed"
    check_installed
    echo "C3D_PASS // SIGNED_TEST_PACKAGE_REPAIR_VERIFIED"
    ;;
  installed)
    check_installed
    echo "C3D_PASS // RUNNING_TEST_SERVICE_FILES_OWNED_BY_VERIFIED_RPM"
    ;;
  cleanup)
    [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
      die "service active at package cleanup"
    check_installed
    rpm -e "$pkg" || die "RPM cleanup failed"
    [[ ! -e "$host" && ! -e "$unitpath" && ! -e "$buspolicy" ]] ||
      die "RPM erase left a protected-service file behind"
    rpm -q "$pkg" >/dev/null 2>&1 &&
      die "RPM database retained erased test package"
    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-after.txt"
    comm -13 "$root/c3d-keys-before.txt" "$root/c3d-keys-after.txt" \
      > "$root/c3d-added-keys.txt"
    [[ "$(wc -l < "$root/c3d-added-keys.txt")" -eq 1 ]] ||
      die "test signer did not add exactly one key"
    added="$(cat "$root/c3d-added-keys.txt")"
    [[ "$added" == gpg-pubkey-* ]] || die "unrecognized guest test key"
    rpm -e "$added" || die "disposable test signer cleanup failed"
    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-cleaned.txt"
    cmp -s "$root/c3d-keys-before.txt" "$root/c3d-keys-cleaned.txt" ||
      die "test key cleanup did not restore original RPM trust records"
    echo "C3D_PASS // SIGNED_FAKE_SERVICE_ERASE_AND_TEST_KEY_CLEANUP"
    echo "C3D_LIMITATION // EPHEMERAL_CI_KEY_NOT_AN_AUTHENTICATED_RELEASE"
    ;;
esac
 c3eb-approved.sha256 ||
        die "root-approved RPM digest had unexpected shape"
      sha256sum --check --status c3eb-approved.sha256 ||
        die "staged RPM was not the root-authorized candidate"
      echo "C3EB_PASS // GUEST_RPM_DIGEST_MATCHES_ROOT_ADMITTED_BYTES"
    fi
    [[ "$(wc -l <c3d-public-fingerprint.txt)" -eq 1 ]] ||
      die "bad public signer fingerprint format"
    [[ "$(cat c3d-public-fingerprint.txt)" =~ ^[A-Fa-f0-9]{40}$ ]] ||
      die "unexpected public signer fingerprint syntax"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}\n' c3d-status.rpm)" == \
         "$pkg 0.1 noarch" ]] ||
      die "unrecognized RPM payload identity"
    [[ -z "$(rpm -qp --scripts c3d-status.rpm)" ]] ||
      die "RPM contains scriptlets"
    [[ -z "$(rpm -qp --triggers c3d-status.rpm)" ]] ||
      die "RPM contains triggers"
    expected_files="$(printf '%s\n' "$host" "$unitpath" "$buspolicy" | sort)"
    observed_files="$(rpm -qpl c3d-status.rpm | sort)" ||
      die "RPM payload file listing failed"
    [[ "$observed_files" == "$expected_files" ]] ||
      die "unexpected or missing signed RPM payload path"
    echo "C3D_PASS // SIGNED_RPM_PAYLOAD_PATH_ALLOWLIST"
    # Refuse unknown signing identities until the test public key is imported.
    before="$(rpmkeys --checksig -v c3d-status.rpm 2>&1)" || true
    echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      die "CI signer unexpectedly trusted before ephemeral public key import"
    echo "C3D_PASS // SIGNER_NOT_TRUSTED_BEFORE_TEST_IMPORT"

    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-before.txt"
    rpm --import "$root/c3d-disposable-public.asc" ||
      die "ephemeral test signer public key import rejected"
    after="$(rpmkeys --checksig -v c3d-status.rpm 2>&1)" ||
      die "native RPM signature invalid after importing test key"
    echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      die "no validated OpenPGP signature in RPM header"
    if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      die "signature still untrusted"
    fi
    echo "C3D_PASS // TEST_ONLY_RPM_SIGNATURE_ACCEPTED"

    # Never activate the fake host during package installation.
    rpm -Uvh "$root/c3d-status.rpm" ||
      die "install of signed fake RPM failed"
    [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
      die "install started service without operator action"
    check_installed
    echo "C3D_PASS // RPMDB_OWNS_AND_VERIFIES_FAKE_SERVICE_FILES"

    # Negative integrity test before service startup. A modified executable
    # must produce a failed native rpm -V, then be restored by reinstall.
    printf '\n# C3D_SYNTHETIC_TAMPER_ONLY\n' >> "$host"
    if rpm -V "$pkg" > "$root/c3d-tamper-result.txt" 2>&1; then
      die "modified fake executable incorrectly passed RPM verification"
    fi
    grep -Fq "$host" "$root/c3d-tamper-result.txt" ||
      die "RPM verification failure did not identify the altered executable"
    echo "C3D_PASS // MODIFIED_FAKE_SERVICE_REFUSED_BY_RPM_VERIFY"
    rpm -Uvh --replacepkgs "$root/c3d-status.rpm" ||
      die "signed package repair failed"
    check_installed
    echo "C3D_PASS // SIGNED_TEST_PACKAGE_REPAIR_VERIFIED"
    ;;
  installed)
    check_installed
    echo "C3D_PASS // RUNNING_TEST_SERVICE_FILES_OWNED_BY_VERIFIED_RPM"
    ;;
  cleanup)
    [[ "$(systemctl is-active "$unit" 2>/dev/null || true)" != active ]] ||
      die "service active at package cleanup"
    check_installed
    rpm -e "$pkg" || die "RPM cleanup failed"
    [[ ! -e "$host" && ! -e "$unitpath" && ! -e "$buspolicy" ]] ||
      die "RPM erase left a protected-service file behind"
    rpm -q "$pkg" >/dev/null 2>&1 &&
      die "RPM database retained erased test package"
    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-after.txt"
    comm -13 "$root/c3d-keys-before.txt" "$root/c3d-keys-after.txt" \
      > "$root/c3d-added-keys.txt"
    [[ "$(wc -l < "$root/c3d-added-keys.txt")" -eq 1 ]] ||
      die "test signer did not add exactly one key"
    added="$(cat "$root/c3d-added-keys.txt")"
    [[ "$added" == gpg-pubkey-* ]] || die "unrecognized guest test key"
    rpm -e "$added" || die "disposable test signer cleanup failed"
    rpm -qa 'gpg-pubkey*' | sort > "$root/c3d-keys-cleaned.txt"
    cmp -s "$root/c3d-keys-before.txt" "$root/c3d-keys-cleaned.txt" ||
      die "test key cleanup did not restore original RPM trust records"
    echo "C3D_PASS // SIGNED_FAKE_SERVICE_ERASE_AND_TEST_KEY_CLEANUP"
    echo "C3D_LIMITATION // EPHEMERAL_CI_KEY_NOT_AN_AUTHENTICATED_RELEASE"
    ;;
esac
