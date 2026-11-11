#!/usr/bin/bash
# C4b Identity Silverblue release fixture: builder only, no guest installation.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${POST_APOLLO_ID_SILVERBLUE_CI_ONLY:-}" == 1 &&
   "$(id -u)" == 0 &&
   -d /src/services/identity && -d /out &&
   -f /src/tests/identity/fixtures/identity_gateway_installed_ci ]] ||
  { echo "C4B_ID_REFUSED // NON_DISPOSABLE_BUILD"; exit 2; }

dnf -y --setopt=install_weak_deps=False install rpm-build rpm-sign gnupg2 python3
umask 077
work="$(mktemp -d /tmp/c4b-id-rpm-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
top="$work/rpmbuild"
keydir="$work/signing-key"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$keydir"
chmod 0700 "$keydir"

# Reuse the EXACT eight files from Identity DOC's merged installed-host fixture.
# Do not introduce a new command gateway, patched module or C4d status daemon.
cp /src/tests/identity/fixtures/identity_gateway_installed_ci "$top/SOURCES/identity-gateway-ci"
for name in \
  desktop_command_gateway_v0.py desktop_host_lifecycle_v0.py \
  desktop_context_projection_v0.py desktop_session_host_v0.py \
  native_loopback_callback_v0.py private_context_ipc_v0.py \
  signed_command_receipt_v0.py; do
  cp "/src/services/identity/$name" "$top/SOURCES/$name"
done
cp /src/tests/connections/identity_silverblue/post-apollo-identity-silverblue-ci.service "$top/SOURCES/"
cp /src/tests/connections/identity_silverblue/signed_identity_gateway.spec "$top/SPECS/"

rpmbuild --define "_topdir $top" --define "_build_id_links none" \
  -bb "$top/SPECS/signed_identity_gateway.spec"
rpmfile="$(find "$top/RPMS/noarch" -maxdepth 1 -type f \
  -name 'post-apollo-identity-silverblue-ci-0.1-*.noarch.rpm' -print -quit)"
[[ -n "$rpmfile" && -s "$rpmfile" ]] ||
  { echo "C4B_ID_FAIL // RPM_MISSING"; exit 2; }
identity="$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")"
[[ "$identity" == 'post-apollo-identity-silverblue-ci 0.1 noarch' ]] ||
  { echo "C4B_ID_FAIL // PACKAGE_IDENTITY_INVALID"; exit 2; }
[[ -z "$(rpm -qp --scripts "$rpmfile")" &&
   -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "C4B_ID_FAIL // PACKAGE_HAS_AUTO_ACTION"; exit 2; }

expected="$work/expected"
actual="$work/actual"
{
  printf '%s\n' \
    /usr/libexec/post-apollo/identity/identity-gateway-ci \
    /usr/libexec/post-apollo/identity/desktop_command_gateway_v0.py \
    /usr/libexec/post-apollo/identity/desktop_host_lifecycle_v0.py \
    /usr/libexec/post-apollo/identity/desktop_context_projection_v0.py \
    /usr/libexec/post-apollo/identity/desktop_session_host_v0.py \
    /usr/libexec/post-apollo/identity/native_loopback_callback_v0.py \
    /usr/libexec/post-apollo/identity/private_context_ipc_v0.py \
    /usr/libexec/post-apollo/identity/signed_command_receipt_v0.py \
    /usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service
} | LC_ALL=C sort > "$expected"
rpm -qpl "$rpmfile" | LC_ALL=C sort > "$actual"
cmp -s "$expected" "$actual" ||
  { echo "C4B_ID_FAIL // RPM_PAYLOAD_NOT_EXACT_ROSTER"; exit 2; }

# Sign the RPM with a disposable, independent build-only GPG key.
# The Ed25519 release-root enrollment and receipt signer are DIFFERENT
# authorities, intentionally absent from this builder and its output.
signer='Post Apollo Identity Silverblue Disposable RPM <ci-only@example.invalid>'
gpg --homedir "$keydir" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key "$signer" rsa2048 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$keydir" --batch --with-colons --list-keys |
  awk -F: '$1=="fpr" { print $10; exit }')"
[[ "$fingerprint" =~ ^[A-Fa-f0-9]{40}$ ]] ||
  { echo "C4B_ID_FAIL // DISPOSABLE_SIGNER_INVALID"; exit 2; }
gpg --homedir "$keydir" --batch --armor --export "$fingerprint" > /out/identity-disposable-rpm-public.asc
printf '%s\n' "$fingerprint" > /out/identity-disposable-rpm-fingerprint.txt
rpmsign --addsign --define "_gpg_name $fingerprint" \
  --define "_gpg_path $keydir" "$rpmfile"
cp "$rpmfile" /out/identity-silverblue-ci.rpm
(
  cd /out
  sha256sum identity-silverblue-ci.rpm identity-disposable-rpm-public.asc \
    identity-disposable-rpm-fingerprint.txt > identity-artifact-manifest.sha256
)
[[ "$(find /out -maxdepth 1 -type f | wc -l)" -eq 4 ]] ||
  { echo "C4B_ID_FAIL // UNEXPECTED_OUTPUT"; exit 2; }
chmod 0644 /out/*
echo "C4B_ID_PASS // EXACT_DENY_ONLY_IDENTITY_GATEWAY_RPM_SIGNED"
echo "C4B_ID_LIMITATION // NO_SILVERBLUE_INSTALL_OR_INDEPENDENT_RELEASE_ENROLLMENT"
