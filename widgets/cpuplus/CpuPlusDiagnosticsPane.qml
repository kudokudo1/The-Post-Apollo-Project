import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticComparison.js" as Compare
import "../../services/diagnostics/CpuPlusDiagnosticsPolicy.js" as Policy
import "../../components"

// UI only. Session owner survives CPU++ closing or changing pages.
Column {
    id: root
    objectName: "cpuplusDiagnosticControls"
    property Item headerTarget: null
    property Item footerTarget: null
    property real workshopViewportHeight: 0
    spacing: 6
    readonly property string selectedReport: CpuPlusDiagnostics.selectedReport
    property bool showReport: false
    property string viewMode: "WORK"
    readonly property bool workshopOpen: viewMode === "WORK"
    function consumeReportView() {
        if (!CpuPlusDiagnostics.pendingReportView) return;
        CpuPlusDiagnostics.pendingReportView = false;
        selectView("REPORT");
    }
    Component.onCompleted: consumeReportView()
    Connections {
        target: CpuPlusDiagnostics
        function onPendingReportViewChanged() { root.consumeReportView(); }
    }
    function selectView(mode) {
        if (!["WORK","QUICK","REPORT","HISTORY","COMPARE"].includes(mode)) return;
        showReport=false;
        showHistory=mode==="HISTORY" || mode==="COMPARE";
        showComparison=mode==="COMPARE";
        viewMode=mode;
        if (showHistory && !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.archiveBusy)
            CpuPlusDiagnostics.loadHistory();
    }
    readonly property var report: CpuPlusDiagnostics.selectedArchiveId
        ? CpuPlusDiagnostics.reportFor(selectedReport, CpuPlusDiagnostics.selectedArchiveId)
        : CpuPlusDiagnostics.reports[selectedReport] || null
    property bool showHistory: false
    property bool showComparison: false
    readonly property var archiveRows: CpuPlusDiagnostics.archiveStatus === "READY" && !CpuPlusDiagnostics.archiveBusy
        ? CpuPlusDiagnostics.archiveRows : []
    readonly property var beforeRecord: archiveRows.find(row => row.id === CpuPlusDiagnostics.compareBeforeId) || null
    readonly property var afterRecord: archiveRows.find(row => row.id === CpuPlusDiagnostics.compareAfterId) || null
    readonly property bool canChooseComparison: !["workflow","stall"].includes(selectedReport) && report !== null && archiveRows.some(row => row.id === report.id && row.status === "COMPLETE")
    readonly property var comparison: showComparison ? Compare.compare(beforeRecord, afterRecord, Policy.summarize, Policy.appControlMetrics) : null
    readonly property var memoryDetails: memoryBreakdown(selectedReport, report, true, true)
    readonly property var hostDetails: memoryDetails ? memoryDetails.hostContext : null
    property bool showHostDetails: true
    function memoryBreakdown(selected, report, includePrivate = false, includeHost = false) {
        // Presentation only: reuse the existing completed JSONL capture.
        if (selected !== "memory" || !report || report.status !== "COMPLETE"
                || typeof report.text !== "string" || report.text.length > 65536) return null;
        try {
            const records = report.text.trim().split("\n").map(line => JSON.parse(line));
            const final = records.pop();
            const keys = ["Rss","Pss","Pss_Anon","Pss_File","Pss_Shmem","Private_Dirty","Swap","SwapPss"];
            const count = value => Number.isSafeInteger(value) && value >= 0;
            if (!final || final.event !== "complete" || !count(final.pid) || final.pid === 0
                    || !count(final.startTicks) || records.length < 1 || records.length > 361)
                return null;
            let duration = 0;
            let privateCoverage = 0;
            const privateValues = [];
            for (let i=0; i<records.length; ++i) {
                const row = records[i];
                if (!row || row.event !== "memory" || row.pid !== final.pid
                        || row.startTicks !== final.startTicks || !row.memoryKiB
                        || !keys.every(key => count(row.memoryKiB[key]))
                        || !count(row.tsMs) || !count(row.cpuTicks)
                        || !count(row.pssPlusSwapPssKiB)
                        || row.pssPlusSwapPssKiB !== row.memoryKiB.Pss + row.memoryKiB.SwapPss
                        || row.memoryKiB.Pss > row.memoryKiB.Rss
                        || row.memoryKiB.Private_Dirty > row.memoryKiB.Rss
                        || row.memoryKiB.SwapPss > row.memoryKiB.Swap)
                    return null;
                if (includePrivate) {
                    const clean = row.memoryKiB.Private_Clean;
                    const resident = row.privateResidentKiB;
                    const hasClean = Object.prototype.hasOwnProperty.call(row.memoryKiB,"Private_Clean");
                    const hasResident = Object.prototype.hasOwnProperty.call(row,"privateResidentKiB");
                    if (hasClean || hasResident) {
                        if (!hasClean || !hasResident || !count(clean) || !count(resident)
                                || !count(clean + row.memoryKiB.Private_Dirty)
                                || resident !== clean + row.memoryKiB.Private_Dirty
                                || resident > row.memoryKiB.Rss) return null;
                        privateCoverage++;
                        privateValues.push({clean:clean,resident:resident});
                    }
                }
                if (i === 0) {
                    if (row.sampleIntervalMs !== null || row.cpuPct !== null) return null;
                } else {
                    if (!count(row.sampleIntervalMs) || row.sampleIntervalMs === 0
                            || typeof row.cpuPct !== "number" || !Number.isFinite(row.cpuPct) || row.cpuPct < 0
                            || row.cpuTicks < records[i-1].cpuTicks) return null;
                    duration += row.sampleIntervalMs;
                    if (!count(duration)) return null;
                }
            }
            const first = records[0].memoryKiB, last = records[records.length-1].memoryKiB;
            const labels = [
                ["RSS","Rss"], ["PSS","Pss"], ["PRIVATE DIRTY","Private_Dirty"],
                ["SWAP","Swap"], ["SWAP PSS","SwapPss"]
            ];
            const details = {pid:final.pid, startTicks:final.startTicks, samples:records.length,
                durationMs:duration, rows:labels.map(pair => ({label:pair[0],
                    first:first[pair[1]], peak:Math.max(...records.map(row=>row.memoryKiB[pair[1]])),
                    last:last[pair[1]], change:records.length > 1 ? last[pair[1]]-first[pair[1]] : null})),
                anon:last.Pss_Anon, file:last.Pss_File, shmem:last.Pss_Shmem};
            if (includePrivate) {
                // A legacy capture has neither field. Never mix partially
                // extended rows into a trend or substitute zero for absence.
                if (privateCoverage !== 0 && privateCoverage !== records.length) return null;
                details.privateResidentAvailable = privateCoverage === records.length;
                if (details.privateResidentAvailable) {
                    for (const pair of [["PRIVATE RESIDENT","resident"],["PRIVATE CLEAN","clean"]]) {
                        const values = privateValues.map(row=>row[pair[1]]);
                        const firstValue=values[0], lastValue=values[values.length-1];
                        details.rows.push({label:pair[0],first:firstValue,peak:Math.max(...values),
                            last:lastValue,change:values.length>1?lastValue-firstValue:null});
                    }
                }
            }
            if (includeHost) {
                // Optional host presentation must never invalidate process evidence.
                try { details.hostContext = hostBreakdown(records); }
                catch (_) { details.hostContext = null; }
            }
            return details;
        } catch (_) { return null; }
    }
    // Optional additive observations; malformed host context does not erase
    // the independently validated process capture. No second collector.
    function hostBreakdown(records) {
        if (!records.length) return null;
        const keys=["MemTotal","MemAvailable","MemFree","AnonPages","Cached","Shmem",
            "SReclaimable","SUnreclaim","SwapTotal","SwapFree"];
        const count=v=>Number.isSafeInteger(v)&&v>=0;
        const valid=v=>!!v&&keys.every(k=>count(v[k]))&&v.MemTotal>0
            &&v.MemAvailable<=v.MemTotal&&v.MemFree<=v.MemTotal&&v.SwapFree<=v.SwapTotal;
        const pairs=records.map(r=>{
            const h=r.hostObservation;
            return h&&typeof h.spanMs==="number"&&Number.isFinite(h.spanMs)&&h.spanMs>=0
                &&valid(h.beforeKiB)&&valid(h.afterKiB)&&h.beforeKiB.MemTotal===h.afterKiB.MemTotal?h:null;
        });
        const observed=pairs.filter(Boolean);
        const result={paired:observed.length,samples:records.length,minimum:null,maxSpan:null,
            complete:false,total:null,start:null,final:null,delta:null,pssDelta:null};
        if (!observed.length) return result;
        // Use bounded iteration rather than Array.flatMap, which is not
        // guaranteed in the deployed QML JavaScript runtime.
        const total=observed[0].beforeKiB.MemTotal;
        let minimum=Infinity, maxSpan=0, sameCapacity=true;
        for (const h of observed) {
            minimum=Math.min(minimum,h.beforeKiB.MemAvailable,h.afterKiB.MemAvailable);
            maxSpan=Math.max(maxSpan,h.spanMs);
            if(h.beforeKiB.MemTotal!==total||h.afterKiB.MemTotal!==total)sameCapacity=false;
        }
        result.minimum=minimum;
        result.maxSpan=maxSpan;
        result.complete=observed.length===records.length&&sameCapacity;
        if (result.complete) {
            result.total=total;
            result.start=pairs[0].beforeKiB.MemAvailable;
            result.final=pairs[pairs.length-1].afterKiB.MemAvailable;
            if(records.length>1){
                result.delta=result.final-result.start;
                result.pssDelta=records[records.length-1].memoryKiB.Pss-records[0].memoryKiB.Pss;
            }
        }
        return result;
    }
    function hostMiB(v,delta=false) {
        return v===null?"N/A":(delta&&v>0?"+":"")+(v/1024).toFixed(1)+" MiB";
    }

    function comparisonLabel(row) {
        return row ? row.kind.toUpperCase() + " // " + row.finishedAt.slice(0, 19).replace("T", " ") + " UTC" : "NOT SELECTED / NO LONGER RETAINED";
    }
    function valueLabel(value, digits, unit, delta) {
        if (value === null) return "N/A";
        return (delta && value > 0 ? "+" : "") + value.toFixed(digits)
            + (unit ? " " + (delta && unit === "%" ? "pp" : unit) : "");
    }

    Column {
        parent: root.headerTarget || root
        objectName: "cpuplusDiagTopControls"
        width: parent.width
        spacing: 3
        GohuText {
            width: parent.width
            text: CpuPlusDiagnostics.feedback
            color: CpuPlusDiagnostics.busy || CpuPlusDiagnostics.faulted ? Colors.orange : Colors.cyan
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        ActionButton {
            width: parent.width
            height: 26
            visible: CpuPlusDiagnostics.busy && (root.viewMode !== "WORK"
                || CpuPlusDiagnostics.captureId !== CpuPlusDiagnostics.workshopRunId) && root.viewMode !== "QUICK"
            available: !CpuPlusDiagnostics.cancelled
            accentColor: Colors.red
            destructive: true
            label: CpuPlusDiagnostics.cancelled ? "STOPPING" : "STOP ACTIVE CAPTURE"
            onLeftClicked: CpuPlusDiagnostics.cancel()
        }
        Grid {
            id: captureGrid
            visible: root.viewMode === "QUICK"
            width: parent.width
            columns: 2
            spacing: 3
            Repeater {
            model: [
                {kind: "memory", label: "MEMORY OBSERVE // 120s"},
                {kind: "inventory", label: "SOURCE WORKLOAD SCAN"},
                {kind: "threads", label: "THREAD SAMPLE // 30s"},
                {kind: "census", label: "PROCESS CENSUS // 30s"},
                {kind: "storage", label: "STORAGE OBSERVE // 30s"},
                {kind: "appcontrol", label: "APPCONTROL // TEST 30s"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(0,(captureGrid.width-captureGrid.spacing)/2)
                height: 26
                label: modelData.label
                labelPixelSize: 10
                labelFontSizeMode: Text.HorizontalFit
                labelMinimumPixelSize: 8
                contentPadding: 2
                available: !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.faulted && !CpuPlusDiagnostics.archiveBusy
                onLeftClicked: {
                    if (CpuPlusDiagnostics.request(modelData.kind)) {
                        root.showReport = false;
                    }
                }
            }
        }
        ActionButton {
            objectName: "cpuplusDiagCancel"
            width: Math.max(0,(captureGrid.width-captureGrid.spacing)/2)
            height: 26
            accentColor: Colors.red
            contentPadding: 2
            available: CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.cancelled
            label: CpuPlusDiagnostics.busy && CpuPlusDiagnostics.cancelled ? "STOPPING" : "CANCEL"
            onLeftClicked: CpuPlusDiagnostics.cancel()
        }
        }
    }
    Loader {
        width: parent.width
        height: active && item ? item.implicitHeight : 0
        active: root.workshopOpen
        visible: active
        sourceComponent: CpuPlusDiagnosticWorkshop { viewportHeight: root.workshopViewportHeight }
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "QUICK"
        text: "Close this menu and reproduce the issue, then return here. APPCONTROL TEST: open AppControl, spend time in APP and KILL, then close it; no process actions needed. CPU sampling runs outside Quickshell; opening markers run inside it. CANCEL stops early without a verified comparison. Memory/thread targets are the newest same-user Quickshell; verify the reported PID. Source scan is not a live census. Process census reads same-user CPU, RSS and storage I/O; Storage observe checks fixed file metadata only; not writer identity, SQL activity or bytes written. GPU is not measured."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "REPORT"
        text: root.report ? root.report.status + " // " + root.report.finishedAt
            + "\n" + root.report.summary : "NO CAPTURE SELECTED"
        color: root.report && root.report.status === "COMPLETE" ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    Column {
        id: memoryInstrument
        objectName: "cpuplusMemoryBreakdown"
        width: parent.width
        spacing: 4
        visible: root.viewMode === "REPORT" && root.selectedReport === "memory" && root.report !== null
        GohuText {
            width: parent.width
            text: "QUICKSHELL // CAPTURE BREAKDOWN"
            color: Colors.magenta
            font.pixelSize: 11
        }
        GohuText {
            width: parent.width
            text: root.memoryDetails
                ? "PID " + root.memoryDetails.pid + " // " + root.memoryDetails.samples
                    + " SAMPLES // " + (root.memoryDetails.durationMs / 1000).toFixed(1) + " s"
                : "COMPLETE MEMORY BREAKDOWN UNAVAILABLE"
            color: root.memoryDetails ? Colors.cyan : Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        ActionButton {
            objectName: "cpuplusDiagHostToggle"
            width: parent.width
            height: 28
            label: root.showHostDetails ? "HOST RAM // HIDE" : "HOST RAM // SHOW"
            selected: root.showHostDetails
            available: root.memoryDetails!==null
            onLeftClicked: root.showHostDetails=!root.showHostDetails
        }
        Column {
            objectName: "cpuplusDiagHostInstrument"
            width: parent.width
            visible: root.showHostDetails && root.memoryDetails!==null
            spacing: 3
            GohuText {
                width: parent.width
                text: "HOST AVAILABLE RAM // HISTORICAL"
                color: Colors.magenta
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: root.hostDetails ? root.hostDetails.paired+"/"+root.hostDetails.samples+" PAIRED SAMPLES"
                    : "HOST CONTEXT UNAVAILABLE"
                color: root.hostDetails && root.hostDetails.complete ? Colors.cyan : Colors.orange
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: root.hostDetails ? "MIN OBSERVED // "+root.hostMiB(root.hostDetails.minimum)
                    +"\nMAX BRACKET // "+(root.hostDetails.maxSpan===null?"N/A":root.hostDetails.maxSpan.toFixed(1)+" ms") : ""
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            Repeater {
                model: root.hostDetails && root.hostDetails.complete
                    ? [{label:"START",value:root.hostDetails.start},{label:"FINAL",value:root.hostDetails.final}] : []
                delegate: Column {
                    required property var modelData
                    width: parent.width
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: modelData.label+" // "+root.hostMiB(modelData.value)
                        color: Colors.cyan
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    Rectangle {
                        width: parent.width
                        height: 10
                        color: Colors.black
                        border.color: Colors.cyan
                        Rectangle {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 1
                            width: Math.max(0,parent.width-2)*Math.min(1,modelData.value/root.hostDetails.total)
                            height: parent.height-2
                            color: Colors.cyan
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: root.hostDetails && root.hostDetails.complete
                    ? "HOST CHANGE // "+root.hostMiB(root.hostDetails.delta,true)
                        +"\nQUICKSHELL PSS CHANGE // "+root.hostMiB(root.hostDetails.pssDelta,true)
                    : "HOST TREND // INCOMPLETE OR CHANGED CAPACITY"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "OBSERVED SAMPLES ONLY // CORRELATION, NOT CAUSE"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
        }
        Repeater {
            model: root.memoryDetails ? root.memoryDetails.rows : []
            delegate: Rectangle {
                required property var modelData
                width: memoryInstrument.width
                height: detailBody.implicitHeight + 8
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: detailBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 4
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: modelData.label + " // " + (modelData.last / 1048576).toFixed(3) + " GiB"
                        color: Colors.cyan
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "START " + (modelData.first / 1048576).toFixed(3)
                            + " / PEAK " + (modelData.peak / 1048576).toFixed(3) + " GiB"
                            + "\nCHANGE // " + (modelData.change === null ? "N/A"
                                : (modelData.change > 0 ? "+" : "") + (modelData.change / 1024).toFixed(1) + " MiB")
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            visible: root.memoryDetails !== null
            text: root.memoryDetails ? "FINAL PSS // ANON " + (root.memoryDetails.anon / 1048576).toFixed(3)
                + " / FILE " + (root.memoryDetails.file / 1048576).toFixed(3)
                + " / SHMEM " + (root.memoryDetails.shmem / 1048576).toFixed(3) + " GiB" : ""
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: root.memoryDetails && root.memoryDetails.privateResidentAvailable
                ? "PRIVATE RESIDENT // CLEAN + DIRTY (EXCLUDES SEPARATELY ACCOUNTED HUGETLB)"
                : "PRIVATE RESIDENT // UNAVAILABLE IN THIS CAPTURE"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "HISTORICAL CAPTURE // NOT LIVE\nRSS includes shared pages; PSS apportions shared pages. Private dirty is not total private memory. GPU memory and component attribution are unavailable. Growth alone does not prove a leak."
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
    }
    TextEdit {
        id: reportText
        width: parent.width
        visible: root.viewMode === "REPORT" && root.showReport && root.report !== null
        height: visible ? implicitHeight : 0
        text: visible && root.report ? root.report.text : ""
        readOnly: true
        selectByMouse: true
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.Wrap
        color: Colors.white
        font.pixelSize: 10
        font.family: "monospace"
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "HISTORY" || root.viewMode === "COMPARE"
        text: "LOCAL ARCHIVE // " + CpuPlusDiagnostics.archiveStatus
        color: CpuPlusDiagnostics.archiveStatus === "READY" ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.showHistory ? CpuPlusDiagnostics.archiveRows : []
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 30
            label: modelData.kind.toUpperCase() + " // " + modelData.finishedAt.slice(5, 16)
            labelPixelSize: 9
            selected: root.report !== null && root.report.id === modelData.id
            onLeftClicked: {
                if (CpuPlusDiagnostics.selectExactReport(modelData.kind, modelData.id, false)) {
                    root.showReport = false;
                    if (root.viewMode === "HISTORY") root.selectView("REPORT");
                }
            }
        }
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "COMPARE"
        text: "COMPARE // SELECT A COMPLETED ARCHIVE REPORT"
        color: Colors.magenta
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "COMPARE"
        text: "BEFORE // " + root.comparisonLabel(root.beforeRecord)
            + "\nAFTER // " + root.comparisonLabel(root.afterRecord)
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    GohuText {
        width: parent.width
        visible: root.showComparison && root.comparison !== null && root.comparison.error !== ""
        text: visible ? root.comparison.error : ""
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.comparison ? root.comparison.rows : []
        delegate: Column {
            required property var modelData
            width: root.width
            spacing: 2
            GohuText {
                width: parent.width
                text: modelData.label
                color: Colors.magenta
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "B " + root.valueLabel(modelData.before, modelData.digits, modelData.unit, false)
                    + "  /  A " + root.valueLabel(modelData.after, modelData.digits, modelData.unit, false)
                    + "\nCHANGE // " + root.valueLabel(modelData.delta, modelData.digits, modelData.unit, true)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
        }
    }
    GohuText {
        width: parent.width
        visible: root.comparison !== null && root.comparison.note !== ""
        text: visible ? root.comparison.note : ""
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Column {
        parent: root.footerTarget || root
        objectName: "cpuplusDiagBottomControls"
        width: parent.width
        spacing: 3
        Row {
            id: diagnosticIndex
            width: parent.width
            spacing: 3
            Repeater {
                model: [{key:"WORK",label:"WORK"},{key:"QUICK",label:"QUICK"},
                        {key:"REPORT",label:"REPORT"},{key:"HISTORY",label:"HIST"},
                        {key:"COMPARE",label:"CMP"}]
                ActionButton {
                    id: diagnosticViewFilter
                    objectName: "cpuplusDiagnosticView-"+modelData.key
                    required property var modelData
                    width: Math.max(0,Math.floor((diagnosticIndex.width-12)/5))
                    height: 25
                    label: modelData.label
                    accentColor: Colors.cyan
                    labelPixelSize: 10
                    labelFontSizeMode: Text.HorizontalFit
                    contentPadding: 1
                    selected: root.viewMode===modelData.key
                    selectedBorderColor: Colors.magenta
                    selectedForegroundColor: Colors.magenta
                    normalFace: true
                    acceptedButtons: Qt.LeftButton
                    onLeftClicked: root.selectView(modelData.key)
                }
            }
        }
        Row {
            id: reportRail
            visible: root.viewMode === "REPORT"
            width: parent.width
            spacing: 3
            Repeater {
                model: ["memory", "inventory", "threads", "census", "storage", "appcontrol", "workflow", "stall"]
                delegate: ActionButton {
                    required property string modelData
                    width: Math.max(0, Math.floor((reportRail.width - 21) / 8))
                    height: 27
                    label: modelData === "inventory" ? "SCAN" : modelData === "memory" ? "MEM" : modelData === "threads" ? "THREAD" : modelData === "census" ? "CENSUS" : modelData === "appcontrol" ? "APP" : modelData === "workflow" ? "WORK" : modelData === "stall" ? "STALL" : "STORE"
                    labelPixelSize: 9
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    contentPadding: 2
                    selected: root.selectedReport === modelData
                    onLeftClicked: {
                        CpuPlusDiagnostics.selectLatest(modelData);
                        root.showReport = false;
                    }
                }
            }
        }
        Row {
            id: reportActions
            visible: root.viewMode === "REPORT"
            width: parent.width
            spacing: 3
            ActionButton {
                width: Math.max(0,(reportActions.width-reportActions.spacing)/2)
                height: 26
                available: root.report !== null && root.report.text.length > 0
                label: root.showReport ? "HIDE REPORT" : "VIEW REPORT"
                onLeftClicked: root.showReport = !root.showReport
            }
            ActionButton {
                width: Math.max(0,(reportActions.width-reportActions.spacing)/2)
                height: 26
                available: root.showReport && root.report !== null && root.report.text.length > 0
                label: "COPY REPORT"
                onLeftClicked: {
                    reportText.selectAll();
                    reportText.copy();
                    reportText.deselect();
                }
            }
        }
        Row {
            id: historyActions
            visible: root.viewMode === "HISTORY" || root.viewMode === "COMPARE"
            width: parent.width
            spacing: 3
            ActionButton {
                width: Math.max(0,(historyActions.width-historyActions.spacing)/2)
                height: 26
                label: "RELOAD ARCHIVE"
                available: !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.archiveBusy
                onLeftClicked: CpuPlusDiagnostics.loadHistory()
            }
            ActionButton {
                width: Math.max(0,(historyActions.width-historyActions.spacing)/2)
                height: 26
                label: root.viewMode === "COMPARE" ? "HISTORY" : "COMPARE"
                labelFontSizeMode: Text.HorizontalFit
                labelMinimumPixelSize: 8
                contentPadding: 2
                available: true
                onLeftClicked: root.selectView(root.viewMode === "COMPARE" ? "HISTORY" : "COMPARE")
            }
        }
        Row {
            id: compareRail
            visible: root.viewMode === "COMPARE"
            width: parent.width
            spacing: 4
            ActionButton {
                width: Math.max(0, (compareRail.width - 4) / 2)
                height: 26
                label: "SET BEFORE"
                available: root.canChooseComparison
                onLeftClicked: CpuPlusDiagnostics.selectComparison("before", root.report.id)
            }
            ActionButton {
                width: Math.max(0, (compareRail.width - 4) / 2)
                height: 26
                label: "SET AFTER"
                available: root.canChooseComparison
                onLeftClicked: CpuPlusDiagnostics.selectComparison("after", root.report.id)
            }
        }
    }
    GohuText {
        width: parent.width
        visible: root.viewMode === "HISTORY"
        text: "Last 8 terminal captures saved locally; oldest replaced on the next save. Session captures remain available if archive write fails. No automatic uploads or privileged actions."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
