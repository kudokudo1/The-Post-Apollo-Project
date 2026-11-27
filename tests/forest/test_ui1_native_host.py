#!/usr/bin/env python3
"""CI-only real ForestW in a fresh private headless Sway. No operator desktop."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import sqlite3
import stat
from contextlib import closing

if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("FOREST_HOST_REQUIRES_GITHUB_ACTIONS")
if os.getuid() == 0:
    raise SystemExit("FOREST_HOST_REQUIRES_UNPRIVILEGED_UID")
ROOT = Path(__file__).resolve().parents[2]
if not any(line.strip() == "NoNewPrivs:\t1" for line in Path("/proc/self/status").read_text().splitlines()):
    raise SystemExit("FOREST_HOST_REQUIRES_NO_NEW_PRIVS")


def stop(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=4)


def joined_db_snapshot(private):
    paths = list(private.glob("forest-r5-public-*/conversation.sqlite"))
    if len(paths) != 1:
        raise AssertionError("JOINED_DB_COUNT")
    path = paths[0]
    directory = path.parent.stat(follow_symlinks=False)
    identity = path.stat(follow_symlinks=False)
    if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid()
            or directory.st_mode & 0o077 or not stat.S_ISREG(identity.st_mode)
            or identity.st_uid != os.getuid() or identity.st_nlink != 1):
        raise AssertionError("JOINED_DB_IDENTITY")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.5)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        revision = db.execute("SELECT revision FROM forest_sessions").fetchall()
        turns = db.execute("SELECT ordinal,role,turn_id FROM forest_turns ORDER BY ordinal").fetchall()
        attempts = db.execute("SELECT expected_revision,status,reply_turn_id FROM forest_attempts_b3 ORDER BY expected_revision").fetchall()
        db.rollback()
    observed = path.stat(follow_symlinks=False)
    if (observed.st_dev, observed.st_ino) != (identity.st_dev, identity.st_ino):
        raise AssertionError("JOINED_DB_CHANGED")
    return (identity.st_dev, identity.st_ino), revision, turns, attempts


def observe_joined_db(qs, scene, log):
    expected = ("BEFORE", "AFTER", "ABORT")
    snapshots = []
    deadline = time.monotonic() + 30
    while len(snapshots) < len(expected):
        if qs.poll() is not None or time.monotonic() >= deadline:
            raise AssertionError("JOINED_DB_GATE_INCOMPLETE")
        stages = [line.split("FOREST_HOST_DB_STAGE ", 1)[1].strip()
                  for line in log.read_text(errors="replace").splitlines()
                  if "FOREST_HOST_DB_STAGE " in line]
        if tuple(stages) != expected[:len(stages)] or len(stages) > len(snapshots)+1:
            raise AssertionError("JOINED_DB_GATE_ORDER")
        if len(stages) == len(snapshots):
            time.sleep(0.025)
            continue
        stage = stages[-1]
        snapshot = joined_db_snapshot(scene / "privateJoined")
        identity, revision, turns, attempts = snapshot
        roles = ["user", "assistant", "user", "assistant"]
        if stage == "ABORT":
            roles.append("user")
        if (revision != [(len(roles),)] or
                [(r[0], r[1]) for r in turns] != list(enumerate(roles, 1)) or
                len({r[2] for r in turns}) != len(roles) or
                [r[1] for r in attempts] != (["COMMITTED", "COMMITTED", "ABORTED"] if stage == "ABORT" else ["COMMITTED", "COMMITTED"]) or
                [r[2] for r in attempts[:2]] != [turns[1][2], turns[3][2]]):
            raise AssertionError("JOINED_DB_CONTENT")
        if stage == "AFTER" and snapshot != snapshots[0]:
            raise AssertionError("JOINED_DB_REOPEN_CHANGED")
        if stage == "ABORT" and (identity != snapshots[0][0] or
                turns[:4] != snapshots[0][2] or attempts[:2] != snapshots[0][3] or
                attempts[2][2] is not None):
            raise AssertionError("JOINED_DB_ABORT_CHANGED")
        snapshots.append(snapshot)
        # Only fixed test stage, no database identifiers or contents in QML.
        temporary = scene / "db-observer-ack.tmp"
        temporary.write_text(stage, encoding="ascii")
        temporary.replace(scene / "db-observer-ack")
        print("FOREST_HOST_DB_OBSERVED " + stage, flush=True)


def trial(width, height, count):
    with tempfile.TemporaryDirectory(prefix="forest-private-wayland-") as name:
        work = Path(name)
        for d in ("run", "home", "cache", "config-home", "data", "config"):
            (work / d).mkdir(mode=0o700)
        # Fedora may ship sway with file capabilities outside the Docker
        # capability bounding set, causing execve EPERM. Copy only bytes,
        # not xattrs or mode bits, into the private unprivileged directory.
        # Do not change /usr/bin/sway, container privileges or host policy.
        packaged_sway = Path("/usr/bin/sway")
        sway = work / "sway-headless"
        shutil.copyfile(packaged_sway, sway)
        sway.chmod(0o700)
        if (sway.read_bytes() != packaged_sway.read_bytes() or
                "security.capability" in os.listxattr(sway) or
                sway.stat().st_mode & 0o6000):
            raise AssertionError("PRIVATE_SWAY_BINARY_MISMATCH_OR_PRIVILEGE")
        print("FOREST_HOST_UNPRIVILEGED_SWAY_COPY_VERIFIED", flush=True)
        scene = work / "config"
        # Stage actual sources under the isolated Quickshell config root.
        for directory in ("components", "widgets", "services", "assets"):
            shutil.copytree(ROOT / directory, scene / directory)
        helper = "scripts/forest/ui_model_preferences.py"
        (scene / helper).parent.mkdir(parents=True)
        shutil.copy2(ROOT / helper, scene / helper)
        # Only the reviewed fixed public child and its existing imports.
        (scene / "runtime").mkdir()
        (scene / "privateJoined").mkdir(mode=0o700)
        for n in (1, 2):
            (scene / f"privateNegative{n}").mkdir(mode=0o700)
        (scene / "db-observer-ack").write_text("", encoding="ascii")
        for name in ("ParentWire.js", "ParentProcess.qml"):
            shutil.copyfile(ROOT / "tests/forest/r6_parent" / name, scene / name)
        for name in ("PublicRuntimeStatusDisplay.js", "PublicHistoryDisplay.js"):
            shutil.copyfile(ROOT / "widgets/forest/ui2" / name, scene / name)
        for name in ("runtime_public_child_r6b.py", "runtime_public_conversation_r5.py",
                     "session_journal_v0.py", "turn_bridge_b3.py", "shared_context_b6r1.py",
                     "context_first_tree_m2.py", "runtime_events_r3.py", "runtime_public_status_r4.py",
                     "runtime_public_delivery_r4b.py", "history_public_fixture_m4.py",
                     "recovery_inspect_b4d.py", "ollama_chat_transport.py", "ollama_inventory.py",
                     "capability_registry_b6r2.py", "runtime_stop_control_r2.py", "local_terminal_outbox_b4f.py"):
            shutil.copyfile(ROOT / "scripts/forest" / name, scene / "runtime" / name)
        shutil.copy2(ROOT / "tests/forest/ui1_native_host/shell.qml", scene / "shell.qml")
        for relative in ("widgets/ForestW.qml", "widgets/ForestChatList.qml",
                         "widgets/forest/ui2/PublicConversationFixture.qml",
                         "widgets/forest/ui2/PublicPreviewGate.qml",
                         "widgets/forest/ui2/PublicRestorationReview.qml",
                         "widgets/forest/ui2/PublicDormantTaskSelector.qml",
                         "widgets/forest/ui2/PublicSeasonIndicator.qml",
                         "widgets/forest/ui2/PublicRuntimeStatusView.qml",
                         "widgets/forest/ui2/PublicRuntimeStatusDisplay.js",
                         "components/ConversationFeed.qml", helper):
            if (ROOT / relative).read_bytes() != (scene / relative).read_bytes():
                raise AssertionError("SOURCE_MISMATCH " + relative)
        config = work / "sway.conf"
        config.write_text(f"xwayland disable\noutput * mode {width}x{height}\n", encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8", "HOME": str(work / "home"),
            "XDG_RUNTIME_DIR": str(work / "run"), "XDG_CONFIG_HOME": str(work / "config-home"),
            "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
            "XDG_SESSION_TYPE": "wayland", "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "1", "WLR_RENDERER": "pixman",
            "WLR_LIBINPUT_NO_DEVICES": "1",
            "QT_QPA_PLATFORM": "wayland", "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "QT_LOGGING_RULES": "qml.debug=true;qml.info=true;qml.warning=true;qml.critical=true",
        }
        compositor = qs = None
        sway_log = work / "sway.log"
        try:
            with sway_log.open("wb") as log:
                compositor = subprocess.Popen([str(sway), "--config", str(config)], env=env,
                    cwd=work, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
            for _ in range(100):
                sockets = [p for p in (work / "run").glob("wayland-*") if p.is_socket()]
                if compositor.poll() is not None:
                    raise AssertionError("PRIVATE_SWAY_EXITED")
                if len(sockets) == 1:
                    env["WAYLAND_DISPLAY"] = sockets[0].name
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("PRIVATE_WAYLAND_SOCKET_MISSING")
            qs_log = work / "quickshell.log"
            with qs_log.open("wb") as log:
                qs = subprocess.Popen(["quickshell", "--path", str(scene / "shell.qml"),
                    "--no-color", "--log-rules", env["QT_LOGGING_RULES"]],
                    env=env, cwd=work, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
                if width == 1366:
                    observe_joined_db(qs, scene, qs_log)
                code = qs.wait(timeout=35)
            output = qs_log.read_text(errors="replace")
            phases = [line.split("FOREST_HOST_PHASE_PASS ", 1)[1].strip()
                      for line in output.splitlines() if "FOREST_HOST_PHASE_PASS " in line]
            negative = [line.split("FOREST_HOST_HISTORY_NEGATIVE_PASS ", 1)[1].strip()
                        for line in output.splitlines() if "FOREST_HOST_HISTORY_NEGATIVE_PASS " in line]
            review = [line.split("FOREST_HOST_REVIEW_PHASE_PASS ", 1)[1].strip()
                      for line in output.splitlines() if "FOREST_HOST_REVIEW_PHASE_PASS " in line]
            dormant = [line.split("FOREST_HOST_DORMANT_PHASE_PASS ", 1)[1].strip()
                       for line in output.splitlines() if "FOREST_HOST_DORMANT_PHASE_PASS " in line]
            season = [line.split("FOREST_HOST_SEASON_PHASE_PASS ", 1)[1].strip()
                      for line in output.splitlines() if "FOREST_HOST_SEASON_PHASE_PASS " in line]
            rail = [line.split("FOREST_HOST_CHAT_RAIL_BASELINE_PASS ", 1)[1].strip()
                    for line in output.splitlines() if "FOREST_HOST_CHAT_RAIL_BASELINE_PASS " in line]
            if len(rail) != 1:
                raise AssertionError("FOREST_HOST_CHAT_RAIL_BASELINE_MISSING_OR_DUPLICATE")
            frame_width, rail_width, rail_visible = map(int, rail[0].split())
            expected_rail = {1366: 184, 770: 148, 420: 0}[width]
            if (not 0 < frame_width <= width or
                    rail_width != expected_rail or rail_visible != int(expected_rail > 0) or
                    rail_width != (184 if frame_width >= 800 else 148 if frame_width >= 680 else 0)):
                raise AssertionError("FOREST_HOST_CHAT_RAIL_BASELINE_MISMATCH")
            unified = [line.split("FOREST_HOST_UNIFIED_RAIL_PASS ", 1)[1].strip()
                       for line in output.splitlines() if "FOREST_HOST_UNIFIED_RAIL_PASS " in line]
            if unified != [str(expected_rail)]:
                raise AssertionError("FOREST_HOST_UNIFIED_RAIL_MISSING_OR_MISMATCH")
            preferences = [line.split("FOREST_HOST_TREE_PREFERENCE_ISOLATION_PASS ", 1)[1].strip()
                           for line in output.splitlines()
                           if "FOREST_HOST_TREE_PREFERENCE_ISOLATION_PASS " in line]
            if preferences != [str(expected_rail)]:
                raise AssertionError("FOREST_HOST_TREE_PREFERENCE_ISOLATION_MISSING_OR_MISMATCH")
            if (output.count("FOREST_HOST_SEASON_SOURCE_DEFAULT_PASS") != 1 or
                    season != ([str(i) for i in range(9)] if width >= 770 else []) or
                    output.count("FOREST_HOST_SEASON_PLACEMENT_PASS") != (1 if width >= 770 else 0) or
                    dormant != ([str(i) for i in range(14)] if width >= 770 else []) or
                    output.count("FOREST_HOST_DORMANT_PLACEMENT_PASS") != (1 if width >= 770 else 0) or
                    review != ([str(i) for i in range(11)] if width >= 770 else []) or
                    output.count("FOREST_HOST_REVIEW_PLACEMENT_PASS") != (1 if width >= 770 else 0) or
                    negative != (["1", "2"] if width == 1366 else []) or
                    code != 0 or "FOREST_HOST_FAIL" in output or
                    phases != [str(i) for i in range(count)] or
                    output.count("FOREST_HOST_NATIVE_PASS") != 1 or
                    output.count("FOREST_HOST_JOINED_PASS") != (1 if width == 1366 else 0) or
                    output.count("FOREST_HOST_TYPED_ABORT_PASS") != (1 if width == 1366 else 0)):
                raise AssertionError("FOREST_HOST_INCOMPLETE")
            print(f"FOREST_HOST_OUTPUT_PASS {width}x{height} phases={count}", flush=True)
        finally:
            stop(qs)
            stop(compositor)
            if sway_log.exists():
                print(sway_log.read_text(errors="replace")[-5000:], flush=True)
            if (work / "quickshell.log").exists():
                print((work / "quickshell.log").read_text(errors="replace"), flush=True)


if __name__ == "__main__":
    trial(1366, 900, 18)
    trial(770, 450, 10)
    trial(420, 340, 3)
