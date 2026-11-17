#!/usr/bin/bash
# One separate official Fedora-signed offline runtime for disposable Silverblue.
set -Eeuo pipefail
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_ENVIRONMENT" == github-hosted &&
   "$POST_APOLLO_ID_SILVERBLUE_CI_ONLY" == 1 &&
   "$(id -u)" == 0 && -d /out ]] ||
  { echo "C4B_ID_BLOCKED // NON_DISPOSABLE_FEDORA_DEPENDENCY_BUILD"; exit 2; }
dnf -y --setopt=install_weak_deps=False install curl gnupg2 rpm
umask 077
work="$(mktemp -d /tmp/c4b-id-dep-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
rpm_name=python3-cryptography-50.0.0-1.fc44.x86_64.rpm
rpmfile="$work/$rpm_name"
key=/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-primary
fingerprint=36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6
[[ -r "$key" && -s "$key" ]] ||
  { echo "C4B_ID_BLOCKED // FEDORA_RELEASE_SIGNER_KEY_MISSING"; exit 2; }
actual="$(gpg --batch --with-colons --show-keys "$key" |
  awk -F: '$1=="fpr" {print $10;exit}')"
[[ "$actual" == "$fingerprint" ]] ||
  { echo "C4B_ID_BLOCKED // FEDORA44_KEY_FINGERPRINT_MISMATCH"; exit 2; }
url="https://download.fedoraproject.org/pub/fedora/linux/updates/44/Everything/x86_64/Packages/p/$rpm_name"
curl --fail --location --retry 2 --connect-timeout 20 --max-time 240 \
  "$url" -o "$rpmfile" ||
  { echo "C4B_ID_BLOCKED // FEDORA_CRYPTOGRAPHY_RPM_DOWNLOAD_REFUSED"; exit 2; }
[[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{RELEASE} %{ARCH}' "$rpmfile")" == \
   "python3-cryptography 50.0.0 1.fc44 x86_64" ]] ||
  { echo "C4B_ID_BLOCKED // WRONG_FEDORA_CRYPTOGRAPHY_RPM_ROLE"; exit 2; }
[[ -z "$(rpm -qp --scripts "$rpmfile")" &&
   -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "C4B_ID_BLOCKED // FEDORA_RUNTIME_HAS_UNEXPECTED_SCRIPTLETS"; exit 2; }

# Fedora's cryptography runtime requires python3.14dist(cffi) >= 2.
# Fedora 44 cffi in turn requires python3.14dist(pycparser). Keep this
# explicit dependency closure signed, exact-versioned and offline.
for dependency in \
  'python3-cffi|2.0.0|3.fc44|x86_64' \
  'python3-pycparser|2.22|8.fc44|noarch'; do
  IFS='|' read -r name version release arch <<< "$dependency"
  filename="$name-$version-$release.$arch.rpm"
  depfile="$work/$filename"
  url="https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/p/$filename"
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 240 \
    "$url" -o "$depfile" ||
    { echo "C4B_ID_BLOCKED // SIGNED_FEDORA_DEPENDENCY_DOWNLOAD_REFUSED_$name"; exit 2; }
  [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{RELEASE} %{ARCH}' "$depfile")" == \
     "$name $version $release $arch" ]] ||
    { echo "C4B_ID_BLOCKED // FEDORA_DEPENDENCY_ROLE_MISMATCH_$name"; exit 2; }
  [[ -z "$(rpm -qp --scripts "$depfile")" &&
     -z "$(rpm -qp --triggers "$depfile")" ]] ||
    { echo "C4B_ID_BLOCKED // FEDORA_DEPENDENCY_HAS_AUTOEXEC_$name"; exit 2; }
done
db="$work/rpmdb"
mkdir -m 0700 "$db"
rpm --dbpath "$db" --initdb
for candidate in \
    "$rpmfile" \
    "$work/python3-cffi-2.0.0-3.fc44.x86_64.rpm" \
    "$work/python3-pycparser-2.22-8.fc44.noarch.rpm"; do
  pretrust="$(rpmkeys --dbpath "$db" --checksig -v "$candidate" 2>&1 || true)"
  printf '%s\n' "$pretrust" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
    { echo "C4B_ID_BLOCKED // FEDORA_SIGNER_PRETRUST_REFUSAL_MISSING"; exit 2; }
done
rpmkeys --dbpath "$db" --import "$key"
for candidate in \
    "$rpmfile" \
    "$work/python3-cffi-2.0.0-3.fc44.x86_64.rpm" \
    "$work/python3-pycparser-2.22-8.fc44.noarch.rpm"; do
  posttrust="$(rpmkeys --dbpath "$db" --checksig -v "$candidate" 2>&1)" ||
    { echo "C4B_ID_BLOCKED // FEDORA_SIGNED_RUNTIME_INVALID"; exit 2; }
  printf '%s\n' "$posttrust" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
    { echo "C4B_ID_BLOCKED // FEDORA_RUNTIME_SIGNATURE_NOT_CONFIRMED"; exit 2; }
  if printf '%s\n' "$posttrust" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
    echo "C4B_ID_BLOCKED // FEDORA_RUNTIME_SIGNATURE_NOT_TRUSTED"
    exit 2
  fi
done
[[ "$(find /out -maxdepth 1 -type f | wc -l)" == 0 ]] ||
  { echo "C4B_ID_BLOCKED // FEDORA_RUNTIME_OUTPUT_ALREADY_EXISTS"; exit 2; }
install -m 0644 "$rpmfile" /out/identity-python3-cryptography-f44.rpm
install -m 0644 "$work/python3-cffi-2.0.0-3.fc44.x86_64.rpm" /out/identity-python3-cffi-f44.rpm
install -m 0644 "$work/python3-pycparser-2.22-8.fc44.noarch.rpm" /out/identity-python3-pycparser-f44.rpm
install -m 0644 "$key" /out/identity-fedora44-runtime-public.asc
(
  cd /out
  sha256sum identity-python3-cryptography-f44.rpm \
    identity-python3-cffi-f44.rpm \
    identity-python3-pycparser-f44.rpm \
    identity-fedora44-runtime-public.asc > identity-fedora44-runtime-manifest.sha256
)
chmod 0644 /out/identity-fedora44-runtime-manifest.sha256
[[ "$(find /out -maxdepth 1 -type f | wc -l)" == 5 ]] ||
  { echo "C4B_ID_BLOCKED // FEDORA_RUNTIME_OUTPUT_ROSTER_UNEXPECTED"; exit 2; }
echo "C4B_ID_PASS // OFFICIAL_FEDORA44_ED25519_RUNTIME_RPM_INDEPENDENTLY_SIGNED_AND_PINNED"
echo "C4B_ID_LIMITATION // DISPOSABLE_OFFLINE_TEST_DEPENDENCY_NOT_PRODUCTION_ADMISSION"
