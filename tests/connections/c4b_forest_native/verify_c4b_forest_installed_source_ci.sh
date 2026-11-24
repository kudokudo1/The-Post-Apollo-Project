#!/usr/bin/env bash
set -euo pipefail
# Real Fedora CI container only, never an operator host.
[[ "$GITHUB_ACTIONS" == true && -f /.dockerenv && "$(id -u)" == 0 ]]
[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{64}$ ]]
package=/input/forest-host-ci.rpm
name=post-apollo-forest-host-ci
host=/usr/libexec/post-apollo/forest-ci/forest-host
dnf -y install python3
[[ -f "$package" && ! -e "$host" ]]
[[ "$(rpm -qp --qf '%{NAME}' "$package")" == "$name" ]]
[[ -z "$(rpm -qp --scripts "$package")" && -z "$(rpm -qp --triggers "$package")" ]]
[[ "$(rpm -qpl "$package" | LC_ALL=C sort)" == \
   "$(printf '%s\n' /usr/libexec/post-apollo/forest-ci "$host")" ]]
rpm -Uvh "$package"
[[ "$(rpm -q --qf '%{NAME}' -f "$host")" == "$name" ]]
[[ "$(stat -c '%u:%g:%a' "$host")" == 0:0:555 ]]
[[ "$(sha256sum "$host" | cut -d ' ' -f1)" == "$EXPECTED_SOURCE_SHA" ]]
rpm -V "$name"
echo C4B_FOREST_ACTUAL_INSTALLED_BYTES_CI_PASS
python3 -I -B /ci/test_c4b_forest_installed_source_ci.py
echo C4B_FOREST_ACTUAL_PROCESS_RENDERER_FD_HOLD_PASS
rpm -V "$name"
rpm -e "$name"
[[ ! -e "$host" && ! -e /usr/libexec/post-apollo/forest-ci ]]
echo C4B_FOREST_DISPOSABLE_TEST_RPM_REMOVED_PASS
echo C4B_FOREST_CI_ONLY_NO_SOURCE_ENROLLMENT_OR_C5_CONSENT
