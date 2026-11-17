#!/usr/bin/bash
# P52 PHONE STATUS-only Fedora 44 RPM builder. GitHub disposable CI only.
# Independent from the C4b Identity signer, C3e reviewer, C5 approval.
set -Eeuo pipefail

[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${POST_APOLLO_PHONE_RPM_CI_ONLY:-}" == 1 &&
   "$(id -u)" == 0 &&
   -d /src/services/phone && -d /out &&
   -f /src/tests/phone/p52_signed_phone_status.spec ]] ||
  { echo "P52_REFUSED // DISPOSABLE_GITHUB_ONLY"; exit 78; }

[[ -z "$(find /out -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
  { echo "P52_REFUSED // OUTPUT_NOT_EMPTY"; exit 78; }

dnf -y --setopt=install_weak_deps=False install rpm-build rpm-sign gnupg2 python3 cpio
umask 077
work="$(mktemp -d /tmp/p52-phone-rpm-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
top="$work/rpmbuild"
keydir="$work/signing-key"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$keydir"
chmod 0700 "$keydir"

names=(
  PhonePersonalHostSocketP47.py
  PhonePersonalPeerEvidenceP48.py
  PhonePersonalStatusHostP49.py
  PhonePersonalInstalledReleaseP50.py
)
for name in "${names[@]}"; do
  [[ -f "/src/services/phone/$name" && ! -L "/src/services/phone/$name" ]] ||
    { echo "P52_REFUSED // MISSING_PHONE_SOURCE"; exit 78; }
  cp -- "/src/services/phone/$name" "$top/SOURCES/$name"
done
service=post-apollo-phone-personal-status-ci.service
cp -- "/src/services/phone/systemd/$service" "$top/SOURCES/$service"
cp -- /src/tests/phone/p52_signed_phone_status.spec "$top/SPECS/"

# Assert the source systemd unit is inert before packaging it.
! grep -Eq '^[[:space:]]*\[Install\]|^[[:space:]]*WantedBy=|^[[:space:]]*ExecStart(Post|Pre)=' \
  "$top/SOURCES/$service" ||
  { echo "P52_REFUSED // UNIT_AUTOACTIVATION"; exit 78; }
grep -Fxq 'Environment=POST_APOLLO_PHONE_STATUS_NO_SAVE=1' "$top/SOURCES/$service" ||
  { echo "P52_REFUSED // INERT_STATUS_GATE_MISSING"; exit 78; }

rpmbuild --define "_topdir $top" --define "_build_id_links none" \
  --undefine __brp_mangle_shebangs \
  -bb "$top/SPECS/p52_signed_phone_status.spec"
rpmfile="$(find "$top/RPMS/noarch" -maxdepth 1 -type f \
  -name 'post-apollo-phone-status-ci-0.1-*.noarch.rpm' -print -quit)"
[[ -n "$rpmfile" && -s "$rpmfile" ]] ||
  { echo "P52_REFUSED // RPM_MISSING"; exit 78; }

[[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")" == \
   "post-apollo-phone-status-ci 0.1 noarch" ]] ||
  { echo "P52_REFUSED // WRONG_RPM_IDENTITY"; exit 78; }
[[ -z "$(rpm -qp --scripts "$rpmfile")" &&
   -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "P52_REFUSED // RPM_AUTO_ACTION"; exit 78; }

prefix=/usr/libexec/post-apollo/phone
{
  for name in "${names[@]}"; do printf '%s/%s\n' "$prefix" "$name"; done
  printf '%s\n' "$prefix/systemd/$service"
  printf '%s\n' "/usr/lib/systemd/system/$service"
} | LC_ALL=C sort >"$work/expected"
rpm -qpl "$rpmfile" | LC_ALL=C sort >"$work/actual"
cmp -s "$work/expected" "$work/actual" ||
  { echo "P52_REFUSED // WRONG_RPM_FILE_ROSTER"; exit 78; }

# Compare actual *packaged* RPM file payload, not merely rpmbuild's inputs.
unpacked="$work/unpacked"
mkdir -p "$unpacked"
( cd "$unpacked" && rpm2cpio "$rpmfile" | cpio -idm --quiet --no-absolute-filenames )
for name in "${names[@]}"; do
  dst="$unpacked$prefix/$name"
  [[ -f "$dst" && ! -L "$dst" ]] &&
    cmp -s "$dst" "/src/services/phone/$name" &&
    [[ "$(stat -c '%a' "$dst")" == 555 ]] ||
    { echo "P52_REFUSED // RPM_MODULE_BYTES_OR_MODE_CHANGED"; exit 78; }
done
for location in "$prefix/systemd/$service" "/usr/lib/systemd/system/$service"; do
  dst="$unpacked$location"
  [[ -f "$dst" && ! -L "$dst" ]] &&
    cmp -s "$dst" "/src/services/phone/systemd/$service" &&
    [[ "$(stat -c '%a' "$dst")" == 644 ]] ||
    { echo "P52_REFUSED // RPM_UNIT_BYTES_OR_MODE_CHANGED"; exit 78; }
done
echo "P52_PASS // REAL_RPM_PAYLOAD_EQUALS_EXACT_PHONE_SOURCES"

# Key exists only in disposable builder /tmp and is removed by EXIT trap.
# It is a TEST-ONLY RPM package signer, never a production release authority.
signer='Post Apollo PHONE STATUS Disposable RPM <phone-ci-only@example.invalid>'
gpg --homedir "$keydir" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key "$signer" rsa2048 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$keydir" --batch --with-colons --list-keys |
  awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" =~ ^[a-fA-F0-9]{40}$ ]] ||
  { echo "P52_REFUSED // TEST_SIGNER_INVALID"; exit 78; }
gpg --homedir "$keydir" --batch --armor --export "$fingerprint" \
  > /out/phone-status-disposable-rpm-public.asc
printf '%s\n' "$fingerprint" > /out/phone-status-disposable-rpm-fingerprint.txt

rpmsign --addsign --define "_gpg_name $fingerprint" \
  --define "_gpg_path $keydir" "$rpmfile"
cp -- "$rpmfile" /out/phone-status-ci.rpm
(
  cd /out
  sha256sum phone-status-ci.rpm phone-status-disposable-rpm-public.asc \
    phone-status-disposable-rpm-fingerprint.txt \
    > phone-status-artifact-manifest.sha256
)
[[ "$(find /out -maxdepth 1 -type f | wc -l)" -eq 4 ]] ||
  { echo "P52_REFUSED // UNEXPECTED_BUILD_ARTIFACT"; exit 78; }
chmod 0644 /out/*
echo "P52_PASS // EXACT_SIGNED_PHONE_STATUS_RPM_BUILD_ONLY"
echo "P52_LIMITATION // DISPOSABLE_RPM_SIGNER_NO_PRODUCTION_RELEASE_ROOT_OR_C5"
