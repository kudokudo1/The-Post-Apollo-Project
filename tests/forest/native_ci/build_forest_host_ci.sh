#!/usr/bin/env bash
set -euo pipefail

# A guard against accidental workstation invocation; NOT authorization.
[[ "${GITHUB_ACTIONS:-}" == true && -f /.dockerenv && "$(id -u)" == 0 ]]
[[ -d /source && -d /out && -n "${EXPECTED_SOURCE_SHA:-}" ]]
[[ "$EXPECTED_SOURCE_SHA" =~ ^[a-f0-9]{64}$ ]]
source_file=/source/scripts/forest/native_host_candidate_b5b.py
spec=/source/tests/forest/native_ci/forest_host_ci.spec
[[ "$(sha256sum "$source_file" | cut -d ' ' -f1)" == "$EXPECTED_SOURCE_SHA" ]]
dnf -y install rpm-build python3
top="$(mktemp -d)"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
install -m 0444 "$source_file" "$top/SOURCES/native_host_candidate_b5b.py"
rpmbuild -bb --define "_topdir $top" "$spec"
shopt -s nullglob
packages=("$top"/RPMS/noarch/post-apollo-forest-host-ci-*.rpm)
[[ "${#packages[@]}" == 1 ]]
[[ ! -e /out/forest-host-ci.rpm ]]
install -m 0644 "${packages[0]}" /out/forest-host-ci.rpm
sha256sum /out/forest-host-ci.rpm
echo B5C_RPM_BUILD_PASS
