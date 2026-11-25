"""Disposable native actual Hub binding, private D-Bus and XDG directories."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")

for trial in ("NORMAL","BLOCK","DND"):
    with tempfile.TemporaryDirectory(prefix="cpu-queue-hub-") as tmp:
        base=Path(tmp)
        scene=base/"scene"
        scene.mkdir(mode=0o700)
        (scene/"services").mkdir()
        shutil.copytree(ROOT/"services/notifications",scene/"services/notifications")
        shutil.copytree(ROOT/"services/memory",scene/"services/memory")
        shutil.copytree(ROOT/"services/memory",scene/"memory")
        widgets=scene/"widgets/cpuplus"
        widgets.mkdir(parents=True)
        for name in ("CpuPlusQueueConsumer.js","CpuPlusQueuePresentation.js",
                     "CpuPlusQueueHistory.js","CpuPlusQueueRecovery.js"):
            shutil.copy2(ROOT/"widgets/cpuplus"/name,widgets/name)
        shutil.copy2(ROOT/"tests/fixtures/CpuPlusQueueHubNative.qml",scene/"smoke.qml")
        shutil.copy2(ROOT/"tests/fixtures/cpuplus_queue_recovery_child.py",scene/"child.py")
        private=scene/"private"
        private.mkdir(mode=0o700)
        env=os.environ.copy()
        for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
            folder=base/key
            folder.mkdir(mode=0o700)
            env[key]=str(folder)
        for key in list(env):
            if key.startswith("POST_APOLLO_QUEUE_") or key in {"DBUS_SESSION_BUS_ADDRESS","DBUS_STARTER_ADDRESS","DBUS_STARTER_BUS_TYPE"}:
                env.pop(key,None)
        env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
                   QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                   POST_APOLLO_QUEUE_PIPE_SMOKE="CI_DISPOSABLE_ONLY",POST_APOLLO_QUEUE_HUB_TRIAL=trial,
                   POST_APOLLO_QUEUE_PIPE_CHILD=str(scene/"child.py"))
        proc=subprocess.run(["dbus-run-session","--","qs","-p",str(scene/"smoke.qml"),"--no-color"],
                            cwd=scene,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            timeout=25,check=False)
        print(proc.stdout)
        if proc.returncode or "QUEUE_HUB_NATIVE_PASS // "+trial not in proc.stdout or "QUEUE_HUB_NATIVE_FAIL" in proc.stdout:
            raise SystemExit("Native Hub fixture failed: "+trial)
        with sqlite3.connect((private/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
            assert db.execute("SELECT count(*) FROM memory_queue_attempts_v1").fetchone()==(2,)
            assert db.execute("SELECT count(*) FROM requests WHERE state='CANCELLED'").fetchone()==(1,)
            assert db.execute("SELECT count(*) FROM memory_queue_local_actions_v1 WHERE state='COMMITTED'").fetchone()==(2,)
        print("QUEUE_HUB_DB_PASS // "+trial)
