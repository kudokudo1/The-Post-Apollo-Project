#!/usr/bin/env bash
set -euo pipefail
# C2h native Quickshell -> C2f fake host -> QML status. CI-only.
if [[ "$GITHUB_ACTIONS" != "true" ]]; then
  echo "C2H_REFUSED_NOT_GITHUB_RUNNER"
  exit 2
fi
for name in quickshell python3 Xvfb timeout mktemp; do
  command -v "$name" >/dev/null || { echo "C2H_REFUSED_MISSING_TOOL"; exit 2; }
done

repo="$(cd "$(dirname "$0")/../../.." && pwd -P)"
umask 077
work="$(mktemp -d /tmp/postapollo-c2c-ci-XXXXXXXX)"
shell_pid=""
xvfb_pid=""
cleanup() {
  [[ -z "$shell_pid" ]] || kill "$shell_pid" 2>/dev/null || true
  [[ -z "$xvfb_pid" ]] || kill "$xvfb_pid" 2>/dev/null || true
  case "$work" in
    /tmp/postapollo-c2c-ci-*) rm -rf -- "$work";;
    *) echo "C2H_REFUSED_CLEANUP_PATH";;
  esac
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/config" "$work/config/widgets" \
  "$work/config/tests/connections/fixtures" "$work/run" \
  "$work/data" "$work/cache" "$work/config-home"
printf 'C2C_PRIVATE_SOCKETPAIR_ONLY\n' > "$work/.ci-only-authority"
chmod 600 "$work/.ci-only-authority"
cp -a "$repo/services" "$work/config/services"
cp -a "$repo/widgets/cpuplus" "$work/config/widgets/cpuplus"
cp -a "$repo/components" "$work/config/components"
cp "$repo/tests/connections/fixtures/C2cDescriptorBroker.py" \
   "$work/config/tests/connections/fixtures/C2cDescriptorBroker.py"
cp "$repo/tests/connections/fixtures/C2hStatusProducer.py" \
   "$work/config/tests/connections/fixtures/C2hStatusProducer.py"
cp "$repo/tests/connections/fixtures/C2hNativeStatusScene.qml" \
   "$work/config/shell.qml"

Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xvfb_pid="$!"
sleep 0.4
kill -0 "$xvfb_pid" 2>/dev/null || {
  echo "C2H_REFUSED_PRIVATE_DISPLAY"; exit 1;
}
set +e
timeout --signal=TERM --kill-after=3s 27s \
  env -i PATH="$PATH" LANG=C.UTF-8 \
  GITHUB_ACTIONS=true POST_APOLLO_C2C_FAKE_ONLY=1 \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" \
  DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software \
  quickshell --no-color -p "$work/config/shell.qml" \
  >"$work/quickshell.log" 2>&1
code=$?
set -e
if [[ "$code" != "0" ]] ||
   ! grep -Fq "C2H_NATIVE_STREAM_PASS // REAL_QML_FAKE_HOST_NO_GRANT" \
     "$work/quickshell.log" ||
   grep -Fq "C2H_NATIVE_STREAM_REFUSED" "$work/quickshell.log"; then
  # Only fixed markers, never whole child logs/request IDs.
  echo "C2H_REFUSED_NATIVE_STREAM_INCOMPLETE"
  exit 1
fi
if find "$work/home" -type f -print | grep -q .; then
  echo "C2H_REFUSED_UNEXPECTED_HOME_WRITE"
  exit 1
fi
echo "C2H_PASS // NATIVE_QML_REAL_FAKE_HOST_STREAM_OFFLINE_NO_CREDENTIALS"
