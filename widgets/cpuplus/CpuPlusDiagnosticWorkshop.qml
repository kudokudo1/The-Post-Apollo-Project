import QtQuick
import QtQuick.Controls as Controls
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticCalibration.js" as Calibration
import "../../services/diagnostics/DiagnosticTargetRegistry.js" as Targets
import "../../services/diagnostics/DiagnosticWorkflowReceipt.js" as Receipt
import "../../services/diagnostics/CpuPlusDiagnosticsPolicy.js" as DiagnosticPolicy
import "../../components"

// Mounted only by the existing DIAG pane. Draft survives pane destruction;
// readiness does not. Neither editing nor opening this view starts a capture.
Column {
    id: root
    objectName: "cpuplusDiagnosticWorkshop"
    spacing: compactLayout ? 1 : 2
    property real viewportHeight: 0
    property Item filterTarget: null
    property Item executionTarget: null
    property Item calibrationTarget: null
    readonly property bool mediumSystemDials: subject==="SYSTEM" && width>=340 && verticalLayout && viewportHeight>=210
    readonly property int sliderCount: 1+["threads","memory","census","hostcpu","gpu","netio","swapio","diskio"].filter(k=>draft.selected.includes(k)).length
    readonly property bool verticalLayout: subject==="SYSTEM" && viewportHeight>0 && (width<340 || (sliderCount>=3 && viewportHeight < sliderCount*(compactLayout?38:52)+(lowerInstrumentCount>0?176:0)+90))
    // Reserve the dial bank and its spacing, then give the rack the remaining viewport.
    readonly property real rackTravel: Math.max(45,Math.floor(viewportHeight-(lowerInstrumentCount>0?instrumentHeight+spacing:0)-34))
    property string subject: "ALL"
    readonly property var filterKinds: Calibration.workshopSubjectKinds(subject)
    readonly property int filterCount: filterKinds.length
    property string selectedTargetId: "automatic"
    readonly property var selectedTarget: Targets.findDiagnosticTarget(selectedTargetId)
    readonly property var targetCompatibility: Targets.targetPlanCompatibility(selectedTargetId,plan,{
        workshopDraftFromPlan: p=>Calibration.workshopDraftFromPlan(p),
        previewCalibration: c=>Calibration.previewCalibration(c)
    })
    readonly property bool targetPickerOpen: targetPicker.opened
    function targetCanSelect(row) {
        return !!row && row.available && row.route==="configured" &&
            row.kinds.some(k=>filterKinds.includes(k));
    }
    function selectTarget(id) {
        if(locked || saveEditorOpen || !targetCanSelect(Targets.findDiagnosticTarget(id))) return false;
        disarm();
        selectedTargetId=id;
        targetPicker.close();
        return true;
    }
    function targetAllowsInstrument(kind) {
        return !!selectedTarget && selectedTarget.kinds.includes(kind);
    }
    readonly property string targetText: {
        if(selectedTargetId!=="automatic" && selectedTarget)
            return "TARGET // "+selectedTarget.label.toUpperCase();
        if (subject==="SYSTEM" && draft.selected.length>1) return "TARGET // "+draft.selected.length+" INSTRUMENTS";
        if (draft.selected.includes("netio")) return "TARGET // ALL VISIBLE INTERFACES";
        if (draft.selected.includes("swapio")) return "TARGET // HOST SWAP";
        if (draft.selected.includes("diskio")) return "TARGET // WHOLE BLOCK DEVICES";
        if (draft.selected.includes("gpu")) return "TARGET // ALL DRM DEVICES";
        if (draft.selected.includes("hostcpu")) return "TARGET // HOST CPU";
        if (subject==="STORAGE" && draft.selected.includes("storage")) return "TARGET // 18 KNOWN FILES";
        const qs=draft.selected.some(k=>k==="threads"||k==="memory"||k==="stall");
        const system=draft.selected.some(k=>k==="census"||k==="storage");
        return qs && system ? "TARGET // QS + USER" : qs ? "TARGET // QUICKSHELL" : system ? "TARGET // USER" : "NO TARGET";
    }
    readonly property bool compactLayout: viewportHeight > 0 && viewportHeight < 480
    readonly property int instrumentHeight: mediumSystemDials && draft.selected.includes("storage") ? Math.max(154,Math.min(184,Math.floor(viewportHeight*0.53))) : subject==="SYSTEM" && verticalLayout ? (draft.selected.includes("storage") ? 132 : Math.max(76,Math.min(112,Math.floor(viewportHeight*0.47)))) : compactLayout ? 112 : Math.min(240,176+Math.floor(Math.max(0,viewportHeight-540)*0.35))
    readonly property int filterSize: compactLayout ? 24 : 32
    readonly property int filterGap: compactLayout ? 3 : 4
    readonly property int filterWidth: Math.min(filterSize,Math.max(16,Math.floor((width-68-filterCount*filterGap)/Math.max(1,filterCount))))
    readonly property int lowerInstrumentCount: ["threads","storage","stall"].filter(k=>draft.selected.includes(k)).length
    readonly property real lowerInstrumentSpace: Math.max(0,width-4*Math.max(0,lowerInstrumentCount-1))
    readonly property real lowerInstrumentWidth: Math.floor(lowerInstrumentSpace/Math.max(1,lowerInstrumentCount))
    readonly property real storageWidth: mediumSystemDials && lowerInstrumentCount===3 ? Math.floor(lowerInstrumentSpace*0.54) : lowerInstrumentCount===3 ? (lowerInstrumentSpace>=420 ? Math.min(Math.max(288,2*(instrumentHeight-57)+18),Math.floor(lowerInstrumentSpace-240)) : Math.floor(lowerInstrumentSpace*(compactLayout ? 0.30 : 0.24))) : lowerInstrumentWidth
    readonly property int storageDialWidth: Math.max(0,Math.floor(Math.min(180,(storageWidth-18)/2,instrumentHeight-57)))
    readonly property int storageDialHeight: storageDialWidth+34
    readonly property bool smallestStorageLayout: width<340 && viewportHeight<380
    // A 92px mounted dial gives the face at least 72 actual logical pixels.
    // Below that size use the existing readable digital controls instead.
    readonly property bool storageMechanical: !smallestStorageLayout && storageDialWidth>=(mediumSystemDials?76:92)
    readonly property real dialWidth: lowerInstrumentCount===3 ? Math.floor((lowerInstrumentSpace-storageWidth)/2) : lowerInstrumentWidth
    readonly property var draft: CpuPlusDiagnostics.draftForSubject(subject)
    readonly property int storageSample: draft.storageSampleSeconds || 1
    readonly property int storageReport: draft.storageReportSeconds || 10
    readonly property bool storageRunning: recording && draft.selected.includes("storage") && !CpuPlusDiagnostics.cancelled
    function countdown(field) {
        return storageRunning && !CpuPlusDiagnostics.storageProgressFault
            ? DiagnosticPolicy.storageCountdown(CpuPlusDiagnostics.storageProgress,field,Math.max(displayNow,Date.now())) : null;
    }
    readonly property var storagePreview: Calibration.previewCalibration({kind:"storage",durationSeconds:draft.durationSeconds,
        sampleSeconds:storageSample,reportSeconds:storageReport})
    readonly property bool locked: CpuPlusDiagnostics.workshopPresetLocked
    readonly property var plan: makePlan(draft)
    readonly property string planText: JSON.stringify(plan)
    readonly property var preview: plan.instruments.length === 1
        ? Calibration.previewCalibration(Object.assign({},plan.instruments[0],{durationSeconds:plan.durationSeconds}))
        : Calibration.previewWorkflow(plan)
    property bool saveEditorOpen: false
    property string savePlanText: ""
    property string pendingSaveName: ""
    property string saveNotice: ""
    property string preparedText: ""
    property int preparedSequence: -1
    property bool calibrating: false
    property int preparationGeneration: 0
    readonly property bool ready: !locked && !calibrating && preparedText !== ""
        && preparedText === planText && preparedSequence === CpuPlusDiagnostics.captureSequence
    readonly property bool recording: CpuPlusDiagnostics.busy
        && CpuPlusDiagnostics.captureId === CpuPlusDiagnostics.workshopRunId
        && CpuPlusDiagnostics.workshopRunId !== ""
        && CpuPlusDiagnostics.workshopRunPlan === planText
    readonly property var terminal: {
        const row=CpuPlusDiagnostics.reports[CpuPlusDiagnostics.workshopRunKind];
        return row && row.id===CpuPlusDiagnostics.workshopRunId
            && CpuPlusDiagnostics.workshopRunPlan===planText ? row : null;
    }
    property double displayNow: 0
    readonly property real elapsedFraction: recording
        ? Math.max(0,Math.min(0.96,(displayNow-CpuPlusDiagnostics.workshopStartedMs)
            / Math.max(1000,CpuPlusDiagnostics.workshopDurationSeconds*1000))) : 0
    readonly property string phase: recording ? (CpuPlusDiagnostics.cancelled ? "STOPPING" : "RECORDING")
        : CpuPlusDiagnostics.busy ? "SHARED BUSY"
        : calibrating ? "CALIBRATING" : ready ? "READY"
        : terminal && terminal.status==="COMPLETE" ? "COMPLETE"
        : terminal ? "RETRY" : "PREPARE"
    readonly property var threadIntervals: [100,250,500,1000,2000,5000]

    function makePlan(d) { return Calibration.workshopPlanFromDraft(d); }
    function disarm() {
        preparationGeneration++;
        calibrating=false;
        preparedText="";
        preparedSequence=-1;
    }
    function edit(key,value) {
        if (locked) return;
        disarm();
        const next=Object.assign({},draft);
        next[key]=value;
        CpuPlusDiagnostics.setDraftForSubject(subject,next);
    }
    function cadenceStep(field,direction) {
        return Calibration.storageCadenceStep(draft.durationSeconds,storageSample,storageReport,field,direction);
    }
    function changeStorageCadence(field,direction) {
        applyStorageCadence(cadenceStep(field,direction));
    }
    function chooseStorageCadence(field,value) {
        applyStorageCadence(Calibration.storageCadenceChoice(draft.durationSeconds,storageSample,storageReport,field,value));
    }
    function applyStorageCadence(pair) {
        if (locked || !draft.selected.includes("storage") || !pair) return;
        disarm();
        CpuPlusDiagnostics.setDraftForSubject(subject,Object.assign({},draft,{
            storageCadenceExplicit:true,storageSampleSeconds:pair.sampleSeconds,storageReportSeconds:pair.reportSeconds}));
    }
    function toggle(kind) {
        if (locked || !filterKinds.includes(kind) || (!draft.selected.includes(kind) && !targetAllowsInstrument(kind))) return;
        // SYSTEM permits every instrument to be selected independently.
        const standalone=["hostcpu","gpu","diskio","swapio","netio"];
        if (subject!=="SYSTEM" && standalone.includes(kind)) { edit("selected",draft.selected.includes(kind)?[]:[kind]); return; }
        const selected=subject==="SYSTEM" ? draft.selected.slice() : draft.selected.filter(k=>!standalone.includes(k));
        const i=selected.indexOf(kind);
        if (i<0) selected.push(kind); else selected.splice(i,1);
        edit("selected",selected);
    }
    function closeSaveEditor() {
        saveEditorOpen=false;
        savePlanText="";
        pendingSaveName="";
        if(workflowName) workflowName.text="";
    }
    function openSaveEditor() {
        if (locked || calibrating || !preview.ok || saveEditorOpen || selectedTargetId!=="automatic") return false;
        disarm();
        saveNotice="";
        savePlanText=planText;
        saveEditorOpen=true;
        if (!CpuPlusDiagnostics.workflowCatalogReady)
            CpuPlusDiagnostics.loadWorkflowCatalog();
        return true;
    }
    function confirmSave() {
        if (!saveEditorOpen || locked || calibrating || !preview.ok || savePlanText!==planText || selectedTargetId!=="automatic") return false;
        if (!CpuPlusDiagnostics.workflowCatalogReady) {
            saveNotice="";
            return CpuPlusDiagnostics.loadWorkflowCatalog();
        }
        const name=workflowName.text;
        if (!CpuPlusDiagnostics.saveWorkshopPreset(name,subject)) {
            saveNotice=CpuPlusDiagnostics.workshopPresetFeedback;
            return false;
        }
        pendingSaveName=name;
        saveNotice="SAVING // WAIT FOR CONFIRMATION";
        return true;
    }
    Connections {
        target: CpuPlusDiagnostics
        function onWorkflowCatalogCompleted(outcome,wasEdit,confirmedDocument) {
            if (!wasEdit || !root.pendingSaveName) return;
            const row=confirmedDocument && confirmedDocument.rows.find(r=>r.name===root.pendingSaveName);
            if (outcome==="READY" && row && row.execution==="configured"
                    && Receipt.sameValue(row.plan,JSON.parse(root.savePlanText))) {
                root.closeSaveEditor();
                root.saveNotice="SAVED // LOCAL WORKFLOW LIBRARY";
            } else {
                root.pendingSaveName="";
                root.saveNotice="SAVE NOT CONFIRMED // RELOAD REQUIRED";
            }
        }
        function onBusyChanged() { if(CpuPlusDiagnostics.busy) root.closeSaveEditor(); }
        function onSetActiveChanged() { if(CpuPlusDiagnostics.setActive) root.closeSaveEditor(); }
    }
    function activate() {
        if (locked || calibrating || !preview.ok || saveEditorOpen || !targetCompatibility.ok || targetPicker.visible) return;
        saveNotice="";
        if (ready) {
            const frozen=JSON.parse(preparedText);
            disarm();
            if (CpuPlusDiagnostics.requestWorkshopCapture(frozen)) displayNow=Date.now();
            return;
        }
        disarm();
        calibrating=true;
        const generation=preparationGeneration, exact=planText, sequence=CpuPlusDiagnostics.captureSequence, target=selectedTargetId;
        // Defer only the synchronous validation handoff, not a fake loading
        // duration. No elapsed timer or launch until the second click.
        Qt.callLater(function() {
            if (!root || root.preparationGeneration!==generation || !root.visible) return;
            root.calibrating=false;
            if (!root.locked && root.planText===exact && root.preview.ok && root.targetCompatibility.ok && root.selectedTargetId===target
                    && CpuPlusDiagnostics.captureSequence===sequence) {
                root.preparedText=exact;
                root.preparedSequence=sequence;
            }
        });
    }
    onSubjectChanged: { disarm(); closeSaveEditor(); saveNotice=""; selectedTargetId="automatic"; if(targetPicker) targetPicker.close(); }
    onSelectedTargetIdChanged: disarm()
    onVisibleChanged: if (!visible) { disarm(); closeSaveEditor(); saveNotice=""; if(targetPicker) targetPicker.close(); }
    onLockedChanged: if (locked) disarm()
    onPlanTextChanged: { disarm(); closeSaveEditor(); saveNotice=""; }
    onRecordingChanged: if (recording) displayNow=Date.now()
    Timer {
        interval: root.storageRunning ? 100 : 250
        repeat: true
        running: root.visible && root.recording && !CpuPlusDiagnostics.cancelled
        onTriggered: root.displayNow=Date.now()
    }


    Grid {
        objectName: "cpuplusWorkshopFilterRail"
        parent: root.filterTarget || root
        width: parent.width
        height: root.filterTarget ? parent.height : root.filterSize
        columns: root.filterTarget && root.subject==="SYSTEM" ? root.filterTarget.selectorColumns : Math.max(1,root.filterCount+(root.filterTarget?0:1))
        spacing: root.filterTarget ? 3 : root.filterGap
        visible: root.visible
        Repeater {
            model: [{kind:"threads",symbol:"≋",subject:"THREADS"},
                {kind:"memory",symbol:"",subject:"MEMORY"},
                {kind:"census",symbol:"",subject:"CPU"},
                {kind:"hostcpu",symbol:"▥",subject:"CPU"},
                {kind:"gpu",symbol:"󰢮",subject:"GPU"},
                {kind:"netio",symbol:"⇄",subject:"NETWORK"},
                {kind:"swapio",symbol:"⇅",subject:"SWAP"},
                {kind:"diskio",symbol:"▥",subject:"STORAGE"},
                {kind:"storage",symbol:"",subject:"STORAGE"},
                {kind:"stall",symbol:"⚡",subject:"UPTIME"}].filter(row=>root.filterKinds.includes(row.kind)).sort((a,b)=>{
                if(root.subject!=="SYSTEM")return 0;
                const order=["threads","hostcpu","memory","census","netio","stall","diskio","storage","gpu","swapio"];
                return order.indexOf(a.kind)-order.indexOf(b.kind);
            })
            ActionButton {
                id: instrumentFilter
                required property var modelData
                objectName: "cpuplusWorkshopInstrument-"+modelData.kind
                width: root.filterTarget && root.subject==="SYSTEM" ? root.filterTarget.selectorButtonSize : root.filterTarget ? parent.height : root.filterWidth
                height: root.filterTarget ? width : root.filterSize
                accentColor: Colors.resourceColor(modelData.subject)
                label: modelData.symbol
                labelPixelSize: Math.max(root.subject==="SYSTEM"?9:16,Math.round(width*0.72))
                labelElide: Text.ElideNone
                contentPadding: 0
                selected: root.draft.selected.includes(modelData.kind)
                contentGlowSelectedOpacity: 0.95
                normalFace: true
                available: !root.locked && (root.targetAllowsInstrument(modelData.kind) || selected)
                acceptedButtons: Qt.LeftButton
                Accessible.name: modelData.kind.toUpperCase()
                Accessible.role: Accessible.Button
                Accessible.onPressAction: root.toggle(modelData.kind)
                onLeftClicked: root.toggle(modelData.kind)
            }
        }
        GohuText {
            visible: !root.filterTarget
            width: Math.max(0,parent.width-root.filterCount*(root.filterWidth+root.filterGap))
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            text: root.targetText
            color: Colors.purple
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            maximumLineCount: 2
        }
    }
    Grid {
        objectName: "cpuplusWorkshopSliderRack"
        width: parent.width
        columns: root.verticalLayout ? root.sliderCount : 1
        spacing: root.verticalLayout ? 2 : root.spacing
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopDuration"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "DUR"
            compact: root.compactLayout
            title: "DURATION"
            readout: root.draft.durationSeconds+" SEC"
            minimumValue: 1
            maximumValue: 120
            currentValue: root.draft.durationSeconds
            adjustable: !root.locked
            onValueRequested: value=>root.edit("durationSeconds",value)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopThreadInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "THR"
            compact: root.compactLayout
            subjectColor: Colors.cyan
            fillColor: Colors.cyan
            visible: root.draft.selected.includes("threads")
            title: "THREAD INTERVAL"
            readout: root.draft.threadIntervalMs+" MS"
            minimumValue: 0
            maximumValue: 5
            currentValue: root.threadIntervals.indexOf(root.draft.threadIntervalMs)
            adjustable: !root.locked
            onValueRequested: value=>root.edit("threadIntervalMs",root.threadIntervals[Math.round(value)])
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopMemoryInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "RAM"
            compact: root.compactLayout
            subjectColor: Colors.magenta
            fillColor: Colors.magenta
            visible: root.draft.selected.includes("memory")
            title: "MEMORY INTERVAL"
            readout: root.draft.memoryIntervalMs/1000+" SEC"
            minimumValue: 5
            maximumValue: 60
            currentValue: root.draft.memoryIntervalMs/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("memoryIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopCensusInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "PROC"
            compact: root.compactLayout
            subjectColor: Colors.orange
            fillColor: Colors.orange
            visible: root.draft.selected.includes("census")
            title: "PROCESS INTERVAL"
            readout: root.draft.censusIntervalMs/1000+" SEC"
            minimumValue: 1
            maximumValue: 60
            currentValue: root.draft.censusIntervalMs/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("censusIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopHostCpuInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "CPU"
            compact: root.compactLayout
            subjectColor: Colors.orange
            fillColor: subjectColor
            visible: root.draft.selected.includes("hostcpu")
            title: "HOST SAMPLE INTERVAL"
            readout: currentValue+" SEC"
            minimumValue: 1
            maximumValue: 5
            currentValue: (root.draft.hostCpuIntervalMs||1000)/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("hostCpuIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopGpuInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "GPU"
            compact: root.compactLayout
            subjectColor: Colors.omnitrix
            fillColor: subjectColor
            visible: root.draft.selected.includes("gpu")
            title: "GPU SAMPLE INTERVAL"
            readout: currentValue+" SEC"
            minimumValue: 1
            maximumValue: 5
            currentValue: (root.draft.gpuIntervalMs||1000)/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("gpuIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopNetIoInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "NET"
            compact: root.compactLayout
            subjectColor: Colors.resourceColor("NETWORK")
            fillColor: subjectColor
            visible: root.draft.selected.includes("netio")
            title: "NETWORK SAMPLE INTERVAL"
            readout: currentValue+" SEC"
            minimumValue: 1
            maximumValue: 5
            currentValue: (root.draft.netIoIntervalMs||1000)/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("netIoIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopSwapIoInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "SWAP"
            compact: root.compactLayout
            subjectColor: Colors.yellow
            fillColor: subjectColor
            visible: root.draft.selected.includes("swapio")
            title: "SWAP SAMPLE INTERVAL"
            readout: currentValue+" SEC"
            minimumValue: 1
            maximumValue: 5
            currentValue: (root.draft.swapIoIntervalMs||1000)/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("swapIoIntervalMs",value*1000)
        }
        CpuPlusDiagnosticSlider {
            objectName: "cpuplusWorkshopDiskIoInterval"
            width: root.verticalLayout ? Math.max(1,Math.floor((parent.width-2*(root.sliderCount-1))/root.sliderCount)) : parent.width
            vertical: root.verticalLayout
            verticalTravel: root.rackTravel
            shortTitle: "I/O"
            compact: root.compactLayout
            subjectColor: Colors.resourceColor("STORAGE")
            fillColor: subjectColor
            visible: root.draft.selected.includes("diskio")
            title: "DISK I/O SAMPLE INTERVAL"
            readout: currentValue+" SEC"
            minimumValue: 1
            maximumValue: 5
            currentValue: (root.draft.diskIoIntervalMs||1000)/1000
            adjustable: !root.locked
            onValueRequested: value=>root.edit("diskIoIntervalMs",value*1000)
        }
    
    }
    GohuText {
        width: parent.width
        visible: !root.verticalLayout && !root.compactLayout && root.draft.selected.includes("netio")
        text: "RX / TX / PACKETS / ERRORS / DROPS · 12 INTERVALS MAX"
        color: Colors.resourceColor("NETWORK")
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: !root.verticalLayout && !root.compactLayout && root.draft.selected.includes("swapio")
        text: "SWAP IN / OUT / PSI / ZRAM · HOST · 12 INTERVALS MAX"
        color: Colors.yellow
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: !root.verticalLayout && !root.compactLayout && root.draft.selected.includes("diskio")
        text: "READ / WRITE / IOPS / IO TIME · WHOLE DEVICES · 12 INTERVALS MAX"
        color: Colors.resourceColor("STORAGE")
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: !root.verticalLayout && !root.compactLayout && root.draft.selected.includes("hostcpu")
        text: "HOST BUSY / LOGICAL CPUs / PSI / SCALING FREQUENCY · 12 SAMPLES MAX"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: !root.verticalLayout && !root.compactLayout && root.draft.selected.includes("gpu")
        text: "BUSY / VRAM / TEMP1 · ALL DRM DEVICES · 12 SAMPLES MAX"
        color: Colors.omnitrix
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 4
        visible: root.lowerInstrumentCount>0
        Item {
            width: root.dialWidth
            height: root.instrumentHeight
            visible: root.draft.selected.includes("threads")
            SelectorDial {
                objectName: "cpuplusWorkshopTopThreads"
                anchors.centerIn: parent
                width: Math.max(0,Math.min(parent.width,parent.height-24,180))
                height: width+24
                labelText: "TOP THREADS"
                options: ["1","2","3","4","5","6","7","8","9","10","11","12"]
                displayOptions: options
                numericLabelPixelSize: root.compactLayout ? 13 : 10
                readoutPixelSize: root.compactLayout ? 17 : 14
                titlePixelSize: 12
                idleRingGlowStrength: 0.65
                titleColor: accentColor
                outlinedOptionLabels: true
                numericDetentInterval: 1
                numericDetentOrigin: 1
                selectorMode: "continuous"
                minimumValue: 1
                maximumValue: 12
                currentValue: root.draft.topCount
                valueStep: 1
                valueDecimals: 0
                snapContinuousToStep: true
                showNumericDetentTicks: true
                numericReferenceValues: [1,2,3,4,5,6,7,8,9,10,11,12]
                accentColor: Colors.cyan
                markerColor: Colors.orange
                readoutColor: Colors.cyan
                readoutGlowEnabled: true
                interactionGlowColor: Colors.magenta
                labelColor: Colors.cyan
                interactive: !root.locked
                onValueRequested: value=>root.edit("topCount",Math.round(value))
            }
        }

        Item {
            visible: root.draft.selected.includes("storage")
            width: root.storageWidth
            height: root.instrumentHeight
            Rectangle {
            objectName: "cpuplusWorkshopStorageInstrument"
            anchors.centerIn: parent
            width: Math.max(0,parent.width-4)
            height: root.subject==="SYSTEM" && root.verticalLayout ? Math.min(parent.height,storageContents.implicitHeight+8) : storageContents.implicitHeight+8
            color: Colors.black
            border.color: Colors.blue
            clip: true
            Column {
                id: storageContents
                objectName: "cpuplusWorkshopStorageContents"
                anchors.centerIn: parent
                width: Math.max(0,parent.width-(root.compactLayout ? 4 : 8))
                spacing: root.compactLayout || root.verticalLayout ? 1 : 3
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: root.lowerInstrumentCount===3 ? "STORAGE" : "STORAGE // METADATA"
                    visible: !root.storageMechanical
                    color: Colors.blue
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                }
                Repeater {
                    model: [{key:"sample",label:"SAMPLE"},{key:"report",label:"REPORT"}]
                    Column {
                        required property var modelData
                        visible: !root.storageMechanical
                        width: storageContents.width
                        spacing: 1
                        CpuPlusMemoryReadout {
                            width: parent.width
                            text: parent.modelData.label
                            color: parent.modelData.key==="sample" ? Colors.orange : Colors.magenta
                            font.pixelSize: root.compactLayout ? 9 : 11
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Row {
                            id: cadenceRow
                            width: parent.width
                            height: root.compactLayout || root.verticalLayout ? (root.storageRunning ? 16 : 19) : 26
                            spacing: 2
                            readonly property string field: parent.modelData.key
                            readonly property int seconds: field==="sample" ? root.storageSample : root.storageReport
                            readonly property var countdown: root.countdown(field)
                            readonly property color selectorColor: field==="sample" ? Colors.orange : Colors.magenta
                            readonly property real buttonSize: Math.min(height-4,Math.max(10,Math.floor((width-30)/2)))
                            ActionButton {
                                objectName: "cpuplusWorkshopStorage-"+cadenceRow.field+"-minus"
                                width: cadenceRow.buttonSize
                                height: cadenceRow.buttonSize
                                anchors.verticalCenter: parent.verticalCenter
                                accentColor: Colors.red
                                normalFace: true
                                label: "−"
                                labelPixelSize: Math.max(9,Math.min(13,height-2))
                                contentPadding: 0
                                acceptedButtons: Qt.LeftButton
                                available: !root.locked && root.cadenceStep(cadenceRow.field,-1)!==null
                                Accessible.name: "Decrease storage "+cadenceRow.field+" interval"
                                Accessible.role: Accessible.Button
                                Accessible.onPressAction: root.changeStorageCadence(cadenceRow.field,-1)
                                onLeftClicked: root.changeStorageCadence(cadenceRow.field,-1)
                            }
                            CpuPlusMemoryReadout {
                                width: Math.max(0,cadenceRow.width-2*cadenceRow.buttonSize-2*cadenceRow.spacing)
                                height: cadenceRow.height
                                objectName: "cpuplusWorkshopStorage-"+cadenceRow.field+"-clock"
                                text: !root.storageRunning ? cadenceRow.seconds+" SEC" : !cadenceRow.countdown ? "WAIT" : (cadenceRow.countdown.remainingMs/1000).toFixed(1)+" SEC"
                                color: cadenceRow.countdown && cadenceRow.countdown.flash ? Colors.white : cadenceRow.selectorColor
                                semanticGlowColor: cadenceRow.selectorColor
                                font.pixelSize: root.compactLayout ? 12 : 16
                                fontSizeMode: Text.HorizontalFit
                                minimumPixelSize: 7
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            ActionButton {
                                objectName: "cpuplusWorkshopStorage-"+cadenceRow.field+"-plus"
                                width: cadenceRow.buttonSize
                                height: cadenceRow.buttonSize
                                anchors.verticalCenter: parent.verticalCenter
                                accentColor: Colors.green
                                normalFace: true
                                label: "+"
                                labelPixelSize: Math.max(9,Math.min(13,height-2))
                                contentPadding: 0
                                acceptedButtons: Qt.LeftButton
                                available: !root.locked && root.cadenceStep(cadenceRow.field,1)!==null
                                Accessible.name: "Increase storage "+cadenceRow.field+" interval"
                                Accessible.role: Accessible.Button
                                Accessible.onPressAction: root.changeStorageCadence(cadenceRow.field,1)
                                onLeftClicked: root.changeStorageCadence(cadenceRow.field,1)
                            }
                        }
                        Rectangle {
                            width: parent.width
                            height: root.storageRunning ? 3 : 0
                            visible: root.storageRunning
                            color: Colors.dark
                            Rectangle {
                                width: parent.width*(cadenceRow.countdown ? cadenceRow.countdown.fraction : 0)
                                height: parent.height
                                color: cadenceRow.countdown && cadenceRow.countdown.flash ? Colors.white : cadenceRow.selectorColor
                            }
                        }
                    }
                }
                Row {
                    id: storageDialPair
                    objectName: "cpuplusWorkshopStorageDialPair"
                    visible: root.storageMechanical
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: visible ? 2*root.storageDialWidth+2 : 0
                    height: visible ? root.storageDialHeight : 0
                    spacing: 2
                    // Fixed instruments, not model delegates. Each sourceComponent
                    // closes over the workshop itself and has a real sized loader.
                    Item {
                        width: root.storageDialWidth
                        height: root.storageDialHeight
                        Loader {
                            anchors.centerIn: parent
                            active: root.storageMechanical && root.draft.selected.includes("storage")
                            width: root.storageDialWidth
                            height: root.storageDialHeight
                            sourceComponent: SelectorDial {
                                objectName: "cpuplusWorkshopStorage-sample-dial"
                                readonly property var stopwatch: root.countdown("sample")
                                stopwatchFace: true
                                stopwatchArmStyle: "tapered"
                                stopwatchArmReach: 95
                                stopwatchGaugeStyle: "segmented"
                                stopwatchScaleStyle: "ticks"
                                chassisStyle: "square"
                                chassisClearance: 10
                                stopwatchActive: root.storageRunning
                                stopwatchFraction: stopwatch ? stopwatch.fraction : -1
                                stopwatchFlash: !!stopwatch && stopwatch.flash
                                stopwatchSetSeconds: root.storageSample
                                labelText: "SAMPLE"
                                selectorMode: "continuous"
                                minimumValue: 0
                                maximumValue: 5
                                currentValue: root.storageRunning ? (stopwatch ? stopwatch.remainingMs/1000 : 0) : root.storageSample
                                options: [0,1,2,3,4,5].map(n=>String(n))
                                displayOptions: options
                                numericReferenceValues: [0,1,2,3,4,5]
                                valueStep: 1
                                valueDecimals: 1
                                numericDetentInterval: 1
                                numericDetentOrigin: 0
                                showNumericDetentTicks: true
                                snapContinuousToStep: true
                                titlePixelSize: 15
                                numericLabelPixelSize: 13
                                readoutPixelSize: 18
                                titleColor: Colors.orange
                                accentColor: Colors.orange
                                labelColor: Colors.orange
                                markerColor: stopwatch && stopwatch.flash ? Colors.white : Colors.orange
                                activeDetentColor: Colors.orange
                                readoutGlowEnabled: true
                                readoutColor: stopwatch && stopwatch.flash ? Colors.white : Colors.orange
                                readoutText: root.storageRunning ? (stopwatch ? (stopwatch.remainingMs/1000).toFixed(1) : "WAIT") : String(Math.round(previewNumericValue))
                                readoutUnit: root.storageRunning && !stopwatch ? "" : "SEC"
                                outlinedOptionLabels: true
                                interactive: root.storageMechanical && !root.locked && root.draft.durationSeconds<=30
                                onValueRequested: value=>root.chooseStorageCadence("sample",value)
                            }
                        }
                    }
                    Item {
                        width: root.storageDialWidth
                        height: root.storageDialHeight
                        Loader {
                            anchors.centerIn: parent
                            active: root.storageMechanical && root.draft.selected.includes("storage")
                            width: root.storageDialWidth
                            height: root.storageDialHeight
                            sourceComponent: SelectorDial {
                                objectName: "cpuplusWorkshopStorage-report-dial"
                                readonly property var stopwatch: root.countdown("report")
                                stopwatchFace: true
                                stopwatchArmStyle: "tapered"
                                stopwatchArmReach: 95
                                stopwatchGaugeStyle: "segmented"
                                stopwatchScaleStyle: "ticks"
                                chassisStyle: "square"
                                chassisClearance: 10
                                stopwatchActive: root.storageRunning
                                stopwatchFraction: stopwatch ? stopwatch.fraction : -1
                                stopwatchFlash: !!stopwatch && stopwatch.flash
                                stopwatchSetSeconds: root.storageReport
                                labelText: "REPORT"
                                selectorMode: "continuous"
                                minimumValue: 0
                                maximumValue: 30
                                currentValue: root.storageRunning ? (stopwatch ? stopwatch.remainingMs/1000 : 0) : root.storageReport
                                options: [0,5,10,15,20,25,30].map(n=>String(n))
                                displayOptions: options
                                numericReferenceValues: [0,5,10,15,20,25,30]
                                valueStep: 1
                                valueDecimals: 1
                                numericDetentInterval: 1
                                numericDetentOrigin: 0
                                showNumericDetentTicks: true
                                snapContinuousToStep: true
                                titlePixelSize: 15
                                numericLabelPixelSize: 13
                                readoutPixelSize: 18
                                titleColor: Colors.magenta
                                accentColor: Colors.magenta
                                labelColor: Colors.magenta
                                markerColor: stopwatch && stopwatch.flash ? Colors.white : Colors.magenta
                                activeDetentColor: Colors.magenta
                                readoutGlowEnabled: true
                                readoutColor: stopwatch && stopwatch.flash ? Colors.white : Colors.magenta
                                readoutText: root.storageRunning ? (stopwatch ? (stopwatch.remainingMs/1000).toFixed(1) : "WAIT") : String(Math.round(previewNumericValue))
                                readoutUnit: root.storageRunning && !stopwatch ? "" : "SEC"
                                outlinedOptionLabels: true
                                interactive: root.storageMechanical && !root.locked && root.draft.durationSeconds<=30
                                onValueRequested: value=>root.chooseStorageCadence("report",value)
                            }
                        }
                    }
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: root.storageRunning ? (CpuPlusDiagnostics.storageProgressFault ? "CLOCK UNVERIFIED" : !CpuPlusDiagnostics.storageProgress ? "WAIT FOR CLOCK" : CpuPlusDiagnostics.storageProgress.tick+" INT / "+CpuPlusDiagnostics.storageProgress.reports+" RPT") : root.storagePreview.ok ? root.storagePreview.intervals+" INT / "+root.storagePreview.observations+" RPT" : "CHECK CADENCE"
                    color: root.storagePreview.ok ? Colors.blue : Colors.yellow
                    font.pixelSize: root.compactLayout ? 9 : 11
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 7
                    horizontalAlignment: Text.AlignHCenter
                }
                GohuText {
                    width: parent.width
                    text: "FINAL INCLUDED"
                    visible: !root.compactLayout && !root.verticalLayout && !root.storageMechanical
                    color: Colors.white
                    font.pixelSize: 8
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 7
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            }
        }
        Item {
            width: root.dialWidth
            height: root.instrumentHeight
            visible: root.draft.selected.includes("stall")
            SelectorDial {
                objectName: "cpuplusWorkshopStallThreshold"
                anchors.centerIn: parent
                width: Math.max(0,Math.min(parent.width,parent.height-24,180))
                height: width+24
                labelText: "STALL THRESHOLD"
                options: ["150","500","1000","1500","2000"]
                displayOptions: options
                numericReferenceValues: [150,500,1000,1500,2000]
                numericLabelPixelSize: root.compactLayout ? 13 : 10
                readoutPixelSize: root.compactLayout ? 17 : 14
                titlePixelSize: 12
                idleRingGlowStrength: 0.65
                titleColor: accentColor
                selectorMode: "continuous"
                minimumValue: 150
                maximumValue: 2000
                currentValue: root.draft.stallThresholdMs
                valueStep: 50
                numericDetentInterval: 50
                numericDetentOrigin: 150
                valueDecimals: 0
                snapContinuousToStep: true
                showNumericDetentTicks: true
                accentColor: Colors.yellow
                markerColor: Colors.magenta
                activeDetentColor: Colors.magenta
                outlinedOptionLabels: true
                labelColor: Colors.yellow
                readoutColor: Colors.yellow
                readoutGlowEnabled: true
                interactionGlowColor: Colors.magenta
                readoutText: String(Math.round(previewNumericValue))
                readoutUnit: "MS"
                interactive: !root.locked
                onValueRequested: value=>root.edit("stallThresholdMs",Math.round(value))
            }
        }
    }
    Column {
        id: executionColumn
        objectName: "cpuplusWorkshopPinnedExecution"
        parent: root.executionTarget || root
        width: parent.width
        spacing: 2
    
        CpuPlusMemoryReadout {
            objectName: "cpuplusWorkshopCalibrationStatus"
            parent: root.calibrationTarget || executionColumn
            // Legacy standalone workshop keeps its readout in the execution column.
            width: parent.width
            text: root.recording ? "ELAPSED TIME // NOT COMPLETION"
                : CpuPlusDiagnostics.busy ? "SHARED CAPTURE ACTIVE // "+CpuPlusDiagnostics.kind.toUpperCase()
                : root.saveEditorOpen ? (root.saveNotice || CpuPlusDiagnostics.workshopPresetFeedback)
                : !root.targetCompatibility.ok && root.preview.ok ? root.targetCompatibility.reason
                : root.ready ? "SECOND CLICK STARTS CAPTURE"
                : root.selectedTargetId!=="automatic" ? "TARGET SELECTED // SAVE SUPPORT PENDING"
                : root.saveNotice || (root.preview.ok ? "CALIBRATION VALID // EST. "+(root.plan.instruments.length===1?root.preview.observations:root.preview.estimatedObservations)
                : root.preview.reason)
            // Multi-instrument previews have a separate aggregate observation field.
            color: root.recording ? Colors.green : root.saveEditorOpen ? Colors.magenta : root.ready ? Colors.orange
                : root.saveNotice.startsWith("SAVED //") ? Colors.omnitrix : root.preview.ok ? Colors.omnitrix : Colors.yellow
            font.pixelSize: 10
            height: 14
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: 7
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
        }
        Row {
            width: parent.width
            spacing: 4
            visible: !root.saveEditorOpen
            ActionButton {
                objectName: "cpuplusWorkshopSave"
                width: 54
                height: 28
                label: "SAVE"
                normalFace: true
                accentColor: Colors.magenta
                available: !root.locked && !root.calibrating && root.preview.ok && root.selectedTargetId==="automatic"
                onLeftClicked: root.openSaveEditor()
            }
            ActionButton {
                objectName: "cpuplusWorkshopTarget"
                width: 54
                height: 28
                label: "TARGET"
                normalFace: true
                accentColor: Colors.purple
                available: !root.locked && !root.calibrating
                onLeftClicked: { root.disarm(); targetPicker.open(); }
            }
            CpuPlusDiagnosticExecutionButton {
                objectName: "cpuplusWorkshopExecute"
                width: Math.max(0,parent.width-156)
                height: 28
                phase: root.phase
                caption: root.phase==="READY" ? "READY // START"
                    : root.phase==="RECORDING" ? "RECORDING // "+Math.floor(root.elapsedFraction*100)+"% TIME"
                    : root.phase==="RETRY" ? "NOT VERIFIED // PREPARE" : root.phase
                progress: root.phase==="READY" || root.phase==="COMPLETE" ? 1
                    : root.phase==="RECORDING" || root.phase==="STOPPING" ? root.elapsedFraction : 0
                available: true
                interactive: !root.locked && !root.calibrating && root.preview.ok && root.targetCompatibility.ok && !targetPicker.visible
                onLeftClicked: root.activate()
            }
            ActionButton {
                objectName: "cpuplusWorkshopStop"
                width: 36
                height: 28
                label: "■"
                labelPixelSize: 21
                accentColor: Colors.red
                destructive: true
                available: root.recording && !CpuPlusDiagnostics.cancelled
                acceptedButtons: Qt.LeftButton
                Accessible.name: "Stop diagnostic recording"
                Accessible.role: Accessible.Button
                Accessible.onPressAction: if (available) CpuPlusDiagnostics.cancel()
                onLeftClicked: CpuPlusDiagnostics.cancel()
            }
        }
        Row {
            objectName: "cpuplusWorkshopSaveEditor"
            visible: root.saveEditorOpen
            width: parent.width
            spacing: 4
            Rectangle {
                width: Math.max(0,parent.width-108)
                height: 28
                color: Colors.black
                border.color: Colors.magenta
                TextInput {
                    id: workflowName
                    objectName: "cpuplusWorkshopSaveName"
                    anchors.fill: parent
                    anchors.margins: 4
                    maximumLength: 32
                    color: Colors.white
                    font.pixelSize: 11
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    enabled: !root.locked
                    onTextChanged: if(!root.pendingSaveName) root.saveNotice=""
                    onAccepted: root.confirmSave()
                }
                GohuText {
                    anchors.centerIn: parent
                    visible: workflowName.text.length===0 && !workflowName.activeFocus
                    text: "WORKFLOW NAME"
                    color: Colors.cyan
                    font.pixelSize: 10
                }
            }
            ActionButton {
                objectName: "cpuplusWorkshopConfirmSave"
                width: 66
                height: 28
                label: CpuPlusDiagnostics.workflowCatalogReady ? "SAVE" : "RELOAD"
                normalFace: true
                accentColor: Colors.omnitrix
                available: !root.locked && root.preview.ok &&
                    (!CpuPlusDiagnostics.workflowCatalogReady || workflowName.text.length>0)
                onLeftClicked: root.confirmSave()
            }
            ActionButton {
                objectName: "cpuplusWorkshopCancelSave"
                width: 34
                height: 28
                label: "X"
                normalFace: true
                accentColor: Colors.red
                available: !CpuPlusDiagnostics.workflowCatalogBusy
                onLeftClicked: { root.closeSaveEditor(); root.saveNotice=""; }
            }
        }
    
    }
    Controls.Popup {
        id: targetPicker
        objectName: "cpuplusWorkshopTargetPicker"
        parent: root
        x: 0
        y: 0
        width: root.width
        height: Math.min(300,Math.max(150,root.height))
        padding: 5
        modal: true
        focus: true
        closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
        property string category: "ALL"
        onOpened: { category="ALL"; targetSearch.text=""; targetSearch.forceActiveFocus(); }
        background: Rectangle { color: Colors.black; border.color: Colors.purple }
        contentItem: Column {
            spacing: 4
            Row {
                width: parent.width
                spacing: 4
                Rectangle {
                    width: Math.max(0,parent.width-120)
                    height: 28
                    color: Colors.black
                    border.color: Colors.purple
                    TextInput {
                        id: targetSearch
                        objectName: "cpuplusWorkshopTargetSearch"
                        anchors.fill: parent
                        anchors.margins: 4
                        maximumLength: 128
                        color: Colors.white
                        font.pixelSize: 11
                        verticalAlignment: TextInput.AlignVCenter
                        selectByMouse: true
                    }
                    GohuText {
                        anchors.centerIn: parent
                        visible: targetSearch.text.length===0 && !targetSearch.activeFocus
                        text: "SEARCH TARGETS"
                        color: Colors.purple
                        font.pixelSize: 10
                    }
                }
                Controls.ComboBox {
                    objectName: "cpuplusWorkshopTargetCategory"
                    width: 82
                    height: 28
                    model: Targets.targetCategories()
                    currentIndex: model.indexOf(targetPicker.category)
                    onActivated: targetPicker.category=currentText
                }
                ActionButton {
                    width: 30
                    height: 28
                    label: "X"
                    normalFace: true
                    accentColor: Colors.red
                    onLeftClicked: targetPicker.close()
                }
            }
            GohuText {
                width: parent.width
                height: 16
                text: root.targetText
                color: Colors.purple
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            ListView {
                objectName: "cpuplusWorkshopTargetResults"
                width: parent.width
                height: Math.max(0,parent.height-52)
                clip: true
                spacing: 3
                model: Targets.searchDiagnosticTargets(targetSearch.text,targetPicker.category)
                delegate: Column {
                    required property var modelData
                    width: ListView.view.width
                    spacing: 1
                    ActionButton {
                        objectName: "cpuplusWorkshopTarget-"+modelData.id
                        width: parent.width
                        height: 26
                        normalFace: true
                        accentColor: Colors.purple
                        selected: root.selectedTargetId===modelData.id
                        label: modelData.label+(modelData.route==="fixed"?" // QUICK ONLY":!modelData.available?" // LOCKED":!root.targetCanSelect(modelData)?" // OUTSIDE SUBJECT":"")
                        labelPixelSize: 10
                        labelFontSizeMode: Text.HorizontalFit
                        labelMinimumPixelSize: 8
                        available: !root.locked && root.targetCanSelect(modelData)
                        onLeftClicked: root.selectTarget(modelData.id)
                    }
                    GohuText {
                        width: parent.width
                        text: modelData.detail
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

}
