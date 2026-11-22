#!/usr/bin/env python3
"""Hermetic regression: no live app, D-Bus, systemd or Quickshell mutation."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/tray/persistent_watcher.sh"
source = PROBE.read_text(encoding="utf-8")
assert 'busctl --user --no-pager list' in source
assert 'WATCHER_CURRENT_OWNER=ABSENT' in source
assert 'TRAY_REGISTRY_STATUS=PERSISTENCE_NOT_VERIFIED' in source
assert 'systemctl --user enable "$unit"' in source
for forbidden in ('systemctl --user restart', 'systemctl --user start', '--now',
                  'pkill ', 'killall ', 'quickshell --', 'rpm-ostree install',
                  'sudo dnf', 'busctl --user call'):
    # "--now" is allowed only as an explicit NO-OP warning/comment.
    if forbidden == "--now":
        assert '"--now"' in source
    else:
        assert forbidden not in source, forbidden

with tempfile.TemporaryDirectory(prefix="post-apollo-tray-") as directory:
    root = Path(directory)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    marker = root / "enabled"
    systemctl = bin_dir / "systemctl"
    systemctl.write_text("""#!/bin/sh
case "$*" in
  "--user show -p Type --value sni-watcher.service") echo "${MOCK_TYPE:-dbus}" ;;
  "--user show -p BusName --value sni-watcher.service") echo "${MOCK_BUS:-org.kde.StatusNotifierWatcher}" ;;
  "--user show -p ActiveState --value sni-watcher.service") echo "${MOCK_STATE:-inactive}" ;;
  "--user show -p UnitFileState --value sni-watcher.service") echo disabled ;;
  "--user cat sni-watcher.service")
    printf '%s\\n' '[Unit]' 'Before=graphical-session-pre.target' '[Service]' \\
      'Type=dbus' 'BusName=org.kde.StatusNotifierWatcher' \\
      'ExecStart=/usr/bin/sni-watcher' '[Install]' \\
      'WantedBy=graphical-session-pre.target'
    ;;
  "--user enable sni-watcher.service") printf enabled > "$MOCK_MARKER" ;;
  *) echo "Unexpected systemctl: $*" >&2; exit 99 ;;
esac
""", encoding="utf-8")
    systemctl.chmod(0o755)
    busctl = bin_dir / "busctl"
    busctl.write_text("""#!/bin/sh
[ "$*" = "--user --no-pager list" ] || exit 98
printf 'NAME PID PROCESS USER\\n'
if [ "${MOCK_NO_WATCHER:-0}" != 1 ]; then
    printf 'org.kde.StatusNotifierWatcher 123 quickshell tester\\n'
fi
""", encoding="utf-8")
    busctl.chmod(0o755)

    def run(*arguments, **overrides):
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                   MOCK_MARKER=str(marker))
        env.update(overrides)
        return subprocess.run(["bash", str(PROBE), *arguments],
                              capture_output=True, text=True, env=env, timeout=15)

    normal = run()
    assert normal.returncode == 0, normal.stderr
    assert "TRAY_REGISTRY_STATUS=PERSISTENCE_NOT_VERIFIED" in normal.stdout
    assert not marker.exists(), "default mode must never enable services"

    live = run("--status", MOCK_STATE="active")
    assert live.returncode == 0
    assert "TRAY_REGISTRY_STATUS=PERSISTENT_WATCHER_ACTIVE" in live.stdout
    assert not marker.exists()

    absent = run("--status", MOCK_NO_WATCHER="1", MOCK_STATE="active")
    assert "WATCHER_CURRENT_OWNER=ABSENT" in absent.stdout
    assert "PERSISTENCE_NOT_VERIFIED" in absent.stdout

    bad = run("--enable-next-login", MOCK_BUS="unexpected.bus")
    assert bad.returncode == 78 and not marker.exists()

    incorrect = run("--enable-next-login", MOCK_TYPE="simple")
    assert incorrect.returncode == 78 and not marker.exists()

    usage = run("--invalid")
    assert usage.returncode == 64 and not marker.exists()

    enabled = run("--enable-next-login")
    assert enabled.returncode == 0, enabled.stderr
    assert marker.read_text(encoding="utf-8") == "enabled"
    assert "NEXT_LOGIN_ENABLED=YES" in enabled.stdout

print("Persistent SNI watcher preflight: inspect-only default, guarded next-login action PASS")
