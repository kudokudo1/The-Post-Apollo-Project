#!/usr/bin/bash
# C4b CI-only policy RPM build/sign. Disposable self-signed key is NOT trusted.
set -Eeuo pipefail
[[ "$(id -u)" == 0 && -f /src/tests/connections/c4b_silverblue/signed-compose-policy.spec &&
   -f /src/tests/connections/c2r_selinux_domain/postapollo_connections.te &&
   -d /out ]] || { echo "C4B_POLICY_BUILDER_NOT_ISOLATED"; exit 2; }
dnf -y --setopt=install_weak_deps=False install \
  rpm-build rpm-sign gnupg2 selinux-policy-devel make
umask 077
work="$(mktemp -d /tmp/c4b-compose-policy-XXXXXX)"
trap 'rm -rf "$work"' EXIT
top="$work/rpmbuild"
keydir="$work/gnupg"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$keydir" "$work/policy"
chmod 0700 "$keydir"
cp /src/tests/connections/c2r_selinux_domain/postapollo_connections.{te,fc} "$work/policy/"
(cd "$work/policy" && make -f /usr/share/selinux/devel/Makefile postapollo_connections.pp)
install -m 0644 "$work/policy/postapollo_connections.pp" "$top/SOURCES/"
install -m 0644 "$work/policy/postapollo_connections.pp" /out/postapollo_connections.pp
cp /src/tests/connections/c4b_silverblue/signed-compose-policy.spec "$top/SPECS/"
rpmbuild --define "_topdir $top" --define "_build_id_links none" \
  -bb "$top/SPECS/signed-compose-policy.spec"
rpmfile="$(find "$top/RPMS/noarch" -maxdepth 1 -type f \
  -name 'postapollo-connections-c4b-policy-ci-0.1-*.noarch.rpm' -print -quit)"
[[ -s "$rpmfile" ]] || { echo "C4B_POLICY_RPM_NOT_BUILT"; exit 2; }
identity="Post Apollo C4b Disposable SELinux Policy <c4b-noreply@example.invalid>"
gpg --homedir "$keydir" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key "$identity" rsa2048 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$keydir" --batch --with-colons --list-keys |
  awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" =~ ^[A-Fa-f0-9]{40}$ ]] ||
  { echo "C4B_POLICY_SIGNER_FINGERPRINT_INVALID"; exit 2; }
gpg --homedir "$keydir" --batch --armor --export "$fingerprint" > /out/c4b-policy-public.asc
printf '%s\n' "$fingerprint" > /out/c4b-policy-fingerprint.txt
rpmsign --addsign --define "_gpg_name $fingerprint" \
  --define "_gpg_path $keydir" "$rpmfile"
[[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}\n' "$rpmfile")" == \
  "postapollo-connections-c4b-policy-ci 0.1 noarch" ]] ||
  { echo "C4B_POLICY_UNEXPECTED_PACKAGE_ID"; exit 2; }
[[ "$(rpm -qpl "$rpmfile")" == \
  "/usr/share/selinux/packages/targeted/postapollo_connections.pp" ]] ||
  { echo "C4B_POLICY_UNEXPECTED_PAYLOAD"; exit 2; }
scripts="$(rpm -qp --scripts "$rpmfile")"
[[ "$scripts" == *"/usr/sbin/semodule -i /usr/share/selinux/packages/targeted/postapollo_connections.pp"* &&
   "$scripts" == *"/usr/sbin/semodule -r postapollo_connections"* ]] ||
  { echo "C4B_POLICY_SCRIPTLET_CONTENT_UNEXPECTED"; exit 2; }
[[ -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "C4B_POLICY_TRIGGERS_FORBIDDEN"; exit 2; }
cp "$rpmfile" /out/c4b-policy.rpm
(cd /out && sha256sum c4b-policy.rpm c4b-policy-public.asc \
  c4b-policy-fingerprint.txt > c4b-policy-artifact-manifest.sha256)
chmod 0644 /out/{postapollo_connections.pp,c4b-policy.rpm,c4b-policy-public.asc,c4b-policy-fingerprint.txt,c4b-policy-artifact-manifest.sha256}
[[ "$(find /out -maxdepth 1 -type f | wc -l)" == 5 ]] ||
  { echo "C4B_POLICY_UNEXPECTED_OUTPUT_FILES"; exit 2; }
echo "C4B_PASS // DISPOSABLE_SIGNED_SELINUX_POLICY_RPM_READY_FOR_OSTREE_COMPOSITION"
echo "C4B_LIMITATION // TEST_SIGNER_NOT_PRODUCTION_TRUST"
