#!/usr/bin/env bash
set -euo pipefail

# Standalone simulation only. Stage the actual shared component module below
# a temporary Quickshell root; never load the repository's production shell.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
case "${1:-preview}" in
  preview) fixture=EnergyProgressPreview.qml ;;
  native) fixture=EnergyProgressNative.qml ;;
  load) fixture=EnergyProgressLoadNative.qml ;;
  queue) fixture=EnergyProgressQueueNative.qml ;;
  *) echo "Usage: $0 [preview|native|load|queue]" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || exit 2
qs_bin="$(command -v quickshell)" || { echo "quickshell not installed" >&2; exit 2; }
work="$(mktemp -d -t energy-progress.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/config"
cp "$repo_root/tests/fixtures/$fixture" "$work/config/shell.qml"
cp -a "$repo_root/components" "$work/config/components"
if [ "$fixture" = EnergyProgressQueueNative.qml ]; then
  mkdir -p "$work/config/widgets"
  cp "$repo_root/widgets/GitHubPullRequestControlView.qml" "$work/config/widgets/"
fi
# In the native CI case, the caller supplies isolated HOME/XDG/display.
# For manual preview preserve the caller's compositor socket and display.
"$qs_bin" --no-color --log-rules "qml.debug=true" -p "$work/config/shell.qml"
