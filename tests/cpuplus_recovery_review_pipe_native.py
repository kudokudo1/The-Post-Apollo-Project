"""DOC 2 disposable combined workspace/pipe/checkpoint qualification."""
import hashlib
import json
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
                 "CpuPlusQueueHistory.js","CpuPlusQueueRecovery.js","CpuPlusQueueRecoveryPane.qml",
                 "CpuPlusAutoWorkspace.qml","CpuPlusQueueHistoryPane.qml"):
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
    (config/"services/memory").mkdir(parents=True)
    shutil.copy2(memory/"MemoryQueueSessionHost.js",config/"services/memory/MemoryQueueSessionHost.js")
    print("QUEUE_R3_WATCHDOG_MODULE // actual watchdog and canonical host, isolated from production singleton",flush=True)
    shutil.copy2(ROOT/"tests/fixtures/CpuPlusRecoveryReviewPipeNative.qml",config/"smoke.qml")
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
    env.update(POST_APOLLO_QUEUE_STAGED_TRIAL="EOF",POST_APOLLO_QUEUE_ACK_TRIAL="LOST",
               POST_APOLLO_QUEUE_GATE_TRIAL="PASS",POST_APOLLO_QUEUE_WATCHDOG_TRIAL="0")
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
    proc=subprocess.run(["qs","-p",str(config/"smoke.qml"),"--no-color"],cwd=config,env=env,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25,check=False)
    print(proc.stdout)
    if proc.returncode or "CPU_M7B_WORKSPACE_PIPE_PASS" not in proc.stdout or "QUEUE_R3_RECOVERY_PASS" not in proc.stdout or "QUEUE_R3_RECOVERY_FAIL" in proc.stdout:
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

    # Independent persistent lineage audit. Do not trust the QML markers
    # or reconstruct identity from the fixture's hardcoded action UUID.
    # The checkpoint reader validates its files; independently recompute
    # the review digest and compare the raw SQLite evidence across stores.
    def digest(value):
        encoded=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
        return hashlib.sha256(encoded.encode("ascii")).hexdigest()

    def require(condition, label):
        if not condition:
            raise SystemExit("M7C persistent lineage mismatch: "+label)

    require(snapshot["startup_unlock"] is False and snapshot["can_execute"] is False,"checkpoint gate")
    action_message=snapshot["action"]["message"]
    checkpoint_review=snapshot["acknowledgment"]["review"]
    with sqlite3.connect((config/"private"/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        actions=db.execute("SELECT ordinal,action_id,payload,state,prepared_at,result_id,committed_at FROM memory_queue_local_actions_v1").fetchall()
        reviews=db.execute("SELECT review_id,action_id,reviewer_owner_id,payload,acknowledged_at FROM memory_queue_recovery_reviews_v1").fetchall()
        requests=db.execute("SELECT id,state,payload FROM requests").fetchall()
        require(db.execute("PRAGMA quick_check").fetchall()==[("ok",)],"database integrity")
    require(len(actions)==1 and len(reviews)==1,"exact journal and receipt cardinality")
    require(requests==[],"no committed request in any state")
    ordinal,action_id,payload,state,prepared_at,result_id,committed_at=actions[0]
    message=json.loads(payload)
    require(message==action_message and action_id==message["action_id"],"action checkpoint and journal identity")
    require(message["kind"]=="QUEUE" and message["expected_request_id"] is None,"original action shape")
    require(state=="PREPARED" and result_id is None and committed_at is None,"uncommitted preparation")
    row={"version":1,"ordinal":ordinal,"message":message,"state":state,
         "prepared_at":prepared_at,"result_request_id":result_id,"committed_at":committed_at,
         "adjustment_outcome":"UNVERIFIED","can_execute":False}
    review_id,review_action_id,reviewer_owner_id,payload,acknowledged_at=reviews[0]
    receipt=json.loads(payload)
    review=receipt["review"]
    require(review==checkpoint_review,"full durable review equality")
    require(review_id==review["review_id"] and review_action_id==review["action_id"]==action_id,
            "receipt key and action identity")
    require(reviewer_owner_id==review["owner_id"] and reviewer_owner_id!=message["owner_id"],
            "distinct original and recovery owners")
    expected_snapshot={"version":1,"record":row,"pending_request_id":None,
                       "pending_digest":digest(None),"adjustment_outcome":"UNVERIFIED",
                       "can_execute":False,"startup_unlock":False}
    require(review["snapshot"]==expected_snapshot,"independent reconstructed snapshot")
    require(review["review_digest"]==digest(expected_snapshot),"independently recomputed digest")
    require(review["can_execute"] is False and review["startup_unlock"] is False,"review nonauthority")
    require(receipt["acknowledged_at_ms"]==acknowledged_at and
            0<=acknowledged_at-review["reviewed_at_ms"]<60000,"receipt time lineage")
    require(receipt["disposition"]=="REVIEW_ACKNOWLEDGED_ONLY" and
            receipt["adjustment_outcome"]=="UNVERIFIED" and receipt["can_execute"] is False and
            receipt["startup_unlock"] is False,"receipt nonauthority")
    print("CPU_M7C_PERSISTENT_LINEAGE_PASS // action + receipt + checkpoint + recomputed digest; zero requests",flush=True)

