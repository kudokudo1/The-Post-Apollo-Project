import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticCalibration.js" as Calibration
import "../../components"

// Mounted only by the existing DIAG pane. Draft survives pane destruction;
// readiness does not. Neither editing nor opening this view starts a capture.
Column {
    id: root
    objectName: "cpuplusDiagnosticWorkshop"
    spacing: compactLayout ? 1 : 2
    property real viewportHeight: 0
    property Item filterTarget: null
    readonly property string targetText: {
        const qs=draft.selected.some(k=>k==="threads"||k==="memory"||k==="stall");
        const system=draft.selected.some(k=>k==="census"||k==="storage");
        return qs && system ? "TARGET // QS + USER" : qs ? "TARGET // QUICKSHELL" : system ? "TARGET // USER" : "NO TARGET";
    }
    readonly property bool compactLayout: viewportHeight > 0 && viewportHeight < 480
    readonly property int instrumentHeight: compactLayout ? 112 : 176
    readonly property int filterSize: compactLayout ? 24 : 32
    readonly property int filterGap: compactLayout ? 3 : 4
    readonly property int filterWidth: Math.min(filterSize,Math.max(16,Math.floor((width-68-5*filterGap)/5)))
    readonly property int lowerInstrumentCount: ["threads","storage","stall"].filter(k=>draft.selected.includes(k)).length
    readonly property real lowerInstrumentSpace: Math.max(0,width-4*Math.max(0,lowerInstrumentCount-1))
    readonly property real lowerInstrumentWidth: Math.floor(lowerInstrumentSpace/Math.max(1,lowerInstrumentCount))
    readonly property real storageWidth: lowerInstrumentCount===3 ? Math.floor(lowerInstrumentSpace*(compactLayout ? 0.30 : 0.24)) : lowerInstrumentWidth
    readonly property real dialWidth: lowerInstrumentCount===3 ? Math.floor((lowerInstrumentSpace-storageWidth)/2) : lowerInstrumentWidth
    readonly property var draft: CpuPlusDiagnostics.workshopDraft
    readonly property bool locked: CpuPlusDiagnostics.workshopPresetLocked
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


    Row {
        objectName: "cpuplusWorkshopFilterRail"
        parent: root.filterTarget || root
        width: parent.width
        height: root.filterTarget ? parent.height : root.filterSize
        spacing: root.filterTarget ? 3 : root.filterGap
        visible: root.visible
        Repeater {
            model: [{kind:"threads",symbol:"≋",subject:"THREADS"},
                {kind:"memory",symbol:"",subject:"MEMORY"},
                {kind:"census",symbol:"",subject:"CPU"},
                {kind:"storage",symbol:"",subject:"STORAGE"},
                {kind:"stall",symbol:"⚡",subject:"UPTIME"}]
            ActionButton {
                id: instrumentFilter
                required property var modelData
                objectName: "cpuplusWorkshopInstrument-"+modelData.kind
                width: root.filterTarget ? parent.height : root.filterWidth
                height: root.filterTarget ? parent.height : root.filterSize
                accentColor: Colors.resourceColor(modelData.subject)
                label: modelData.symbol
                labelPixelSize: Math.max(16,Math.round(width*0.72))
                labelElide: Text.ElideNone
                contentPadding: 0
                selected: root.draft.selected.includes(modelData.kind)
                contentGlowSelectedOpacity: 0.95
                normalFace: true
                available: !root.locked
                acceptedButtons: Qt.LeftButton
                Accessible.name: modelData.kind.toUpperCase()
                Accessible.role: Accessible.Button
                Accessible.onPressAction: root.toggle(modelData.kind)
                onLeftClicked: root.toggle(modelData.kind)
            }
        }
        GohuText {
            visible: !root.filterTarget
            width: Math.max(0,parent.width-5*(root.filterWidth+root.filterGap))
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
    CpuPlusDiagnosticSlider {
        objectName: "cpuplusWorkshopDuration"
        width: parent.width
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
        width: parent.width
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
        width: parent.width
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
        width: parent.width
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
                scale: Math.min(1.1, parent.width/width, parent.height/height)
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
            height: storageContents.implicitHeight+8
            color: Colors.black
            border.color: Colors.blue
            clip: true
            Column {
                id: storageContents
                objectName: "cpuplusWorkshopStorageContents"
                anchors.centerIn: parent
                width: Math.max(0,parent.width-(root.compactLayout ? 4 : 8))
                spacing: root.compactLayout ? 1 : 3
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: root.lowerInstrumentCount===3 ? "STORAGE" : "STORAGE // METADATA"
                    color: Colors.blue
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: "1 SEC"
                    semanticGlowColor: Colors.blue
                    color: Colors.blue
                    font.pixelSize: root.compactLayout ? 17 : 24
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                }
                Rectangle {
                    width: parent.width
                    height: root.compactLayout ? 10 : 14
                    color: Colors.black
                    border.color: Colors.blue
                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        Repeater {
                            model: 10
                            Rectangle {
                                width: Math.max(0,(parent.width-18)/10)
                                height: parent.height
                                color: Colors.blue
                            }
                        }
                    }
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: "FIXED CADENCE"
                    color: Colors.white
                    font.pixelSize: root.compactLayout ? 9 : 10
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 7
                    horizontalAlignment: Text.AlignHCenter
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: root.draft.durationSeconds+" INTERVALS"
                    color: Colors.blue
                    font.pixelSize: 11
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                    horizontalAlignment: Text.AlignHCenter
                }
                GohuText {
                    width: parent.width
                    text: root.lowerInstrumentCount===3 ? "10s / FINAL" : "10s / FINAL REPORT"
                    color: Colors.white
                    font.pixelSize: 9
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
                scale: Math.min(1.1,parent.width/width,parent.height/height)
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
    GohuText {
        width: parent.width
        text: root.recording ? "ELAPSED TIME // NOT COMPLETION"
            : root.ready ? "SECOND CLICK STARTS CAPTURE"
            : root.preview.ok ? "CALIBRATION VALID // EST. "+(root.plan.instruments.length===1?root.preview.observations:root.preview.estimatedObservations)
            : root.preview.reason
        // Multi-instrument previews have a separate aggregate observation field.
        color: root.recording ? Colors.green : root.ready ? Colors.orange : root.preview.ok ? Colors.omnitrix : Colors.yellow
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Row {
        width: parent.width
        spacing: 4
        CpuPlusDiagnosticExecutionButton {
            objectName: "cpuplusWorkshopExecute"
            width: Math.max(0,parent.width-40)
            height: root.compactLayout ? 28 : 34
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
            height: root.compactLayout ? 28 : 34
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
}
