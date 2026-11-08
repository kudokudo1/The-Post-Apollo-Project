#!/usr/bin/env bash
set -euo pipefail
# CI-only native Fedora Xvfb fixture with disposable HOME/XDG directories.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout sha256sum; do
  command -v "$cmd" >/dev/null || { echo "U3_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/favorites-u3.XXXXXXXX)"
pid=""
xpid=""
cleanup(){
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-home" "$work/config/services/favorites"
cp -a "$repo/components" "$work/config/components"
cp "$repo/services/favorites/"* "$work/config/services/favorites/"
cp "$repo/tests/favorites/fixtures/FavoritesU3NativeProbe.qml" \
  "$work/config/shell.qml"
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
wait_for(){
  local marker="$1"
  for ((i=0;i<160;i++)); do
    if grep -F "U3_FAIL" "$log" >/dev/null 2>&1; then
      cat "$log"
      echo "U3_FAIL // stopped before marker: $marker"
      return 1
    fi
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "U3_FAIL // exited without marker: $marker"
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "U3_FAIL // marker timeout: $marker"
  return 1
}
phase(){
  local name="$1" success="$2"
  log="$work/$name.log"
  echo "U3_PHASE // $name"
  timeout --signal=TERM --kill-after=3s 22s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" U3_PHASE="$name" \
    quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" >"$log" 2>&1 &
  pid="$!"
  if [ "$name" = "save" ]; then
    wait_for "U3_READY // x="
    local window coords x y
    window="$(xdotool search --onlyvisible --name "U3-COLLECTIONS" | head -n 1)"
    [ -n "$window" ] || { cat "$log"; echo "U3_FAIL // no window"; return 1; }
    xdotool windowmove "$window" 0 0
    coords="$(grep -F "U3_READY // x=" "$log" | tail -n 1 |
      sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
    read -r x y <<<"$coords"
    [ -n "$x" ] && [ -n "$y" ] ||
      { echo "U3_FAIL // missing click coordinates"; return 1; }
    xdotool mousemove --window "$window" "$x" "$y" click 1
  fi
  wait_for "$success"
  local rc
  set +e
  wait "$pid"
  rc="$?"
  set -e
  pid=""
  cat "$log"
  if grep -F "U3_FAIL" "$log" >/dev/null; then
    echo "U3_FAIL // phase=$name contained failure marker"; return 1
  fi
  [ "$rc" -eq 0 ] || { echo "U3_FAIL // process rc=$rc"; return 1; }
}
phase save "U3_PASS // NATIVE_CLICK_RAPID_WRITE_ORDER"
saved="$(find "$work/data" -name favorites-collections-v1.json -print -quit)"
[ -n "$saved" ] && [ -f "$saved" ] ||
  { echo "U3_FAIL // missing saved document"; exit 1; }
node - "$saved" <<'NODE'
const assert=require("node:assert/strict"),fs=require("node:fs");
const doc=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
assert.deepEqual(doc,{
  schema:"post-apollo.favorites.collections.v1",version:1,revision:4,
  nextId:2,
  collections:[{id:"c1",name:"Synthetic Group",members:[
    "fav1:local:places:saved-place:12",
    "fav1:local:time:timezone:UTC"
  ]}]
});
console.log("U3_PASS // EXACT_LOCAL_COLLECTION_REFERENCE_DOCUMENT");
NODE
for legacy in appcontrol-favorites.json favorites-default-v1.json \
  weather-home-favorites-v1.json time-world-favorites-v1.json places-v1.json \
  notification-favorites.json hospital-reception.json weather-radio-memory.json; do
  [ -z "$(find "$work/data" -name "$legacy" -print -quit)" ] ||
    { echo "U3_FAIL // unrelated writer touched $legacy"; exit 1; }
done
before="$(sha256sum "$saved" | cut -d' ' -f1)"
phase read "U3_PASS // RESTART_READBACK"
after="$(sha256sum "$saved" | cut -d' ' -f1)"
[ "$before" = "$after" ] ||
  { echo "U3_FAIL // reading changed bytes"; exit 1; }

printf '{"schema":' >"$saved"
before="$(sha256sum "$saved" | cut -d' ' -f1)"
phase corrupt "U3_PASS // CORRUPT_PRESERVED"
after="$(sha256sum "$saved" | cut -d' ' -f1)"
[ "$before" = "$after" ] ||
  { echo "U3_FAIL // corrupt file overwritten"; exit 1; }

printf '{"schema":"post-apollo.favorites.collections.v1","version":99,"revision":0,"nextId":1,"collections":[]}\n' >"$saved"
before="$(sha256sum "$saved" | cut -d' ' -f1)"
phase unsupported "U3_PASS // UNSUPPORTED_PRESERVED"
after="$(sha256sum "$saved" | cut -d' ' -f1)"
[ "$before" = "$after" ] ||
  { echo "U3_FAIL // unsupported version overwritten"; exit 1; }
echo "U3_PASS // NATIVE_ATOMIC_COLLECTIONS_RESTART_AND_REFUSAL"
