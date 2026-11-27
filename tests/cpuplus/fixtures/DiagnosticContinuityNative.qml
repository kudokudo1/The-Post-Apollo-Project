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
    property bool resourcePaneActive: false
    property string resourceSubject: "CPU"
    property string cpuDraftWitness: ""
    property string generalDraftWitness: ""
    property int completions: 0
    property string diagnosticFooterGeometry: ""
    property string completedId: ""
    property real compactThumbLength: 0
    property real mediumThumbLength: 0
    property int automotiveVariantIndex: 0
    property real lowFillOpacity: 0
    property real lowHaloOpacity: 0
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
    function footerGeometry(paneItem, keys) {
        const context=findItem(paneItem,"cpuplusDiagnosticContextRail");
        const workspace=findItem(paneItem,"cpuplusDiagnosticWorkspaceRail");
        const footer=findItem(paneItem,"cpuplusDiagBottomControls");
        const buttons=keys.map(k=>findItem(paneItem,"cpuplusDiagnosticView-"+k))
            .concat(["WORK","PRESETS"].map(k=>findItem(paneItem,"cpuplusDiagnosticWorkspace-"+k)));
        if(!context||!workspace||!footer||buttons.some(b=>!b||!b.visible))return "";
        return JSON.stringify([footer,context,workspace,...buttons].map(b=>{
            const p=b.mapToItem(paneItem,0,0);
            return [p.x,p.y,b.width,b.height];
        }));
    }
    function normalFace(item, name, selected) {
        const b=findItem(item,name);
        const glow=b && findItem(b,"actionButtonNormalPerimeter");
        const broadSoft=b && findItem(b,"actionButtonBroadSoftGlow");
        const broadWide=b && findItem(b,"actionButtonBroadWideGlow");
        // Independent palette oracle: selection is asserted by the caller,
        // and transient pointer/keyboard state is observed separately.
        const state = !b ? "missing" : b.pressed ? "pressed"
            : selected ? "selected"
            : (b.keyboardSelected || b.contentKeyboardPrimary) ? "keyboard-preview"
            : b.hovered && !(b.contentKeyboardNavigationActive
                && !b.contentKeyboardPrimary && !b.keyboardSelected) ? "primary-hover"
            : "idle-or-secondary";
        const expectedColor = state === "pressed" ? "#c74ec7"
            : ["selected", "keyboard-preview", "primary-hover"].includes(state)
                ? "#f2be4e" : "#1b0623";
        const ok = b && b.normalFace && b.washSafePerimeter && b.selected===selected
            && b.available && b.visible && b.color.a===1
            && String(b.color).toLowerCase()===expectedColor
            && !b.softGlowEnabled && !b.wideGlowEnabled && b.contentGlowEnabled
            && broadSoft && !broadSoft.visible && broadWide && !broadWide.visible
            && glow && glow.active && glow.z===-1 && glow.item && glow.item.color.a===0;
        // On any mismatch, retain exact runtime evidence.
        if (!ok) {
            console.log("CPU_DIAG_FACE_EVIDENCE // " + JSON.stringify({
                name: name, phase: root.phase, exists: !!b,
                expectedSelected: selected,
                expectedColor: expectedColor, expectedState: state,
                actual: b ? {
                    color: String(b.color), alpha: b.color.a,
                    fillColor: String(b.fillColor),
                    idleFillColor: String(b.idleFillColor),
                    hoverFillColor: String(b.hoverFillColor),
                    selectedFillColor: String(b.selectedFillColor),
                    normalFace: b.normalFace, washSafePerimeter: b.washSafePerimeter,
                    selected: b.selected, hovered: b.hovered, pressed: b.pressed,
                    keyboardSelected: b.keyboardSelected,
                    contentKeyboardPrimary: b.contentKeyboardPrimary,
                    cursorPrimaryNotActivated: b.cursorPrimaryNotActivated,
                    pointerSecondaryHovered: b.pointerSecondaryHovered,
                    available: b.available, visible: b.visible,
                    softGlowEnabled: b.softGlowEnabled, wideGlowEnabled: b.wideGlowEnabled,
                    contentGlowEnabled: b.contentGlowEnabled,
                    perimeterGlowEnabled: b.perimeterGlowEnabled,
                    perimeterGlowOpacity: b.perimeterGlowOpacity
                } : null,
                broadSoft: broadSoft ? {visible: broadSoft.visible} : null,
                broadWide: broadWide ? {visible: broadWide.visible} : null,
                perimeter: glow ? {
                    active: glow.active, visible: glow.visible, z: glow.z,
                    itemExists: !!glow.item,
                    itemColor: glow.item ? String(glow.item.color) : null,
                    itemAlpha: glow.item ? glow.item.color.a : null
                } : null
            }));
        }
        return ok;
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
        id: nativeWindow
        width: 320
        height: 620
        visible: true
        Loader {
            id: pane
            anchors.fill: parent
            active: root.paneActive
            sourceComponent: CpuPlusMemoryActuatorPane {}
        }
        Loader {
            id: resourcePane
            anchors.fill: parent
            active: root.resourcePaneActive
            sourceComponent: CpuPlusResourceDiagnosticsPane { subject: root.resourceSubject }
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
            if (++root.ticks > 480) {
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
                if (!root.check(duration && execute && dial && duration.width===(workshop.compactLayout?22:32)
                    && duration.horizontalStepPresentation && !CpuPlusDiagnostics.busy
                    && workshop.phase==="PREPARE" && dial.options.length===12 && dial.readoutGlowEnabled && String(dial.markerColor).toLowerCase()==="#ed981a"
                    && dial.numericDetentInterval===1,"actual Workshop hardware and no automatic launch")) return;
                const host=root.findItem(pane.item,"cpuplusDiagnosticFilterHost");
                const rail=root.findItem(pane.item,"cpuplusWorkshopFilterRail");
                if (!root.check(host && rail && rail.parent===host && rail.width===host.width
                    && ["threads","memory","census","storage","stall"].every(k=>{
                        const b=root.findItem(rail,"cpuplusWorkshopInstrument-"+k);
                        return b && b.visible && b.width===b.height && b.height===host.height;
                    }),"five equal square tools mounted in the header")) return;
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!root.check(viewport && viewport.contentHeight<=viewport.height+1,
                    "default Workshop fits native 320x620 viewport // "+viewport.contentHeight+" / "+viewport.height)) return;
                if (!root.check(root.normalFace(pane.item,"cpuplusMemoryMode-DIAG",true)
                    && root.normalFace(pane.item,"cpuplusMemoryMode-CAP",false)
                    && root.normalFace(pane.item,"cpuplusWorkshopInstrument-threads",true)
                    && root.normalFace(pane.item,"cpuplusWorkshopInstrument-storage",false), "normal opaque faces before unload")) return;
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
                if (!root.check(storage && storage.visible && storage.height<=workshop.instrumentHeight && storage.y>0 && dial.visible
                    && duration.height===workshop.width && dial.mapToItem(workshop,0,0).y>root.findItem(workshop,"cpuplusWorkshopCensusInterval").mapToItem(workshop,0,0).y
                    && ["Duration","ThreadInterval","MemoryInterval","CensusInterval"].every(name=>{
                        const slider=root.findItem(workshop,"cpuplusWorkshop"+name+"-hardware");
                        return slider && slider.visible && slider.height===workshop.width
                            && String(slider.border.color)===String(duration.border.color)
                            && String(slider.border.color).toLowerCase()==="#ffffff"
                            && slider.responsiveHardware && slider.energizedValueFill
                            && slider.hardwareThumbWidth<=slider.width
                            && slider.hardwareThumbLength<52
                            && String(slider.frameGlowColor)===String(slider.valueFillColor)
                            && String(slider.handleGlowColor)===String(slider.valueFillColor)
                            && String(slider.activityGlowColor)===String(slider.valueFillColor);
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
                    && root.normalFace(pane.item,"cpuplusWorkshopInstrument-census",true)
                    && root.normalFace(pane.item,"cpuplusWorkshopInstrument-threads",false), "normal opaque faces after actual remount")) return;
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
                root.paneActive=true;
                root.phase=23;
                return;
            }
            if (root.phase===23 && pane.item) {
                pane.item.selectMenu(4);
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop) return;
                workshop.edit("selected",["threads","memory","census","storage","stall"]);
                workshop.edit("durationSeconds",30);
                root.phase=24;
                return;
            }
            if (root.phase===24 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const dial=root.findItem(workshop,"cpuplusWorkshopStallThreshold");
                const threads=root.findItem(workshop,"cpuplusWorkshopTopThreads");
                const storage=root.findItem(workshop,"cpuplusWorkshopStorageInstrument");
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!root.check(dial && dial.visible && threads.visible && storage.visible
                    && dial.numericDetentInterval===50 && dial.markerColor.toString().toLowerCase()==="#c74ec7"
                    && String(dial.activeDetentColor)===String(dial.markerColor)
                    && String(dial.accentColor).toLowerCase()==="#f2be4e" && dial.outlinedOptionLabels
                    && root.normalFace(pane.item,"cpuplusWorkshopInstrument-stall",true),
                    "actual second dial and fifth normal-face selector")) return;
                const storageContents=root.findItem(storage,"cpuplusWorkshopStorageContents");
                if (!root.check(storageContents && storageContents.y>=0
                    && storageContents.y+storageContents.height<=storage.height+1
                    && storageContents.children.every(c=>c.x>=0 && c.x+c.width<=storageContents.width+1),
                    "storage contents fit card with all five instruments")) return;
                if (!root.check(viewport.contentHeight<=viewport.height+1,
                    "all five instruments fit // "+viewport.contentHeight+" / "+viewport.height)) return;
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const fill=root.findItem(duration,"selectorNumericFill");
                const halo=root.findItem(duration,"selectorNumericFillHalo");
                if (!duration || !fill || !halo || Math.abs(duration.liveFillFraction-29/119)>0.02) return;
                if (!root.check(fill.width>4 && halo.visible && duration.hardwareThumbLength<52,
                    "compact thumb and widened energized fill")) return;
                root.compactThumbLength=duration.hardwareThumbLength;
                root.lowFillOpacity=fill.opacity;
                root.lowHaloOpacity=halo.opacity;
                workshop.edit("durationSeconds",100);
                root.phase=241;
                return;
            }
            if (root.phase===241 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                if (!duration || duration.liveFillFraction<0.82) return;
                const fill=root.findItem(duration,"selectorNumericFill");
                const halo=root.findItem(duration,"selectorNumericFillHalo");
                if (!root.check(fill.opacity>root.lowFillOpacity && halo.opacity>root.lowHaloOpacity
                    && !CpuPlusDiagnostics.busy,"fill and halo intensify without launching capture")) return;
                nativeWindow.width=400;
                nativeWindow.height=700;
                root.phase=242;
                return;
            }
            if (root.phase===242 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!duration || duration.hardwareThumbLength<=root.compactThumbLength) return;
                if (!root.check(viewport.contentHeight<=viewport.height+1,"medium instruments fit")) return;
                root.mediumThumbLength=duration.hardwareThumbLength;
                nativeWindow.width=500;
                nativeWindow.height=800;
                root.phase=243;
                return;
            }
            if (root.phase===243 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!duration || duration.hardwareThumbLength<=root.mediumThumbLength) return;
                if (!root.check(viewport.contentHeight<=viewport.height+1,"large instruments fit")) return;
                const pair=root.findItem(workshop,"cpuplusWorkshopStorageDialPair");
                const sampleDial=root.findItem(pair,"cpuplusWorkshopStorage-sample-dial");
                const reportDial=root.findItem(pair,"cpuplusWorkshopStorage-report-dial");
                if (!sampleDial || !reportDial) return;
                const instruments=[sampleDial,reportDial].map(d=>root.findItem(d,"selectorAutomotiveDial"));
                if (instruments.some(d=>!d || !root.findItem(d,"automotiveGauge")?.hasPainted || !root.findItem(d,"automotiveArm")?.hasPainted)) return;
                const rendered=(d,value,color)=>{
                    const a=d.mapToItem(pair,0,0), b=d.mapToItem(pair,d.width,d.height);
                    return d.visible && d.opacity>0 && a.x>=-1 && a.y>=-1
                        && b.x<=pair.width+1 && b.y<=pair.height+1
                        && b.x-a.x>=74 && b.y-a.y>=87
                        && d.currentValue===value && String(d.accentColor).toLowerCase()===color;
                };
                if (!root.check(pair && pair.visible && workshop.storageMechanical && workshop.storageDialWidth>=92
                    && rendered(sampleDial,workshop.storageSample,"#ed981a")
                    && rendered(reportDial,workshop.storageReport,"#c74ec7")
                    && [sampleDial,reportDial].every(d=>d.stopwatchFace && d.stopwatchLitSegments===30
                        && root.findItem(d,"selectorStopwatchFace").visible
                        && root.findItem(d,"selectorStopwatchCenter").visible
                        && root.findItem(d,"automotiveGauge").visible
                        && root.findItem(d,"automotiveArm").visible
                        && root.findItem(d,"selectorAutomotiveDial").boundedArmReach===95
                        && root.findItem(d,"instrumentChassis").width===d.automotivePlateSize
                        && root.findItem(d,"instrumentChassis").screwSlotWidth>=1.5
                        && root.findItem(d,"selectorAutomotiveDial").actualFaceDiameter>=72
                        && root.findItem(d,"selectorAutomotiveDial").unitPixelSize>=9
                        && root.findItem(d,"automotiveGauge").width===root.findItem(d,"selectorAutomotiveDial").actualFaceDiameter
                        && root.findItem(d,"selectorAutomotiveDial").insetWindowFits(root.findItem(d,"selectorAutomotiveDial").upperGeometry)
                        && root.findItem(d,"selectorAutomotiveDial").insetWindowFits(root.findItem(d,"selectorAutomotiveDial").lowerGeometry)
                        && root.findItem(d,"automotiveValueWindow").visible
                        && root.findItem(d,"automotiveSetWindow").visible
                        && root.findItem(d,"instrumentChassis").screwEdgeClearance>=2.5
                        && (!root.findItem(d,"automotiveValueUnit").visible || (()=>{
                            const v=root.findItem(d,"selectorStopwatchCenter"),u=root.findItem(d,"automotiveValueUnit");
                            return v.x+v.width<=u.x+0.01 || v.y+v.height<=u.y+0.01;
                        })())
                        && root.findItem(d,"selectorDialReadableValue").visible
                        && root.findItem(d,"selectorDialReadableValue").text.includes("SEC")
                        && d.scale===1)
                    && !root.findItem(workshop,"cpuplusWorkshopStallThreshold").stopwatchFace
                    && !root.findItem(workshop,"cpuplusWorkshopTopThreads").stopwatchFace,
                    "both mechanical dials use allocated pixels, legible unit, Phillips slot and actual values")) return;
                // Exercise the configurable variants on real mounted instruments.
                const combinations=[["industrial","continuous","numbers","chamfered"],["capsule","dualRail","sparse","rounded"],["tapered","radialTeeth","none","square"],["tapered","segmented","ticks","square"]];
                if(root.automotiveVariantIndex<combinations.length){
                    const v=combinations[root.automotiveVariantIndex++];
                    sampleDial.stopwatchArmStyle=v[0]; sampleDial.stopwatchGaugeStyle=v[1];
                    sampleDial.stopwatchScaleStyle=v[2]; sampleDial.chassisStyle=v[3];
                    sampleDial.stopwatchArmReach=120;
                    const index=root.automotiveVariantIndex-1;
                    const metal=["#a66c42","#914578","#d16041","#40899b"][index];
                    const strength=index<2?1:0.75;
                    sampleDial.screwColor=metal;
                    sampleDial.screwColorStrength=strength;
                    const chassis=root.findItem(sampleDial,"instrumentChassis");
                    if(!root.check(String(chassis.screwColor).toLowerCase()===metal && String(instruments[0].screwColor).toLowerCase()===metal
                        && chassis.screwColorStrength===strength && instruments[0].screwColorStrength===strength
                        && Math.abs(chassis.screwTone(64,137,155).r-((64/255)*(1-strength)+chassis.screwColor.r*strength))<=1/255
                        && Math.abs(chassis.screwTone(64,137,155).g-((137/255)*(1-strength)+chassis.screwColor.g*strength))<=1/255
                        && Math.abs(chassis.screwTone(64,137,155).b-((155/255)*(1-strength)+chassis.screwColor.b*strength))<=1/255
                        && (strength!==1 || String(chassis.screwTone(64,137,155)).toLowerCase()===metal)
                        && chassis.screwShadow===0.75 && chassis.screwDirectLight===0.20 && chassis.screwReflectedLight===0.10
                        && chassis.screwCatchlight===0.40 && chassis.screwRecessDepth===0.14
                        && String(root.findItem(reportDial,"instrumentChassis").screwColor).toLowerCase()==="#40899b"
                        && root.findItem(reportDial,"instrumentChassis").screwColorStrength===0.75,
                        "shared screw finish follows caller color with fixed approved lighting; sibling unchanged")) return;
                    if(!root.check(instruments[0].boundedArmReach===95 && instruments[0].armStyle===v[0] && instruments[0].gaugeStyle===v[1] && instruments[0].scaleStyle===v[2] && instruments[0].chassisStyle===v[3],"automotive variant and reach bound "+v.join("/"))) return;
                    sampleDial.stopwatchArmReach=95;
                    return;
                }
                // Use a valid storage duration for winding; the preceding
                // resize witness intentionally used an invalid 100s plan.
                workshop.edit("durationSeconds",30);
                sampleDial.valueRequested(2);
                if (!root.check(workshop.storageSample===2 && !CpuPlusDiagnostics.busy,"stopwatch winding edits cadence only")) return;
                sampleDial.valueRequested(1);
                if (!root.check(workshop.storageSample===1 && workshop.storageReport===10,"stopwatch setting restored")) return;
                workshop.edit("durationSeconds",100);
                nativeWindow.width=320;
                nativeWindow.height=620;
                root.phase=244;
                return;
            }
            if (root.phase===244 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const duration=root.findItem(workshop,"cpuplusWorkshopDuration-hardware");
                const dial=root.findItem(workshop,"cpuplusWorkshopStallThreshold");
                const viewport=root.findItem(pane.item,"cpuplusMemoryScroll");
                if (!duration || duration.hardwareThumbLength!==root.compactThumbLength) return;
                if (!root.check(viewport.contentHeight<=viewport.height+1,"compact instruments fit after resize")) return;
                if (!root.check(!workshop.storageMechanical && !root.findItem(workshop,"cpuplusWorkshopStorageDialPair").visible,
                    "narrow slot returns to digital clocks")) return;
                workshop.edit("selected",["storage","stall"]);
                workshop.edit("durationSeconds",5);
                dial.valueRequested(500);
                const samplePlus=root.findItem(workshop,"cpuplusWorkshopStorage-sample-plus");
                const reportMinus=root.findItem(workshop,"cpuplusWorkshopStorage-report-minus");
                if (!root.check(!workshop.storageMechanical && samplePlus && samplePlus.visible && samplePlus.available
                    && reportMinus && reportMinus.visible && reportMinus.available
                    && String(samplePlus.accentColor).toLowerCase()==="#9ece6a"
                    && String(reportMinus.accentColor).toLowerCase()==="#d16041"
                    && samplePlus.width===samplePlus.height && samplePlus.height<19,
                    "smallest storage stays digital with compact green plus and red minus")) return;
                const prepare=root.findItem(workshop,"cpuplusWorkshopExecute");
                if (!root.check(prepare && prepare.preparationFace && prepare.washStrength===0.24
                    && String(prepare.color)===String(prepare.steadyWashColor) && !prepare.softGlowEnabled && !prepare.wideGlowEnabled,
                    "prepare uses stable opaque special wash, not broad shadow or ornament")) return;
                samplePlus.leftClicked(null);
                reportMinus.leftClicked(null);
                if (!root.check(workshop.draft.storageCadenceExplicit && workshop.draft.storageSampleSeconds===2
                    && workshop.draft.storageReportSeconds===8 && !CpuPlusDiagnostics.busy,
                    "storage controls change real detached calibration without launch")) return;
                if (!root.check(workshop.preview.ok && workshop.plan.instruments[1].thresholdMs===500,
                    "stall dial changes submitted calibration")) return;
                workshop.activate();
                root.phase=25;
                return;
            }
            if (root.phase===25 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop || workshop.calibrating) return;
                if (!root.check(workshop.ready && !CpuPlusDiagnostics.busy,"stall prepare does not launch")) return;
                const reportMinus=root.findItem(workshop,"cpuplusWorkshopStorage-report-minus");
                if (!root.check(reportMinus && reportMinus.available,"prepared storage report control available")) return;
                reportMinus.leftClicked(null);
                if (!root.check(!workshop.ready && !CpuPlusDiagnostics.busy && workshop.draft.storageReportSeconds===6,
                    "cadence edit invalidates prepared capture")) return;
                reportMinus.leftClicked(null);
                if (!root.check(workshop.draft.storageReportSeconds===4,"nondefault report interval")) return;
                workshop.activate();
                root.phase=251;
                return;
            }
            if (root.phase===251 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop || workshop.calibrating) return;
                if (!root.check(workshop.ready && !CpuPlusDiagnostics.busy,"cadence reprepare never launches")) return;
                workshop.activate();
                if (!root.check(CpuPlusDiagnostics.kind==="workflow" && CpuPlusDiagnostics.stallCaptureActive,
                    "second click starts coordinated stall capture")) return;
                root.phase=252;
                return;
            }
            if (root.phase===252 && pane.item) {
                if (!root.check(!CpuPlusDiagnostics.storageProgressFault && CpuPlusDiagnostics.busy,
                    "storage live side channel remains valid")) return;
                const p=CpuPlusDiagnostics.storageProgress;
                if (!p || p.tick<1) return;
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!root.check(p.tick===1 && p.reports===0 && workshop.countdown("sample")
                    && workshop.countdown("sample").remainingMs>0 && workshop.countdown("sample").remainingMs<=2000,
                    "observed sample resets scheduled countdown before report")) return;
                nativeWindow.width=500;
                nativeWindow.height=800;
                root.phase=253;
                return;
            }
            if (root.phase===253 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                const sample=root.findItem(workshop,"cpuplusWorkshopStorage-sample-dial");
                const report=root.findItem(workshop,"cpuplusWorkshopStorage-report-dial");
                if (!sample || !report || !sample.stopwatchActive || !report.stopwatchActive) return;
                if (!root.check(workshop.recording && !CpuPlusDiagnostics.storageProgressFault
                    && CpuPlusDiagnostics.captureId===CpuPlusDiagnostics.workshopRunId
                    && [sample,report].every(d=>d.visible && !d.interactive && d.stopwatchFraction>=0
                        && d.stopwatchFraction<=1 && d.stopwatchLitSegments===Math.ceil(d.stopwatchFraction*30)
                        && root.findItem(d,"selectorStopwatchCenter").text===d.readoutText
                        && root.findItem(d,"selectorAutomotiveDial").boundedFraction===d.stopwatchFraction
                        && root.findItem(d,"selectorDialReadableValue").visible
                        && root.findItem(d,"selectorAutomotiveDial").rotationDegrees===360*d.stopwatchFraction)
                    && sample.stopwatchSetSeconds===2 && report.stopwatchSetSeconds===4,
                    "live mechanical countdown face retains exact capture and independent cadence after resize")) return;
                nativeWindow.width=320;
                nativeWindow.height=620;
                root.paneActive=false;
                root.phase=26;
                return;
            }
            if (root.phase===26) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report=CpuPlusDiagnostics.reports.workflow;
                if (!root.check(report && report.status==="COMPLETE" && report.id===CpuPlusDiagnostics.workshopRunId
                    && !CpuPlusDiagnostics.stallCaptureActive && report.summary.indexOf("THRESHOLD 500 ms")>=0
                    && CpuPlusDiagnostics.archiveRows.some(row=>row.id===report.id),
                    "real coordinated storage/clock witness and fixture heartbeat // "+CpuPlusDiagnostics.feedback+" / "+(report?report.summary:"NO REPORT"))) return;
                const storageEvidence=JSON.parse(report.text).instruments.find(i=>i.config.kind==="storage");
                if (!root.check(storageEvidence && storageEvidence.config.sampleSeconds===2 && storageEvidence.config.reportSeconds===4
                    && storageEvidence.records[0].intervals===2 && storageEvidence.records[1].intervals===3,
                    "edited storage calibration reaches actual coordinated receipt")) return;
                console.log("CPU_D3E_NATIVE_PASS");
                root.paneActive=true;
                root.phase=27;
                return;
            }
            if (root.phase===27 && pane.item) {
                pane.item.selectMenu(4);
                root.phase=271;
                return;
            }
            if(root.phase===271 && pane.item){
                const rail=root.findItem(pane.item,"cpuplusDiagnosticWorkspaceRail");
                const context=root.findItem(pane.item,"cpuplusDiagnosticContextRail");
                const footer=root.findItem(pane.item,"cpuplusDiagBottomControls");
                const modes=root.findItem(pane.item,"cpuplusMemoryMenuRail");
                const controls=root.findItem(pane.item,"cpuplusDiagnosticWorkspace-WORK");
                const workflows=root.findItem(pane.item,"cpuplusDiagnosticWorkspace-PRESETS");
                if (!root.check(rail && context && footer && modes && controls && workflows && rail.visible
                    && footer.parent===root.findItem(pane.item,"cpuplusWorkFooter")
                    && footer.height===53 && context.height===25 && rail.height===25
                    && context.y+context.height+3===rail.y && modes.y===0 && controls.selected,
                    "fixed two-row footer with context above workspace // "+JSON.stringify({footer:footer?footer.height:null,context:context?{y:context.y,h:context.height}:null,rail:rail?{y:rail.y,h:rail.height,v:rail.visible}:null,modes:modes?modes.y:null,selected:controls?controls.selected:null,parent:footer?footer.parent.objectName:null}))) return;
                root.diagnosticFooterGeometry=root.footerGeometry(pane.item,["QUICK","REPORT","HISTORY","COMPARE"]);
                if(!root.check(root.diagnosticFooterGeometry!=="","control footer geometry"))return;
                root.findItem(pane.item,"cpuplusDiagnosticView-REPORT").leftClicked(null);
                root.phase=270;
                return;
            }
            if(root.phase===270 && pane.item){
                if(!root.check(root.footerGeometry(pane.item,["QUICK","REPORT","HISTORY","COMPARE"])===root.diagnosticFooterGeometry,
                    "report controls do not shift either navigation row"))return;
                const workflows=root.findItem(pane.item,"cpuplusDiagnosticWorkspace-PRESETS");
                workflows.leftClicked(null);
                root.phase=28;
                return;
            }
            if (root.phase===28 && pane.item) {
                const catalog=root.findItem(pane.item,"cpuplusDiagnosticWorkflowCatalog");
                const name=root.findItem(catalog,"cpuplusDiagnosticPresetName");
                const save=root.findItem(catalog,"cpuplusDiagnosticSavePreset");
                if (!root.check(catalog && catalog.visible && !root.findItem(pane.item,"cpuplusDiagnosticWorkshop")
                    && !CpuPlusDiagnostics.busy,"workflow catalog separate from controls")) return;
                if(!root.check(root.footerGeometry(pane.item,["LIBRARY","QUEUE","SETS","RESULTS"])===root.diagnosticFooterGeometry,
                    "workflow navigation matches Controls geometry"))return;
                root.findItem(pane.item,"cpuplusDiagnosticView-RESULTS").leftClicked(null);
                root.phase=280;
                return;
            }
            if(root.phase===280 && pane.item){
                if(!root.check(root.footerGeometry(pane.item,["LIBRARY","QUEUE","SETS","RESULTS"])===root.diagnosticFooterGeometry
                    && root.findItem(pane.item,"cpuplusDiagnosticView-RESULTS").selected,
                    "results filter keeps both rows fixed"))return;
                root.findItem(pane.item,"cpuplusDiagnosticView-LIBRARY").leftClicked(null);
                root.phase=281;
                return;
            }
            if(root.phase===281 && pane.item){
                const name=root.findItem(pane.item,"cpuplusDiagnosticPresetName");
                const save=root.findItem(pane.item,"cpuplusDiagnosticSavePreset");
                if(!root.check(name&&save&&name.visible&&save.visible,"library restored by bottom filter"))return;
                name.text="STALL SESSION";
                save.leftClicked(null);
                if (!root.check(CpuPlusDiagnostics.workshopPresets.length===1
                    && CpuPlusDiagnostics.workshopPresets[0].plan.instruments[1].thresholdMs===500
                    && !CpuPlusDiagnostics.saveWorkshopPreset("stall session")
                    && !CpuPlusDiagnostics.busy,"save calibrated session preset without starting")) return;
                root.paneActive=false;
                root.phase=29;
                return;
            }
            if (root.phase===29) {
                if (!root.check(CpuPlusDiagnostics.workshopPresets.length===1,"preset survives menu destruction")) return;
                root.paneActive=true;
                root.phase=30;
                return;
            }
            if (root.phase===30 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!workshop) return;
                workshop.edit("stallThresholdMs",650);
                root.findItem(pane.item,"cpuplusDiagnosticWorkspace-PRESETS").leftClicked(null);
                root.phase=31;
                return;
            }
            if (root.phase===31 && pane.item) {
                const load=root.findItem(pane.item,"cpuplusDiagnosticLoadPreset-STALL SESSION");
                if (!root.check(load && load.visible,"saved preset shown after reopen")) return;
                load.leftClicked(null);
                root.phase=32;
                return;
            }
            if (root.phase===32 && pane.item) {
                const workshop=root.findItem(pane.item,"cpuplusDiagnosticWorkshop");
                if (!root.check(workshop && workshop.draft.stallThresholdMs===500 && !workshop.ready
                    && !CpuPlusDiagnostics.busy,"loaded calibration requires fresh prepare")) return;
                if(!root.check(root.footerGeometry(pane.item,["QUICK","REPORT","HISTORY","COMPARE"])===root.diagnosticFooterGeometry,
                    "footer geometry preserved after loading a preset and remount"))return;
                console.log("CPU_D4A_NATIVE_PASS");
                console.log("CPU_D4B_FIXED_FOOTER_PASS");
                workshop.edit("selected",["census","storage"]);
                workshop.edit("durationSeconds",1);
                workshop.edit("censusIntervalMs",1000);
                if (!root.check(!workshop.preview.ok && workshop.draft.storageSampleSeconds===2,
                    "shortening duration preserves explicit cadence and refuses invalid plan")) return;
                workshop.chooseStorageCadence("sample",1);
                workshop.chooseStorageCadence("report",10);
                if (!root.check(workshop.preview.ok && workshop.draft.storageSampleSeconds===1 && workshop.draft.storageReportSeconds===10,
                    "explicit recalibration enables short set capture")) return;
                if (!root.check(CpuPlusDiagnostics.saveWorkshopPreset("QUICK A")
                    && CpuPlusDiagnostics.saveWorkshopPreset("QUICK B")
                    && CpuPlusDiagnostics.queueWorkshop("QUICK A")
                    && CpuPlusDiagnostics.queueWorkshop("QUICK B")
                    && CpuPlusDiagnostics.moveWorkshopQueue(1,-1)
                    && CpuPlusDiagnostics.saveWorkshopSet("ORDERED")
                    && CpuPlusDiagnostics.clearWorkshopQueue()
                    && CpuPlusDiagnostics.removeWorkshopPreset("QUICK A")
                    && CpuPlusDiagnostics.loadWorkshopSet("ORDERED")
                    && CpuPlusDiagnostics.workshopQueue[0].name==="QUICK B"
                    && CpuPlusDiagnostics.workshopQueue[1].name==="QUICK A"
                    && !CpuPlusDiagnostics.busy,"set snapshots retain ordered independent calibrations")) return;
                if (!root.check(!CpuPlusDiagnostics.startWorkshopSet("[]")
                    && CpuPlusDiagnostics.startWorkshopSet(JSON.stringify(CpuPlusDiagnostics.queuePreview.items))
                    && CpuPlusDiagnostics.setActive && !CpuPlusDiagnostics.request("inventory"),
                    "explicit set launch holds shared single-flight")) return;
                root.paneActive=false;
                root.phase=33;
                return;
            }
            if (root.phase===33) {
                if(CpuPlusDiagnostics.setActive||CpuPlusDiagnostics.busy||CpuPlusDiagnostics.archiveBusy)return;
                const rows=CpuPlusDiagnostics.setRunResults;
                if(!root.check(rows.length===2 && rows[0].name==="QUICK B" && rows[1].name==="QUICK A"
                    && rows[0].id!==rows[1].id && rows.every(x=>x.status==="COMPLETE"
                       && CpuPlusDiagnostics.archiveRows.some(r=>r.id===x.id))
                    && CpuPlusDiagnostics.setFeedback.startsWith("SET COMPLETE"),
                    "ordered set archives each exact step across unload // "+CpuPlusDiagnostics.setFeedback))return;
                if(!root.check(CpuPlusDiagnostics.startWorkshopSet(JSON.stringify(CpuPlusDiagnostics.queuePreview.items)),
                    "explicit second set launch"))return;
                CpuPlusDiagnostics.stopWorkshopSet();
                root.phase=34;
                return;
            }
            if(root.phase===34){
                if(CpuPlusDiagnostics.setActive||CpuPlusDiagnostics.busy||CpuPlusDiagnostics.archiveBusy)return;
                if(!root.check(CpuPlusDiagnostics.setRunResults.length===1
                    && CpuPlusDiagnostics.setFeedback.startsWith("SET CANCELLED"),
                    "cancel prevents next queued capture // "+CpuPlusDiagnostics.setFeedback))return;
                console.log("CPU_D4B_NATIVE_PASS");
                root.generalDraftWitness=JSON.stringify(CpuPlusDiagnostics.workshopDraft);
                root.resourcePaneActive=true;
                root.phase=35;
                return;
            }
            if (root.phase===35 && resourcePane.item) {
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!w)return;
                const footer=root.findItem(resourcePane.item,"cpuplusDiagBottomControls");
                if(!root.check(w.subject==="CPU" && w.preview.ok && !w.ready && !CpuPlusDiagnostics.busy
                    && w.draft.selected.join(",")==="census"
                    && !!root.findItem(resourcePane.item,"cpuplusWorkshopInstrument-census")
                    && !!root.findItem(resourcePane.item,"cpuplusWorkshopInstrument-threads")
                    && !root.findItem(resourcePane.item,"cpuplusWorkshopInstrument-storage")
                    && footer && footer.height===53 && footer.mapToItem(resourcePane.item,0,0).y>=0
                    && footer.mapToItem(resourcePane.item,0,0).y+footer.height<=resourcePane.item.height+1,
                    "CPU resource mounts shared instrument and pinned footer without starting capture"))return;
                w.edit("durationSeconds",20);
                if(!root.check(CpuPlusDiagnostics.cpuWorkshopDraft.durationSeconds===20
                    && JSON.stringify(CpuPlusDiagnostics.workshopDraft)===root.generalDraftWitness
                    && !CpuPlusDiagnostics.loadWorkshopPreset("STALL SESSION","CPU")
                    && CpuPlusDiagnostics.saveWorkshopPreset("CPU ONLY","CPU"),
                    "CPU draft and preset scope isolated from general calibration"))return;
                w.activate(); root.phase=36; return;
            }
            if(root.phase===36 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && w.ready && !CpuPlusDiagnostics.busy,"CPU first click prepares without execution"))return;
                root.resourcePaneActive=false; root.phase=37; return;
            }
            if(root.phase===37){
                if(!root.check(!resourcePane.item && !CpuPlusDiagnostics.busy,"unload discards prepared authority"))return;
                root.resourcePaneActive=true; root.phase=38; return;
            }
            if(root.phase===38 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!w)return;
                if(!root.check(w.draft.durationSeconds===20 && !w.ready && !CpuPlusDiagnostics.busy
                    && JSON.stringify(CpuPlusDiagnostics.workshopDraft)===root.generalDraftWitness,
                    "CPU calibration survives remount, readiness does not"))return;
                console.log("CPU_D6A_RESOURCE_NATIVE_PASS");
                const host=root.findItem(resourcePane.item,"cpuplusWorkshopInstrument-hostcpu");
                if(!root.check(host && host.available,"host instrument available"))return;
                host.leftClicked(null);
                w.edit("durationSeconds",1);
                w.edit("hostCpuIntervalMs",1000);
                if(!root.check(w.draft.selected.join(",")==="hostcpu" && w.preview.ok
                    && root.findItem(w,"cpuplusWorkshopHostCpuInterval").visible && !CpuPlusDiagnostics.busy,
                    "standalone host calibration, no automatic launch"))return;
                w.activate(); root.phase=39; return;
            }
            if(root.phase===39 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && w.ready && !CpuPlusDiagnostics.busy,"host prepare only"))return;
                w.activate();
                if(!root.check(CpuPlusDiagnostics.busy && CpuPlusDiagnostics.kind==="hostcpu","host capture started"))return;
                root.resourcePaneActive=false;root.phase=40;return;
            }
            if(root.phase===40){
                if(CpuPlusDiagnostics.busy||CpuPlusDiagnostics.archiveBusy)return;
                const report=CpuPlusDiagnostics.reports.hostcpu;
                if(!root.check(report && report.status==="COMPLETE"
                    && report.summary.includes("HOST CPU //")
                    && CpuPlusDiagnostics.archiveRows.some(r=>r.id===report.id && r.kind==="hostcpu"),
                    "actual host capture and archive survived unload // "+CpuPlusDiagnostics.feedback))return;
                root.resourcePaneActive=true;root.phase=41;return;
            }
            if(root.phase===41 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!w)return;
                if(!root.check(!w.ready && !CpuPlusDiagnostics.busy
                    && w.draft.selected.join(",")==="hostcpu"
                    && JSON.stringify(CpuPlusDiagnostics.workshopDraft)===root.generalDraftWitness,
                    "host remount retains calibration without authority"))return;
                console.log("CPU_D6B_HOST_NATIVE_PASS");
                root.cpuDraftWitness=JSON.stringify(CpuPlusDiagnostics.cpuWorkshopDraft);
                w.activate();
                root.phase=42;return;
            }
            if(root.phase===42 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && w.ready && !CpuPlusDiagnostics.busy,"CPU ready before switch"))return;
                root.resourceSubject="GPU";root.phase=43;return;
            }
            if(root.phase===43 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                const slider=root.findItem(w,"cpuplusWorkshopGpuInterval");
                if(!root.check(w && w.subject==="GPU" && !w.ready && w.preview.ok
                    && slider && slider.visible && w.draft.selected.join(",")==="gpu"
                    && w.targetText==="TARGET // ALL DRM DEVICES"
                    && !root.findItem(resourcePane.item,"cpuplusWorkshopInstrument-hostcpu")
                    && !CpuPlusDiagnostics.busy,"same workspace switches to GPU without carrying readiness"))return;
                w.edit("durationSeconds",2);
                if(!root.check(JSON.stringify(CpuPlusDiagnostics.cpuWorkshopDraft)===root.cpuDraftWitness
                    && !CpuPlusDiagnostics.loadWorkshopPreset("CPU ONLY","GPU")
                    && CpuPlusDiagnostics.saveWorkshopPreset("GPU ONLY","GPU"),"GPU calibration and preset scope isolated"))return;
                w.activate();root.phase=44;return;
            }
            if(root.phase===44 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && w.ready && !CpuPlusDiagnostics.busy,"GPU prepare does not launch"))return;
                w.activate();
                if(!root.check(CpuPlusDiagnostics.busy && CpuPlusDiagnostics.kind==="gpu","GPU capture started"))return;
                root.resourceSubject="CPU";root.phase=45;return;
            }
            if(root.phase===45 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && !w.recording && !w.ready && w.locked
                    && CpuPlusDiagnostics.busy && CpuPlusDiagnostics.kind==="gpu","CPU does not display foreign GPU recording as its own"))return;
                root.phase=46;return;
            }
            if(root.phase===46){
                if(CpuPlusDiagnostics.busy||CpuPlusDiagnostics.archiveBusy)return;
                const report=CpuPlusDiagnostics.reports.gpu;
                if(!root.check(report && report.status==="COMPLETE" && report.summary.includes("CARD0")
                    && report.summary.includes("CARD1") && report.summary.includes("BUSY // N/A")
                    && CpuPlusDiagnostics.archiveRows.some(r=>r.id===report.id && r.kind==="gpu"),"GPU reader and archive survive subject switch // "+CpuPlusDiagnostics.feedback))return;
                root.resourceSubject="GPU";root.phase=47;return;
            }
            if(root.phase===47 && resourcePane.item){
                const w=root.findItem(resourcePane.item,"cpuplusDiagnosticWorkshop");
                if(!root.check(w && !w.ready && !CpuPlusDiagnostics.busy && w.draft.durationSeconds===2
                    && JSON.stringify(CpuPlusDiagnostics.cpuWorkshopDraft)===root.cpuDraftWitness
                    && JSON.stringify(CpuPlusDiagnostics.workshopDraft)===root.generalDraftWitness,
                    "GPU draft survives navigation, other drafts untouched"))return;
                console.log("CPU_D7A_GPU_NATIVE_PASS");
                console.log("CPU_DIAG_NATIVE_PASS");
                root.done = true;
                Qt.quit();
            }
        }
    }
}
