#!/usr/bin/bash
# GitHub CI disposable Fedora 44 container only. Private key never exported.
set -Eeuo pipefail
[[ "$(id -u)" == 0 ]] || { echo "C2T_REFUSED_NOT_ROOT_IN_DISPOSABLE_FEDORA_BUILDER"; exit 2; }
test -d /src/tests/connections/c2t_signed_rpm || exit 2
test -d /out || exit 2

dnf -y --setopt=install_weak_deps=False install rpm-build rpm-sign gnupg2
umask 077
work="$(mktemp -d /tmp/postapollo-c2t-build-XXXXXX)"
trap 'rm -rf "$work"' EXIT
top="$work/rpmbuild"
keydir="$work/gnupg"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$keydir"
chmod 0700 "$keydir"

# No production signing identity and no persistent key.
uid="Post Apollo C2t Disposable CI Test <c2t-noreply@example.invalid>"
gpg --homedir "$keydir" --batch --pinentry-mode loopback --passphrase '' \
    --quick-generate-key "$uid" rsa2048 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$keydir" --batch --with-colons --list-keys \
    | awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" =~ ^[A-Fa-f0-9]{40}$ ]] || exit 2
gpg --homedir "$keydir" --batch --armor --export "$fingerprint" \
    > /out/c2t-disposable-public.asc
printf '%s\n' "$fingerprint" > /out/c2t-public-fingerprint.txt

cp /src/tests/connections/c2r_selinux_domain/C2rStatusHost.py "$top/SOURCES/"
cp /src/tests/connections/c2r_selinux_domain/postapollo_connections.te "$top/SOURCES/"
cp /src/tests/connections/c2r_selinux_domain/postapollo_connections.fc "$top/SOURCES/"
cp /src/services/connections/experiments/c2n_package/postapollo-connections-status.service.template "$top/SOURCES/"
cp /src/services/connections/experiments/c2n_package/org.postapollo.ConnectionsStatus1.conf.template "$top/SOURCES/"

for version in 0.1 0.2; do
    sed "s/@VERSION@/$version/g" \
       /src/tests/connections/c2t_signed_rpm/status-fixture.spec.in \
       > "$top/SPECS/status-fixture.spec"
    rpmbuild --define "_topdir $top" --define "_build_id_links none" -bb \
       "$top/SPECS/status-fixture.spec"
    rpmfile="$(find "$top/RPMS/noarch" -maxdepth 1 -type f \
       -name "postapollo-connections-c2t-fixture-$version-*.noarch.rpm" -print -quit)"
    [[ -s "$rpmfile" ]] || { echo "C2T_FAIL // RPM_BUILD_MISSING_$version"; exit 2; }
    # RPM native OpenPGP signature, not merely an adjacent .asc file.
    rpmsign --addsign \
       --define "_gpg_name $fingerprint" \
       --define "_gpg_path $keydir" \
       "$rpmfile"
    scripts="$(rpm -qp --scripts "$rpmfile")"
    [[ -z "$scripts" ]] || { echo "C2T_FAIL // UNEXPECTED_RPM_SCRIPTLETS"; exit 2; }
    cp "$rpmfile" "/out/c2t-$version.rpm"
    echo "C2T_PASS // BUILT_NATIVE_SIGNED_RPM_VERSION_$version"
done

(
  cd /out
  sha256sum c2t-0.1.rpm c2t-0.2.rpm c2t-disposable-public.asc \
     > c2t-artifact-manifest.sha256
)
# Private key is not within /out and disappears with container.
[[ "$(find /out -maxdepth 1 -type f | wc -l)" == 5 ]] || {
    echo "C2T_FAIL // OUTPUT_SET_NOT_EXACT"; exit 2;
}
echo "C2T_PASS // ONLY_PUBLIC_KEY_TWO_RPMS_AND_MANIFESTS_EXPORTED"
echo "C2T_LIMITATION // EPHEMERAL_SELF_SIGNED_TEST_KEY_NOT_RELEASE_TRUST"
