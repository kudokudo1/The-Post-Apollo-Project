#!/usr/bin/python3 -I
"""Signal trace calibration only, in guarded disposable Silverblue guest."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import select
import signal
import subprocess
import sys
import time

PIN = "5f6e6d800dcf41c1f0f7330fdb248dfd2177104f"
ROOT = Path("/sys/kernel/tracing")
INSTANCE = ROOT/"instances"/"pa_cpu_mem_signal_ci"
MARKER = Path("/etc/postapollo-memory-native-signalcustody-ci-only")
GUARD = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
EVENTS = ("signal/signal_generate","signal/signal_deliver")

def require(condition,message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_SIGNALCUSTODY_STAGE // "+message,flush=True)

def guarded():
    require(os.geteuid()==0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader=importlib.machinery.SourceFileLoader("signal_guard",str(GUARD))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    guard=importlib.util.module_from_spec(spec)
    loader.exec_module(guard)
    require(guard.protected_bytes(MARKER).strip()==b"DISPOSABLE_CPU_MEMORY_SIGNALCUSTODY_V1",
            "signal fixture marker absent")
    guard.PIN=PIN
    guard.guard()
    require(platform.machine()=="x86_64","unsupported architecture")
    return guard

def bounded(path,limit=1048576):
    with path.open("rb") as stream:
        raw=stream.read(limit+1)
    require(len(raw)<=limit,"bounded read exceeded")
    return raw.decode("ascii")

def write(path,value):
    payload=(value+"\n").encode("ascii")
    fd=os.open(path,os.O_WRONLY|os.O_CLOEXEC|os.O_TRUNC)
    try:
        require(os.write(fd,payload)==len(payload),"short private trace control write")
    finally:
        os.close(fd)

def fields(path):
    return set(re.findall(r"^\s*field:[^;]*\b([A-Za-z_][A-Za-z_0-9]*)\s*(?:\[[^\]]*\])?;",
                          bounded(path,65536),re.M))

def stat_identity(pid):
    values=bounded(Path("/proc")/str(pid)/"stat",4096).rsplit(")",1)[1].split()
    require(int(values[1])==os.getpid() and int(values[19])>0,"child identity mismatch")
    return int(values[19])

def stats():
    cpus=sorted((INSTANCE/"per_cpu").glob("cpu[0-9]*"))
    require(cpus,"trace statistics unavailable")
    for cpu in cpus:
        raw=bounded(cpu/"stats",65536)
        for key in ("overrun","commit overrun","dropped events"):
            require(re.findall(r"^"+key+r":\s*(\d+)\s*$",raw,re.M)==["0"],
                    "trace buffer loss or ambiguous counters")

def numeric(payload,name):
    matches=re.findall(r"(?:^|\s)"+name+r"=(-?\d+)(?=\s|$)",payload)
    require(len(matches)==1,"missing or repeated numeric signal field: "+name)
    return int(matches[0])

def parse(raw,sender,target,start_ticks):
    """Use event TARGET pid for generation, current pid for delivery."""
    require(all(type(x) is int and x>0 for x in (sender,target,start_ticks))
            and sender!=target,"invalid sender or target identity")
    events=[]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match=re.fullmatch(r"\s*.+-(\d+)\s+\[\d+\]\s+\S+\s+(\d+)\.(\d+):\s*(.*)",line)
        require(match is not None,"unrecognized trace row")
        actor,sec,frac,payload=match.groups()
        require(1<=len(frac)<=9,"invalid trace timestamp")
        stamp=int(sec)*10**9+int(frac.ljust(9,"0"))
        if payload.startswith("signal_generate:"):
            require(int(actor)==sender and numeric(payload,"pid")==target
                    and numeric(payload,"sig")==int(signal.SIGTERM)
                    and numeric(payload,"res")==0,"signal generation target or result mismatch")
            kind="SIGNAL_GENERATE"
        elif payload.startswith("signal_deliver:"):
            require(int(actor)==target and numeric(payload,"sig")==int(signal.SIGTERM),
                    "signal delivery actor mismatch")
            kind="SIGNAL_DELIVER"
        else:
            raise RuntimeError("unexpected private signal event")
        events.append({"kind":kind,"time_ns":stamp,"target_pid":target,
                       "target_start_ticks":start_ticks,"emitter_pid":int(actor)})
    require([e["kind"] for e in events]==["SIGNAL_GENERATE","SIGNAL_DELIVER"]
            and events[0]["time_ns"]<events[1]["time_ns"],
            "signal pair incomplete, repeated or unordered")
    return events

def read_one(fd,expected):
    ready,_,_=select.select([fd],[],[],5)
    require(ready and os.read(fd,1)==expected,"child handshake failed")

def wait_child(pid):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        observed,status=os.waitpid(pid,os.WNOHANG)
        if observed==pid:
            require(os.WIFEXITED(status) and os.WEXITSTATUS(status)==0,
                    "fixture child failed")
            return
        time.sleep(.02)
    raise RuntimeError("fixture child exit unverified")

def signature(guard):
    return {p:[kind,size,priority] for p,(kind,size,used,priority) in guard.rows().items()}

def run(guard):
    require(guard.command("/usr/bin/findmnt","-n","-o","FSTYPE","-T",str(ROOT)).strip()=="tracefs",
            "tracefs unavailable; no mount or policy change")
    require(callable(getattr(os,"pidfd_open",None))
            and callable(getattr(signal,"pidfd_send_signal",None)),"pidfd APIs unavailable")
    paths=(guard.BASE.parent,guard.EXT,guard.HISTORY,Path("/var/lib/post-apollo-memory-reclaim"))
    require(not any(os.path.lexists(p) for p in paths) and not INSTANCE.exists(),"fresh isolated guest required")
    original=signature(guard)
    boot=guard.boot_id()
    created=False
    pid=None
    pidfd=None
    ack_r,ack_w=os.pipe()
    done_r,done_w=os.pipe()
    try:
        INSTANCE.mkdir()
        created=True
        write(INSTANCE/"tracing_on","0")
        write(INSTANCE/"current_tracer","nop")
        write(INSTANCE/"events"/"enable","0")
        write(INSTANCE/"trace_clock","global")
        require("[global]" in bounded(INSTANCE/"trace_clock",4096),"global clock unavailable")
        write(INSTANCE/"buffer_size_kb","64")
        for event,required in ((EVENTS[0],{"common_pid","pid","sig","result"}),
                               (EVENTS[1],{"common_pid","sig"})):
            require(required<=fields(INSTANCE/"events"/event/"format"),"signal event schema mismatch")
        pid=os.fork()
        if pid==0:
            try:
                os.close(ack_r)
                os.close(done_w)
                def handler(signum,frame):
                    if signum==signal.SIGTERM:
                        os.write(ack_w,b"S")
                signal.signal(signal.SIGTERM,handler)
                os.write(ack_w,b"R")
                os._exit(0 if os.read(done_r,1)==b"D" else 2)
            except BaseException:
                os._exit(2)
        os.close(ack_w)
        ack_w=None
        os.close(done_r)
        done_r=None
        read_one(ack_r,b"R")
        pidfd=os.pidfd_open(pid,0)
        start=stat_identity(pid)
        sender=os.getpid()
        for event,expression in ((EVENTS[0],"pid == "+str(pid)+" && sig == 15"),
                                 (EVENTS[1],"common_pid == "+str(pid)+" && sig == 15")):
            path=INSTANCE/"events"/event
            write(path/"filter",expression)
            require(bounded(path/"filter",4096).strip()==expression,"signal filter readback mismatch")
            write(path/"enable","1")
            require(bounded(path/"enable",32).strip()=="1","signal event not enabled")
        write(INSTANCE/"trace","")
        stats()
        write(INSTANCE/"tracing_on","1")
        require(stat_identity(pid)==start,"child identity changed before signal")
        # Only owned, still-live fixture child with installed handler; no
        # swapoff actor or system process ever receives a signal here.
        signal.pidfd_send_signal(pidfd,signal.SIGTERM,None,0)
        read_one(ack_r,b"S")
        write(INSTANCE/"tracing_on","0")
        require(stat_identity(pid)==start,"child identity changed after signal")
        stats()
        events=parse(bounded(INSTANCE/"trace"),sender,pid,start)
        stage("SIGNAL_PAIR "+json.dumps(events,separators=(",",":")))
        print("CPU_MEM_SIGNALCUSTODY_PASS // PIDFD_TARGET_GENERATION_DELIVERY_AND_HANDLER",flush=True)
        os.write(done_w,b"D")
        wait_child(pid)
        pid=None
        # Merely report interface presence. A kprobe profile is not a
        # per-fprobe missed-event witness; no inference from absence/zero.
        stage("MISSED_PROBE_ACCOUNTING_DISCOVERY "+json.dumps(
              {"kprobe_profile_present":(ROOT/"kprobe_profile").is_file(),
               "fprobe_profile_present":(ROOT/"fprobe_profile").is_file(),
               "fprobe_loss_qualified":False,"interruption_qualified":False},sort_keys=True))
    finally:
        for fd in (ack_r,ack_w,done_r,done_w,pidfd):
            if fd is not None:
                os.close(fd)
        # Closing the control pipe releases our child on failure. Never
        # send a generic PID kill or retry a signal. VM is disposable.
        if created:
            write(INSTANCE/"tracing_on","0")
            write(INSTANCE/"events"/"enable","0")
            INSTANCE.rmdir()
    require(not INSTANCE.exists() and guard.boot_id()==boot and signature(guard)==original
            and not any(os.path.lexists(p) for p in paths),"scope cleanup or swap baseline changed")
    print("CPU_MEM_SIGNALCUSTODY_PASS // PRIVATE_SCOPE_RETIRED_NO_MANAGED_SWAP_MUTATION",flush=True)

def main():
    guard=guarded()
    require(len(sys.argv)==2,"phase required")
    if sys.argv[1]=="guard":
        stage("EXACT_CANDIDATE "+PIN)
    elif sys.argv[1]=="run":
        run(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print("CPU_MEM_SIGNALCUSTODY_FAIL // "+type(exc).__name__+": "+str(exc),flush=True)
        raise SystemExit(2)
