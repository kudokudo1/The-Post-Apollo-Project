#!/usr/bin/env python3
"""One explicit, bounded parallel diagnostic capture. No daemon or archive writes.

Only fixed existing collectors are launched. Monotonic timestamps share the
Linux boot clock; actual start skew and overlap are observed, not assumed.
The envelope is transport evidence, not a qualified UI COMPLETE result.
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from syntagma_quickshell_thread_sampler import find_quickshell, parse_stat_line

ORDER = ("threads", "memory", "census", "storage", "stall")
SCRIPTS = dict(zip(ORDER, ("syntagma_quickshell_thread_sampler.py",
                         "cpuplus_quickshell_memory_observer.py",
                         "cpuplus_process_census.py", "cpuplus_storage_observer.py",
                         "cpuplus_stall_clock_witness.py")))
CHILD_BYTES = 65536
ENVELOPE_BYTES = 300000
PLAN_BYTES = 4096


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    def invalid(_):
        raise ValueError("non-finite JSON")
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid)


def validate(plan):
    if type(plan) is not dict or set(plan) != {"durationSeconds", "instruments"}:
        raise ValueError("invalid workflow fields")
    duration, items = plan["durationSeconds"], plan["instruments"]
    if not integer(duration, 1, 120) or type(items) is not list or not 2 <= len(items) <= 5:
        raise ValueError("invalid workflow duration/count")
    configs = {}
    for item in items:
        if type(item) is not dict or type(item.get("kind")) is not str:
            raise ValueError("invalid instrument")
        kind = item["kind"]
        if kind not in ORDER or kind in configs:
            raise ValueError("unsupported/duplicate instrument")
        keys = {"kind"} if kind == "storage" else {"kind", "thresholdMs"} if kind == "stall" else {"kind", "intervalMs"}
        if kind == "threads":
            keys.add("topCount")
        if kind == "storage" and set(item) == {"kind", "sampleSeconds", "reportSeconds"}:
            keys = set(item)
        if set(item) != keys:
            raise ValueError("unsupported instrument fields")
        if kind == "stall":
            if duration<5 or not integer(item["thresholdMs"],150,2000) or item["thresholdMs"]%50:
                raise ValueError("stall calibration")
        elif kind == "storage":
            if duration > 30:
                raise ValueError("storage duration")
            if "sampleSeconds" in item:
                sample, report = item["sampleSeconds"], item["reportSeconds"]
                if (not integer(sample,1,min(5,duration)) or not integer(report,sample,30)
                        or report%sample or (duration+report-1)//report>6):
                    raise ValueError("storage cadence or report budget")
        else:
            ms = item["intervalMs"]
            if not integer(ms, 100, min(60000, duration*1000)):
                raise ValueError("invalid interval")
            n = (duration*1000+ms-1)//ms
            if kind == "threads":
                top = item["topCount"]
                if ms not in (100,250,500,1000,2000,5000) or not integer(top,1,12) or n>30 or n*(top+1)>150:
                    raise ValueError("thread budget")
            elif kind == "memory":
                if ms<5000 or ms%1000 or n>12:
                    raise ValueError("memory budget")
            elif duration>60 or ms%1000 or n>3:
                raise ValueError("census budget")
        configs[kind] = dict(item, durationSeconds=duration)
    return [configs[kind] for kind in ORDER if kind in configs]


def pin_quickshell(root=Path("/proc")):
    uid = os.getuid()
    pid = find_quickshell(root, uid)
    if pid is None:
        raise ValueError("Quickshell unavailable")
    path = root/str(pid)
    first = parse_stat_line((path/"stat").read_text())
    if path.stat().st_uid != uid or first["name"] != "quickshell" or first["start"]<=0:
        raise ValueError("Quickshell identity unavailable")
    return {"pid":pid,"startTicks":first["start"]}


def commands(configs, data_dir, scripts, pinned):
    result = {}
    for c in configs:
        kind = c["kind"]
        if kind == "stall":
            result[kind]=[sys.executable,"-B",str(scripts/SCRIPTS[kind]),"--workflow",
                          "--duration",str(c["durationSeconds"])]
            continue
        args = [sys.executable, "-B", str(scripts/SCRIPTS[kind]), "--workshop",
                "--duration", str(c["durationSeconds"])]
        if kind == "storage":
            args += ["--data-dir", str(data_dir), "--shell-dir", str(scripts.parent)]
            if "sampleSeconds" in c:
                args += ["--sample-seconds",str(c["sampleSeconds"]),"--report-seconds",str(c["reportSeconds"])]
        else:
            args += ["--interval", str(c["intervalMs"]/1000) if kind=="threads" else str(c["intervalMs"]//1000)]
        if kind == "threads":
            args += ["--top",str(c["topCount"])]
        if kind in ("threads","memory"):
            if not pinned:
                raise ValueError("missing process pin")
            args += ["--workshop-identity",str(pinned["pid"]),str(pinned["startTicks"])]
        result[kind]=args
    return result


def now_ms():
    return round(time.monotonic()*1000)


def collect_children(argvs, duration, cancelled):
    """Internal fixed argv dispatch. Drain all pipes concurrently with hard caps."""
    children, data, errors, launches = {}, {}, {}, {}
    selector = selectors.DefaultSelector()
    started = now_ms()
    deadline = time.monotonic()+duration+20
    reason = ""
    try:
        for kind, argv in argvs.items():
            if cancelled():
                reason="CANCELLED"
                break
            try:
                # No new process group: outer timeout can clean up the whole tree.
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                children[kind]=child
                launches[kind]=now_ms()
                data[kind]=bytearray()
                os.set_blocking(child.stdout.fileno(),False)
                selector.register(child.stdout, selectors.EVENT_READ,kind)
            except OSError:
                errors[kind]="SPAWN FAILED"
        while selector.get_map() or any(p.poll() is None for p in children.values()):
            if cancelled():
                reason="CANCELLED"
                break
            if time.monotonic()>=deadline:
                reason="DEADLINE"
                break
            for key,_ in selector.select(0.1):
                kind=key.data
                try:
                    chunk=os.read(key.fd,8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if len(data[kind])+len(chunk)>CHILD_BYTES:
                    errors[kind]="OUTPUT LIMIT"
                    selector.unregister(key.fileobj)
                    if children[kind].poll() is None:
                        children[kind].terminate()
                    continue
                data[kind].extend(chunk)
    finally:
        selector.close()
        # Only our owned child handles are stopped, never the observed PID.
        for child in children.values():
            if child.poll() is None:
                child.terminate()
        until=time.monotonic()+1
        for child in children.values():
            try:
                child.wait(timeout=max(0,until-time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
        for child in children.values():
            child.wait()
            child.stdout.close()
    result={}
    for kind in argvs:
        p=children.get(kind)
        result[kind]={"exitCode":p.returncode if p else None,
                      "launchMonotonicMs":launches.get(kind),
                      "error":errors.get(kind,reason or ("NOT STARTED" if p is None else "")),
                      "raw":bytes(data.get(kind,b""))}
    return started,now_ms(),reason,result


def receipt(config, raw, pinned):
    """Transport checks; full metric semantics remain the existing JS policy's job."""
    if len(raw)>CHILD_BYTES or not raw.endswith(b"\n"):
        raise ValueError("missing complete JSONL")
    rows=[decode(line) for line in raw.decode("ascii").splitlines()]
    if not rows or any(type(r) is not dict for r in rows):
        raise ValueError("invalid rows")
    kind=config["kind"]
    end=rows[-1]
    if kind=="stall":
        if len(raw)>2048 or len(rows)!=1 or end.get("schema")!="post-apollo-stall-clock-v1":
            raise ValueError("invalid stall witness")
        first,last=end.get("startedMonotonicMs"),end.get("monotonicMs")
        a,b=end.get("startWallMs"),end.get("endWallMs")
        elapsed=end.get("elapsedMs")
        if (end.get("durationSeconds")!=config["durationSeconds"]
                or not integer(first,0,2**53-1) or not integer(last,first,2**53-1)
                or not integer(a,1,2**53-1) or not integer(b,a,2**53-1)
                or not integer(elapsed,config["durationSeconds"]*1000,config["durationSeconds"]*1000+5000)
                or abs(last-first-elapsed)>2 or abs(b-a-elapsed)>250):
            raise ValueError("stall witness timeline")
        return rows,first,last
    if end.get("event")!="complete":
        raise ValueError("missing terminal receipt")
    if kind=="threads":
        start=rows[0]
        if (len(rows)<3 or start.get("event")!="start" or start.get("workshopSchema")!="post-apollo-thread-calibration-v1"
                or end.get("workshopSchema")!=start.get("workshopSchema")
                or any(start.get(k)!=config[k] for k in ("durationSeconds","intervalMs","topCount"))
                or end.get("samples")!=len(rows)-2
                or any(row.get("event")!="threads" for row in rows[1:-1])):
            raise ValueError("thread receipt mismatch")
        first=start.get("monotonicMs")
    else:
        if (end.get("workshopSchema")!="post-apollo-observer-calibration-v1"
                or end.get("calibration")!=config or end.get("samples")!=len(rows)-1
                or any(row.get("event")!=kind for row in rows[:-1])):
            raise ValueError("observer receipt mismatch")
        if kind=="memory" and len(rows)<3:
            raise ValueError("missing memory baseline or interval")
        first=rows[0].get("monotonicMs") if kind=="memory" else end.get("startedMonotonicMs")
    if kind in ("threads","memory"):
        if not pinned or any(row.get("pid")!=pinned["pid"] or row.get("startTicks")!=pinned["startTicks"] for row in rows):
            raise ValueError("process identity mismatch")
    stamps=[r.get("monotonicMs") for r in rows]
    last=end.get("monotonicMs")
    if (len(rows)<2 or not integer(first,0,2**53-1)
            or not integer(last,first,2**53-1)
            or any(not integer(t,first,last) for t in stamps)
            or stamps!=sorted(stamps)
            or not integer(end.get("observedMs"),config["durationSeconds"]*1000,145000)
            or abs(last-first-end["observedMs"])>2):
        raise ValueError("timeline mismatch")
    return rows,first,last


def run(plan, data_dir, cancelled):
    configs=validate(plan)
    pinned=pin_quickshell() if any(c["kind"] in ("threads","memory") for c in configs) else None
    argvs=commands(configs,data_dir,Path(__file__).resolve().parent,pinned)
    start,end,reason,results=collect_children(argvs,plan["durationSeconds"],cancelled)
    instruments=[]
    for config in configs:
        child=results[config["kind"]]
        raw=child.pop("raw")
        item={"config":config,**child,"payloadBytes":len(raw),"status":"NOT VERIFIED","records":[]}
        if not child["error"] and child["exitCode"]==0:
            try:
                rows,first,last=receipt(config,raw,pinned)
                if not start<=first<=last<=end:
                    raise ValueError("outside capture window")
                item.update(status="COLLECTED",records=rows,firstMonotonicMs=first,lastMonotonicMs=last)
            except (ValueError,UnicodeError,TypeError):
                item["error"]="RECEIPT MISMATCH"
        elif not child["error"]:
            item["error"]="COLLECTOR EXIT"
        instruments.append(item)
    collected=[i for i in instruments if i["status"]=="COLLECTED"]
    overlap=None
    if len(collected)==len(instruments):
        overlap=max(0,min(i["lastMonotonicMs"] for i in collected)-max(i["firstMonotonicMs"] for i in collected))
    status=("CANCELLED" if reason=="CANCELLED" else
            "COLLECTED" if len(collected)==len(instruments) and overlap>0 else "NOT VERIFIED")
    return {"schema":"post-apollo-diagnostic-workflow-transport-v1","status":status,
            "durationSeconds":plan["durationSeconds"],"pinnedQuickshell":pinned,
            "startedMonotonicMs":start,"finishedMonotonicMs":end,
            "overlapMs":overlap,"instruments":instruments}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",required=True)
    p.add_argument("--data-dir",type=Path,required=True)
    a=p.parse_args(argv)
    if len(a.plan.encode("utf-8"))>PLAN_BYTES or not a.data_dir.is_absolute():
        p.error("invalid plan size or data root")
    stopped=False
    def stop(_sig,_frame):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        plan=decode(a.plan)
        result=run(plan,a.data_dir,lambda:stopped)
        encoded=json.dumps(result,ensure_ascii=True,separators=(",",":"),allow_nan=False)
        if len(encoded)+1>ENVELOPE_BYTES:
            raise ValueError("aggregate output limit")
        print(encoded,flush=True)
        return 0 if result["status"]=="COLLECTED" else 130 if result["status"]=="CANCELLED" else 1
    except (OSError,ValueError,TypeError,RecursionError):
        print("Workflow not verified",file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
