#!/usr/bin/env bash
# M14: isolated Fedora Toolbox test of the existing Company vector probe.
# Does not install to ~/.local, change Quickshell, or import Company records.
set -euo pipefail

fail() { printf 'M14_BLOCKED: %s\n' "$*" >&2; exit 2; }
usage() {
  printf 'Usage: bash fedora_lab_m14.sh check|build|run-offline|run-online\n' >&2
  exit 2
}
[[ $# -eq 1 ]] || usage
case "$1" in check|build|run-offline|run-online) ;; *) usage ;; esac
ACTION="$1"
LAB="${POST_APOLLO_VECTOR_LAB:-$HOME/postapollo-vector-lab}"
REPO="${POST_APOLLO_REPO:-$HOME/.config/quickshell}"
PREFIX="$LAB/maplibre-install"
SOURCE="$REPO/experiments/company-vector-qt"
BUILD="$LAB/company-vector-build"
QMAPLIBRE_DIR="$PREFIX/lib64/cmake/QMapLibre"

command -v pkg-config >/dev/null || fail 'pkg-config missing in Toolbox'
command -v cmake >/dev/null || fail 'cmake missing in Toolbox'
for file in \
  "$SOURCE/CMakeLists.txt" \
  "$SOURCE/main.cpp" \
  "$SOURCE/main.qml" \
  "$SOURCE/style-fixture.json" \
  "$SOURCE/style-post-apollo-online.json" \
  "$QMAPLIBRE_DIR/QMapLibreConfig.cmake" \
  "$PREFIX/lib64/libQMapLibre.so.3.0.0" \
  "$PREFIX/lib64/libQMapLibreLocation.so.3.0.0" \
  "$PREFIX/qml/MapLibre/qmldir" \
  "$PREFIX/plugins/geoservices/libqtgeoservices_maplibre.so"; do
  [[ -f "$file" ]] || fail "required file missing: $file"
done
qt_version="$(pkg-config --modversion Qt6Core)" || fail 'Qt6Core unavailable'
for module in Qt6Quick Qt6Location Qt6Positioning; do
  version="$(pkg-config --modversion "$module")" || fail "$module unavailable"
  [[ "$version" == "$qt_version" ]] || fail "$module version $version differs from Qt6Core $qt_version"
done
printf 'M14_PREFLIGHT_PASSED Qt=%s\n' "$qt_version"
[[ "$ACTION" != check ]] || exit 0

if [[ "$ACTION" == build ]]; then
  # Only creates build products inside the already dedicated lab.
  cmake -S "$SOURCE" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$PREFIX" \
    -DQMapLibre_DIR="$QMAPLIBRE_DIR"
  cmake --build "$BUILD" --parallel 3
  [[ -x "$BUILD/company-vector-probe" ]] || fail 'Company vector binary not built'
  printf 'M14_COMPANY_PROBE_BUILT %s\n' "$BUILD/company-vector-probe"
  exit 0
fi

[[ -x "$BUILD/company-vector-probe" ]] || fail 'Build the Company probe first: bash fedora_lab_m14.sh build'
export LD_LIBRARY_PATH="$PREFIX/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="$PREFIX/plugins${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
export QML_IMPORT_PATH="$PREFIX/qml${QML_IMPORT_PATH:+:$QML_IMPORT_PATH}"
export QML2_IMPORT_PATH="$PREFIX/qml${QML2_IMPORT_PATH:+:$QML2_IMPORT_PATH}"
# C++ sets OpenGL RHI process-locally; no global Quickshell graphics changes.
cd "$BUILD"
if [[ "$ACTION" == run-online ]]; then
  printf 'M14_ONLINE_CONSENT: public viewport tiles and IP are sent to OpenFreeMap.\n' >&2
  exec "$BUILD/company-vector-probe" --styled-online
fi
exec "$BUILD/company-vector-probe"
