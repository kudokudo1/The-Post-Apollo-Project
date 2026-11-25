#!/usr/bin/python3 -I
"""Guest-only trace collector calibration; no deliberate kernel interruption."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import sys
import time

PIN = "6bac8be7b1de6883f480a95944d6ba1130852270"
KERNEL_PIN = "f0889696b252969d5f96f7824d4f7374fad2108c"
MARKER = Path("/etc/postapollo-memory-native-tracecollect-ci-only")
GUARD = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
CUSTODY = Path("/usr/local/libexec/postapollo-memory-ci-custody.py")
ROOT = Path("/sys/kernel/tracing")
GROUP = "pa_cpu_mem_ci"
INSTANCE = ROOT / "instances" / GROUP
EVENTS = ("syscalls/sys_enter_swapoff", "syscalls/sys_exit_swapoff",
          GROUP + "/unuse_enter", GROUP + "/unuse_return")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def load(name,path):
    loader = importlib.machinery.SourceFileLoader(name,str(path))
    spec = importlib.util.spec_from_loader(loader.name,loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    guard=load("collector_guard",GUARD)
    require(guard.protected_bytes(MARKER).strip()==b"DISPOSABLE_CPU_MEMORY_TRACECOLLECT_V1",
            "collector fixture marker absent")
    guard.PIN=PIN
    guard.guard()
    require(platform.machine()=="x86_64","unexpected architecture")
    import hashlib
    source=guard.protected_bytes(CUSTODY)
    require(hashlib.sha1(b"blob "+str(len(source)).encode()+b"\0"+source).hexdigest()==KERNEL_PIN,
            "custody fixture mismatch")
    return guard

def bounded(path,limit=1048576):
    with path.open("rb") as stream:
        raw=stream.read(limit+1)
    require(len(raw)<=limit,"trace read bound exceeded")
    return raw.decode("ascii")

def write(path,value):
    with path.open("w",encoding="ascii") as stream:
        stream.write(value+"\n")

def append_probe(value):
    with (ROOT/"kprobe_events").open("a",encoding="ascii") as stream:
        stream.write(value+"\n")

def stage(message):
    print("CPU_MEM_TRACECOLLECT_STAGE // "+message,flush=True)

def stats(instance):
    cpus=sorted((instance/"per_cpu").glob("cpu[0-9]*"))
    require(cpus,"per-CPU trace statistics unavailable")
    for cpu in cpus:
        raw=bounded(cpu/"stats",65536)
        for key in ("overrun","commit overrun","dropped events"):
            values=re.findall(r"^"+key+r":\s*(\d+)\s*$",raw,re.M)
            require(values==["0"],"trace loss or ambiguous counters")

def parse(raw,pid):
    """Require the original actor and four actual, strictly ordered events.

    The formatted trace can use syscall event names or the common sys_swapoff
    label. Do not retain filename pointer fields or raw kernel addresses.
    """
    records=[]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match=re.fullmatch(r"\s*.+-(\d+)\s+\[\d+\]\s+\S+\s+(\d+)\.(\d+):\s*(.*)",line)
        require(match is not None,"unrecognized trace row")
        actor,sec,fraction,payload=match.groups()
        require(int(actor)==pid and 1<=len(fraction)<=9,"trace actor or timestamp mismatch")
        stamp=int(sec)*10**9+int(fraction.ljust(9,"0"))
        if re.match(r"(?:sys_enter_swapoff:|sys_swapoff:?\s*\()",payload):
            kind="SYSCALL_ENTER"
        elif re.match(r"(?:sys_exit_swapoff:|sys_swapoff\s*(?::\s*)?->)",payload):
            # Successful return only. No interruption qualification.
            require(re.search(r"(?:->\s*|ret=|ret:\s*)(?:0x0+|0)(?:\s|$)",payload) is not None,
                    "successful syscall return not observed")
            kind="SYSCALL_EXIT"
        elif re.match(r"(?:pa_cpu_mem_ci:)?unuse_enter:",payload):
            kind="UNUSE_ENTER"
        elif re.match(r"(?:pa_cpu_mem_ci:)?unuse_return:",payload):
            require(re.search(r"\bret=(?:0x0+|0)(?:\s|$)",payload) is not None,
                    "successful function return not observed")
            kind="UNUSE_RETURN"
        else:
            raise RuntimeError("unexpected event in private trace")
        records.append((kind,stamp))
    require([kind for kind,_ in records]==["SYSCALL_ENTER","UNUSE_ENTER","UNUSE_RETURN","SYSCALL_EXIT"],
            "missing, repeated or misordered kernel boundaries")
    require(all(a[1]<b[1] for a,b in zip(records,records[1:])),"trace ordering ambiguous")
    return records

def run(guard):
    require(guard.command("/usr/bin/findmnt","-n","-o","FSTYPE","-T",str(ROOT)).strip()=="tracefs",
            "tracefs not mounted; no security change allowed")
    require(not INSTANCE.exists() and not (ROOT/"events"/GROUP).exists(),
            "trace scope already exists")
    custody=load("collector_custody",CUSTODY)
    guard.verify_swap(True)
    require(custody.no_records(guard),"unfenced extension required")
    original=custody.signature(guard)
    identities=[guard.identity(guard.BASE),guard.identity(guard.EXTRA)]
    history=guard.history()
    boot=guard.boot_id()
    require(len(history)==2,"normal cycles required")
    ready=guard.helper("reduction-preflight","4")
    require(ready.returncode==0 and json.loads(ready.stdout)["state"]=="READY_ADVISORY",
            "ordinary withdrawal admission unavailable")
    # Registration precedes helper start; on unavailable tracing, fail
    # without initiating the third withdrawal. All changes are guest-only.
    created=[]
    instance_created=False
    try:
        INSTANCE.mkdir()
        instance_created=True
        write(INSTANCE/"tracing_on","0")
        write(INSTANCE/"current_tracer","nop")
        write(INSTANCE/"events"/"enable","0")
        write(INSTANCE/"trace_clock","global")
        require("[global]" in bounded(INSTANCE/"trace_clock",4096),"global clock not selected")
        write(INSTANCE/"buffer_size_kb","64")
        append_probe("p:"+GROUP+"/unuse_enter try_to_unuse")
        created.append("unuse_enter")
        append_probe("r:"+GROUP+"/unuse_return try_to_unuse ret=$retval:s64")
        created.append("unuse_return")
        stage("PRIVATE_INSTANCE_AND_PROBES_REGISTERED")
        root,swap=custody.trace_to_entry(guard)
        intent_path,result_path=(guard.EXT/name for name in guard.RECORD_NAMES[:2])
        intent=guard.protected_bytes(intent_path)
        require(json.loads(intent)["state"]=="PREPARED"
                and not os.path.lexists(result_path)
                and custody.signature(guard)==original
                and custody.same_executable(swap,custody.SWAPOFF)
                and custody.inherited_lock_fds(swap),"actor or durable boundary mismatch")
        proc=Path("/proc")/str(swap)/"stat"
        fields=bounded(proc,4096).rsplit(")",1)[1].split()
        start_ticks=int(fields[19])
        require(start_ticks>0,"actor start identity unavailable")
        # Repeat the already reviewed parent-death custody boundary. No
        # signal is sent to the swapoff child and no syscall is interrupted.
        os.kill(root,signal.SIGKILL)
        pid,status=custody.wait_event(time.monotonic()+10)
        require(pid==root and os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL,
                "parent death not confirmed")
        require(custody.same_executable(swap,custody.SWAPOFF)
                and custody.inherited_lock_fds(swap)
                and int(bounded(proc,4096).rsplit(")",1)[1].split()[19])==start_ticks,
                "original child identity changed")
        custody.expect_busy(guard)
        for event in EVENTS:
            path=INSTANCE/"events"/event
            write(path/"filter","common_pid == "+str(swap))
            require(bounded(path/"filter",4096).strip()=="common_pid == "+str(swap),
                    "actor filter not installed")
            write(path/"enable","1")
            require(bounded(path/"enable",32).strip()=="1","event not enabled")
        write(INSTANCE/"trace","")
        stats(INSTANCE)
        write(INSTANCE/"tracing_on","1")
        custody.ptrace(custody.CONT,swap)
        pid,status=custody.wait_event(time.monotonic()+30)
        write(INSTANCE/"tracing_on","0")
        require(pid==swap and os.WIFEXITED(status) and os.WEXITSTATUS(status)==0,
                "original child did not complete normally")
        stats(INSTANCE)
        records=parse(bounded(INSTANCE/"trace"),swap)
        stage("ORDERED_BOUNDARIES "+json.dumps({"pid":swap,"start_ticks":start_ticks,
                                               "events":records},separators=(",",":")))
        print("CPU_MEM_TRACECOLLECT_PASS // EXACT_ACTOR_SUCCESSFUL_KERNEL_INTERVAL_ZERO_BUFFER_LOSS",flush=True)
        guard.verify_swap(False)
        expected=dict(original)
        del expected[str(guard.EXTRA)]
        require(guard.boot_id()==boot and custody.signature(guard)==expected
                and [guard.identity(guard.BASE),guard.identity(guard.EXTRA)]==identities
                and guard.history()==history and guard.protected_bytes(intent_path)==intent
                and not os.path.lexists(result_path),"post-effect evidence changed")
        guard.fence()
        observed=guard.success("inspect-recovery-authorized",prefix="RECOVERY INSPECTION: ")
        require(observed["code"]=="INTENT_ONLY_INACTIVE"
                and observed["mutationAllowed"] is False and observed["recordCleared"] is False,
                "original unknown operation not fenced")
        print("CPU_MEM_TRACECOLLECT_PASS // ORIGINAL_EFFECT_UNKNOWN_RESULT_RETAINED",flush=True)
    finally:
        if instance_created:
            write(INSTANCE/"tracing_on","0")
            write(INSTANCE/"events"/"enable","0")
            INSTANCE.rmdir()
        for event in reversed(created):
            append_probe("-:"+GROUP+"/"+event)
    require(not INSTANCE.exists() and not (ROOT/"events"/GROUP).exists(),
            "private trace scope not retired")
    print("CPU_MEM_TRACECOLLECT_PASS // PRIVATE_TRACE_SCOPE_RETIRED",flush=True)

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
    except (OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        print("CPU_MEM_TRACECOLLECT_FAIL // "+type(exc).__name__+": "+str(exc),flush=True)
        raise SystemExit(2)
