"""Offscreen actual-checkout recovery fixture; no host changes."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="cpu-queue-recovery-") as tmp:
    base=Path(tmp)
    config=base/"scene"
    config.mkdir(mode=0o700)
    shutil.copytree(ROOT/"components",config/"components")
    widgets=config/"widgets/cpuplus"
    widgets.mkdir(parents=True)
    for name in ("CpuPlusQueuePane.qml","CpuPlusQueueConsumer.js","CpuPlusQueuePresentation.js",
                 "CpuPlusQueueHistory.js","CpuPlusQueueRecovery.js","CpuPlusQueueRecoveryPane.qml"):
        shutil.copy2(ROOT/"widgets/cpuplus"/name,widgets/name)
    # Copy only the actual Python sources for the child. Import the actual
    # watchdog and its JS dependency in a separate, narrow QML directory.
    # Do not copy the production qmldir: its unrelated MemoryOperation
    # singleton imports qs.services.time, outside this disposable fixture.
    memory=ROOT/"services/memory"
    backend=config/"memory"
    backend.mkdir()
    for source in memory.glob("*.py"):
        shutil.copy2(source,backend/source.name)
    watchdog=config/"watchdog"
    watchdog.mkdir()
    for name in ("MemoryQueueSessionWatchdog.qml","MemoryQueueSessionHost.js"):
        shutil.copy2(memory/name,watchdog/name)
        if (watchdog/name).read_bytes()!=(memory/name).read_bytes():
            raise SystemExit("Watchdog fixture source mismatch")
    print("QUEUE_R3_WATCHDOG_MODULE // actual watchdog and canonical host, isolated from production singleton",flush=True)
    shutil.copy2(ROOT/"tests/fixtures/CpuPlusQueueRecoveryNative.qml",config/"smoke.qml")
    child=config/"child.py"
    shutil.copy2(ROOT/"tests/fixtures/cpuplus_queue_recovery_child.py",child)
    (config/"private").mkdir(mode=0o700)
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
               QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",POST_APOLLO_QUEUE_PIPE_CHILD=str(child))
    proc=subprocess.run(["qs","-p",str(config/"smoke.qml"),"--no-color"],cwd=config,env=env,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25,check=False)
    print(proc.stdout)
    if proc.returncode or "QUEUE_R3_RECOVERY_PASS" not in proc.stdout or "QUEUE_R3_RECOVERY_FAIL" in proc.stdout:
        raise SystemExit("Native recovery fixture failed")
    if env.get("POST_APOLLO_QUEUE_WATCHDOG_TRIAL")=="1" and "QUEUE_R3_WATCHDOG_PASS" not in proc.stdout:
        raise SystemExit("Native watchdog fixture failed")
    trial=env.get("POST_APOLLO_QUEUE_STAGED_TRIAL")
    if trial and "QUEUE_R3_STAGED_PASS //" not in proc.stdout:
        raise SystemExit("Native staged transport fixture failed")
    ack_trial=env.get("POST_APOLLO_QUEUE_ACK_TRIAL")
    if ack_trial:
        if "QUEUE_R3_ACK_PASS // "+ack_trial not in proc.stdout:
            raise SystemExit("Native review acknowledgment fixture failed")
        # Independently verify durable row counts after child and shell exit.
        # Read-only URI; no startup migration or fixture repair.
        dbpath=config/"private"/"queue.db"
        with sqlite3.connect(dbpath.as_uri()+"?mode=ro",uri=True) as db:
            rows=db.execute("SELECT state,result_id FROM memory_queue_local_actions_v1").fetchall()
            if rows!=[("PREPARED",None)]:
                raise SystemExit("Unexpected durable local action state")
            table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_queue_recovery_reviews_v1'").fetchone()
            count=db.execute("SELECT count(*) FROM memory_queue_recovery_reviews_v1").fetchone()[0] if table else 0
            if count!=(0 if ack_trial=="EOF" else 1):
                raise SystemExit("Unexpected durable acknowledgment count")
        print("QUEUE_R3_ACK_DB_PASS // "+ack_trial+" exact persistent counts",flush=True)
