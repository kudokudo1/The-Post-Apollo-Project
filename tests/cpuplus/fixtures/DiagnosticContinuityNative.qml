import QtQuick
import QtQuick.Window
import Quickshell
import qs.services.diagnostics
import "widgets/cpuplus"

ShellRoot {
    id: root
    // Reference remains alive while the memory pane is unloaded.
    readonly property var diagnosticSessionOwner: CpuPlusDiagnostics
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property bool paneActive: true
    property int completions: 0
    property string completedId: ""
    Connections {
        target: CpuPlusDiagnostics
        function onCaptureFinished(job, reportId) {
            if (job === "inventory") {
                root.completions += 1;
                root.completedId = reportId;
            }
        }
    }

    function findItem(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = findItem(child,name);
            if (found) return found;
        }
        return null;
    }
    function normalFace(item, name, selected) {
        const b=findItem(item,name);
        const glow=b && findItem(b,"actionButtonNormalPerimeter");
        return b && b.normalFace && b.selected===selected && String(b.color).toLowerCase()==="#1b0623"
            && !b.softGlowEnabled && !b.wideGlowEnabled && b.contentGlowEnabled
            && glow && glow.active && glow.z===-1 && glow.item && glow.item.color.a===0;
    }
    function check(ok, message) {
        if (!ok) {
            console.error("CPU_DIAG_NATIVE_FAIL // " + message);
            done = true;
            Qt.quit();
        }
        return ok;
    }
    Window {
        width: 320
        height: 620
        visible: true
        Loader {
            id: pane
            anchors.fill: parent
            active: root.paneActive
            sourceComponent: CpuPlusMemoryActuatorPane {}
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: CpuPlusDiagnostics.stallCaptureActive
        onTriggered: CpuPlusDiagnostics.recordStallTick(Date.now())
    }
    Timer {
        interval: 100
        repeat: true
        running: !root.done
        onTriggered: {
            if (++root.ticks > 260) {
                root.check(false, "timeout // " + CpuPlusDiagnostics.feedback);
                return;
            }
            if (root.phase === 0 && pane.item) {
                pane.item.selectMenu(4);
                if (!root.check(pane.item.page === "DIAG", "select DIAG")) return;
                if (!root.check(CpuPlusDiagnostics.request("inventory"), "start fixture scan")) return;
                if (!root.check(CpuPlusDiagnostics.busy, "capture did not enter busy")) return;
                root.paneActive = false;
                root.phase = 1;
                return;
            }
            if (root.phase === 1) {
                if (!root.check(!pane.item, "pane was not destroyed")) return;
                if (!root.check(CpuPlusDiagnostics.busy, "capture lost when pane unloaded")) return;
                root.paneActive = true;
                root.phase = 2;
                return;
            }
            if (root.phase === 2 && pane.item) {
                if (!root.check(pane.item.page === "DIAG", "reopened on wrong page")) return;
                if (!root.check(CpuPlusDiagnostics.selectedReport === "inventory", "report selection lost")) return;
                pane.item.selectMenu(1);
                if (!root.check(pane.item.page === "POL", "switch to POL")) return;
                root.paneActive = false;
                root.phase = 3;
                return;
            }
            if (root.phase === 3) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report = CpuPlusDiagnostics.reports.inventory;
                if (!root.check(report && report.status === "COMPLETE",
                                "scan failed // " + CpuPlusDiagnostics.feedback)) return;
                if (!root.check(report.summary.indexOf("826 files") >= 0, "wrong report")) return;
                if (!root.check(root.completions === 1 && root.completedId === report.id,
                                "terminal signal or capture identity mismatch")) return;
                if (!root.check(CpuPlusDiagnostics.reportFor("inventory", report.id) === report
                                && CpuPlusDiagnostics.reportFor("inventory", "stale") === null,
                                "exact report resolution")) return;
                if (!root.check(CpuPlusDiagnostics.archiveStatus === "READY"
                        && CpuPlusDiagnostics.archiveRows.length === 1
                        && CpuPlusDiagnostics.archiveRows[0].id === report.id,
                        "archive save receipt")) return;
                if (!root.check(CpuPlusDiagnostics.loadHistory(), "archive reload request")) return;
                root.phase = 5;
                return;
            }
            if (root.phase === 5) {
                if (CpuPlusDiagnostics.archiveBusy) return;
                if (!root.check(CpuPlusDiagnostics.archiveStatus === "READY"
                        && CpuPlusDiagnostics.archiveRows[0].id === root.completedId,
                        "archive reload receipt")) return;
                root.paneActive = true;
                root.phase = 4;
                return;
            }
            if (root.phase === 4 && pane.item) {
                if (!root.check(pane.item.page === "POL", "non-DIAG page continuity")) return;
                pane.item.selectMenu(4);
                if (!root.check(CpuPlusDiagnostics.reports.inventory.status === "COMPLETE",
                                "completed report lost")) return;
                if (!root.check(CpuPlusDiagnostics.selectedReport === "inventory", "wrong report after reopen")) return;
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                if (!ui) return;
                const one = {event:"memory",pid:12,startTicks:99,tsMs:1000,cpuTicks:100,cpuPct:null,sampleIntervalMs:null,
                    memoryKiB:{Rss:2097152,Pss:1048576,Pss_Anon:524288,Pss_File:262144,Pss_Shmem:262144,
                        Private_Dirty:524288,Swap:131072,SwapPss:65536},pssPlusSwapPssKiB:1114112};
                const two = Object.assign({},one,{tsMs:11000,cpuTicks:110,cpuPct:1,sampleIntervalMs:10000,
                    memoryKiB:Object.assign({},one.memoryKiB,{Rss:3145728,Pss:1572864,Private_Dirty:1048576}),
                    pssPlusSwapPssKiB:1638400});
                const terminal = {event:"complete",pid:12,startTicks:99};
                // Isolated presentation fixture only; do not request another observer or archive a fabricated report.
                const report = {id:"synthetic-memory",status:"COMPLETE",summary:"TEST ONLY",
                    text:[one,two,terminal].map(row=>JSON.stringify(row)).join("\n"),finishedAt:"2026-11-24T12:00:00.000Z"};
                CpuPlusDiagnostics.reports = Object.assign({},CpuPlusDiagnostics.reports,{memory:report});
                CpuPlusDiagnostics.selectLatest("memory");
                ui.selectView("REPORT");
                root.phase = 6;
                return;
            }
            if (root.phase === 6 && pane.item) {
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                const breakdown = root.findItem(pane.item,"cpuplusMemoryBreakdown");
                if (!ui || !breakdown) return;
                if (!root.check(breakdown.visible && ui.memoryDetails
                    && ui.memoryDetails.rows.length === 5 && ui.memoryDetails.rows[1].change === 524288
                    && !CpuPlusDiagnostics.busy && root.completions === 1,
                    "historical memory presentation without new capture")) return;
                if (!root.check(!ui.memoryDetails.privateResidentAvailable,"legacy private total unavailable")) return;
                const report = CpuPlusDiagnostics.reports.memory;
                const lines = report.text.split("\n").map(line=>JSON.parse(line));
                for (let i=0;i<lines.length-1;i++) {
                    lines[i].memoryKiB.Private_Clean = (i+1)*262144;
                    lines[i].privateResidentKiB = lines[i].memoryKiB.Private_Clean + lines[i].memoryKiB.Private_Dirty;
                }
                CpuPlusDiagnostics.reports = Object.assign({},CpuPlusDiagnostics.reports,{
                    memory:Object.assign({},report,{text:lines.map(row=>JSON.stringify(row)).join("\n")})});
                root.phase = 8;
                return;
            }
            if (root.phase === 8 && pane.item) {
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                if (!root.check(ui && ui.memoryDetails && ui.memoryDetails.privateResidentAvailable
                        && ui.memoryDetails.rows.length === 7
                        && ui.memoryDetails.rows.find(row=>row.label==="PRIVATE RESIDENT").change === 786432
                        && !CpuPlusDiagnostics.busy,"extended capture private resident breakdown")) return;
                const report=CpuPlusDiagnostics.reports.memory;
                const lines=report.text.split("\n").map(line=>JSON.parse(line));
                const before={MemTotal:33554432,MemAvailable:8388608,MemFree:1024,AnonPages:1024,Cached:1024,Shmem:0,SReclaimable:0,SUnreclaim:0,SwapTotal:1024,SwapFree:1024};
                lines[0].hostObservation={beforeKiB:before,afterKiB:before,spanMs:2};
                lines[1].hostObservation={beforeKiB:before,afterKiB:Object.assign({},before,{MemAvailable:6291456}),spanMs:3};
                CpuPlusDiagnostics.reports=Object.assign({},CpuPlusDiagnostics.reports,{memory:Object.assign({},report,{text:lines.map(row=>JSON.stringify(row)).join("\n")})});
                root.phase=12;
                return;
            }
            if(root.phase===12&&pane.item) {
                const ui=root.findItem(pane.item,"cpuplusDiagnosticControls");
                const host=root.findItem(pane.item,"cpuplusDiagHostInstrument");
                const toggle=root.findItem(pane.item,"cpuplusDiagHostToggle");
                if(!host||!toggle||!ui)return;
                if(!root.check(host.visible&&toggle.available&&ui.hostDetails&&ui.hostDetails.complete
                    &&ui.hostDetails.minimum===6291456&&ui.hostDetails.delta===-2097152
                    &&ui.hostDetails.pssDelta===524288&&!CpuPlusDiagnostics.busy,"paired host instrument // "+JSON.stringify({visible:host.visible,available:toggle.available,details:ui.hostDetails,busy:CpuPlusDiagnostics.busy})))return;
                toggle.leftClicked(null);
                if(!root.check(!host.visible&&!ui.showHostDetails,"hide historical host instrument"))return;
                toggle.leftClicked(null);
                if(!root.check(host.visible&&ui.showHostDetails,"show historical host instrument"))return;
                const report=CpuPlusDiagnostics.reports.memory;
                const lines=report.text.split("\n").map(line=>JSON.parse(line));
                lines[1].hostObservation=null;
                CpuPlusDiagnostics.reports=Object.assign({},CpuPlusDiagnostics.reports,{memory:Object.assign({},report,{text:lines.map(row=>JSON.stringify(row)).join("\n")})});
                root.phase=13;return;
            }
            if(root.phase===13&&pane.item) {
                const ui=root.findItem(pane.item,"cpuplusDiagnosticControls");
                if(!root.check(ui&&ui.hostDetails.paired===1&&!ui.hostDetails.complete
                    &&ui.hostDetails.total===null&&ui.hostDetails.delta===null&&ui.hostDetails.pssDelta===null
                    &&ui.memoryDetails.rows.length===7&&!CpuPlusDiagnostics.busy&&root.completions===1,
                    "partial host context retains process evidence without comparative bars"))return;
                console.log("CPU_M10_HOST_INSTRUMENT_PASS // actual hide/show, full and partial evidence, zero new captures");
                CpuPlusDiagnostics.selectLatest("inventory");
                root.phase = 7;
                return;
            }
            if (root.phase === 7 && pane.item) {
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                const breakdown = root.findItem(pane.item,"cpuplusMemoryBreakdown");
                if (!root.check(ui && breakdown && !breakdown.visible && ui.memoryDetails === null,
                    "no stale memory presentation after report change")) return;
                pane.item.selectMenu(2);
                root.phase = 9;
                return;
            }
            if (root.phase === 9 && pane.item) {
                if (CpuPlusDiagnostics.archiveBusy) return;
                const start = root.findItem(pane.item,"cpuplusProcStart");
                const cancel = root.findItem(pane.item,"cpuplusProcCancel");
                if (!start || !cancel) return;
                if (!root.check(start.available && !cancel.available,"idle PROC cancel unavailable")) return;
                // ActionButton.leftClicked(var mouseEvent) requires an argument.
                // No real pointer event is needed in this signal-level fixture.
                start.leftClicked(null);
                if (!root.check(CpuPlusDiagnostics.busy && CpuPlusDiagnostics.kind==="census"
                    && cancel.available,"census started; cancel enabled")) return;
                // Give the disposable child a turn to start before cancellation.
                root.phase=10;
                return;
            }
            if (root.phase === 10 && pane.item) {
                const cancel=root.findItem(pane.item,"cpuplusProcCancel");
                if (!root.check(cancel && cancel.available && CpuPlusDiagnostics.busy,
                    "running census can be cancelled")) return;
                cancel.leftClicked(null);
                root.phase=11;
                return;
            }
            if (root.phase === 11 && pane.item) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.census;
                const cancel=root.findItem(pane.item,"cpuplusProcCancel");
                if (!root.check(report && report.status==="CANCELLED" && cancel && !cancel.available,
                    "census cancellation terminal receipt")) return;
                if (!root.check(!CpuPlusDiagnostics.requestConfigured({kind:"threads",durationSeconds:2,intervalMs:500,topCount:99}),
                    "invalid calibration refused")) return;
                const config={kind:"threads",durationSeconds:2,intervalMs:500,topCount:2};
                if (!root.check(CpuPlusDiagnostics.requestConfigured(config), "configured thread launch")) return;
                config.topCount=12;
                if (!root.check(!CpuPlusDiagnostics.request("inventory"), "configured run retains single-flight guard")) return;
                root.paneActive=false;
                root.phase=14;
                return;
            }
            if (root.phase===14) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.threads;
                if (!root.check(report && report.status==="COMPLETE"
                    && report.summary.indexOf("CALIBRATION // 2 s / 500 ms / TOP 2")>=0
                    && CpuPlusDiagnostics.archiveRows.some(row=>row.id===report.id),
                    "configured capture survives unload and archive // "+CpuPlusDiagnostics.feedback)) return;
                console.log("CPU_D1B_NATIVE_PASS");
                const plan={durationSeconds:1,instruments:[{kind:"census",intervalMs:1000},{kind:"storage"}]};
                if (!root.check(CpuPlusDiagnostics.requestWorkflow(plan),"workflow launch")) return;
                plan.durationSeconds=99;
                if (!root.check(!CpuPlusDiagnostics.request("inventory") && !CpuPlusDiagnostics.requestWorkflow(plan),
                    "shared workflow single flight")) return;
                root.phase=15;
                return;
            }
            if (root.phase===15) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.workflow;
                if (!root.check(report && report.status==="COMPLETE"
                    && report.summary.indexOf("2 / 2 VERIFIED")>=0
                    && CpuPlusDiagnostics.archiveRows.some(row=>row.id===report.id)
                    && !CpuPlusDiagnostics.selectComparison("before",report.id),
                    "workflow receipt and archive // "+CpuPlusDiagnostics.feedback)) return;
                if (!root.check(CpuPlusDiagnostics.loadHistory(),"workflow history reload")) return;
                root.phase=16;
                return;
            }
            if (root.phase===16) {
                if (CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.workflow;
                if (!root.check(CpuPlusDiagnostics.archiveStatus==="READY"
                    && CpuPlusDiagnostics.archiveRows.some(row=>row.id===report.id&&row.text===report.text),
                    "workflow exact archive readback")) return;
                console.log("CPU_D2C_NATIVE_PASS");
                root.paneActive=true;
                root.phase=17;
                return;
            }
            if (root.phase===17 && pane.item) {
                pane.item.selectMenu(4);
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop) return;
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const execute=root.findItem(workshop,"cpuplusWorkshopExecute");
                const dial=root.findItem(workshop,"cpuplusWorkshopTopThreads");
                if (!root.check(duration && execute && dial && duration.width===(workshop.compactLayout?24:32)
                    && duration.horizontalStepPresentation && !CpuPlusDiagnostics.busy
                    && workshop.phase==="PREPARE" && dial.options.length===12 && dial.readoutGlowEnabled && String(dial.markerColor).toLowerCase()==="#ed981a"
                    && dial.numericDetentInterval===1,"actual Workshop hardware and no automatic launch")) return;
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!root.check(viewport && viewport.contentHeight<=viewport.height+1,
                    "default Workshop fits native 320x620 viewport // "+viewport.contentHeight+" / "+viewport.height)) return;
                if (!root.check(root.normalFace(pane.item,"cpuplusMemoryMode-DIAG",true)
                    && root.normalFace(pane.item,"cpuplusMemoryMode-CAP",false)
                    && root.normalFace(workshop,"cpuplusWorkshopInstrument-threads",true)
                    && root.normalFace(workshop,"cpuplusWorkshopInstrument-storage",false), "normal opaque faces before unload")) return;
                workshop.edit("selected",["threads","memory","census","storage"]);
                root.phase=171;
                return;
            }
            if (root.phase===171 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const execute=root.findItem(workshop,"cpuplusWorkshopExecute");
                const dial=root.findItem(workshop,"cpuplusWorkshopTopThreads");
                const storage=root.findItem(workshop,"cpuplusWorkshopStorageInstrument");
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!root.check(storage && storage.visible && storage.height===workshop.instrumentHeight && dial.visible
                    && duration.height===workshop.width && dial.mapToItem(workshop,0,0).y>root.findItem(workshop,"cpuplusWorkshopCensusInterval").mapToItem(workshop,0,0).y
                    && ["Duration","ThreadInterval","MemoryInterval","CensusInterval"].every(name=>{
                        const slider=root.findItem(workshop,"cpuplusWorkshop"+name+"-hardware");
                        return slider && slider.visible && slider.height===workshop.width;
                    }),
                    "full-length sliders above storage/thread instrument row")) return;
                if (!root.check(viewport.contentHeight<=viewport.height+1,"all four instruments fit default viewport // "+viewport.contentHeight+" / "+viewport.height)) return;
                workshop.edit("selected",["census","storage"]);
                workshop.edit("censusIntervalMs",1000);
                duration.valueRequested(1);
                if (!root.check(workshop.preview.ok && workshop.draft.durationSeconds===1,"valid calibrated slider")) return;
                execute.leftClicked(null);
                if (!root.check(!CpuPlusDiagnostics.busy,"prepare never launches")) return;
                root.phase=18;
                return;
            }
            if (root.phase===18 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop || workshop.calibrating) return;
                if (!root.check(workshop.ready,"second click armed")) return;
                workshop.edit("durationSeconds",2);
                if (!root.check(!workshop.ready && !CpuPlusDiagnostics.busy,"edit disarms")) return;
                workshop.edit("durationSeconds",1);
                workshop.activate();
                root.phase=19;
                return;
            }
            if (root.phase===19 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop || workshop.calibrating) return;
                if (!root.check(workshop.ready,"reprepared")) return;
                root.findItem(workshop,"cpuplusWorkshopExecute").leftClicked(null);
                if (!root.check(CpuPlusDiagnostics.busy && workshop.recording
                    && CpuPlusDiagnostics.kind==="workflow","explicit second-click launch")) return;
                root.paneActive=false;
                root.phase=20;
                return;
            }
            if (root.phase===20) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.workflow;
                if (!root.check(report && report.status==="COMPLETE"
                    && report.id===CpuPlusDiagnostics.workshopRunId,"Workshop capture survives unload")) return;
                root.paneActive=true;
                root.phase=21;
                return;
            }
            if (root.phase===21 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop) return;
                if (!root.check(workshop.draft.durationSeconds===1 && workshop.phase==="COMPLETE"
                    && !workshop.ready && !CpuPlusDiagnostics.busy,"draft and terminal continuity without rearming")) return;
                if (!root.check(root.normalFace(pane.item,"cpuplusMemoryMode-DIAG",true)
                    && root.normalFace(pane.item,"cpuplusMemoryMode-CAP",false)
                    && root.normalFace(workshop,"cpuplusWorkshopInstrument-census",true)
                    && root.normalFace(workshop,"cpuplusWorkshopInstrument-threads",false), "normal opaque faces after actual remount")) return;
                console.log("CPU_D3A_NATIVE_PASS");
                if (!root.check(CpuPlusDiagnostics.requestConfigured({kind:"stall",durationSeconds:5,thresholdMs:350})
                    && CpuPlusDiagnostics.stallCaptureActive && !CpuPlusDiagnostics.request("inventory"),
                    "explicit stall capture owns existing single-flight")) return;
                root.paneActive=false;
                root.phase=22;
                return;
            }
            if (root.phase===22) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.stall;
                if (!root.check(report && report.status==="COMPLETE" && !CpuPlusDiagnostics.stallCaptureActive
                    && CpuPlusDiagnostics.archiveRows.some(row=>row.id===report.id)
                    && report.summary.indexOf("THRESHOLD // 350 ms")>=0,
                    "real clock witness plus fixture heartbeat, archive and unload // "+CpuPlusDiagnostics.feedback)) return;
                console.log("CPU_D3D_NATIVE_PASS");
                console.log("CPU_DIAG_NATIVE_PASS");
                root.done = true;
                Qt.quit();
            }
        }
    }
}
