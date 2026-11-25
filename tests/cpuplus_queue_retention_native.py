"""Actual QML canonical host, real v2 pipe, independent Linux exit witness."""
import os
import re
import select
import selectors
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable fixture only")

def ticks(pid):
    return Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()[19]

def trial(name):
    with tempfile.TemporaryDirectory(prefix="cpu-queue-retention-",dir="/tmp") as tmp:
        root=Path(tmp)
        for folder in ("memory","host","widgets/cpuplus","private","checkpoint"):
            (root/folder).mkdir(mode=0o700,parents=True)
        for source in (ROOT/"services/memory").glob("*.py"):
            shutil.copy2(source,root/"memory"/source.name)
        for filename in ("MemoryQueueSessionHost.js","MemoryQueueCheckpointAdapter.qml"):
            shutil.copy2(ROOT/"services/memory"/filename,root/"host")
        for filename in ("CpuPlusQueueConsumer.js","CpuPlusQueuePresentation.js","CpuPlusQueueHistory.js","CpuPlusQueueRecovery.js"):
            shutil.copy2(ROOT/"widgets/cpuplus"/filename,root/"widgets/cpuplus")
        for filename,target in (("CpuPlusQueueRetentionNative.qml","smoke.qml"),
                                ("cpuplus_queue_retention_child.py","child.py"),
                                ("cpuplus_queue_retention_helper.py","helper.py")):
            shutil.copy2(ROOT/"tests/fixtures"/filename,root/target)
        env=os.environ.copy()
        for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
            (root/key).mkdir(mode=0o700)
            env[key]=str(root/key)
        env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
                   QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                   POST_APOLLO_RETENTION_TRIAL=name,POST_APOLLO_RETENTION_ROOT=str(root))
        proc=subprocess.Popen(["qs","-p",str(root/"smoke.qml"),"--no-color"],cwd=root,env=env,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        output=bytearray()
        buffer=b""
        handles={}
        exits=[]
        originals=None
        try:
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout,selectors.EVENT_READ)
                deadline=time.monotonic()+40
                while True:
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not sel.select(remaining):
                        raise AssertionError("Native fixture deadline")
                    part=os.read(proc.stdout.fileno(),4096)
                    if not part:
                        break
                    output.extend(part)
                    if len(output)>1048576 or b"R6F_FAIL //" in output:
                        raise AssertionError("Unexpected native fixture output")
                    buffer+=part
                    while b"\n" in buffer:
                        line,buffer=buffer.split(b"\n",1)
                        match=re.search(rb"R6F_OWNER // (\d+) (\d+) (\d+)\b",line)
                        if match:
                            generation,pid=map(int,match.groups()[:2])
                            stamp=match[3].decode()
                            if generation!=len(handles)+1 or ticks(pid)!=stamp:
                                raise AssertionError("Wrong process identity")
                            fd=os.pidfd_open(pid,0)
                            handles[generation]=fd
                            argv=Path("/proc",str(pid),"cmdline").read_bytes().split(b"\0")
                            if ticks(pid)!=stamp or os.fsencode(root/"child.py") not in argv or str(generation).encode() not in argv:
                                raise AssertionError("Wrong child command")
                            poller=select.poll();poller.register(fd,select.POLLIN)
                            if poller.poll(0):
                                raise AssertionError("Owner already dead")
                            (root/("owner-%d.ready"%generation)).touch(mode=0o600,exist_ok=False)
                        match=re.search(rb"R6F_CHILD_EXIT // (\d+)\b",line)
                        if match:
                            generation=int(match[1])
                            if generation!=len(exits)+1 or generation not in handles:
                                raise AssertionError("Uncorrelated child exit")
                            poller=select.poll();poller.register(handles[generation],select.POLLIN)
                            if not any(fd==handles[generation] and mask&select.POLLIN for fd,mask in poller.poll(2000)):
                                raise AssertionError("Exact owner not exited")
                            exits.append(generation)
                            print("R6F_PIDFD_EXIT_PASS // %s %d"%(name,generation),flush=True)
                            if generation==3:
                                originals={p.name:p.read_bytes() for p in (root/"checkpoint").iterdir()}
                                if set(originals)!={"action-v1.json","review-dismiss-v1.json"}:
                                    raise AssertionError("Unexpected original checkpoint evidence")
                                if name!="MISSING":
                                    (root/"advance.ready").touch(mode=0o600,exist_ok=False)
            if proc.wait(timeout=5) or ("R6F_NATIVE_PASS // "+name).encode() not in output or exits!=[1,2,3]:
                raise AssertionError("Native retention qualification failed")
            if any((root/"checkpoint"/key).read_bytes()!=value for key,value in originals.items()):
                raise AssertionError("Original checkpoint overwritten")
            with sqlite3.connect((root/"private"/"queue.db").as_uri()+"?mode=ro",uri=True) as db:
                rows=db.execute("SELECT action_id,state,result_id,dismissal FROM memory_queue_local_actions_v1").fetchall()
                if len(rows)!=1 or rows[0][:3]!=("c23683a9-b2ab-4a2c-87ce-000000000061","PREPARED",None):
                    raise AssertionError("Unexpected local action")
                if db.execute("SELECT count(*) FROM requests").fetchone()[0]!=0 or (rows[0][3] is None)!=(name=="MISSING"):
                    raise AssertionError("Unexpected backend mutation")
            checkpoint=root/"checkpoint"
            if name=="MISSING":
                if set(p.name for p in checkpoint.iterdir())!=set(originals):
                    raise AssertionError("Missing receipt advanced storage")
            else:
                import json
                seal=json.loads((checkpoint/"dismissed-v2.json").read_text())
                if seal["receipt"]!=json.loads(rows[0][3]) or not (checkpoint/"generation-0001").is_dir():
                    raise AssertionError("Retained seal not exact backend receipt")
                if list((checkpoint/"generation-0001").iterdir()):
                    raise AssertionError("New generation is not empty")
            print("R6F_DB_STORAGE_PASS // "+name,flush=True)
        finally:
            print(output.decode("utf-8",errors="replace"),flush=True)
            for fd in handles.values():
                os.close(fd)
            try:
                os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
            proc.stdout.close()

for name in ("LIVE","LOST","MISSING"):
    trial(name)
