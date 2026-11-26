import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticCalibration.js" as Calibration
import "../../components"

// Mounted only by the existing DIAG pane. Draft survives pane destruction;
// readiness does not. Neither editing nor opening this view starts a capture.
Column {
    id: root
    objectName: "cpuplusDiagnosticWorkshop"
    spacing: 5
    readonly property var draft: CpuPlusDiagnostics.workshopDraft
    readonly property bool locked: CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy || CpuPlusDiagnostics.faulted
    readonly property var plan: makePlan(draft)
    readonly property string planText: JSON.stringify(plan)
    readonly property var preview: plan.instruments.length === 1
        ? Calibration.previewCalibration(Object.assign({},plan.instruments[0],{durationSeconds:plan.durationSeconds}))
        : Calibration.previewWorkflow(plan)
    property string preparedText: ""
    property int preparedSequence: -1
    property bool calibrating: false
    property int preparationGeneration: 0
    readonly property bool ready: !locked && !calibrating && preparedText !== ""
        && preparedText === planText && preparedSequence === CpuPlusDiagnostics.captureSequence
    readonly property bool recording: CpuPlusDiagnostics.busy
        && CpuPlusDiagnostics.captureId === CpuPlusDiagnostics.workshopRunId
        && CpuPlusDiagnostics.workshopRunId !== ""
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
        : calibrating ? "CALIBRATING" : ready ? "READY"
        : terminal && terminal.status==="COMPLETE" ? "COMPLETE"
        : terminal ? "RETRY" : "PREPARE"
    readonly property var threadIntervals: [100,250,500,1000,2000,5000]

    function makePlan(d) {
        const instruments=[];
        for (const kind of ["threads","memory","census","storage"]) {
            if (!d.selected.includes(kind)) continue;
            if (kind==="threads") instruments.push({kind:kind,intervalMs:d.threadIntervalMs,topCount:d.topCount});
            else if (kind==="memory") instruments.push({kind:kind,intervalMs:d.memoryIntervalMs});
            else if (kind==="census") instruments.push({kind:kind,intervalMs:d.censusIntervalMs});
            else instruments.push({kind:kind});
        }
        return {durationSeconds:d.durationSeconds,instruments:instruments};
    }
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
        CpuPlusDiagnostics.workshopDraft=next;
    }
    function toggle(kind) {
        if (locked) return;
        const selected=draft.selected.slice();
        const i=selected.indexOf(kind);
        if (i<0) selected.push(kind); else selected.splice(i,1);
        edit("selected",selected);
    }
    function activate() {
        if (locked || calibrating || !preview.ok) return;
        if (ready) {
            const frozen=JSON.parse(preparedText);
            disarm();
            if (CpuPlusDiagnostics.requestWorkshopCapture(frozen)) displayNow=Date.now();
            return;
        }
        disarm();
        calibrating=true;
        const generation=preparationGeneration, exact=planText, sequence=CpuPlusDiagnostics.captureSequence;
        // Defer only the synchronous validation handoff, not a fake loading
        // duration. No elapsed timer or launch until the second click.
        Qt.callLater(function() {
            if (!root || root.preparationGeneration!==generation || !root.visible) return;
            root.calibrating=false;
            if (!root.locked && root.planText===exact && root.preview.ok
                    && CpuPlusDiagnostics.captureSequence===sequence) {
                root.preparedText=exact;
                root.preparedSequence=sequence;
            }
        });
    }
    onVisibleChanged: if (!visible) disarm()
    onLockedChanged: if (locked) disarm()
    onPlanTextChanged: disarm()
    onRecordingChanged: if (recording) displayNow=Date.now()
    Timer {
        interval: 250
        repeat: true
        running: root.visible && root.recording && !CpuPlusDiagnostics.cancelled
        onTriggered: root.displayNow=Date.now()
    }

    GohuText {
        width: parent.width
        text: "DIAG // WORKSHOP"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: "INSTRUMENTS // " + root.plan.instruments.length
        color: Colors.white
        font.pixelSize: 10
    }
    Flow {
        width: parent.width
        spacing: 4
        Repeater {
            model: [{kind:"threads",symbol:"≋",subject:"THREADS"},
                {kind:"memory",symbol:"",subject:"MEMORY"},
                {kind:"census",symbol:"",subject:"CPU"},
                {kind:"storage",symbol:"",subject:"STORAGE"}]
            ActionButton {
                required property var modelData
                objectName: "cpuplusWorkshopInstrument-"+modelData.kind
                width: 36
                height: 36
                accentColor: Colors.resourceColor(modelData.subject)
                label: modelData.symbol
                labelPixelSize: 24
                labelElide: Text.ElideNone
                contentPadding: 0
                selected: root.draft.selected.includes(modelData.kind)
                available: !root.locked
                acceptedButtons: Qt.LeftButton
                Accessible.name: modelData.kind.toUpperCase()
                Accessible.role: Accessible.Button
                Accessible.onPressAction: root.toggle(modelData.kind)
                onLeftClicked: root.toggle(modelData.kind)
            }
        }
    }
    GohuText {
        width: parent.width
        text: "TARGET // " + (root.draft.selected.some(k=>k==="threads"||k==="memory") ? "SAME-USER QUICKSHELL" : "SYSTEM")
        color: Colors.purple
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    CpuPlusDiagnosticSlider {
        objectName: "cpuplusWorkshopDuration"
        width: parent.width
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
        width: parent.width
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
        width: parent.width
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
        width: parent.width
        visible: root.draft.selected.includes("census")
        title: "PROCESS INTERVAL"
        readout: root.draft.censusIntervalMs/1000+" SEC"
        minimumValue: 1
        maximumValue: 60
        currentValue: root.draft.censusIntervalMs/1000
        adjustable: !root.locked
        onValueRequested: value=>root.edit("censusIntervalMs",value*1000)
    }
    GohuText {
        width: parent.width
        visible: root.draft.selected.includes("storage")
        text: "STORAGE // FIXED 1 SEC METADATA CADENCE"
        color: Colors.blue
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Item {
        width: parent.width
        height: 160
        visible: root.draft.selected.includes("threads")
        SelectorDial {
            objectName: "cpuplusWorkshopTopThreads"
            anchors.centerIn: parent
            labelText: "TOP THREADS"
            selectorMode: "continuous"
            minimumValue: 1
            maximumValue: 12
            currentValue: root.draft.topCount
            valueStep: 1
            valueDecimals: 0
            snapContinuousToStep: true
            showNumericDetentTicks: true
            numericReferenceValues: [1,4,8,12]
            accentColor: Colors.cyan
            markerColor: Colors.magenta
            labelColor: Colors.cyan
            interactive: !root.locked
            onValueRequested: value=>root.edit("topCount",Math.round(value))
        }
    }
    GohuText {
        width: parent.width
        text: root.preview.ok ? "CALIBRATION VALID // EST. "+(root.plan.instruments.length===1?root.preview.observations:root.preview.estimatedObservations)
            : root.preview.reason
        // Multi-instrument previews have a separate aggregate observation field.
        color: root.preview.ok ? Colors.omnitrix : Colors.yellow
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Row {
        width: parent.width
        spacing: 4
        CpuPlusDiagnosticExecutionButton {
            objectName: "cpuplusWorkshopExecute"
            width: Math.max(0,parent.width-40)
            phase: root.phase
            caption: root.phase==="READY" ? "READY // START"
                : root.phase==="RECORDING" ? "RECORDING // "+Math.floor(root.elapsedFraction*100)+"% TIME"
                : root.phase==="RETRY" ? "NOT VERIFIED // PREPARE" : root.phase
            progress: root.phase==="READY" || root.phase==="COMPLETE" ? 1
                : root.phase==="RECORDING" || root.phase==="STOPPING" ? root.elapsedFraction : 0
            available: true
            interactive: !root.locked && !root.calibrating && root.preview.ok
            onLeftClicked: root.activate()
        }
        ActionButton {
            objectName: "cpuplusWorkshopStop"
            width: 36
            height: 34
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
    GohuText {
        width: parent.width
        text: root.recording ? "TIME ELAPSED // NOT COMPLETION" :
            root.ready ? "SECOND CLICK STARTS CAPTURE" :
            "PREPARE VALIDATES SETTINGS // NO AUTOMATIC START"
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.Wrap
    }
}
