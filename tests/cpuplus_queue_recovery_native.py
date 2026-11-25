"""Offscreen actual-checkout recovery fixture; no host changes."""
import os
import re
import select
import uuid
from pathlib import Path
import shutil
import sqlite3
import signal
import selectors
import time
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def process_start_ticks(pid):
    return Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()[19]


def owner_pidfd(pid,start_ticks,config):
    # Bind a stable kernel process handle before killing Quickshell.
    # PID reuse must not be mistaken for retirement of the actual owner.
    if process_start_ticks(pid)!=start_ticks:
        raise AssertionError("Owner PID identity changed before pidfd")
    fd=os.pidfd_open(pid,0)
    try:
        if process_start_ticks(pid)!=start_ticks:
            raise AssertionError("Owner PID identity changed during pidfd open")
        argv=Path("/proc",str(pid),"cmdline").read_bytes().split(b"\0")
        if os.fsencode(config/"child.py") not in argv:
            raise AssertionError("Reported PID is not the disposable owner")
        poller=select.poll()
        poller.register(fd,select.POLLIN)
        if poller.poll(0):
            raise AssertionError("Original owner already dead at boundary")
        return fd
    except BaseException:
        os.close(fd)
        raise


def kill_at_boundary(command,config,env,trial):
    # Binary reads avoid text-reader buffering hiding an already received
    # marker. Bound total output and deadline; own process group only.
    proc=subprocess.Popen(command,cwd=config,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,start_new_session=True)
    output=bytearray()
    owner_fd=None
    try:
        with selectors.DefaultSelector() as sel:
            sel.register(proc.stdout,selectors.EVENT_READ)
            until=time.monotonic()+20
            marker=("QUEUE_R3_CRASH_POINT // "+trial).encode()
            while marker not in output:
                remaining=until-time.monotonic()
                if remaining<=0 or not sel.select(remaining):
                    raise AssertionError("Crash boundary timeout")
                part=os.read(proc.stdout.fileno(),4096)
                if not part:
                    raise AssertionError("Shell exited before crash boundary")
                output.extend(part)
                if len(output)>1048576 or b"QUEUE_R3_RECOVERY_FAIL" in output:
                    raise AssertionError("Unexpected crash fixture output")
            pids=re.findall(rb"QUEUE_R3_OWNER_PID // (\d+) (\d+)\b",output)
            ids=re.findall(rb"QUEUE_R3_CRASH_ID_GENERATED // ([0-9a-f-]{36})\b",output)
            if not pids or len(ids)!=1:
                raise AssertionError("Missing exact child owner or generated action identity")
            generated_id=ids[0].decode("ascii")
            if str(uuid.UUID(generated_id,version=4))!=generated_id:
                raise AssertionError("Invalid original action UUID")
            owner_pid=int(pids[-1][0])
            owner_start=pids[-1][1].decode("ascii")
            owner_fd=owner_pidfd(owner_pid,owner_start,config)
            # Kill only the disposable shell, not a named process or user's
            # desktop. The child must retire via parent pipe EOF.
            proc.send_signal(signal.SIGKILL)
            if proc.wait(timeout=5)!=-signal.SIGKILL:
                raise AssertionError("Shell not terminated by SIGKILL")
            poller=select.poll()
            poller.register(owner_fd,select.POLLIN)
            events=poller.poll(5000)
            if not any(fd==owner_fd and mask & select.POLLIN for fd,mask in events):
                raise AssertionError("Exact original owner did not exit after shell death")
            print("QUEUE_R3_OWNER_EXIT_PASS // "+trial+" pidfd readable before cleanup",flush=True)
        # Check ownership released using the actual cooperative queue lock.
        # This waits for retirement, not a new owner or operation retry.
        import fcntl
        with open(config/"private"/"queue.db","rb") as db:
            until=time.monotonic()+5
            while True:
                try:
                    fcntl.flock(db.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    fcntl.flock(db.fileno(),fcntl.LOCK_UN)
                    break
                except BlockingIOError:
                    if time.monotonic()>=until:
                        raise AssertionError("Old owner retained custody")
                    time.sleep(0.02)
        print("QUEUE_R3_SHELL_SIGKILL // "+trial+" old owner exited and custody released",flush=True)
        return generated_id
    finally:
        if owner_fd is not None:
            os.close(owner_fd)
        print(output.decode("utf-8",errors="replace"))
        # Cleanup only processes inside this disposable process group.
        try:
            os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
        proc.stdout.close()

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
    for name in ("MemoryQueueSessionWatchdog.qml","MemoryQueueSessionHost.js","MemoryQueueCheckpointAdapter.qml"):
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
    gate=env.get("POST_APOLLO_QUEUE_GATE_TRIAL")
    checkpoint_dir=config/"checkpoint"
    checkpoint_dir.mkdir(mode=0o700)
    env.update(POST_APOLLO_QUEUE_CHECKPOINT_HELPER=str(backend/"memory_queue_checkpoint_io.py"),
               POST_APOLLO_QUEUE_CHECKPOINT_DIR=str(checkpoint_dir))
    if gate=="FAIL":
        # Bypass initial load solely to exercise actual SAVE failure.
        slot=checkpoint_dir/"action-v1.json"
        slot.write_bytes(b"{")
        slot.chmod(0o600)
    command=["qs","-p",str(config/"smoke.qml"),"--no-color"]
    crash=env.get("POST_APOLLO_QUEUE_CRASH_TRIAL")
    if crash:
        if crash not in {"BEFORE_PREPARE","PREPARED","COMMITTED","ACK_BEFORE","ACK_SAVED"}:
            raise SystemExit("Unknown crash trial")
        generated_id=kill_at_boundary(command,config,env,crash)
        # Witness the durable checkpoint before starting recovery. No
        # generated identity or old PID is injected into the new shell.
        before={path.name:path.read_bytes() for path in checkpoint_dir.iterdir()}
        # New process, same durable files. Never pass volatile action or
        # review identities from supervisor to shell.
        env["POST_APOLLO_QUEUE_CRASH_RESTORE"]="1"
        proc=subprocess.run(command,cwd=config,env=env,text=True,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,timeout=25,check=False)
        print(proc.stdout)
        if proc.returncode or "QUEUE_R3_CRASH_RESTORE_PASS // "+crash not in proc.stdout or "QUEUE_R3_RECOVERY_FAIL" in proc.stdout:
            raise SystemExit("Fresh shell recovery failed")
        restored_ids=re.findall(r"QUEUE_R3_CRASH_ID_RESTORED // ([0-9a-f-]{36})\b",proc.stdout)
        if restored_ids!=[generated_id] or "QUEUE_R3_CRASH_ID_GENERATED //" in proc.stdout:
            raise SystemExit("Fresh shell did not discover original identity solely from LOAD")
        if before!={path.name:path.read_bytes() for path in checkpoint_dir.iterdir()}:
            raise SystemExit("Recovery altered durable checkpoint evidence")
        import sys
        sys.path.insert(0,str(backend))
        from memory_queue_host_checkpoint import HostCheckpoint
        snapshot=HostCheckpoint(checkpoint_dir).load()
        action=snapshot["action"]["message"]
        if action["action_id"]!=generated_id:
            raise SystemExit("Generated identity differs from persistent evidence")
        print("QUEUE_R3_CRASH_ID_PASS // "+crash+" generated, restored, persisted match",flush=True)
        ack=snapshot["acknowledgment"]
        with sqlite3.connect((config/"private"/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
            rows=db.execute("SELECT action_id,state,result_id FROM memory_queue_local_actions_v1").fetchall()
            expected="COMMITTED" if crash=="COMMITTED" else "PREPARED"
            if crash=="BEFORE_PREPARE":
                if rows:
                    raise SystemExit("Withheld PREPARE mutated queue")
            elif len(rows)!=1 or rows[0][:2]!=(action["action_id"],expected) or (rows[0][2] is not None)!=(expected=="COMMITTED"):
                raise SystemExit("Unexpected action recovery rows")
            if db.execute("SELECT count(*) FROM requests").fetchone()[0]!=(1 if expected=="COMMITTED" else 0):
                raise SystemExit("Unexpected request count")
            table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_queue_recovery_reviews_v1'").fetchone()
            receipts=db.execute("SELECT review_id,action_id FROM memory_queue_recovery_reviews_v1").fetchall() if table else []
            if crash=="ACK_SAVED":
                if ack is None or receipts!=[(ack["review"]["review_id"],action["action_id"])]:
                    raise SystemExit("Unexpected recovered receipt")
            elif receipts:
                raise SystemExit("Unexpected acknowledgment")
            if (ack is not None)!=(crash in {"ACK_BEFORE","ACK_SAVED"}):
                raise SystemExit("Unexpected checkpoint presence")
        print("QUEUE_R3_CRASH_DB_PASS // "+crash,flush=True)
        raise SystemExit(0)
    proc=subprocess.run(command,cwd=config,env=env,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25,check=False)
    print(proc.stdout)
    if proc.returncode or "QUEUE_R3_RECOVERY_PASS" not in proc.stdout or "QUEUE_R3_RECOVERY_FAIL" in proc.stdout:
        raise SystemExit("Native recovery fixture failed")
    if env.get("POST_APOLLO_QUEUE_WATCHDOG_TRIAL")=="1" and "QUEUE_R3_WATCHDOG_PASS" not in proc.stdout:
        raise SystemExit("Native watchdog fixture failed")
    trial=env.get("POST_APOLLO_QUEUE_STAGED_TRIAL")
    if trial and gate!="FAIL" and "QUEUE_R3_STAGED_PASS //" not in proc.stdout:
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
    if gate:
        if "QUEUE_R3_GATE_PASS // "+gate not in proc.stdout:
            raise SystemExit("Native checkpoint gate fixture failed")
        if gate=="FAIL":
            with sqlite3.connect((config/"private"/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
                if db.execute("SELECT count(*) FROM memory_queue_local_actions_v1").fetchone()[0]!=0:
                    raise SystemExit("Failed SAVE allowed preparation")
            if (checkpoint_dir/"action-v1.json").read_bytes()!=b"{":
                raise SystemExit("Failed SAVE overwrote evidence")
        else:
            import sys
            sys.path.insert(0,str(backend))
            from memory_queue_host_checkpoint import HostCheckpoint
            snapshot=HostCheckpoint(checkpoint_dir).load()
            if snapshot["action"] is None or snapshot["acknowledgment"] is None:
                raise SystemExit("Native checkpoints missing")
        print("QUEUE_R3_GATE_DB_PASS // "+gate,flush=True)
