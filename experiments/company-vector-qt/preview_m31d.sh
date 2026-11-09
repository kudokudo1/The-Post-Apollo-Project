#!/usr/bin/env bash
# Company M31d // optional standalone Fedora MapLibre visual preview.
# Executes ONLY from a dedicated source checkout in the existing vector lab.
# Never checks out, overwrites, pulls or restarts live Quickshell / SwayPX.
set -euo pipefail

fail() { printf 'COMPANY_M31D_REFUSED: %s\n' "$*" >&2; exit 2; }
usage() {
  printf 'Usage: bash preview_m31d.sh check|build|run-offline|run-online\n' >&2
  exit 2
}
[[ $# -eq 1 ]] || usage
case "$1" in check|build|run-offline|run-online) ;; *) usage ;; esac

# Do not permit path/environment overrides to trick this helper into touching
# the owner's live ~/.config/quickshell tree or an arbitrary repository.
[[ "$(id -u)" -ne 0 && "$(id -ru)" -eq "$(id -u)" ]] ||
  fail 'nonroot, same-UID execution required'
[[ -n "${HOME:-}" && -d "$HOME" ]] || fail 'HOME unavailable'
lab="$HOME/postapollo-vector-lab"
expected="$lab/company-preview-src"
helper_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
root="$(cd -- "$helper_dir/../.." && pwd -P)"
[[ "$root" == "$expected" ]] ||
  fail "source checkout must be the isolated $expected (never live Quickshell)"
[[ -d "$root/.git" && ! -L "$root/.git" ]] ||
  fail 'dedicated Git clone not found'
[[ -f "$root/experiments/company-vector-qt/fedora_lab_m14.sh" ]] ||
  fail 'existing Fedora M14 lab helper missing'
[[ -f "$root/experiments/company-vector-qt/main.cpp" &&
   -f "$root/experiments/company-vector-qt/main.qml" ]] ||
  fail 'original Company native Qt probe missing'
[[ ! -L "$lab" && ! -L "$root" ]] ||
  fail 'symlink lab/source paths are not allowed'
[[ -z "${POST_APOLLO_REPO:-}" && -z "${POST_APOLLO_VECTOR_LAB:-}" ]] ||
  fail 'do not override preview source or lab paths'
[[ -z "${QSG_RHI_BACKEND:-}" ]] ||
  fail 'global Qt renderer override is not permitted for this preview'

if [[ "$1" == run-online ]]; then
  printf 'COMPANY_M31D_ONLINE_CONSENT: explicit public OpenFreeMap tile requests may disclose IP and viewport.\n' >&2
fi

printf 'COMPANY_M31D_PREVIEW mode=%s source=isolated-clone production=OFF live_quickshell=UNCHANGED\n' "$1"
# M14 already validates the pinned MapLibre install and Qt module versions,
# builds strictly under $lab/company-vector-build and runs a single Qt process.
exec env POST_APOLLO_REPO="$root" POST_APOLLO_VECTOR_LAB="$lab" \
  bash "$root/experiments/company-vector-qt/fedora_lab_m14.sh" "$1"
