#!/usr/bin/bash
# C3d ephemeral Fedora CI builder. Never a production release/signing key.
set -Eeuo pipefail
[[ "$(id -u)" == 0 && -d /src/tests/connections/c3d_provenance && -d /out ]] ||
  { echo "C3D_BUILDER_REFUSED_NOT_DISPOSABLE"; exit 2; }
dnf -y --setopt=install_weak_deps=False install rpm-build rpm-sign gnupg2
umask 077
work="$(mktemp -d /tmp/c3d-build-XXXXXX)"
trap 'rm -rf "$work"' EXIT
top="$work/rpmbuild"
keydir="$work/gnupg"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$keydir"
chmod 0700 "$keydir"
# Never export private signing material or a system-authorized release key.
identity="Post Apollo C3d Disposable CI Fixture <c3d-noreply@example.invalid>"
gpg --homedir "$keydir" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key "$identity" rsa2048 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$keydir" --batch --with-colons --list-keys |
  awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" =~ ^[A-Fa-f0-9]{40}$ ]] ||
  { echo "C3D_BUILDER_BAD_FINGERPRINT"; exit 2; }
gpg --homedir "$keydir" --batch --armor --export "$fingerprint" \
  > /out/c3d-disposable-public.asc
printf '%s\n' "$fingerprint" > /out/c3d-public-fingerprint.txt

cp /src/tests/connections/c2r_selinux_domain/C2rStatusHost.py "$top/SOURCES/"
cp /src/services/connections/experiments/c2n_package/postapollo-connections-status.service.template "$top/SOURCES/"
cp /src/services/connections/experiments/c2n_package/org.postapollo.ConnectionsStatus1.conf.template "$top/SOURCES/"
cp /src/tests/connections/c3d_provenance/signed-status.spec "$top/SPECS/"
rpmbuild --define "_topdir $top" --define "_build_id_links none" \
  -bb "$top/SPECS/signed-status.spec"
rpmfile="$(find "$top/RPMS/noarch" -maxdepth 1 -type f \
  -name 'postapollo-connections-c3d-ci-status-0.1-*.noarch.rpm' -print -quit)"
[[ -s "$rpmfile" ]] || { echo "C3D_BUILDER_RPM_MISSING"; exit 2; }
# A real RPM OpenPGP signature, not an adjacent checksum or detached .asc.
rpmsign --addsign \
  --define "_gpg_name $fingerprint" \
  --define "_gpg_path $keydir" "$rpmfile"
[[ -z "$(rpm -qp --scripts "$rpmfile")" ]] ||
  { echo "C3D_BUILDER_UNEXPECTED_SCRIPTLETS"; exit 2; }
[[ -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "C3D_BUILDER_UNEXPECTED_TRIGGERS"; exit 2; }
cp "$rpmfile" /out/c3d-status.rpm
(
  cd /out
  sha256sum c3d-status.rpm c3d-disposable-public.asc \
    c3d-public-fingerprint.txt > c3d-artifact-manifest.sha256
)
[[ "$(find /out -maxdepth 1 -type f | wc -l)" -eq 4 ]] ||
  { echo "C3D_BUILDER_UNEXPECTED_OUTPUT"; exit 2; }
chmod 0644 /out/c3d-status.rpm /out/c3d-disposable-public.asc \
  /out/c3d-public-fingerprint.txt /out/c3d-artifact-manifest.sha256
echo "C3D_PASS // EPHEMERAL_SIGNED_FAKE_HOST_RPM_BUILT"
echo "C3D_LIMITATION // DISPOSABLE_SELF_SIGNED_KEY_NOT_PRODUCTION_TRUST"
