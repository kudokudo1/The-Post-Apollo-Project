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
                 "CpuPlusResourceDiagnosticsPane.qml", "CpuPlusDiagnosticWorkshop.qml", "CpuPlusLifecycleDumpPopup.qml", "CpuPlusDiagnosticSlider.qml", "CpuPlusDiagnosticExecutionButton.qml",
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
    shutil.copy2(ROOT / "scripts/cpuplus_host_cpu_observer.py", scripts / "cpuplus_host_cpu_observer.py")
    shutil.copy2(ROOT / "scripts/cpuplus_diagnostic_archive.py", scripts / "cpuplus_diagnostic_archive.py")
    # Exercise the real GPU reader against a deterministic disposable sysfs
    # tree; hosted CI need not expose a physical graphics device.
    shutil.copy2(ROOT / "scripts/cpuplus_gpu_observer.py", scripts / "gpu_reader_fixture.py")
    gpu_fixture = base / "gpu-fixture"
    drm = gpu_fixture / "drm"
    devices = gpu_fixture / "devices"
    drm.mkdir(parents=True)
    devices.mkdir()
    for i in range(2):
        dev = devices / ("0000:0%d:00.0" % (i+1))
        dev.mkdir()
        card = drm / ("card%d" % i)
        card.mkdir()
        (card / "device").symlink_to(dev)
        if i == 0:
            (dev / "gpu_busy_percent").write_text("40")
            (dev / "mem_info_vram_used").write_text("1048576")
            (dev / "mem_info_vram_total").write_text("2097152")
    (scripts / "cpuplus_gpu_observer.py").write_text("""import sys
from pathlib import Path
from gpu_reader_fixture import capture
assert sys.argv[1:]==["--workshop","--duration","2","--interval","1"]
base=Path(__file__).resolve().parents[2]/"gpu-fixture"
sys.stdout.write(capture(2,1,base/"drm",base/"devices"))
""")
    # Real disk observer, disposable whole-device sysfs and exact argv.
    shutil.copy2(ROOT / "scripts/cpuplus_disk_io_observer.py", scripts / "disk_reader_fixture.py")
    block = base / "disk-fixture" / "block"
    disk_devices = base / "disk-fixture" / "devices"
    block.mkdir(parents=True)
    disk_parent = disk_devices / "pci0" / "sda"
    disk = disk_parent / "block" / "sda"
    disk.mkdir(parents=True)
    (disk / "device").symlink_to(disk_parent)
    (disk / "dev").write_text("8:0")
    (disk / "diskseq").write_text("42")
    (disk / "stat").write_text("10 1 20 30 40 2 50 60 0 70 80")
    (block / "sda").symlink_to(disk)
    (scripts / "cpuplus_disk_io_observer.py").write_text("""import sys
from pathlib import Path
from disk_reader_fixture import capture
assert sys.argv[1:]==["--workshop","--duration","1","--interval","1"]
base=Path(__file__).resolve().parents[2]/"disk-fixture"
sys.stdout.write(capture(1,1,base/"block",base/"devices"))
""")
    # Real swap observer against disposable procfs/sysfs, fixed argv.
    shutil.copy2(ROOT / "scripts/cpuplus_swap_io_observer.py", scripts / "swap_reader_fixture.py")
    swap_proc = base / "swap-fixture" / "proc"
    swap_block = base / "swap-fixture" / "block"
    (swap_proc / "pressure").mkdir(parents=True)
    (swap_block / "zram0").mkdir(parents=True)
    (swap_proc / "swaps").write_text("Filename Type Size Used Priority\n/dev/zram0 partition 8192 4096 100\n")
    (swap_proc / "meminfo").write_text("MemTotal: 16384 kB\nMemAvailable: 2048 kB\nSwapTotal: 8192 kB\nSwapFree: 4096 kB\n")
    (swap_proc / "vmstat").write_text("pswpin 100\npswpout 200\n")
    (swap_proc / "pressure/memory").write_text("some avg10=2.50 avg60=1.00 avg300=0.00 total=100000\nfull avg10=0.10 avg60=0.00 avg300=0.00 total=20000\n")
    (swap_block / "zram0/mm_stat").write_text("4194304 1048576 1572864 0 0 0 0 0\n")
    (scripts / "cpuplus_swap_io_observer.py").write_text("""import sys
from pathlib import Path
from swap_reader_fixture import capture
assert sys.argv[1:]==["--workshop","--duration","1","--interval","1"]
base=Path(__file__).resolve().parents[2]/"swap-fixture"
sys.stdout.write(capture(1,1,base/"proc",base/"block",4096))
""")
    # Real Network observer against disposable proc/sysfs, no sockets.
    shutil.copy2(ROOT / "scripts/cpuplus_network_io_observer.py", scripts / "net_reader_fixture.py")
    net_base = base / "net-fixture"
    net = net_base / "net"
    net.mkdir(parents=True)
    for name, index, kind in (("eth0", 2, 1), ("lo", 1, 772)):
        interface = net_base / "devices" / name
        interface.mkdir(parents=True)
        (interface / "ifindex").write_text(str(index))
        (interface / "iflink").write_text(str(index))
        (interface / "type").write_text(str(kind))
        (interface / "operstate").write_text("up")
        (net / name).symlink_to(interface)
    (net_base / "dev").write_text("Inter-| Receive | Transmit\n face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\neth0: "+" ".join(["0"]*16)+"\nlo: "+" ".join(["0"]*16)+"\n")
    (scripts / "cpuplus_network_io_observer.py").write_text("""import sys
from pathlib import Path
from net_reader_fixture import capture
assert sys.argv[1:]==["--workshop","--duration","1","--interval","1"]
base=Path(__file__).resolve().parents[2]/"net-fixture"
sys.stdout.write(capture(1,1,base/"dev",base/"net",base/"devices"))
""")
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

    # Keep the genuine collector tree separate from the synthetic executable
    # fixtures. Production imports and script-relative paths stay unchanged.
    real_scripts = config / "real-capture" / "scripts"
    real_scripts.mkdir(parents=True)
    for name in ("cpuplus_diagnostic_workflow.py", "cpuplus_storage_observer.py",
                 "syntagma_quickshell_thread_sampler.py", "cpuplus_stall_clock_witness.py",
                 "cpuplus_diagnostic_workflow_catalog.py", "cpuplus_diagnostic_archive.py"):
        shutil.copy2(ROOT / "scripts" / name, real_scripts / name)
    (scripts / "cpuplus_diagnostic_workflow_catalog.py").write_text("""import os,sys
from pathlib import Path
target=Path(__file__).resolve().parents[1]/"real-capture"/"scripts"/"cpuplus_diagnostic_workflow_catalog.py"
assert len(sys.argv)==1
os.execv(sys.executable,[sys.executable,"-E","-s","-B",str(target)])
""")
    # Standalone Storage uses the real observer and real sampler import, not
    # the synthetic thread fixture in scripts/. Keep disposable path arguments.
    (scripts / "cpuplus_storage_observer.py").write_text("""import os,sys
from pathlib import Path
target=Path(__file__).resolve().parents[1]/"real-capture"/"scripts"/"cpuplus_storage_observer.py"
assert "--workshop" in sys.argv and "--sample-seconds" in sys.argv and "--report-seconds" in sys.argv
os.execv(sys.executable,[sys.executable,"-B",str(target),*sys.argv[1:]])
""")
    # Fail at setup, not five seconds into the native test, if the collector
    # import graph is incomplete or accidentally resolves the fake sampler.
    subprocess.run(["python3", "-B", "-c",
                    "from pathlib import Path; import syntagma_quickshell_thread_sampler as s; "
                    "assert Path(s.__file__).resolve().parent == Path.cwd(); "
                    "from syntagma_quickshell_thread_sampler import WorkshopOutput, WorkshopOutputLimit; "
                    "import cpuplus_diagnostic_workflow, cpuplus_storage_observer"],
                   cwd=real_scripts, check=True, timeout=10)
    (scripts / "cpuplus_diagnostic_workflow.py").write_text("""import json,sys,time,os,pathlib
assert sys.argv[1]=="--plan" and sys.argv[3]=="--data-dir"
plan=json.loads(sys.argv[2])
if any(c["kind"]=="stall" for c in plan["instruments"]):
    assert plan=={"durationSeconds":5,"instruments":[{"kind":"storage","sampleSeconds":2,"reportSeconds":4},{"kind":"stall","thresholdMs":500}]}
    os.execv(sys.executable,[sys.executable,"-B",str(pathlib.Path(__file__).parent.parent/"real-capture"/"scripts"/"cpuplus_diagnostic_workflow.py"),*sys.argv[1:]])
assert plan in [{"durationSeconds":1,"instruments":[{"kind":"census","intervalMs":1000},{"kind":"storage"}]},
                {"durationSeconds":1,"instruments":[{"kind":"census","intervalMs":1000},{"kind":"storage","sampleSeconds":1,"reportSeconds":10}]}]
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
                            stderr=subprocess.STDOUT, timeout=95, check=False)
    print(result.stdout)
    if result.returncode or "CPU_DIAG_NATIVE_PASS" not in result.stdout or "CPU_M10_HOST_INSTRUMENT_PASS" not in result.stdout or "CPU_D1B_NATIVE_PASS" not in result.stdout or "CPU_D2C_NATIVE_PASS" not in result.stdout or "CPU_D3A_NATIVE_PASS" not in result.stdout or "CPU_D3D_NATIVE_PASS" not in result.stdout or "CPU_D3E_NATIVE_PASS" not in result.stdout or CPU_Q4_TARGET_CUSTODY_PASS", "CPU_Q5F_DUMP_ADMISSION_PASS" not in result.stdout or "CPU_Q4_TARGET_SELECTOR_PASS" not in result.stdout or "CPU_Q3_DIRECT_SAVE_PASS" not in result.stdout or "CPU_D4A_NATIVE_PASS" not in result.stdout or "CPU_D4B_NATIVE_PASS" not in result.stdout or "CPU_D4B_FIXED_FOOTER_PASS" not in result.stdout or "CPU_D6A_RESOURCE_NATIVE_PASS" not in result.stdout or "CPU_D6B_HOST_NATIVE_PASS" not in result.stdout or "CPU_D7A_GPU_NATIVE_PASS" not in result.stdout or "CPU_D8A_STORAGE_NATIVE_PASS" not in result.stdout or "CPU_D8C_DISK_NATIVE_PASS" not in result.stdout or "CPU_D9A_SWAP_NATIVE_PASS" not in result.stdout or "CPU_D10A_NETWORK_NATIVE_PASS" not in result.stdout or "CPU_D10B_SYSTEM_MEMORY_NATIVE_PASS" not in result.stdout or "CPU_DIAG_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native diagnostic continuity failed")
