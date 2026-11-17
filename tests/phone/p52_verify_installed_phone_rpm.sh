#!/usr/bin/bash
# P52 // independent disposable Fedora 44 verifier, REAL RPM install/erase.
# Does not run systemd, install on the user's host, or enroll a release root.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${POST_APOLLO_PHONE_RPM_CI_ONLY:-}" == 1 &&
   "$(id -u)" == 0 && -d /input && -d /src/services/phone ]] ||
  { echo "P52_REFUSED // NOT_DISPOSABLE_VERIFIER"; exit 78; }

dnf -y --setopt=install_weak_deps=False install rpm gnupg2 python3
(cd /input && sha256sum --check --status phone-status-artifact-manifest.sha256) ||
  { echo "P52_REFUSED // ARTIFACT_HASH"; exit 78; }

rpmfile=/input/phone-status-ci.rpm
public=/input/phone-status-disposable-rpm-public.asc
package=post-apollo-phone-status-ci
service=post-apollo-phone-personal-status-ci.service
prefix=/usr/libexec/post-apollo/phone
[[ -s "$rpmfile" && -s "$public" &&
   "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")" == \
   "$package 0.1 noarch" ]] ||
  { echo "P52_REFUSED // WRONG_PACKAGE"; exit 78; }
[[ -z "$(rpm -qp --scripts "$rpmfile")" &&
   -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "P52_REFUSED // INSTALLED_SCRIPTLET_OR_TRIGGER"; exit 78; }
[[ ! -e "$prefix/PhonePersonalStatusHostP49.py" &&
   ! -e "/usr/lib/systemd/system/$service" ]] ||
  { echo "P52_REFUSED // CONTAINER_ALREADY_INSTALLED"; exit 78; }

work="$(mktemp -d /tmp/p52-phone-verifier-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
db="$work/trust-db"
mkdir -m 0700 "$db"
rpm --dbpath "$db" --initdb
before="$(rpmkeys --dbpath "$db" --checksig -v "$rpmfile" 2>&1 || true)"
echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
  { echo "P52_REFUSED // SIGNER_ALREADY_TRUSTED"; exit 78; }

# Explicit separate trust action; this public key belongs to a disposable
# RPM builder, NOT the user's independently anchored production release root.
rpmkeys --dbpath "$db" --import "$public"
after="$(rpmkeys --dbpath "$db" --checksig -v "$rpmfile" 2>&1)" ||
  { echo "P52_REFUSED // RPM_SIGNATURE_INVALID"; exit 78; }
echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
  { echo "P52_REFUSED // SIGNATURE_NOT_CONFIRMED"; exit 78; }
if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
  echo "P52_REFUSED // STILL_UNTRUSTED_SIGNATURE"
  exit 78
fi
echo "P52_PASS // INDEPENDENT_FEDORA_DISPOSABLE_RPM_SIGNATURE_VALID"

# Container-local default rpmdb: ephemeral import and actual install. Neither
# the key nor package can reach the operator's Silverblue or keyring.
rpm --import "$public"
rpm -ivh --nodeps "$rpmfile"
rpm -q "$package" >/dev/null
rpm -V --nomtime "$package" >"$work/verify-files"
[[ ! -s "$work/verify-files" ]] ||
  { echo "P52_REFUSED // RPM_INSTALLED_FILES_VERIFICATION_FAILED"; exit 78; }

names=(
  PhonePersonalHostSocketP47.py
  PhonePersonalPeerEvidenceP48.py
  PhonePersonalStatusHostP49.py
  PhonePersonalInstalledReleaseP50.py
)
for name in "${names[@]}"; do
  target="$prefix/$name"
  [[ -f "$target" && ! -L "$target" ]] &&
    [[ "$(stat -c '%u:%g %a %h' "$target")" == "0:0 555 1" ]] &&
    cmp -s "$target" "/src/services/phone/$name" ||
    { echo "P52_REFUSED // INSTALLED_MODULE_NOT_EXACT"; exit 78; }
done
for target in "$prefix/systemd/$service" "/usr/lib/systemd/system/$service"; do
  [[ -f "$target" && ! -L "$target" ]] &&
    [[ "$(stat -c '%u:%g %a %h' "$target")" == "0:0 644 1" ]] &&
    cmp -s "$target" "/src/services/phone/systemd/$service" ||
    { echo "P52_REFUSED // INSTALLED_UNIT_NOT_EXACT"; exit 78; }
done
[[ "$(rpm -ql "$package" | wc -l)" == 6 ]] ||
  { echo "P52_REFUSED // UNEXPECTED_INSTALLED_FILE_ROSTER"; exit 78; }
# A source-only installed unit has NO enable target and remains ungated
# without the separately authorized marker. No systemd daemon is running.
! grep -Eq '^\[Install\]|^WantedBy=|^ExecStart(Post|Pre)=' \
  "/usr/lib/systemd/system/$service" ||
  { echo "P52_REFUSED // UNIT_AUTOACTIVATION"; exit 78; }

# Source sanity using the real installed bytes under Python isolated mode.
# Does NOT call the actual keyring, host SAVE, Identity, C3e, C5 or a signer.
python3 -I -B -c '
import sys
sys.path.insert(0, "/usr/libexec/post-apollo/phone")
import PhonePersonalHostSocketP47 as p
import PhonePersonalInstalledReleaseP50 as release
assert p.STATUS["status"] == "HOST_UNTRUSTED_STATUS_ONLY"
assert p.STATUS["personalSaveAuthorized"] is False
assert p.STATUS["keyReadAuthorized"] is False
assert release.RESULT["productionEnabled"] is False
assert release.RESULT["personalSaveAuthorized"] is False
'
echo "P52_PASS // REAL_FEDORA_RPM_INSTALLED_ROOT_OWNED_STATUS_ONLY"

# An RPM erase in disposable Fedora checks removable files; it is NOT an
# OSTree deployment rollback or two-boot Silverblue verification.
rpm -e "$package"
! rpm -q "$package" >/dev/null 2>&1 ||
  { echo "P52_REFUSED // PACKAGE_STILL_INSTALLED"; exit 78; }
for name in "${names[@]}"; do
  [[ ! -e "$prefix/$name" ]] ||
    { echo "P52_REFUSED // CODE_LEFT_AFTER_RPM_ERASE"; exit 78; }
done
[[ ! -e "/usr/lib/systemd/system/$service" &&
   ! -e "$prefix/systemd/$service" ]] ||
  { echo "P52_REFUSED // UNIT_LEFT_AFTER_RPM_ERASE"; exit 78; }
echo "P52_PASS // DISPOSABLE_FEDORA_RPM_ERASE_CLEAN"
echo "P52_LIMITATION // NO_SILVERBLUE_OSTREE_BOOT_SELINUX_SEAT_OR_C5"
