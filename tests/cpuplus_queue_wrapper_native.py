"""Disposable actual recovery desktop wrapper. No installed launch or unlock."""
import json
import os
from pathlib import Path
import select
import selectors
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable fixture only")
sys.path.insert(0,str(ROOT/"services/memory"))
from memory_adjustment_queue import Queue
from memory_queue_owner import Owner
from memory_queue_runtime import Runtime
from memory_queue_checkpoint_generations import CheckpointGenerations

ACTION="c23683a9-b2ab-4a2c-87ce-000000000062"

def seed(root,trial):
    queue=Queue(root/"private"/"queue.db")
    store=CheckpointGenerations(root/"checkpoint")
    def owner():
        return Owner(queue,lambda q:Runtime(q,lambda:None,lambda *_:None,
            interval_ms=10000,max_age_ms=20000,max_gap_ms=20000,stable_ms=20000,
            local_disposition_enabled=True),durable_actions=True,staged_max_age_ms=10000,
            local_disposition_enabled=True)
    with owner() as first:
        message={"version":1,"owner_id":first.owner_id,"action_id":ACTION,"action_sequence":1,
                 "kind":"QUEUE","expected_request_id":None,"target_gib":16,"expires_at":int(time.time())+180}
        store.save(0,{"version":1,"kind":"ACTION","message":message})
        first.prepare_action(message)
    if trial!="LIVE":
        with owner() as second:
            review=second.begin_recovery_review(ACTION,max_age_ms=10000)["review"]
            store.save(0,{"version":1,"kind":"REVIEW_DISMISS","review":review})
            if trial=="RECOVERED":
                second.dismiss_recovery_preparation(review_id=review["review_id"],review_digest=review["review_digest"])

def start_ticks(pid):
    return Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()[19]

def run(trial):
    with tempfile.TemporaryDirectory(prefix="cpu-queue-wrapper-",dir="/tmp") as name:
        root=Path(name)
        (root/"services").mkdir()
        for module in ("memory","notifications","time","sounds"):
            shutil.copytree(ROOT/"services"/module,root/"services"/module)
        shutil.copytree(ROOT/"services/memory",root/"memory")
        widgets=root/"widgets/cpuplus"
        widgets.mkdir(parents=True)
        for file in ("CpuPlusQueueConsumer.js","CpuPlusQueuePresentation.js","CpuPlusQueueHistory.js","CpuPlusQueueRecovery.js"):
            shutil.copy2(ROOT/"widgets/cpuplus"/file,widgets/file)
        for file,target in (("CpuPlusQueueDesktopWrapperNative.qml","smoke.qml"),
            ("cpuplus_queue_wrapper_child.py","child.py"),("cpuplus_queue_retention_helper.py","helper.py")):
            shutil.copy2(ROOT/"tests/fixtures"/file,root/target)
        for folder in ("private","checkpoint"):
            (root/folder).mkdir(mode=0o700)
        seed(root,trial)
        before={p.name:p.read_bytes() for p in (root/"checkpoint").iterdir()}
        env=os.environ.copy()
        for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
            (root/key).mkdir(mode=0o700);env[key]=str(root/key)
        for key in ("DBUS_SESSION_BUS_ADDRESS","DBUS_STARTER_ADDRESS","DBUS_STARTER_BUS_TYPE"):
            env.pop(key,None)
        env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
                   QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                   POST_APOLLO_WRAPPER_TRIAL=trial,POST_APOLLO_WRAPPER_ROOT=str(root))
        proc=subprocess.Popen(["dbus-run-session","--","qs","-p",str(root/"smoke.qml"),"--no-color"],
                              cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        output=bytearray()
        handles={}
        exits=set()
        final=2 if trial=="LIVE" else 1
        originals=None
        def witness():
            nonlocal originals
            for generation in range(1,final+1):
                file=root/("owner-%d.identity"%generation)
                if generation not in handles and file.is_file():
                    fields=file.read_text().split()
                    if len(fields)!=2: continue
                    pid,stamp=int(fields[0]),fields[1]
                    if generation!=len(handles)+1 or start_ticks(pid)!=stamp:
                        raise AssertionError("Wrong owner identity")
                    fd=os.pidfd_open(pid,0);handles[generation]=fd
                    argv=Path("/proc",str(pid),"cmdline").read_bytes().split(b"\0")
                    if start_ticks(pid)!=stamp or os.fsencode(root/"child.py") not in argv or str(generation).encode() not in argv:
                        raise AssertionError("Wrong owner command")
                    (root/("owner-%d.ready"%generation)).touch(mode=0o600,exist_ok=False)
                if generation in handles and generation not in exits:
                    poll=select.poll();poll.register(handles[generation],select.POLLIN)
                    if poll.poll(0):
                        exits.add(generation)
                        print("R6H_PIDFD_EXIT_PASS // %s %d"%(trial,generation),flush=True)
                        if generation==final and trial!="MISSING":
                            originals={p.name:p.read_bytes() for p in (root/"checkpoint").iterdir()}
                            if set(originals)!={"action-v1.json","review-dismiss-v1.json"}:
                                raise AssertionError("Missing original evidence")
                            (root/"advance.ready").touch(mode=0o600,exist_ok=False)
        try:
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout,selectors.EVENT_READ)
                deadline=time.monotonic()+40
                while time.monotonic()<deadline:
                    witness()
                    for _key,_event in sel.select(.025):
                        part=os.read(proc.stdout.fileno(),4096)
                        if not part:
                            break
                        output.extend(part)
                        if len(output)>1048576 or b"R6H_FAIL //" in output:
                            raise AssertionError("Wrapper fixture failed")
                    if proc.poll() is not None:
                        output.extend(proc.stdout.read())
                        break
                else: raise AssertionError("Wrapper timeout")
            witness()
            if proc.wait(timeout=5) or ("R6H_NATIVE_PASS // "+trial).encode() not in output or exits!=set(range(1,final+1)):
                raise AssertionError("Wrapper native qualification failed")
            cp=root/"checkpoint"
            for key,value in before.items():
                assert (cp/key).read_bytes()==value
            with sqlite3.connect((root/"private"/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
                rows=db.execute("SELECT action_id,state,result_id,dismissal FROM memory_queue_local_actions_v1").fetchall()
                assert len(rows)==1 and rows[0][:3]==(ACTION,"PREPARED",None)
                assert db.execute("SELECT count(*) FROM requests").fetchone()[0]==0
                assert (rows[0][3] is None)==(trial=="MISSING")
            if trial=="MISSING":
                assert set(p.name for p in cp.iterdir())==set(before)
            else:
                assert originals is not None
                for key,value in originals.items(): assert (cp/key).read_bytes()==value
                assert json.loads((cp/"dismissed-v2.json").read_text())["receipt"]==json.loads(rows[0][3])
                assert not list((cp/"generation-0001").iterdir())
            print("R6H_DB_STORAGE_PASS // "+trial,flush=True)
        finally:
            print(output.decode("utf-8",errors="replace"),flush=True)
            for fd in handles.values():os.close(fd)
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=5)
            proc.stdout.close()

for trial in ("LIVE","RECOVERED","MISSING"):
    run(trial)
