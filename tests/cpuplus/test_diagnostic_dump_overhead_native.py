#!/usr/bin/env python3
"""Disposable native overhead/identity witness. No production shell is started."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")

IDS = ["appcontrol","camera","hospital","finance","git","company-network","tasks",
       "forest","apollo-hub","cpuplus","weather","social","time","notifications","media"]
HZ = os.sysconf("SC_CLK_TCK")
SCRIPT = "cpuplus_quickshell_memory_observer.py"

def scene_text(mounted):
    flags = "\n".join("    QtObject { id: flag%d; property bool %s: false }" %
                      (i, "deckOpen" if key == "media" else "menuOpen") for i,key in enumerate(IDS))
    refs = ",".join('"%s":flag%d' % (key,i) for i,key in enumerate(IDS))
    adapter = """
    DiagnosticDumpResourceCapture { id: resource }
    DiagnosticWidgetLifecycleAdapter {
        id: recorder
        sources: root.flags
        resourceCapture: resource
    }
""" if mounted else ""
    functions = """
    function idle() { return !recorder.active && !resource.busy && !resource.faulted; }
    function startCapture() { return recorder.start(Object.keys(flags),5000); }
    function tickCapture(elapsed, now) { if(recorder.observing)recorder.loopTick(elapsed,now); }
    function finished() { return !recorder.active && !resource.busy; }
    function confirmCapture() {
        const r=recorder.report;
        if(!r || r.status!=="COMPLETE" || !r.resource || r.resource.status!=="COMPLETE" ||
            !r.resource.evidence || r.events.length===0 || r.eventLoop.ticks===0){
            console.error("CPU_Q6_TERMINAL "+JSON.stringify(r?{status:r.status,reason:r.reason||"",resourceStatus:r.resource?r.resource.status:"MISSING",resourceReason:r.resource?(r.resource.reason||""):"",ticks:r.eventLoop?r.eventLoop.ticks:0,events:r.events?r.events.length:0}:null));
            return false;
        }
        console.log("CPU_Q6_IDENTITY "+JSON.stringify({pid:r.resource.evidence.pid,startTicks:r.resource.evidence.startTicks,
            samples:r.resource.evidence.samples.length,overlapMs:r.resource.evidence.overlapMs,
            ticks:r.eventLoop.ticks,events:r.events.length}));
        return true;
    }
    function stopCapture() { return recorder.cancel(); }
    function confirmStop() { return recorder.report && recorder.report.status==="CANCELLED" && idle(); }
""" if mounted else """
    function idle() { return true; }
    function startCapture() { return true; }
    function tickCapture(elapsed, now) {}
    function finished() { return phase===5 || Date.now()-phaseStart>=5500; }
    function confirmCapture() { return true; }
    function stopCapture() { return true; }
    function confirmStop() { return true; }
"""
    return """import QtQuick
import Quickshell
import qs.services.diagnostics
ShellRoot {
    id: root
    property int phase: 0
    property double phaseStart: 0
    property double previous: 0
    property int step: 0
    property var flags: ({""" + refs + """})
""" + flags + adapter + functions + """
    function mark(name) { console.log("CPU_Q6_MARK "+name); }
    function fail(name) { console.error("CPU_Q6_FAIL "+name); Qt.exit(1); }
    function advance(next,now) { phase=next;phaseStart=now; }
    Timer {
        interval: 100; running: true; repeat: true
        onTriggered: {
            const now=Date.now();
            if(!root.phaseStart)root.phaseStart=now;
            const elapsed=root.previous ? now-root.previous : 0;
            root.previous=now;
            const keys=Object.keys(root.flags);
            const key=keys[root.step++%keys.length], source=root.flags[key];
            if(key==="media")source.deckOpen=!source.deckOpen;
            else source.menuOpen=!source.menuOpen;
            root.tickCapture(elapsed,now);
            const age=now-root.phaseStart;
            if(root.phase===0 && age>=1000){
                if(!root.idle()){root.fail("startup not idle");return;}
                root.mark("IDLE_BEGIN");root.advance(1,now);
            }else if(root.phase===1 && age>=5000){
                if(!root.idle()){root.fail("idle worker");return;}
                root.mark("IDLE_END");root.mark("ACTIVE_BEGIN");
                if(!root.startCapture()){root.fail("start refused");return;}
                root.advance(2,now);
            }else if(root.phase===2 && root.finished()){
                if(!root.confirmCapture()){root.fail("real resource receipt unavailable");return;}
                root.mark("ACTIVE_END");root.mark("POST_BEGIN");root.advance(3,now);
            }else if(root.phase===3 && age>=3000){
                if(!root.idle()){root.fail("post capture not idle");return;}
                root.mark("POST_END");
                if(!root.startCapture()){root.fail("second start refused");return;}
                root.advance(4,now);
            }else if(root.phase===4 && age>=1000){
                if(!root.stopCapture()){root.fail("stop refused");return;}
                root.advance(5,now);
            }else if(root.phase===5 && root.finished()){
                if(!root.confirmStop()){root.fail("stop not terminal");return;}
                root.mark("CLEANUP_BEGIN");root.advance(6,now);
            }else if(root.phase===6 && age>=1000){
                if(!root.idle()){root.fail("cleanup not idle");return;}
                root.mark("CLEANUP_END");root.advance(7,now);
            }else if(root.phase===7 && age>=300){
                console.log("CPU_Q6_PASS");Qt.quit();
            }
        }
    }
}
"""

def proc_snapshot(pid):
    p = Path("/proc")/str(pid)
    raw = (p/"stat").read_text()
    fields = raw[raw.rfind(")")+1:].split()
    memory = {}
    for line in (p/"smaps_rollup").read_text().splitlines():
        name, _, tail = line.partition(":")
        if name in ("Pss","Rss","SwapPss"):
            memory[name] = int(tail.split()[0])
    assert set(memory) == {"Pss","Rss","SwapPss"}
    return dict(pid=pid,startTicks=int(fields[19]),ticks=int(fields[11])+int(fields[12]),
                atNs=time.monotonic_ns(),memoryKiB=memory)

def descendants(pid):
    pending=[pid]
    seen=set()
    while pending:
        parent=pending.pop()
        try:
            tasks=list((Path("/proc")/str(parent)/"task").iterdir())
        except OSError:
            continue
        for task in tasks:
            try:
                children=(task/"children").read_text().split()
            except OSError:
                continue
            for child in map(int,children):
                if child not in seen and child!=pid:
                    seen.add(child);pending.append(child)
    return seen

def observer_children(pid,script):
    found=[]
    for child in descendants(pid):
        try:
            args=(Path("/proc")/str(child)/"cmdline").read_bytes().split(b"\0")
            if os.fsencode(str(script)) in args and args and Path(os.fsdecode(args[0])).name.startswith("python"):
                found.append(child)
        except OSError:
            pass
    return found

def run_scene(folder,mounted):
    folder.mkdir()
    scene=folder/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"services/diagnostics",scene/"services/diagnostics")
    scripts=scene/"scripts";scripts.mkdir()
    for name in (SCRIPT,"syntagma_quickshell_thread_sampler.py"):
        shutil.copy2(ROOT/"scripts"/name,scripts/name)
    # Test-only diagnostic wrapper, executing the unchanged observer in the
    # same Python process (no extra parent, no permission or identity bypass).
    # Preserve its exact stdout, stderr and exit status. Keep the capture in
    # this private temporary scene, and print only bounded structural evidence.
    actual=scripts/"actual_memory_observer.py"
    (scripts/SCRIPT).rename(actual)
    (scripts/SCRIPT).write_text(r"""
import contextlib,json,os,runpy,sys
from pathlib import Path
from syntagma_quickshell_thread_sampler import launching_quickshell,parse_stat_line
base=Path(__file__).parent
diag={"parent":os.getppid(),"parentComm":None,"launcher":None,"smaps":"NOT CHECKED"}
try:
    diag["parentComm"]=(Path("/proc")/str(os.getppid())/"comm").read_text().strip()
    diag["launcher"]=launching_quickshell()
    if diag["launcher"]:
        p=Path("/proc")/str(diag["launcher"])
        diag["launcherStart"]=parse_stat_line((p/"stat").read_text())["start"]
        try:
            with (p/"smaps_rollup").open() as handle:
                diag["smapsFields"]=[line.partition(":")[0] for line in handle if line.partition(":")[0] in
                    ("Rss","Pss","Pss_Anon","Pss_File","Pss_Shmem","Private_Clean","Private_Dirty","Swap","SwapPss")]
            diag["smaps"]="READABLE"
        except OSError as e:
            diag["smaps"]="ERRNO_"+str(e.errno)
except (OSError,ValueError,IndexError) as e:
    diag["preflightError"]=type(e).__name__
(base/"observer-preflight.json").write_text(json.dumps(diag))
class Tee:
    def __init__(self,stream,copy):
        self.stream,self.copy=stream,copy
    def write(self,data):
        self.copy.write(data);self.copy.flush()
        return self.stream.write(data)
    def flush(self):
        self.copy.flush();self.stream.flush()
with (base/"observer-stdout.jsonl").open("w") as out,(base/"observer-stderr.txt").open("w") as err:
    with contextlib.redirect_stdout(Tee(sys.stdout,out)),contextlib.redirect_stderr(Tee(sys.stderr,err)):
        try:
            runpy.run_path(str(base/"actual_memory_observer.py"),run_name="__main__")
        except SystemExit as e:
            (base/"observer-exit.txt").write_text(str(e.code))
            raise
""")
    (scene/"smoke.qml").write_text(scene_text(mounted))
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=folder/key;d.mkdir(mode=0o700);env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="")
    executable=shutil.which("quickshell") or shutil.which("qs")
    assert executable, "Quickshell executable missing"
    proc=subprocess.Popen([os.path.realpath(executable),"-p",str(scene/"smoke.qml"),"--no-color"],
                          cwd=scene,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    lines=queue.Queue()
    def read():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)
    threading.Thread(target=read,daemon=True).start()
    marks={};peak={};observed_pids={};phase="STARTUP";identity=None;passed=False;logs=[]
    until=time.monotonic()+40
    try:
        while time.monotonic()<until:
            try:
                line=lines.get(timeout=.05)
            except queue.Empty:
                line=""
            if line is None:
                break
            if line:
                logs.append(line.rstrip())
                if "CPU_Q6_FAIL " in line:
                    raise AssertionError(line.strip())
                if "CPU_Q6_MARK " in line:
                    name=line.split("CPU_Q6_MARK ",1)[1].strip()
                    marks[name]=proc_snapshot(proc.pid)
                    phase=name.split("_")[0] if name.endswith("_BEGIN") else ("STOP" if name=="POST_END" else "BETWEEN")
                if "CPU_Q6_IDENTITY " in line:
                    identity=json.loads(line.split("CPU_Q6_IDENTITY ",1)[1])
                if "CPU_Q6_PASS" in line:
                    passed=True
            children=observer_children(proc.pid,scripts/SCRIPT)
            for child in children:
                try:
                    snap=proc_snapshot(child)
                except (OSError, ValueError, IndexError):
                    continue
                key=(child,snap["startTicks"])
                prev=observed_pids.get(key,{"maxCpuTicks":0,"peakPssKiB":0})
                observed_pids[key]={"maxCpuTicks":max(prev["maxCpuTicks"],snap["ticks"]),
                    "peakPssKiB":max(prev["peakPssKiB"],snap["memoryKiB"]["Pss"])}
            peak[phase]=max(peak.get(phase,0),len(children))
            if phase in ("STARTUP","IDLE","POST","CLEANUP") and children:
                raise AssertionError("observer running outside capture: "+phase)
        assert passed and proc.wait(timeout=3)==0, "native witness incomplete"
        for name in ("IDLE","ACTIVE","POST","CLEANUP"):
            assert name+"_BEGIN" in marks and name+"_END" in marks
        if mounted:
            assert identity and identity["pid"]==proc.pid and identity["startTicks"]==marks["ACTIVE_BEGIN"]["startTicks"], "launching-shell identity mismatch"
            assert peak.get("ACTIVE",0)==1 and peak.get("STOP",0)==1, "expected exactly one observer per active operation"
            for pid,birth in observed_pids:
                try:
                    raw=(Path("/proc")/str(pid)/"stat").read_text()
                    start=int(raw[raw.rfind(")")+1:].split()[19])
                except OSError:
                    continue
                assert start!=birth, "observer survived cleanup"
        else:
            assert not observed_pids, "baseline unexpectedly collected resources"
        phases={}
        for name in ("IDLE","ACTIVE","POST","CLEANUP"):
            a,b=marks[name+"_BEGIN"],marks[name+"_END"]
            assert a["startTicks"]==b["startTicks"] and b["ticks"]>=a["ticks"]
            elapsed=(b["atNs"]-a["atNs"])/1e9
            phases[name]=dict(seconds=round(elapsed,3),cpuTicks=b["ticks"]-a["ticks"],
                cpuPct=round(100*(b["ticks"]-a["ticks"])/HZ/elapsed,3),
                pssStartKiB=a["memoryKiB"]["Pss"],pssEndKiB=b["memoryKiB"]["Pss"],
                rssStartKiB=a["memoryKiB"]["Rss"],rssEndKiB=b["memoryKiB"]["Rss"])
        return dict(phases=phases,observerPeak=peak,identity=identity,
                    observedWorkerCpuTicksLowerBound=sum(v["maxCpuTicks"] for v in observed_pids.values()),
                    observedWorkerPeakPssKiB=max((v["peakPssKiB"] for v in observed_pids.values()),default=0))
    except BaseException:
        print("\n".join(logs[-80:]))
        preflight=scripts/"observer-preflight.json"
        if preflight.exists():
            print("CPU_Q6_PREFLIGHT",preflight.read_text()[:2048])
        output=scripts/"observer-stdout.jsonl"
        if output.exists():
            for line in output.read_text()[:65536].splitlines()[:14]:
                try:
                    row=json.loads(line)
                    print("CPU_Q6_OBSERVER_ROW",json.dumps({k:row.get(k) for k in ("event","pid","startTicks","tsMs","monotonicMs","cpuTicks","cpuPct","sampleIntervalMs","samples","observedMs","reason","calibration")}))
                except ValueError:
                    print("CPU_Q6_OBSERVER_ROW invalid JSON")
        for name in ("observer-exit.txt","observer-stderr.txt"):
            candidate=scripts/name
            if candidate.exists():
                print("CPU_Q6_OBSERVER",name,candidate.read_text()[:512])
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=3)

with tempfile.TemporaryDirectory(prefix="cpu-q6-disposable-") as tmp:
    folder=Path(tmp)
    baseline=run_scene(folder/"baseline",False)
    mounted=run_scene(folder/"mounted",True)
    b,m=baseline["phases"],mounted["phases"]
    result=dict(schema="post-apollo-q6-native-overhead-v1",baseline=baseline,mounted=mounted,
        idleCpuDeltaPercentagePoints=round(m["IDLE"]["cpuPct"]-b["IDLE"]["cpuPct"],3),
        idlePssDeltaKiB=m["IDLE"]["pssEndKiB"]-b["IDLE"]["pssEndKiB"],
        activeCpuDeltaPercentagePoints=round(m["ACTIVE"]["cpuPct"]-m["IDLE"]["cpuPct"],3),
        postCpuDeltaPercentagePoints=round(m["POST"]["cpuPct"]-m["IDLE"]["cpuPct"],3),
        note="Disposable shell synthetic flag workload, real procfs sampler. Shell CPU excludes observer child CPU; child sampled ticks are a lower bound and PSS a sampled peak. Short CI windows are noisy; no production performance threshold inferred.")
    print("CPU_Q6_METRICS "+json.dumps(result,sort_keys=True))
    print("CPU_Q6_REAL_NATIVE_PASS")
