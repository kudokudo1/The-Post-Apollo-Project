#!/usr/bin/env bash
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && -f /.dockerenv && "$(id -u)" == 0 ]]
[[ "${EXPECTED_SOURCE_SHA:-}" =~ ^[a-f0-9]{64}$ ]]
name=post-apollo-forest-host-ci
directory=/usr/libexec/post-apollo/forest-ci
host="$directory/forest-host"
package=/input/forest-host-ci.rpm
dnf -y install python3
[[ ! -e "$directory" ]]
if rpm -q "$name" >/dev/null 2>&1; then exit 1; fi
[[ "$(rpm -qp --qf '%{NAME}' "$package")" == "$name" ]]
[[ -z "$(rpm -qp --scripts "$package")" && -z "$(rpm -qp --triggers "$package")" ]]
[[ "$(rpm -qpl "$package" | LC_ALL=C sort)" == "$(printf '%s\n' "$directory" "$host")" ]]
rpm -Uvh "$package"
[[ -f "$host" && ! -L "$host" && -d "$directory" && ! -L "$directory" ]]
[[ "$(stat -c '%u:%g:%a' "$directory")" == 0:0:755 ]]
[[ "$(stat -c '%u:%g:%a' "$host")" == 0:0:555 ]]
[[ "$(sha256sum "$host" | cut -d ' ' -f1)" == "$EXPECTED_SOURCE_SHA" ]]
rpm -V "$name"
# The test itself has no network operations, private data or installed service.
# Staged test sources are read-only Docker mounts; not production launcher code.
python3 -I -B /ci/test_split_uid_host_b5f.py
echo B5F_SPLIT_UID_TESTS_PASS
rpm -V "$name"
rpm -e "$name"
if rpm -q "$name" >/dev/null 2>&1; then exit 1; fi
[[ ! -e "$host" && ! -e "$directory" ]]
echo B5F_PACKAGE_REMOVAL_PASS
