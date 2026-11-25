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
import subprocess
import sys
import time

PIN = "5f6e6d800dcf41c1f0f7330fdb248dfd2177104f"
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
    # Fixed guest control names only, no raw trace contents or addresses.
    try:
        with path.open("w",encoding="ascii") as stream:
            stream.write(value+"\n")
    except OSError as exc:
        raise RuntimeError("trace control refused: "+str(path.relative_to(ROOT))+
                           " errno="+str(exc.errno)) from exc

def probe_diagnostic(raw, command):
    """Match the kernel's latest Command: record, not an arbitrary old error."""
    lines=raw.splitlines()
    matches=[i for i,line in enumerate(lines) if line.strip().startswith("Command:")]
    if not matches:
        return {"category":"NO_COMMAND_RECORD"}
    index=matches[-1]
    if lines[index].strip().removeprefix("Command:").strip()!=command:
        return {"category":"LAST_COMMAND_MISMATCH"}
    if index==0:
        return {"category":"ERROR_HEADER_MISSING"}
    header=lines[index-1]
    match=re.fullmatch(r"\s*\[\s*\d+(?:\.\d+)?\]\s*([a-zA-Z0-9_/-]+):\s*error:\s*(.*)",header)
    if match is None:
        return {"category":"ERROR_HEADER_UNRECOGNIZED"}
    location,message=match.groups()
    # Export only bounded safe text from the fixed command's error header.
    # Redact hex tokens, decimal addresses/large numbers, and any other
    # non-prose characters; never emit raw trace or raw error_log.
    message=re.sub(r"(?i)\b(?:0x)?[0-9a-f]{8,}\b","[redacted]",message)
    message=re.sub(r"[^a-zA-Z0-9 _.,:;()/\[\]'%-]","?",message)[:160]
    category="KERNEL_DIAGNOSTIC"
    for label,pattern in (
        ("SYMBOL_NOT_FOUND",r"symbol.*not found|failed to find.*symbol|no such symbol"),
        ("PROBE_REGISTRATION_REJECTED",r"failed to register|not probeable|not probed|blacklist"),
        ("INVALID_PROBE_ARGUMENT",r"invalid.*arg|bad.*arg|invalid.*type"),
        ("UNSUPPORTED_PROBE",r"not supported|unsupported"),
        ("PERMISSION_REFUSED",r"permission denied|operation not permitted"),
    ):
        if re.search(pattern,message,re.I):
            category=label
            break
    return {"category":category,"location":location[:64],"message":message}

def append_probe(value):
    # Use one explicit write of the fixed command. Distinguish opening
    # the interface from the kernel rejecting the command itself.
    operation=value.split()[0]
    stage("PROBE_CONTROL_BEGIN "+operation)
    before=None
    try:
        before=bounded(ROOT/"error_log",65536)
    except (OSError,ValueError,RuntimeError):
        pass
    phase="open"
    fd=None
    try:
        fd=os.open(ROOT/"dynamic_events",os.O_WRONLY|os.O_APPEND|os.O_CLOEXEC)
        phase="write"
        payload=(value+"\n").encode("ascii")
        require(os.write(fd,payload)==len(payload),"short probe control write")
    except OSError as exc:
        diagnostic={"category":"ERROR_LOG_UNAVAILABLE"}
        try:
            after=bounded(ROOT/"error_log",65536)
            diagnostic=(probe_diagnostic(after,value) if before is not None and after!=before
                        else {"category":"NO_NEW_KERNEL_ERROR_RECORD"})
        except (OSError,ValueError,RuntimeError):
            pass
        stage("REGISTRATION_DIAGNOSTIC "+json.dumps(
              {"operation":operation,"phase":phase,"errno":exc.errno,
               "kernel":diagnostic},sort_keys=True))
        raise RuntimeError("fprobe control refused: "+operation+
                           " phase="+phase+" errno="+str(exc.errno)) from exc
    finally:
        if fd is not None:
            os.close(fd)
    stage("PROBE_CONTROL_COMPLETE "+operation)

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
    require(not any(os.path.lexists(path) for path in
                    (guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "fresh guest required before registration")
    # Establish the rejected registration boundary before allocating any
    # managed swap. No additional native cycles if registration fails.
    # All changes are confined to this disposable guest.
    created=[]
    instance_created=False
    try:
        stage("PRIVATE_INSTANCE_CREATE_BEGIN")
        INSTANCE.mkdir()
        instance_created=True
        stage("PRIVATE_INSTANCE_CREATED")
        write(INSTANCE/"tracing_on","0")
        write(INSTANCE/"current_tracer","nop")
        write(INSTANCE/"events"/"enable","0")
        stage("PRIVATE_INSTANCE_DISABLED")
        write(INSTANCE/"trace_clock","global")
        require("[global]" in bounded(INSTANCE/"trace_clock",4096),"global clock not selected")
        stage("GLOBAL_CLOCK_SELECTED")
        write(INSTANCE/"buffer_size_kb","64")
        stage("PRIVATE_BUFFER_CONFIGURED")
        require((ROOT/"dynamic_events").is_file(),"dynamic event control unavailable")
        functions=bounded(ROOT/"available_filter_functions",16*1024*1024)
        require(sum(line.split()[:1]==["try_to_unuse"] for line in functions.splitlines())==1,
                "exact unique function unavailable")
        stage("EXPLICIT_FPROBE_BACKEND")
        append_probe("f:"+GROUP+"/unuse_enter try_to_unuse")
        created.append("unuse_enter")
        append_probe("f:"+GROUP+"/unuse_return try_to_unuse%return ret=$retval:s32")
        created.append("unuse_return")
        definitions=bounded(ROOT/"dynamic_events",1048576).splitlines()
        require(sum(line.split()[:2]==["f:"+GROUP+"/unuse_enter","try_to_unuse"]
                    for line in definitions)==1
                and sum(line.split()[:2]==["f:"+GROUP+"/unuse_return","try_to_unuse%return"]
                        for line in definitions)==1,"registered fprobe identity unverified")
        stage("PRIVATE_INSTANCE_AND_PROBES_REGISTERED")
        # All earlier assertions remain mandatory for calibration PASS.
        # Tracing is disabled during the two normal cycles.
        subprocess.run(["/usr/bin/bash","/usr/local/libexec/postapollo-memory-ci-cycle.sh"],
                       check=True,cwd="/")
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
        # Preserve the first exception instead of masking it with cleanup.
        # Cleanup only our exact private scope; any failure still fails CI.
        original_failure = sys.exc_info()[0] is not None
        cleanup_errors = []
        if instance_created:
            for name, action in (
                ("tracing_on", lambda: write(INSTANCE/"tracing_on","0")),
                ("events", lambda: write(INSTANCE/"events"/"enable","0")),
                ("instance", INSTANCE.rmdir),
            ):
                try:
                    action()
                except (OSError,RuntimeError) as exc:
                    cleanup_errors.append(name)
                    stage("PRIVATE_CLEANUP_FAILED "+name+" "+type(exc).__name__)
        for event in reversed(created):
            try:
                append_probe("-:"+GROUP+"/"+event)
            except (OSError,RuntimeError) as exc:
                cleanup_errors.append(event)
                stage("PRIVATE_CLEANUP_FAILED "+event+" "+type(exc).__name__)
        if cleanup_errors and not original_failure:
            raise RuntimeError("private trace cleanup failed")
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
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print("CPU_MEM_TRACECOLLECT_FAIL // "+type(exc).__name__+": "+str(exc),flush=True)
        raise SystemExit(2)
