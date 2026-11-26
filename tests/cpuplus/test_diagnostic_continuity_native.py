#!/usr/bin/env python3
"""Native QML lifetime test using real Process and a disposable fake report."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")

with tempfile.TemporaryDirectory(prefix="cpu-diag-native-") as temporary:
    base = Path(temporary)
    config = base / "scene"
    config.mkdir()
    shutil.copytree(ROOT / "components", config / "components")
    shutil.copytree(ROOT / "services/diagnostics", config / "services/diagnostics")
    destination = config / "widgets/cpuplus"
    destination.mkdir(parents=True)
    for name in ("CpuPlusMemoryActuatorPane.qml",
                 "CpuPlusMemoryCapacitySlider.qml",
                 "CpuPlusMemoryAddControl.qml", "CpuPlusSwapComposition.qml",
                 "CpuPlusMemorySnapshot.js", "CpuPlusMemoryReadout.qml", "CpuPlusMemoryReadout.js", "CpuPlusDiagnosticsPane.qml",
                 "CpuPlusDiagnosticWorkshop.qml", "CpuPlusDiagnosticSlider.qml", "CpuPlusDiagnosticExecutionButton.qml",
                 "CpuPlusZramPolicyPane.qml", "CpuPlusZramPolicy.js",
                 "CpuPlusAdvancedPolicyPane.qml", "CpuPlusAdvancedPolicy.js",
                 "CpuPlusQueuePane.qml", "CpuPlusQueuePresentation.js", "CpuPlusQueueConsumer.js"):
        shutil.copy2(ROOT / "widgets/cpuplus" / name, destination / name)
    for name in ("CpuPlusProcessPane.qml", "CpuPlusProcessPresentation.js", "CpuPlusProfilePane.qml", "CpuPlusProfilePreview.js", "CpuPlusProfileCatalog.js", "CpuPlusProfileCatalogStore.qml", "CpuPlusProfileComparison.js", "CpuPlusProfileComparison.qml", "CpuPlusAutoWorkspace.qml", "CpuPlusQueueHistoryPane.qml", "CpuPlusQueueHistory.js", "CpuPlusQueueRecoveryPane.qml", "CpuPlusQueueRecovery.js"):
        shutil.copy2(ROOT / "widgets/cpuplus" / name, destination / name)
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/DiagnosticContinuityNative.qml", config / "smoke.qml")
    memory = config / "services/memory"
    memory.mkdir(parents=True)
    shutil.copy2(ROOT / "services/memory/MemoryQueueSessionHost.js", memory / "MemoryQueueSessionHost.js")
    (memory / "qmldir").write_text("module qs.services.memory\n\nsingleton MemoryOperation 1.0 MemoryOperation.qml\n")
    (memory / "MemoryOperation.qml").write_text("""pragma Singleton
import QtQuick
import Quickshell
Scope {
    property bool busy: false
    property int revision: 0
    property string feedback: "TEST ONLY"
    function request(action, value) { throw new Error("unexpected privileged request") }
}
""")
    scripts = config / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts/cpuplus_stall_clock_witness.py", scripts / "cpuplus_stall_clock_witness.py")
    shutil.copy2(ROOT / "scripts/cpuplus_diagnostic_archive.py", scripts / "cpuplus_diagnostic_archive.py")
    (scripts / "cpuplus_qml_workload_inventory.py").write_text(
        'import json,time\ntime.sleep(3)\nprint(json.dumps({"schema":"post-apollo-qml-workload-inventory-v1",'
        '"trackedQml":826,"scannedQml":826,"skipped":[],"totals":{"Timer":426,"Process":415,"Repeater":743}}))\n')
    (scripts / "cpuplus_process_census.py").write_text("import time\ntime.sleep(10)\n")
    # Disposable child validates exact argv, emits a calibrated synthetic report.
    (scripts / "syntagma_quickshell_thread_sampler.py").write_text("""import json,sys,time
assert sys.argv[1:]==["--workshop","--duration","2","--interval","0.5","--top","2"]
time.sleep(1)
tag={"workshopSchema":"post-apollo-thread-calibration-v1","pid":123,"startTicks":456}
main={"tid":123,"cpuPct":55}
start=dict(tag,event="start",durationSeconds=2,intervalMs=500,topCount=2)
row=dict(event="threads",pid=123,startTicks=456,sampleIntervalMs=500,totalCpuPct=55,threadCount=1,main=main,top=[main])
end=dict(tag,event="complete",samples=4,observedMs=2000)
for entry in [start,row,row,row,row,end]: print(json.dumps(entry))
""")

    (scripts / "cpuplus_diagnostic_workflow.py").write_text("""import json,sys,time
assert sys.argv[1]=="--plan" and sys.argv[3]=="--data-dir"
plan=json.loads(sys.argv[2])
assert plan=={"durationSeconds":1,"instruments":[{"kind":"census","intervalMs":1000},{"kind":"storage"}]}
time.sleep(.4)
ids=["notifications.history","notifications.favorites","notifications.policies","notifications.scroll","weather.cache","weather.history","weather.events","weather.places","weather.dossier","hub.layout","hub.notes","hub.todo","social.identities","git.journal","git.delta","forest.preferences","finance.manual","company.hubs"]
items=[]
for c in plan["instruments"]:
    config=dict(c,durationSeconds=1); kind=c["kind"]
    schema="post-apollo-process-census-v1" if kind=="census" else "post-apollo-storage-observation-v1"
    if kind=="census":
        row=dict(schema=schema,event=kind,sequence=1,scope="same-user",observed=1,cpuMeasured=1,ioMeasured=1,coverage={"truncated":False},previousCoverage={"truncated":False},rows=[dict(pid=123,name="quickshell",rssKiB=100,cpuPct=2,readBps=0,writeBps=0)],monotonicMs=2000)
    else:
        row=dict(schema=schema,event=kind,sequence=1,intervals=1,elapsedMs=1000,monotonicMs=2000,rows=[dict(id=i,initialState="absent",finalState="absent",initialBytes=None,finalBytes=None,changedIntervals=0,replacementIntervals=0,unavailableIntervals=0,comparableIntervals=1) for i in ids])
    end=dict(schema=schema,event="complete",workshopSchema="post-apollo-observer-calibration-v1",calibration=config,samples=1,observedMs=1000,startedMonotonicMs=1000,monotonicMs=2000)
    records=[row,end]
    items.append(dict(config=config,records=records,status="COLLECTED",error="",exitCode=0,launchMonotonicMs=900,firstMonotonicMs=1000,lastMonotonicMs=2000,payloadBytes=sum(len(json.dumps(r))+1 for r in records)))
print(json.dumps(dict(schema="post-apollo-diagnostic-workflow-transport-v1",status="COLLECTED",durationSeconds=1,pinnedQuickshell=None,startedMonotonicMs=900,finishedMonotonicMs=2100,overlapMs=1000,instruments=items)))
""")
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    result = subprocess.run(["qs", "-p", str(config / "smoke.qml"), "--no-color"],
                            cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=35, check=False)
    print(result.stdout)
    if result.returncode or "CPU_DIAG_NATIVE_PASS" not in result.stdout or "CPU_M10_HOST_INSTRUMENT_PASS" not in result.stdout or "CPU_D1B_NATIVE_PASS" not in result.stdout or "CPU_D2C_NATIVE_PASS" not in result.stdout or "CPU_D3A_NATIVE_PASS" not in result.stdout or "CPU_D3D_NATIVE_PASS" not in result.stdout or "CPU_DIAG_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native diagnostic continuity failed")
