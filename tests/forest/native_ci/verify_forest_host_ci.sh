#!/usr/bin/env bash
set -euo pipefail

# Only the fresh disposable verification container; no operator host install.
[[ "${GITHUB_ACTIONS:-}" == true && -f /.dockerenv && "$(id -u)" == 0 ]]
[[ "${EXPECTED_SOURCE_SHA:-}" =~ ^[a-f0-9]{64}$ ]]
package=/input/forest-host-ci.rpm
name=post-apollo-forest-host-ci
directory=/usr/libexec/post-apollo/forest-ci
host="$directory/forest-host"
dnf -y install python3 util-linux
[[ -f "$package" && ! -e "$directory" ]]
if rpm -q "$name" >/dev/null 2>&1; then exit 1; fi
[[ "$(rpm -qp --qf '%{NAME}' "$package")" == "$name" ]]
[[ -z "$(rpm -qp --scripts "$package")" ]]
[[ -z "$(rpm -qp --triggers "$package")" ]]
[[ "$(rpm -qpl "$package" | LC_ALL=C sort)" == "$(printf '%s\n' "$directory" "$host")" ]]
echo B5C_RPM_ROSTER_NO_ACTIVATION_PASS

# Unsigned CI artifact, never a production trust root.
rpm -Uvh "$package"
[[ "$(rpm -q --qf '%{NAME}' -f "$host")" == "$name" ]]
[[ -f "$host" && ! -L "$host" && -d "$directory" && ! -L "$directory" ]]
[[ "$(stat -c '%u:%g:%a' "$directory")" == 0:0:755 ]]
[[ "$(stat -c '%u:%g:%a' "$host")" == 0:0:555 ]]
[[ "$(sha256sum "$host" | cut -d ' ' -f1)" == "$EXPECTED_SOURCE_SHA" ]]
rpm -V "$name"
echo B5C_INSTALLED_EXACT_BYTES_AND_MODE_PASS

# Run real test requester and child under the same unprivileged CI UID.
# No seat, protected DB, installed independent identity, or production grant.
install -m 0444 /ci/test_installed_forest_host_b5c.py /tmp/test_installed_forest_host_b5c.py
runuser -u nobody -- /usr/bin/python3 -I -B /tmp/test_installed_forest_host_b5c.py "$EXPECTED_SOURCE_SHA"
rpm -V "$name"

rpm -e "$name"
if rpm -q "$name" >/dev/null 2>&1; then exit 1; fi
[[ ! -e "$host" && ! -e "$directory" ]]
echo B5C_PACKAGE_REMOVAL_PASS
echo B5C_INSTALLED_CANDIDATE_CI_PASS
