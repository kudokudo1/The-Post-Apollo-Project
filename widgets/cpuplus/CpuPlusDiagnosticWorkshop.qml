import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticCalibration.js" as Calibration
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
    property string subject: "ALL"
    readonly property var filterKinds: Calibration.workshopSubjectKinds(subject)
    readonly property int filterCount: filterKinds.length
    readonly property string targetText: {
        if (draft.selected.includes("gpu")) return "TARGET // ALL DRM DEVICES";
        if (draft.selected.includes("hostcpu")) return "TARGET // HOST CPU";
        if (subject==="STORAGE" && draft.selected.includes("storage")) return "TARGET // 18 KNOWN FILES";
        const qs=draft.selected.some(k=>k==="threads"||k==="memory"||k==="stall");
        const system=draft.selected.some(k=>k==="census"||k==="storage");
        return qs && system ? "TARGET // QS + USER" : qs ? "TARGET // QUICKSHELL" : system ? "TARGET // USER" : "NO TARGET";
    }
    readonly property bool compactLayout: viewportHeight > 0 && viewportHeight < 480
    readonly property int instrumentHeight: compactLayout ? 112 : Math.min(240,176+Math.floor(Math.max(0,viewportHeight-540)*0.35))
    readonly property int filterSize: compactLayout ? 24 : 32
    readonly property int filterGap: compactLayout ? 3 : 4
    readonly property int filterWidth: Math.min(filterSize,Math.max(16,Math.floor((width-68-filterCount*filterGap)/Math.max(1,filterCount))))
    readonly property int lowerInstrumentCount: ["threads","storage","stall"].filter(k=>draft.selected.includes(k)).length
    readonly property real lowerInstrumentSpace: Math.max(0,width-4*Math.max(0,lowerInstrumentCount-1))
    readonly property real lowerInstrumentWidth: Math.floor(lowerInstrumentSpace/Math.max(1,lowerInstrumentCount))
    readonly property real storageWidth: lowerInstrumentCount===3 ? (lowerInstrumentSpace>=420 ? Math.min(Math.max(288,2*(instrumentHeight-57)+18),Math.floor(lowerInstrumentSpace-240)) : Math.floor(lowerInstrumentSpace*(compactLayout ? 0.30 : 0.24))) : lowerInstrumentWidth
    readonly property int storageDialWidth: Math.max(0,Math.floor(Math.min(180,(storageWidth-18)/2,instrumentHeight-57)))
    readonly property int storageDialHeight: storageDialWidth+34
    readonly property bool smallestStorageLayout: width<340 && viewportHeight<380
    // A 92px mounted dial gives the face at least 72 actual logical pixels.
    // Below that size use the existing readable digital controls instead.
    readonly property bool storageMechanical: !smallestStorageLayout && storageDialWidth>=92
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
        if (locked || !filterKinds.includes(kind)) return;
        // Host capture is standalone in D6b; mixed sequential sets remain supported.
        if (kind==="hostcpu" || kind==="gpu") { edit("selected",draft.selected.includes(kind)?[]:[kind]); return; }
        const selected=draft.selected.filter(k=>k!=="hostcpu");
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
    onSubjectChanged: disarm()
    onVisibleChanged: if (!visible) disarm()
    onLockedChanged: if (locked) disarm()
    onPlanTextChanged: disarm()
    onRecordingChanged: if (recording) displayNow=Date.now()
    Timer {
        interval: root.storageRunning ? 100 : 250
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
                {kind:"hostcpu",symbol:"▥",subject:"CPU"},
                {kind:"gpu",symbol:"󰢮",subject:"GPU"},
                {kind:"storage",symbol:"",subject:"STORAGE"},
                {kind:"stall",symbol:"⚡",subject:"UPTIME"}].filter(row=>root.filterKinds.includes(row.kind))
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
    CpuPlusDiagnosticSlider {
        objectName: root.subject==="GPU" ? "cpuplusWorkshopGpuInterval" : "cpuplusWorkshopHostCpuInterval"
        width: parent.width
        compact: root.compactLayout
        subjectColor: root.subject==="GPU" ? Colors.omnitrix : Colors.orange
        fillColor: subjectColor
        visible: root.draft.selected.includes("hostcpu") || root.draft.selected.includes("gpu")
        title: root.subject==="GPU" ? "GPU SAMPLE INTERVAL" : "HOST SAMPLE INTERVAL"
        readout: currentValue+" SEC"
        minimumValue: 1
        maximumValue: 5
        currentValue: root.subject==="GPU" ? (root.draft.gpuIntervalMs||1000)/1000 : (root.draft.hostCpuIntervalMs||1000)/1000
        adjustable: !root.locked
        onValueRequested: value=>root.edit(root.subject==="GPU"?"gpuIntervalMs":"hostCpuIntervalMs",value*1000)
    }
    GohuText {
        width: parent.width
        visible: root.draft.selected.includes("hostcpu") || root.draft.selected.includes("gpu")
        text: root.subject==="GPU" ? "BUSY / VRAM / TEMP1 · ALL DRM DEVICES · 12 SAMPLES MAX" : "HOST BUSY / LOGICAL CPUs / PSI / SCALING FREQUENCY · 12 SAMPLES MAX"
        color: root.subject==="GPU" ? Colors.omnitrix : Colors.orange
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
                            height: root.compactLayout ? (root.storageRunning ? 16 : 19) : 26
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
                    visible: !root.compactLayout && !root.storageMechanical
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
    CpuPlusMemoryReadout {
        objectName: "cpuplusWorkshopCalibrationStatus"
        width: parent.width
        text: root.recording ? "ELAPSED TIME // NOT COMPLETION"
            : CpuPlusDiagnostics.busy ? "SHARED CAPTURE ACTIVE // "+CpuPlusDiagnostics.kind.toUpperCase()
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
