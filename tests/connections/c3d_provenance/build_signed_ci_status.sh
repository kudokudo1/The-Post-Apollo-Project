#!/usr/bin/bash
# C3d ephemeral Fedora CI builder. Never a production release/signing key.
set -Eeuo pipefail
[[ "$(id -u)" == 0 && -d /src/tests/connections/c3d_provenance && -d /out ]] ||
  { echo "C3D_BUILDER_REFUSED_NOT_DISPOSABLE"; exit 2; }
dnf -y --setopt=install_weak_deps=False install rpm-build rpm-sign gnupg2 python3
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
# Opt-in C3e-B: the SAME temporary key signs a detached release manifest
# for the RPM it signed, but cannot authorize that release; a separate root
# policy, generated OUTSIDE this builder, must approve these exact bytes.
expected_outputs=4
if [[ "${POST_APOLLO_C3EB_EXPORT_MANIFEST:-0}" == 1 ]]; then
  python3 - <<'PY'
import hashlib, json
from pathlib import Path
rpm = Path("/out/c3d-status.rpm")
manifest = {
    "schema": "postapollo.connections.release-manifest.v1",
    "release_id": "postapollo-connections-status",
    "sequence": 1,
    "sha256": hashlib.sha256(rpm.read_bytes()).hexdigest(),
    "size": rpm.stat().st_size,
}
Path("/out/c3eb-release-manifest.json").write_text(
    json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
)
PY
  gpg --homedir "$keydir" --batch --yes --pinentry-mode loopback \
    --passphrase '' --local-user "$fingerprint" --detach-sign \
    --output /out/c3eb-release-manifest.sig /out/c3eb-release-manifest.json
  expected_outputs=6
  echo "C3EB_PASS // RPM_SIGNER_DETACHED_MANIFEST_SAME_DISPOSABLE_KEY"
fi
[[ "$(find /out -maxdepth 1 -type f | wc -l)" -eq "$expected_outputs" ]] ||
  { echo "C3D_BUILDER_UNEXPECTED_OUTPUT"; exit 2; }
chmod 0644 /out/c3d-status.rpm /out/c3d-disposable-public.asc \
  /out/c3d-public-fingerprint.txt /out/c3d-artifact-manifest.sha256
if [[ "$expected_outputs" == 6 ]]; then
  chmod 0644 /out/c3eb-release-manifest.json /out/c3eb-release-manifest.sig
fi
echo "C3D_PASS // EPHEMERAL_SIGNED_FAKE_HOST_RPM_BUILT"
echo "C3D_LIMITATION // DISPOSABLE_SELF_SIGNED_KEY_NOT_PRODUCTION_TRUST"
