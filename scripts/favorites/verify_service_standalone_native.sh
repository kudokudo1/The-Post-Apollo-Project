#!/usr/bin/env bash
set -euo pipefail
# Synthetic Fedora native proof. No widget sources or real user settings.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb timeout sha256sum node; do
  command -v "$cmd" >/dev/null || { echo "FB_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/favorites-standalone.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT

install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-home" "$work/config/services/favorites"
# Keep singleton resolution valid, but copy NO AppControl or CPU++ sources.
cp "$repo/services/favorites/"* "$work/config/services/favorites/"
cp "$repo/tests/favorites/fixtures/FavoritesServiceStandaloneNative.qml" \
  "$work/config/shell.qml"
test ! -e "$work/config/widgets/AppControlW.qml"
test ! -e "$work/config/widgets/CpuPlusW.qml"

Xvfb :99 -screen 0 1024x768x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

run_phase() {
  local phase="$1" marker="$2" log="$work/$1.log" rc
  local shell_path="${3:-$work/config/shell.qml}" data_path="${4:-$work/data}"
  echo "FB_PHASE // $phase"
  set +e
  timeout --signal=TERM --kill-after=3s 18s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$data_path" XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" FB_PHASE="$phase" \
    quickshell --no-color --log-rules "qml.debug=true" \
    -p "$shell_path" >"$log" 2>&1
  rc="$?"
  set -e
  cat "$log"
  if [ "$rc" -ne 0 ] || grep -F "FB_FAIL" "$log" >/dev/null 2>&1 \
      || ! grep -F "$marker" "$log" >/dev/null 2>&1; then
    echo "FB_FAIL // phase=$phase rc=$rc or missing marker=$marker"
    return 1
  fi
}

run_phase save "FB_PASS // STANDALONE_SERVICE_WRITE"
saved="$(find "$work/data" -name appcontrol-favorites.json -print -quit)"
[ -n "$saved" ] && [ -f "$saved" ] || {
  echo "FB_FAIL // original persisted JSON absent"; exit 1;
}
node - "$saved" <<'NODE'
const fs = require("node:fs");
const assert = require("node:assert/strict");
const path = process.argv[2];
const data = JSON.parse(fs.readFileSync(path,"utf8"));
assert.deepEqual(data, {
  favoriteKeys: ["file:/tmp/favorites-synthetic-only","task|firefox"],
  favoriteDetailActionKeys: ["app|synthetic.desktop|desktop|Open"],
  favoriteMonitorBoxKeys: ["watchbox|system|cpu|load"],
  favoriteTaskMetricKeys: ["taskmetric|firefox|cpu"]
});
console.log("FB_PASS // ORIGINAL_FOUR_ARRAY_JSON_UNCHANGED");
NODE
for sibling in favorites-default-v1.json favorites-collections-v1.json; do
  [ -z "$(find "$work/data" -name "$sibling" -print -quit)" ] || {
    echo "FB_FAIL // unrelated writer created $sibling"; exit 1;
  }
done
before="$(sha256sum "$saved" | cut -d' ' -f1)"
run_phase read "FB_PASS // STANDALONE_RESTART_READ_ONLY"
after="$(sha256sum "$saved" | cut -d' ' -f1)"
[ "$before" = "$after" ] || {
  echo "FB_FAIL // readback changed original JSON bytes"; exit 1;
}
echo "FB_PASS // WIDGET_INDEPENDENT_MEMBERSHIP_LIFECYCLE"

# Native QML integration of the exact current AppControl Favorites binding
# and wrappers, against synthetic provider rows and an independent data dir.
install -d -m 700 "$work/binding-data"
node - "$repo/widgets/AppControlW.qml" "$repo/tests/favorites/fixtures/FavoritesAppControlBindingNative.qml" "$work/config/binding.qml" <<'NODE'
const fs=require("node:fs");
const [source,template,out]=process.argv.slice(2);
const host=fs.readFileSync(source,"utf8");
const names=["favoriteKeyFor","favoriteRecordForApp","favoriteRecordForRunCommand",
  "favoriteRecordForModeItem","favoriteRecordForTaskIdentity","isFavoriteItem",
  "monitorEntryHasBoxFavorite","taskPersistentIdentity","taskIdentityFromFavoriteKey",
  "taskMetricFavoriteData","runFavoriteKey","runFavoriteDataFromKey",
  "detailFavoriteContextKey","detailActionStableId","detailFavoriteKeyFor"];
const wrappers=names.map(name=>{
  const start=host.indexOf("    function "+name+"(");
  const end=host.indexOf("\n    }",start);
  if(start<0||end<start)throw Error("Missing wrapper "+name);
  return host.slice(start,end+6);
});
const start=host.indexOf("    ScriptModel {\n        id: favoriteResults");
const end=host.indexOf("    function resultCount()",start);
if(start<0||end<start)throw Error("Missing Favorites ScriptModel");
const model=host.slice(start,end).trimEnd();
if(!model.endsWith("}")||!model.includes("FavoriteCombi.buildLocalCatalog(")
    ||!model.includes("DesktopEntries.applications.values"))throw Error("Unexpected model shape");
const fixture=fs.readFileSync(template,"utf8");
if(!fixture.includes("// INSERT_APP_CONTROL_BINDING"))throw Error("Missing fixture marker");
fs.writeFileSync(out,fixture.replace("// INSERT_APP_CONTROL_BINDING",
  wrappers.join("\n\n")+"\n\n"+model.replace("DesktopEntries.applications.values","fixtureDesktopEntries.applications.values")));
NODE
run_phase binding "FB_PASS // APP_CONTROL_EXACT_BINDING_REACTIVE" "$work/config/binding.qml" "$work/binding-data"
