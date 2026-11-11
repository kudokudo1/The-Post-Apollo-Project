#!/usr/bin/bash
# Separate disposable Fedora verifier. Do not use the builder's key database.
set -Eeuo pipefail
[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${POST_APOLLO_ID_SILVERBLUE_CI_ONLY:-}" == 1 &&
   "$(id -u)" == 0 && -d /input ]] ||
  { echo "C4B_ID_REFUSED // NON_DISPOSABLE_VERIFICATION"; exit 2; }

dnf -y --setopt=install_weak_deps=False install rpm gnupg2
(cd /input && sha256sum --check --status identity-artifact-manifest.sha256) ||
  { echo "C4B_ID_FAIL // ARTIFACT_DIGEST_REFUSED"; exit 2; }
rpmfile=/input/identity-silverblue-ci.rpm
public=/input/identity-disposable-rpm-public.asc
[[ -s "$rpmfile" && -s "$public" &&
   "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")" == \
   'post-apollo-identity-silverblue-ci 0.1 noarch' ]] ||
  { echo "C4B_ID_FAIL // RPM_ROLE_REFUSED"; exit 2; }
[[ -z "$(rpm -qp --scripts "$rpmfile")" &&
   -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
  { echo "C4B_ID_FAIL // RPM_SCRIPTLETS_REFUSED"; exit 2; }

work="$(mktemp -d /tmp/c4b-id-verifier-XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
keydb="$work/rpmdb"
mkdir -m 0700 "$keydb"
rpm --dbpath "$keydb" --initdb
before="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1 || true)"
echo "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
  { echo "C4B_ID_FAIL // SIGNER_PRETRUSTED_BEFORE_IMPORT"; exit 2; }
rpmkeys --dbpath "$keydb" --import "$public"
after="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)" ||
  { echo "C4B_ID_FAIL // SIGNATURE_REFUSED"; exit 2; }
echo "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
  { echo "C4B_ID_FAIL // SIGNATURE_UNCONFIRMED"; exit 2; }
if echo "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
  echo "C4B_ID_FAIL // UNTRUSTED_SIGNATURE_RESULT"
  exit 2
fi
test "$(rpm -qpl "$rpmfile" | wc -l)" -eq 9 ||
  { echo "C4B_ID_FAIL // UNEXPECTED_INSTALLED_FILE_COUNT"; exit 2; }

# A verifier with a disposable imported public key proves the RPM signature;
# it does not prove any operator-controlled release-root or receipt key.
echo "C4B_ID_PASS // SEPARATELY_IMPORTED_DISPOSABLE_SIGNER_VERIFIED"
echo "C4B_ID_LIMITATION // NO_SELINUX_SYSTEMD_PROCESS_OR_OSTREE_ADMISSION"
