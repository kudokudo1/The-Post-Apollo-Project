import QtQuick
import Quickshell.Io
import qs.services.memory
import qs.services.diagnostics
import "../../components"
import "CpuPlusMemorySnapshot.js" as Snapshot
import "CpuPlusMemoryReadout.js" as Readout
import "CpuPlusProfilePreview.js" as Profiles
import "CpuPlusProfileCatalog.js" as Catalog

// Demand-loaded by SYSTEM memory/swap selection. No privileged operations.
Item {
    id: root
    // Borrowed session: this view does not own its lifecycle or launch paths.
    property var recoverySession: null
    // Only the DIAG instrument scope changes; capacity and policy stay shared.
    property string diagnosticSubject: "MEMORY"
    readonly property bool diagnosticInfoOpen: memoryDiagnosticInfo.hovered && root.page==="DIAG"
    property var sample: null
    property var lastGoodSample: null
    readonly property var displaySample: lastGoodSample
    readonly property var displayCapacity: Snapshot.capacityPlan(displaySample,stagedGiB)
    property string scanMode: "LIVE"
    readonly property bool scanLive: scanMode==="LIVE"
    property int pausedRemainingMs: 0
    property int scanDelayMs: scanIntervalSeconds*1000
    property int scanIntervalSeconds: 10
    property bool scanDiagnosticsOpen: false
    property double scanClockMs: Date.now()
    property double scanLastSuccessMs: 0
    property double scanNextMs: 0
    property var scanRows: []
    property var pendingReport: null
    property string scanReason: "No completed attempt"
    readonly property string scanBadge: status==="READING" ? (lastGoodSample?"RESCANNING":"SCANNING") : !scanLive ? (scanMode==="STOPPED"?"MANUAL":"PAUSED") : status==="OBSERVED" ? "LIVE // "+Math.max(0,Math.ceil((scanNextMs-scanClockMs)/1000))+"s" : lastGoodSample ? "STALE // "+Math.max(0,Math.ceil((scanNextMs-scanClockMs)/1000))+"s" : "UNAVAILABLE"
    function scheduleScan(delay) {
        scanTimer.stop();
        scanClockMs=Date.now();
        scanDelayMs=Number.isFinite(delay)?Math.max(1,Math.min(scanIntervalSeconds*1000,delay)):scanIntervalSeconds*1000;
        scanNextMs=scanLive ? scanClockMs+scanDelayMs : 0;
        if(scanLive&&visible&&status!=="READING")scanTimer.start();
    }
    function setScanMode(value) {
        if(!["LIVE","PAUSED","STOPPED"].includes(value)||scanMode===value)return;
        const previous=scanMode;
        if(value==="PAUSED")pausedRemainingMs=scanNextMs>0?Math.max(0,scanNextMs-Date.now()):scanIntervalSeconds*1000;
        if(value==="STOPPED")pausedRemainingMs=0;
        scanMode=value;
        if(!scanLive){sample=null;clearCapConfirmation();scheduleScan();return;}
        if(status==="READING")return;
        if(previous==="PAUSED"&&pausedRemainingMs>0)scheduleScan(pausedRemainingMs);
        else refresh();
    }
    function setScanLive(value) { setScanMode(value?"LIVE":"PAUSED"); }
    function setScanInterval(value) {
        if(!Number.isInteger(value)||value<5||value>60||value%5!==0||value===scanIntervalSeconds)return;
        scanIntervalSeconds=value;
        if(scanMode==="PAUSED")pausedRemainingMs=value*1000;
        scheduleScan();
    }
    property string status: "READING"
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property var pendingSample: null
    function finish() {
        if (!received || !exited) return;
        scanRows=pendingReport ? pendingReport.rows : Snapshot.scanReport("").rows;
        scanReason=exitOk&&pendingReport?pendingReport.reason:"Scanner exited unsuccessfully; snapshot not published";
        const result=exitOk?pendingSample:null;
        if(result){lastGoodSample=result;scanLastSuccessMs=Date.now();}
        sample = scanLive ? result : null;
        status = result ? "OBSERVED" : "UNAVAILABLE";
        scheduleScan();
    }
    // Draft belongs to this memory pane, not the demand-loaded PROF subpage.
    property string selectedProfile: ""
    property var customProfileDraft: Catalog.empty()
    CpuPlusProfileCatalogStore { id: profileCatalog }
    function loadProfileDraft(name) {
        if(page!=="PROF" || !profileCatalog.ready) return;
        const row=profileCatalog.document.profiles.find(x=>x.name===name);
        if(!row || !Catalog.validDraft(row.targets)) return;
        customProfileDraft=Catalog.copyTargets(row.targets,"post-apollo-cpuplus-profiles-v2");
        selectedProfile="CUSTOM";
    }
    function chooseProfile(name) {
        if (page === "PROF" && Profiles.names().includes(name)) selectedProfile = name;
    }
    function captureProfileTarget(key) {
        if (page !== "PROF" || selectedProfile !== "CUSTOM" || !sample || status !== "OBSERVED" || MemoryOperation.busy) return;
        if (key === "capacityGiB" && !capacity) return;
        if (key === "swappiness" && !Profiles.policy(sample.swappiness)) return;
        if (!["capacityGiB","swappiness"].includes(key)) return;
        const next = Catalog.capture(customProfileDraft,key,key === "capacityGiB" ? stagedGiB : stagedSwappiness);
        if (next) customProfileDraft = next;
    }
    function clearProfileDraft() {
        if (page === "PROF" && selectedProfile === "CUSTOM") customProfileDraft = Catalog.empty();
    }
    // Copies are explicit, historical preview data, not re-observed authority.
    function copyPriorityProfile() {
        if(page!=="POL"||policySection!==1||MemoryOperation.busy||status!=="OBSERVED")return;
        const row=matchingPriorityRow(priorityBaseline,priorityObservations(sample));
        if(!row||stagedPriority<0)return;
        const next=Catalog.capture(customProfileDraft,"priority",{deviceHint:row.name,sizeKiB:row.size,value:stagedPriority});
        if(next)customProfileDraft=next;
    }
    function copyZramProfile(value) {
        if(page!=="POL"||policySection!==2||MemoryOperation.busy||status!=="OBSERVED"||!value)return;
        if(!priorityObservations(sample).some(x=>x.name===value.deviceHint&&x.size===value.sizeKiB))return;
        const next=Catalog.capture(customProfileDraft,"zram",value);
        if(next)customProfileDraft=next;
    }
    function copyAdvancedProfile(key,unit,value) {
        if(page!=="POL"||policySection!==3||MemoryOperation.busy)return;
        const next=Catalog.captureAdvanced(customProfileDraft,key,unit,value);
        if(next)customProfileDraft=next;
    }
    property int stagedGiB: 16
    property bool initializedTarget: false
    readonly property var capacity: Snapshot.capacityPlan(sample, stagedGiB)
    function adoptActual() {
        if (!sample || initializedTarget) return;
        const plan = Snapshot.capacityPlan(sample, stagedGiB);
        if (!plan) return;
        if (plan.active) stagedGiB = Math.max(4, Math.min(64, Math.round(plan.actualGiB / 4) * 4));
        initializedTarget = true;
    }
    property int stagedSwappiness: -1
    property int policySection: 0 // SWAPPINESS / PRIORITY / ZRAM / ADV
    property var priorityBaseline: null
    property int stagedPriority: -1 // no explicit target for kernel-assigned priorities
    readonly property var priorityRows: priorityObservations(sample)
    readonly property var priorityRow: matchingPriorityRow(priorityBaseline, priorityRows)
    readonly property bool priorityEditable: page === "POL" && policySection === 1
        && priorityRow !== null && !MemoryOperation.busy

    function priorityObservations(observation) {
        if (!observation || !Array.isArray(observation.rows)) return [];
        const rows = [];
        for (const row of observation.rows) {
            if (!row || typeof row.name !== "string" || !row.name.length
                || !Number.isSafeInteger(row.size) || row.size <= 0
                || !Number.isSafeInteger(row.used) || row.used < 0 || row.used > row.size
                || !Number.isSafeInteger(row.priority) || row.priority < -32768 || row.priority > 32767
                || rows.some(entry => entry.name === row.name)) return [];
            rows.push(row);
        }
        return rows;
    }
    function matchingPriorityRow(baseline, rows) {
        if (!baseline) return null;
        return rows.find(row => row.name === baseline.name && row.size === baseline.size
            && row.priority === baseline.priority) || null;
    }
    function selectPolicySection(index) {
        if (page !== "POL" || (!Number.isInteger(index) || index < 0 || index > 3) || index === policySection) return;
        policySection = index;
        scroll.contentY = 0;
    }
    function selectPriorityDevice(name) {
        if (page !== "POL" || policySection !== 1 || !sample || MemoryOperation.busy) return;
        const row = priorityObservations(sample).find(entry => entry.name === name);
        if (!row) return;
        if (matchingPriorityRow(priorityBaseline, [row])) return;
        priorityBaseline = {name:row.name, size:row.size, priority:row.priority};
        stagedPriority = row.priority >= 0 ? row.priority : -1;
    }
    function reconcilePriority() {
        // A transient refresh does not erase a preview. A completed observation
        // that no longer matches its baseline invalidates it. This is not
        // protected device identity or permission to act.
        if (priorityBaseline && sample
                && !matchingPriorityRow(priorityBaseline, priorityObservations(sample))) {
            priorityBaseline = null;
            stagedPriority = -1;
        }
    }
    function stagePriority(value) {
        if (page !== "POL" || policySection !== 1 || !sample || MemoryOperation.busy
            || !matchingPriorityRow(priorityBaseline, priorityObservations(sample))
            || !Number.isInteger(value) || value < 0 || value > 32767) return;
        stagedPriority = value;
    }
    function resetPriority() {
        if (page !== "POL" || policySection !== 1 || !sample || MemoryOperation.busy) return;
        const row = matchingPriorityRow(priorityBaseline, priorityObservations(sample));
        if (row) stagedPriority = row.priority >= 0 ? row.priority : -1;
    }
    function priorityName(row) {
        if (row.name === "/var/lib/post-apollo-memory-swap/swapfile") return "BASE NVMe";
        if (row.name === "/var/lib/post-apollo-memory-extension/swapfile") return "EXTENSION";
        return row.name;
    }
    function stageCapacity(value) {
        if (page !== "CAP" || capSection !== 0 || !capacity || MemoryOperation.busy
                || !Number.isInteger(value) || value < 0 || value > 64 || value % 4 !== 0)
            return;
        stagedGiB = value;
    }
    function stagePolicy(value) {
        if (page !== "POL" || policySection !== 0 || !sample || MemoryOperation.busy
                || !Number.isInteger(value) || value < 0 || value > 200)
            return;
        stagedSwappiness = value;
    }
    onSampleChanged: {
        if(sample)lastGoodSample=sample;
        adoptActual();
        reconcilePriority();
        if (sample && stagedSwappiness < 0)
            stagedSwappiness = sample.swappiness;
    }
    function gib(kib) { return (kib / 1048576).toFixed(2) + " GiB"; }
    function refresh() {
        if (probe.running || (status === "READING" && (received || exited))) return;
        received = false;
        exited = false;
        exitOk = false;
        pendingSample = null;
        pendingReport = null;
        sample = null; // invalidate operation input, not the retained display
        clearCapConfirmation();
        scanTimer.stop();
        scanNextMs=0;
        status = "READING";
        probe.running = true;
    }
    Component.onCompleted: refresh()
    onVisibleChanged: { if(visible&&scanLive&&status!=="READING")refresh(); else if(!visible)scanTimer.stop(); }
    Connections {
        target: MemoryOperation
        function onRevisionChanged() { root.sample=null; if(root.scanLive)root.refresh(); }
    }
    Timer {
        id: scanTimer
        interval: root.scanDelayMs
        repeat: false
        onTriggered: if(root.scanLive&&root.visible)root.refresh()
    }
    Timer {
        interval: 1000
        repeat: true
        running: root.visible
        onTriggered: root.scanClockMs=Date.now()
    }
    Process {
        id: probe
        running: false
        command: ["/usr/bin/python3", "-I", "-B", "-c", "import json\npaths=(\"/proc/meminfo\",\"/proc/swaps\",\"/proc/pressure/memory\",\"/proc/sys/vm/swappiness\")\nout=[]\nfor path in paths:\n    try:\n        with open(path,\"rb\") as f:\n            data=f.read(65537)\n        if len(data)>65536:\n            raise ValueError(\"limit\")\n        out.append(dict(path=path,ok=True,text=data.decode(\"ascii\"),error=\"\"))\n    except (OSError,ValueError) as exc:\n        out.append(dict(path=path,ok=False,text=\"\",error=type(exc).__name__+((\" errno=\"+str(exc.errno)) if isinstance(exc,OSError) else \"\")))\nprint(json.dumps(out,separators=(\",\",\":\")))"]
        stdout: StdioCollector {
            onStreamFinished: {
                root.pendingReport = Snapshot.scanReport(this.text);
                root.pendingSample = root.pendingReport.sample;
                root.received = true;
                root.finish();
            }
        }
        onExited: function(code, exitStatus) {
            root.exited = true;
            root.exitOk = code === 0 && exitStatus === 0;
            root.finish();
        }
    }
    // Page selection is presentation only. Keep the existing snapshot, target
    // and operation owner alive across submenus; never start a second poller.
    readonly property var menus: ["CAP", "POL", "PROC", "AUTO", "DIAG", "PROF"]
    readonly property var menuTitles: [
        "CAPACITY", "MEMORY BEHAVIOR", "PROCESS MANAGEMENT",
        "AUTOMATION & SAFETY", "DIAGNOSTICS", "PROFILES"
    ]
    property int capSection: 0 // TARGET / ACTIONS / DETAILS
    property string capDetailSubject: "SWAP"
    property bool detailsInfoOpen: false
    property int infoSizeLevel: 1
    property bool headerRefreshAvailable: false
    readonly property bool refreshBusy: probe.running
    readonly property real detailScale: Math.max(1,Math.min(2, root.height/620, root.width/320))
    readonly property int detailMeterHeight: Math.max(12, Math.round(12*detailScale))
    readonly property bool capDetailsActive: page==="CAP" && capSection===2
    readonly property var ramDetailRows: Snapshot.ramDetailRows(displaySample)
    // Operator-approved RAM dataset identities. Component identity remains
    // magenta; do not change the shared theme for a local dataset.
    // Match the established resize-arrow purple locally; shared theme is unchanged.
    readonly property color ramAnonymousPurple: "#a46aff"
    function ramDatasetColor(label) {
        switch(label) {
        case "AVAILABLE": return Colors.omnitrix;
        case "FREE": return Colors.green;
        case "ANONYMOUS": return ramAnonymousPurple;
        case "FILE CACHE": return Colors.blue;
        case "SHARED / TMPFS": return Colors.magenta;
        case "RECLAIMABLE SLAB": return Colors.yellow;
        case "UNRECLAIMABLE SLAB": return Colors.white;
        default: return Colors.cyan;
        }
    }
    function ramDatasetGlow(label) {
        const ink=ramDatasetColor(label);
        return ink===Colors.white?Colors.cyan:ink;
    }
    function ramDetailText(row) {
        // Only fixed labels and validated numeric observations reach rich text.
        const ink=ramDatasetColor(row.label), white=Colors.white;
        const token=(value,color)=>'<font color="'+color+'">'+value+'</font>';
        const label=Readout.format(row.label,ink,white)+token(" // ",white);
        if(row.value===null)return label+token("UNAVAILABLE",Colors.orange);
        const parts=(row.value/1048576).toFixed(2).split(".");
        return label+token(parts[0],ink)+token(".",white)+token(parts[1],ink)+token(" GiB",white);
    }
    function selectCapDetailSubject(subject) {
        if(page!=="CAP"||capSection!==2||!["RAM","SWAP"].includes(subject))return;
        capDetailSubject=subject;
        detailsInfoOpen=false;
        scroll.contentY=0;
    }
    readonly property int menuIndex: CpuPlusDiagnostics.memoryMenuIndex
    readonly property string page: menus[menuIndex]
    function clearCapConfirmation() {
        addControl.armed = false;
        addControl.persistArmed = false;
        addControl.expandArmed = false;
    }
    function selectCapSection(index) {
        if (page !== "CAP" || index < 0 || index > 2 || index === capSection) return;
        clearCapConfirmation();
        capSection = index;
        detailsInfoOpen=false;
        scroll.contentY = 0;
    }
    function selectMenu(index) {
        if (index < 0 || index >= menus.length || index === menuIndex) return;
        // Hidden confirmation must not survive a trip to another page.
        // Do not cancel or repeat a request already owned by MemoryOperation.
        if (page === "CAP") {
            clearCapConfirmation();
            capSection = 0;
        }
        detailsInfoOpen=false;
        CpuPlusDiagnostics.memoryMenuIndex = index;
        scroll.contentY = 0;
    }

    Grid {
        id: menuRail
        objectName: "cpuplusMemoryMenuRail"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        columns: width >= 240 ? 6 : 3
        spacing: 4
        height: Math.ceil(root.menus.length / columns) * 28
                + (Math.ceil(root.menus.length / columns) - 1) * spacing
        Repeater {
            model: root.menus
            delegate: ActionButton {
                id: memoryModeFilter
                objectName: "cpuplusMemoryMode-"+modelData
                required property string modelData
                required property int index
                width: Math.max(0, Math.floor((menuRail.width
                       - (menuRail.columns - 1) * menuRail.spacing) / menuRail.columns))
                height: 28
                label: modelData
                contentPadding: 2
                selected: root.menuIndex === index
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                accentColor: Colors.cyan
                selectedForegroundColor: Colors.magenta
                selectedBorderColor: Colors.magenta
                contentGlowEnabled: true
                normalFace: true
                onLeftClicked: root.selectMenu(index)
            }
        }
    }
    // One literal CAP layout, shared by both views. No additional observation.
    component LiveCapacityBars: Column {
        id: liveBars
        required property var sample
        required property var capacity
        required property var formatGiB
        spacing: 5
        CpuPlusMemoryReadout {
            width: parent.width
            text: liveBars.sample ? "RAM AVAIL // " + liveBars.formatGiB(liveBars.sample.available)
                + " / " + liveBars.formatGiB(liveBars.sample.total) : "RAM // UNAVAILABLE"
            color: Colors.cyan
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 24
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta
            clip: true
            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                color: Colors.cyan
                opacity: liveBars.sample ? 0.22 : 0
            }
            Rectangle {
                x: 3; y: 3
                height: Math.max(0, parent.height - 6)
                width: liveBars.sample && liveBars.sample.total > 0
                    ? Math.max(0, parent.width - 6) * liveBars.sample.available / liveBars.sample.total : 0
                color: Colors.cyan
                opacity: 0.85
            }
        }
        CpuPlusSwapComposition {
            width: parent.width
            sample: liveBars.sample
            capacity: liveBars.capacity
            compact: true
        }

    }
    // CAP is the reference. All memory/swap modes mount the same header
    // and divider, with identical margins, row height and bar composition.
    component LiveCapacityHeader: Column {
        id: sharedHeader
        required property var sample
        required property var capacity
        required property var formatGiB
        required property string badge
        required property bool showRefresh
        required property bool canRefresh
        property string refreshName: "cpuplusWorkRefresh"
        readonly property real dividerBottom: capacityDivider.y+capacityDivider.height
        signal refreshRequested()
        spacing: 5
        Row {
            objectName: "cpuplusSharedCapacityTitle"
            width: parent.width
            height: 25
            spacing: 5
            CpuPlusMemoryReadout {
                width: Math.max(0,parent.width-(sharedRefresh.visible ? sharedRefresh.width+parent.spacing : 0))
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "MEMORY // " + sharedHeader.badge
                color: sharedHeader.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            ActionButton {
                id: sharedRefresh
                objectName: sharedHeader.refreshName
                visible: sharedHeader.showRefresh
                accentColor: Colors.yellow
                idleFillColor: Colors.yellow
                idleForegroundColor: Colors.magenta
                idleBorderColor: Colors.orange
                width: 68
                height: parent.height
                label: "REFRESH"
                contentPadding: 2
                available: sharedHeader.canRefresh
                onLeftClicked: sharedHeader.refreshRequested()
            }
        }
        LiveCapacityBars {
            objectName: "cpuplusSharedLiveCapacityBars"
            width: parent.width
            sample: sharedHeader.sample
            capacity: sharedHeader.capacity
            formatGiB: sharedHeader.formatGiB
        }
        Rectangle {
            id: capacityDivider
            objectName: "cpuplusSharedCapacityDivider"
            width: parent.width
            height: 1
            color: Colors.cyan
        }
    }
    readonly property bool fixedWorkPage: ["PROC","AUTO","DIAG","PROF"].includes(root.page)
    Column {
        id: workHeader
        objectName: "cpuplusWorkHeader"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: menuRail.bottom
        anchors.leftMargin: 5
        anchors.rightMargin: 5
        anchors.topMargin: 6
        spacing: 5
        visible: root.page !== "CAP"
        height: visible ? implicitHeight : 0
        Row {
            width: parent.width
            visible: root.page==="DIAG" && root.diagnosticSubject!=="ALL"
            spacing: 4
            GohuText {
                width: Math.max(0,parent.width-28)
                height: 24
                verticalAlignment: Text.AlignVCenter
                text: root.diagnosticSubject+" // OBSERVATION"
                color: Colors.resourceColor(root.diagnosticSubject)
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            InformationButton {
                id: memoryDiagnosticInfo
                objectName: "cpuplusMemoryDiagnosticsInfo"
                selected: root.diagnosticInfoOpen
            }
        }
        LiveCapacityHeader {
            id: diagnosticCapacityHeader
            objectName: "cpuplusSharedCapacityHeader"
            width: parent.width
            sample: root.displaySample
            capacity: root.displayCapacity
            formatGiB: value => root.gib(value)
            badge: root.scanBadge
            showRefresh: !root.headerRefreshAvailable
            canRefresh: !probe.running && root.status !== "READING"
            onRefreshRequested: root.refresh()
        }
        Row {
            id: diagnosticHeaderBand
            objectName: "cpuplusDiagnosticHeaderBand"
            width: parent.width
            visible: root.page === "DIAG"
            spacing: 4
            readonly property int toolSize: root.diagnosticSubject==="ALL" ? Math.max(16,Math.min(36,Math.floor((width*0.57-12)/5))) : Math.ceil(diagnosticStatusBlock.implicitHeight)
            Column {
                id: diagnosticStatusBlock
                objectName: "cpuplusMemoryDiagnosticStatusBlock"
                width: Math.max(0,parent.width-(diagnosticFilterHost.visible ? diagnosticFilterHost.width+parent.spacing : 0))
                spacing: 1
                anchors.verticalCenter: parent.verticalCenter
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: CpuPlusDiagnostics.feedback
                    color: CpuPlusDiagnostics.busy || CpuPlusDiagnostics.faulted ? Colors.orange : Colors.cyan
                    font.pixelSize: 11
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                    elide: Text.ElideRight
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    color: Colors.yellow
                    font.pixelSize: 10
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                    text: root.displaySample ? "PSI 10s // "+root.displaySample.some.toFixed(2)+" / "+root.displaySample.full.toFixed(2)+"%" : "PSI // UNAVAILABLE"
                    elide: Text.ElideRight
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    visible: diagnosticFilterHost.visible
                    text: diagnosticPaneLoader.item ? diagnosticPaneLoader.item.workshopTargetText : ""
                    color: Colors.purple
                    font.pixelSize: 9
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                    elide: Text.ElideRight
                }
            }
            Item {
                id: diagnosticFilterHost
                objectName: "cpuplusDiagnosticFilterHost"
                visible: root.page === "DIAG" && !!diagnosticPaneLoader.item && diagnosticPaneLoader.item.workshopOpen
                width: visible ? (root.diagnosticSubject==="ALL" ? 5*diagnosticHeaderBand.toolSize+12 : diagnosticHeaderBand.toolSize) : 0
                height: visible ? diagnosticHeaderBand.toolSize : 0
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    Column {
        id: footer
        objectName: "cpuplusMemoryFooter"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 3
        Rectangle { width: parent.width; height: 1; color: Colors.cyan; visible: root.page!=="DIAG" || root.diagnosticSubject==="ALL" }
        CpuPlusMemoryReadout {
            width: parent.width
            visible: root.page !== "DIAG" || MemoryOperation.busy
            text: MemoryOperation.busy ? "OPERATION // IN PROGRESS"
                : "AUTH // EXPLICIT ONE-SHOT ONLY"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        CpuPlusMemoryReadout {
            width: parent.width
            visible: root.page !== "DIAG"
            text: "QUEUE // NOT CONNECTED"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Column {
            id: workFooter
            objectName: "cpuplusWorkFooter"
            width: parent.width
            spacing: 3
            visible: root.fixedWorkPage
            height: visible ? implicitHeight : 0
        }
        Row {
            id: capBottomRail
            objectName: "cpuplusCapBottomRail"
            visible: root.page === "CAP"
            height: visible ? 28 : 0
            width: parent.width
            spacing: 4
            Repeater {
                model: ["TARGET", "ACTIONS", "DETAILS"]
                delegate: ActionButton {
                    required property string modelData
                    required property int index
                    width: Math.max(0, (capBottomRail.width - 8) / 3)
                    height: 28
                    label: modelData
                    contentPadding: 2
                    selected: root.capSection === index
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.selectCapSection(index)
                }
            }
        }
        Row {
            id: policyBottomRail
            objectName: "cpuplusPolicyBottomRail"
            visible: root.page === "POL"
            height: visible ? 28 : 0
            width: parent.width
            spacing: 4
            Repeater {
                model: ["SWAPPINESS", "PRIORITY", "ZRAM", "ADV"]
                delegate: ActionButton {
                    required property string modelData
                    required property int index
                    width: Math.max(0, (policyBottomRail.width - 12) / 4)
                    height: 28
                    label: modelData
                    contentPadding: 2
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    selected: root.policySection === index
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.selectPolicySection(index)
                }
            }
        }
    }
    Column {
        id: capInstrument
        objectName: "cpuplusMemoryPinned"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: menuRail.bottom
        anchors.leftMargin: 5
        anchors.rightMargin: 5
        anchors.topMargin: 6
        visible: root.page === "CAP"
        height: visible ? implicitHeight : 0
        spacing: 5

        LiveCapacityHeader {
            objectName: "cpuplusSharedCapacityHeader"
            width: parent.width
            sample: root.displaySample
            capacity: root.displayCapacity
            formatGiB: value => root.gib(value)
            badge: root.scanBadge
            showRefresh: !root.headerRefreshAvailable
            canRefresh: !probe.running && root.status !== "READING"
            refreshName: "cpuplusCapRefresh"
            onRefreshRequested: root.refresh()
        }
        Grid {
            width: parent.width
            columns: 3
            spacing: 4
            Repeater {
                model: 3
                delegate: Rectangle {
                    required property int index
                    readonly property var modelData: index===0
                        ? {label:"ACTUAL DISK",value:root.displayCapacity?root.gib(root.displayCapacity.actualKiB):"—",accent:Colors.cyan}
                        : index===1 ? {label:"TARGET DISK",value:root.stagedGiB+" GiB",accent:Colors.yellow}
                        : {label:"TOTAL PLAN",value:root.displayCapacity?root.gib(root.displayCapacity.projectedKiB):"—",accent:Colors.yellow}
                    width: Math.max(0, (parent.width - 8) / 3)
                    height: 40
                    border.width: 1
                    border.color: modelData.accent
                    color: Colors.black
                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 2
                        CpuPlusMemoryReadout {
                            width: parent.width
                            text: modelData.label
                            color: Colors.white
                            font.pixelSize: 10
                            fontSizeMode: Text.HorizontalFit
                            minimumPixelSize: 8
                            horizontalAlignment: Text.AlignHCenter
                        }
                        CpuPlusMemoryReadout {
                            width: parent.width
                            text: modelData.value
                            color: modelData.accent
                            font.pixelSize: 13
                            fontSizeMode: Text.HorizontalFit
                            minimumPixelSize: 10
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }
        }
        Column {
            width: parent.width
            spacing: 4
            visible: root.capSection === 0
            enabled: visible
            CpuPlusMemoryCapacitySlider {
                id: capacitySelector
                objectName: "cpuplusCapacitySelector"
                width: parent.width
                currentValue: root.stagedGiB
                enabledSlider: root.page === "CAP" && root.capSection === 0
                    && root.capacity !== null && !MemoryOperation.busy
                onValueRequested: function(value) { root.stageCapacity(value); }
            }
            CpuPlusMemoryReadout {
                width: parent.width
                text: !root.displayCapacity ? "WAITING FOR LIVE CAPACITY"
                    : root.displayCapacity.direction === "unchanged" ? "TARGET MATCHES ACTIVE CAPACITY"
                    : root.displayCapacity.direction === "expand" && root.displayCapacity.baseActive && !root.displayCapacity.extensionActive
                        ? "EXPANSION // SEPARATE TEMPORARY SWAP"
                    : root.displayCapacity.active ? "PREVIEW ONLY // RESIZE NOT AVAILABLE YET"
                    : "TARGET // RESERVES DISK SPACE"
                color: Colors.white
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 28
                label: "RESET TARGET"
                available: root.capacity !== null && root.capacity.active && !MemoryOperation.busy
                    && root.capacity.direction !== "unchanged"
                onLeftClicked: root.stageCapacity(Math.max(4, Math.min(64, Math.round(root.capacity.actualGiB / 4) * 4)))
            }
        }
        Row {
            id: capDetailRail
            // Same mounting origin as slider, original 28px subject buttons.
            objectName: "cpuplusCapDetailRail"
            visible: root.capSection===2
            height: visible ? 28 : 0
            width: parent.width
            spacing: 4
            Repeater {
                model: ["RAM","SWAP"]
                delegate: ActionButton {
                    required property string modelData
                    objectName: modelData==="RAM"?"cpuplusCapDetailRam":"cpuplusCapDetailSwap"
                    width: Math.max(0,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: modelData
                    accentColor: modelData==="RAM"?Colors.magenta:Colors.yellow
                    selected: root.capDetailSubject===modelData
                    available: root.page==="CAP"&&root.capSection===2
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.selectCapDetailSubject(modelData)
                }
            }
        }
    }
    Flickable {
        id: scroll
        objectName: "cpuplusMemoryScroll"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: root.page === "CAP" ? capInstrument.bottom : workHeader.bottom
        anchors.bottom: footer.top
        visible: root.page !== "CAP" || root.capSection !== 0
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.implicitHeight + (root.capDetailsActive || root.page === "DIAG" ? 4 : 18))
        // Fixed instrument whenever it fits; preserve access if the operator shrinks it.
        interactive: (root.page !== "DIAG" && !root.capDetailsActive) || contentHeight > height + 1
        Column {
            id: body
            x: 5
            y: root.capDetailsActive || root.page === "DIAG" ? 2 : 8
            width: Math.max(0, scroll.width - 17)
            spacing: root.page === "DIAG" ? 2 : 10
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "PROC"
                visible: active
                sourceComponent: CpuPlusProcessPane { headerTarget: workHeader; footerTarget: workFooter }
            }
            Loader {
                id: diagnosticPaneLoader
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "DIAG"
                visible: active
                sourceComponent: CpuPlusDiagnosticsPane {
                    headerTarget: workHeader
                    footerTarget: workFooter
                    workshopViewportHeight: scroll.height
                    workshopSubject: root.diagnosticSubject
                    workshopFilterTarget: diagnosticFilterHost
                    onNavigationChanged: scroll.contentY=0
                }
            }
            Column {
                width: parent.width
                spacing: 6
                visible: root.page === "CAP" && root.capSection === 1
                enabled: visible
                CpuPlusMemoryAddControl {
                    id: addControl
                    width: parent.width
                    stagedGiB: root.stagedGiB
                    sample: root.sample
                }
            }
            Column {
                width: parent.width
                id: detailBody
                objectName: "cpuplusCapDetailsBody"
                spacing: 2
                visible: root.capDetailsActive
                Row {
                    width: parent.width
                    height: 22
                    spacing: 4
                    CpuPlusMemoryReadout {
                        width: Math.max(0,parent.width-infoButton.width-parent.spacing)
                        height: parent.height
                        text: "DETAILS // LIVE "+root.capDetailSubject
                        color: Colors.magenta
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                    }
                    ActionButton {
                        id: infoButton
                        objectName: "cpuplusCapDetailsInfo"
                        width: 24
                        height: parent.height
                        label: "i"
                        contentPadding: 2
                        accentColor: Colors.yellow
                        idleForegroundColor: Colors.white
                        hoverForegroundColor: Colors.white
                        selectedForegroundColor: Colors.magenta
                        idleContentGlowColor: Colors.yellow
                        hoverContentGlowColor: Colors.yellow
                        selectedContentGlowColor: Colors.magenta
                        contentGlowIdleOpacity: 0.85
                        selected: root.detailsInfoOpen
                        acceptedButtons: Qt.LeftButton
                        keyboardActivationSignal: "leftClicked"
                        onLeftClicked: root.detailsInfoOpen=!root.detailsInfoOpen
                    }
                }
                Column {
                    objectName: "cpuplusCapRamDetails"
                    width: parent.width
                    spacing: 2
                    visible: root.capDetailSubject==="RAM"
                    CpuPlusMemoryReadout {
                        width: parent.width
                        text: root.displaySample?"KERNEL USABLE RAM // "+root.gib(root.displaySample.total):"RAM SNAPSHOT UNAVAILABLE"
                        color: Colors.cyan
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                    Grid {
                        id: ramCardGrid
                        objectName: "cpuplusRamCardGrid"
                        width: parent.width
                        columns: width >= 440 ? 2 : 1
                        spacing: Math.round(2*root.detailScale)
                        Repeater {
                            model: root.page==="CAP"&&root.capSection===2&&root.capDetailSubject==="RAM"&&root.displaySample?7:0
                            delegate: Rectangle {
                                required property int index
                                readonly property var modelData: root.ramDetailRows[index]
                                objectName: "cpuplusRamMetricCard"
                                width: Math.max(0,(ramCardGrid.width-(ramCardGrid.columns-1)*ramCardGrid.spacing)/ramCardGrid.columns)
                                height: ramCardContent.implicitHeight
                                color: "transparent"
                                border.width: 0
                                Column {
                                    id: ramCardContent
                                    x: 0
                                    y: 0
                                    width: parent.width
                                    spacing: 1
                                    Item {
                                        width: parent.width
                                        height: ramMetricText.implicitHeight
                                        GohuText {
                                            id: ramMetricText
                                            objectName: "cpuplusRamMetricText"
                                            width: parent.width
                                            text: root.ramDetailText(modelData)
                                            textFormat: Text.RichText
                                            color: Colors.white
                                            font.pixelSize: Math.round(11*root.detailScale)
                                            wrapMode: Text.Wrap
                                        }
                                        // One existing safe effect per visible dataset.
                                        TextHashGlow {
                                            objectName: "cpuplusRamMetricGlow"
                                            safeSource: ramMetricText.visible ? ramMetricText : null
                                            requestedVisible: ramMetricText.visible
                                            foregroundColor: Colors.white
                                            preferredGlowColor: root.ramDatasetGlow(modelData.label)
                                            opacity: 0.95
                                        }
                                    }
                                    Rectangle {
                                        objectName: "cpuplusRamMetricBar"
                                        width: parent.width
                                        height: root.detailMeterHeight
                                        visible: modelData.fraction!==null
                                        color: Colors.black
                                        border.color: root.ramDatasetColor(modelData.label)
                                        Rectangle {
                                            anchors.left: parent.left
                                            objectName: "cpuplusRamMetricFill"
                                            anchors.leftMargin: 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: Math.max(0,parent.width-4)*(modelData.fraction===null?0:modelData.fraction)
                                            height: parent.height-4
                                            color: root.ramDatasetColor(modelData.label)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    CpuPlusMemoryReadout {
                        width: parent.width
                        text: root.displaySample?"PSI AVG10 // SOME "+root.displaySample.some+"% / FULL "+root.displaySample.full+"%":"PSI UNAVAILABLE"
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
                Repeater {
                    model: root.page === "CAP" && root.capSection === 2 && root.capDetailSubject==="SWAP" && root.displaySample ? root.displaySample.rows.length : 0
                    delegate: Rectangle {
                        required property int index
                        readonly property var modelData: root.displaySample.rows[index]
                        objectName: "cpuplusSwapDetailCard"
                        width: parent.width
                        height: swapCardContent.implicitHeight+10
                        color: Colors.black
                        border.color: Colors.yellow
                        Column {
                            id: swapCardContent
                            x: 5
                            y: 5
                            width: Math.max(0,parent.width-10)
                            spacing: 3
                            CpuPlusMemoryReadout {
                                width: parent.width
                                text: modelData.kind + " // " + modelData.name
                                color: Colors.yellow
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                            CpuPlusMemoryReadout {
                                width: parent.width
                                text: root.gib(modelData.used) + " / " + root.gib(modelData.size)
                                    + " // PRIORITY " + modelData.priority
                                color: Colors.yellow
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                visible: active
                active: root.page === "POL" && root.policySection === 0
                sourceComponent: Column {
                    spacing: 8
                    GohuText {
                        width: parent.width
                        text: "SWAPPINESS // 0–200"
                        color: Colors.magenta
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: root.sample ? "ACTUAL // " + root.sample.swappiness : "ACTUAL // UNAVAILABLE"
                        color: Colors.cyan
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: root.stagedSwappiness < 0 ? "TARGET // UNAVAILABLE" : "TARGET // " + root.stagedSwappiness
                        color: Colors.yellow
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    Row {
                        id: policyInstrument
                        objectName: "cpuplusPolicyInstrument"
                        width: parent.width
                        height: Math.max(policyDial.height, policyActions.implicitHeight)
                        spacing: 8
                        SelectorDial {
                            objectName: "cpuplusSwappinessDial"
                            id: policyDial
                            width: 136
                            height: 160
                            labelText: "SWAP"
                            selectorMode: "continuous"
                            minimumValue: 0
                            maximumValue: 200
                            currentValue: Math.max(0, root.stagedSwappiness)
                            valueStep: 1
                            valueDecimals: 0
                            snapContinuousToStep: true
                            options: ["0", "50", "100", "150", "200"]
                            numericReferenceValues: [0, 50, 100, 150, 200]
                            interactive: root.page === "POL" && root.policySection === 0 && root.sample !== null
                                         && root.stagedSwappiness >= 0 && !MemoryOperation.busy
                            enabled: interactive
                            onValueRequested: function(value) { root.stagePolicy(Math.round(value)); }
                        }
                        Column {
                            id: policyActions
                            objectName: "cpuplusPolicyActions"
                            width: Math.max(0, policyInstrument.width - policyDial.width - policyInstrument.spacing)
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            ActionButton {
                                objectName: "cpuplusPolicyReset"
                                width: parent.width
                                height: 30
                                label: "RESET TARGET"
                                contentPadding: 2
                                labelFontSizeMode: Text.HorizontalFit
                                available: root.sample !== null && !MemoryOperation.busy
                                onLeftClicked: root.stagePolicy(root.sample.swappiness)
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: "Relative cost of reclaiming anonymous memory through swap versus reclaiming filesystem cache. Not a RAM usage percentage."
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "PREVIEW ONLY // APPLY NOT CONNECTED"
                        color: Colors.orange
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "POL" && root.policySection === 1
                visible: active
                sourceComponent: Column {
                    objectName: "cpuplusPriorityPane"
                    spacing: 6
                    Row {
                        width: parent.width
                        height: 28
                        spacing: 4
                        GohuText {
                            width: Math.max(0, parent.width - priorityRefresh.width - parent.spacing)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: "SWAP PRIORITY"
                            color: Colors.magenta
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            id: priorityRefresh
                            width: 78
                            height: parent.height
                            label: "REFRESH"
                            accentColor: Colors.yellow
                            idleFillColor: Colors.yellow
                            idleForegroundColor: Colors.magenta
                            idleBorderColor: Colors.orange
                            contentPadding: 2
                            available: !probe.running
                            onLeftClicked: root.refresh()
                        }
                    }
                    GohuText {
                        width: parent.width
                        visible: root.priorityRows.length === 0
                        text: root.sample ? "NO VALID ACTIVE DEVICES" : "LIVE DATA UNAVAILABLE"
                        color: Colors.orange
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: root.priorityRows
                        delegate: ActionButton {
                            required property var modelData
                            width: parent.width
                            height: 30
                            label: root.priorityName(modelData) + " // " + modelData.priority
                            labelFontSizeMode: Text.HorizontalFit
                            contentPadding: 3
                            selected: root.priorityRow !== null && root.priorityRow.name === modelData.name
                            available: !MemoryOperation.busy
                            onLeftClicked: root.selectPriorityDevice(modelData.name)
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: root.priorityRow ? root.priorityRow.name : "SELECT ACTIVE DEVICE"
                        textFormat: Text.PlainText
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                    Row {
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: [
                                {label:"ACTUAL", value:root.priorityRow ? String(root.priorityRow.priority) : "—", color:Colors.cyan},
                                {label:"TARGET", value:root.priorityRow && root.stagedPriority >= 0 ? String(root.stagedPriority) : "—", color:Colors.yellow}
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                width: Math.max(0, (parent.width - 4) / 2)
                                height: 38
                                color: Colors.black
                                border.color: modelData.color
                                border.width: 1
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    GohuText {
                                        width: parent.width
                                        text: modelData.label
                                        color: Colors.white
                                        font.pixelSize: 10
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: modelData.value
                                        color: modelData.color
                                        font.pixelSize: 14
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        visible: root.priorityRow !== null && root.priorityRow.priority < 0
                        text: "NEGATIVE PRIORITY // KERNEL ASSIGNED"
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    Row {
                        width: parent.width
                        height: 160
                        spacing: 8
                        SelectorDial {
                            id: priorityDial
                            objectName: "cpuplusPriorityDial"
                            width: 136
                            height: 160
                            labelText: "PRIORITY"
                            selectorMode: "continuous"
                            minimumValue: 0
                            maximumValue: 32767
                            valueStep: 1
                            valueDecimals: 0
                            snapContinuousToStep: true
                            options: ["0", "8K", "16K", "24K", "32767"]
                            numericReferenceValues: [0, 8192, 16384, 24576, 32767]
                            currentValue: Math.max(0, root.stagedPriority)
                            readoutText: root.stagedPriority < 0 && !rotating ? "—" : String(Math.round(previewNumericValue))
                            interactive: root.priorityEditable
                            enabled: interactive
                            onValueRequested: function(value) { root.stagePriority(Math.round(value)); }
                        }
                        Column {
                            width: Math.max(0, parent.width - priorityDial.width - parent.spacing)
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 5
                            Repeater {
                                model: [-10, -1, 1, 10]
                                delegate: ActionButton {
                                    required property int modelData
                                    width: parent.width
                                    height: 24
                                    label: modelData > 0 ? "+" + modelData : String(modelData)
                                    contentPadding: 2
                                    available: root.priorityEditable && root.stagedPriority >= 0
                                        && root.stagedPriority + modelData >= 0
                                        && root.stagedPriority + modelData <= 32767
                                    onLeftClicked: root.stagePriority(root.stagedPriority + modelData)
                                }
                            }
                            ActionButton {
                                width: parent.width
                                height: 26
                                label: root.stagedPriority < 0 ? "SET 0" : "RESET"
                                contentPadding: 2
                                available: root.priorityEditable
                                onLeftClicked: {
                                    if (root.stagedPriority < 0) root.stagePriority(0);
                                    else root.resetPriority();
                                }
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: "PREVIEW ONLY // APPLY NOT CONNECTED"
                        color: Colors.orange
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 28
                        label: "COPY PRIORITY TO CUSTOM"
                        available: root.priorityEditable && root.stagedPriority>=0 && root.status==="OBSERVED"
                        onLeftClicked: root.copyPriorityProfile()
                    }
                    GohuText {
                        width: parent.width
                        text: "Higher priority is preferred for new swap allocation. Equal priorities share allocation. Changing an active device may require safe deactivation."
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "POL" && root.policySection === 2
                visible: active
                sourceComponent: CpuPlusZramPolicyPane {
                    sample: root.sample
                    operationBusy: MemoryOperation.busy
                    onProfileCopyRequested: value => root.copyZramProfile(value)
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "POL" && root.policySection === 3
                visible: active
                sourceComponent: CpuPlusAdvancedPolicyPane {
                    operationBusy: MemoryOperation.busy
                    onProfileCopyRequested: (key,unit,value) => root.copyAdvancedProfile(key,unit,value)
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "AUTO"
                visible: active
                sourceComponent: CpuPlusAutoWorkspace {
                    headerTarget: workHeader
                    footerTarget: workFooter
                    observedDiskKiB: root.capacity ? root.capacity.actualKiB : null
                    capacityTargetGiB: root.stagedGiB
                    // Production launch/lifecycle remains HOLD. No session
                    // owner is constructed inside the demand-loaded widget.
                    hostState: null
                    recoverySession: root.recoverySession
                    onSectionChangedByUser: scroll.contentY = 0
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "PROF"
                visible: active
                sourceComponent: CpuPlusProfilePane {
                    headerTarget: workHeader
                    footerTarget: workFooter
                    selectedProfile: root.selectedProfile
                    customDraft: root.customProfileDraft
                    actualKiB: root.capacity ? root.capacity.actualKiB : null
                    actualSwappiness: root.sample ? root.sample.swappiness : null
                    capacityTarget: root.stagedGiB
                    policyTarget: root.stagedSwappiness
                    observationReady: root.status === "OBSERVED"
                    operationBusy: MemoryOperation.busy
                    onProfileSelected: name => root.chooseProfile(name)
                    onDraftCapture: key => root.captureProfileTarget(key)
                    onDraftCleared: root.clearProfileDraft()
                    memorySample: root.sample
                    catalog: profileCatalog.document
                    catalogStatus: profileCatalog.status
                    catalogBusy: profileCatalog.busy || profileCatalog.faulted
                    onCatalogLoadRequested: if(root.page==="PROF") profileCatalog.list()
                    onCatalogSaveRequested: name => {
                        if(root.page==="PROF" && root.selectedProfile==="CUSTOM") profileCatalog.saveNew(name,root.customProfileDraft);
                    }
                    onSavedDraftRequested: name => root.loadProfileDraft(name)
                    onCatalogChangeRequested: request => {
                        if(root.page!=="PROF" || !request)return;
                        if(request.action==="edit" && (root.selectedProfile!=="CUSTOM" || !Catalog.validDraft(request.targets)
                            || JSON.stringify(Catalog.copyTargets(request.targets,"post-apollo-cpuplus-profiles-v2"))!==JSON.stringify(root.customProfileDraft)))return;
                        profileCatalog.changeExisting(request);
                    }
                }
            }
        }
    }
    Rectangle {
        id: detailInfoPopup
        objectName: "cpuplusCapDetailsInfoPopup"
        visible: root.capDetailsActive && root.detailsInfoOpen
        z: 30
        anchors.left: scroll.left
        anchors.right: scroll.right
        anchors.top: scroll.top
        anchors.topMargin: 26
        anchors.leftMargin: 5
        anchors.rightMargin: 5
        height: Math.max(0,Math.min(infoContents.implicitHeight+12, (footer.y-y-4)*[0.55,0.78,1][root.infoSizeLevel]))
        color: "#190309"
        border.color: Colors.red
        clip: true
        MouseArea { anchors.fill: parent }
        Flickable {
            anchors.fill: parent
            anchors.margins: 6
            contentWidth: width
            contentHeight: infoContents.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: infoContents
                width: parent.width
                spacing: 4
                Row {
                    width: parent.width
                    height: 26
                    CpuPlusMemoryReadout {
                        width: Math.max(0,parent.width-78)
                        height: parent.height
                        text: "MEMORY // INFO"
                        color: Colors.red
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                    }
                    ResizeButton {
                        width: 26
                        direction: "down"
                        available: root.infoSizeLevel>0
                        onResizeRequested: delta=>root.infoSizeLevel+=delta
                    }
                    ResizeButton {
                        width: 26
                        direction: "up"
                        available: root.infoSizeLevel<2
                        onResizeRequested: delta=>root.infoSizeLevel+=delta
                    }
                    CloseButton {
                        objectName: "cpuplusCapDetailsInfoClose"
                        width: 26
                        onCloseRequested: root.detailsInfoOpen=false
                    }
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: "INDEPENDENT KERNEL COUNTERS // OVERLAP; DO NOT ADD. NO DIMM ATTRIBUTION."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: root.capDetailSubject==="RAM" ? [
                        {label:"AVAILABLE", note:"Estimated usable RAM, not free RAM."},
                        {label:"FREE", note:"Unused physical memory."},
                        {label:"ANONYMOUS", note:"Anonymous mapped pages."},
                        {label:"FILE CACHE", note:"Cached file pages."},
                        {label:"SHARED / TMPFS", note:"Shared memory and tmpfs."},
                        {label:"RECLAIMABLE SLAB", note:"Potentially reclaimable kernel slab."},
                        {label:"UNRECLAIMABLE SLAB", note:"Unreclaimable kernel slab."}
                    ] : [
                        {label:"ZRAM", note:"Logical compressed swap, not extra physical RAM.", ink:Colors.cyan},
                        {label:"BASE NVMe", note:"Disk-backed base swap.", ink:Colors.yellow},
                        {label:"EXTENSION", note:"Temporary disk-backed extension.", ink:Colors.magenta},
                        {label:"OTHER SWAP", note:"Other observed swap.", ink:Colors.blue}
                    ]
                    delegate: CpuPlusMemoryReadout {
                        required property var modelData
                        width: infoContents.width
                        text: modelData.label+" // "+modelData.note
                        color: modelData.ink || root.ramDatasetColor(modelData.label)
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: "RAM bright = estimated available. Swap bright = used, dim = free. Target changes do not alter the live bars."
                    color: Colors.cyan
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    text: "Disk swap targets reserve storage. Zero and reduction remain previews until supported by the authorized capacity backend."
                    color: Colors.yellow
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    Rectangle {
        id: scanInspector
        objectName: "cpuplusMemoryScanDiagnostics"
        anchors.fill: parent
        z: 40
        visible: root.scanDiagnosticsOpen
        color: "#110319"
        border.color: Colors.magenta
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
        DiagnosticsServicePopup {
            id: scanReportPopup
            anchors.fill: parent
            anchors.margins: 4
            heading: "MEMORY // SCAN DIAGNOSTICS"
            liveReadyColor: Colors.omnitrix
            manualStateColor: Colors.red
            headerAccessory: Component {
                Column {
                    id: scanControls
                    objectName: "cpuplusScanControls"
                    spacing: 3
                    CpuPlusMemoryReadout {
                        width: parent.width
                        text: "SCAN INTERVAL // "+root.scanIntervalSeconds+" s"
                        color: Colors.white
                        font.pixelSize: 11
                    }
                    Row {
                        width: parent.width
                        height: 36
                        spacing: 5
                        ActionButton {
                            objectName: "cpuplusScanPlayPause"
                            width: 28
                            height: 28
                            anchors.verticalCenter: parent.verticalCenter
                            label: root.scanLive?"Ⅱ":"▶"
                            labelPixelSize: 21
                            contentPadding: 1
                            accentColor: Colors.omnitrix
                            selected: root.scanLive
                            idleForegroundColor: Colors.omnitrix
                            hoverForegroundColor: Colors.omnitrix
                            pressedForegroundColor: Colors.black
                            selectedForegroundColor: Colors.black
                            idleBorderColor: Colors.omnitrix
                            hoverBorderColor: Colors.omnitrix
                            pressedBorderColor: Colors.black
                            selectedBorderColor: Colors.black
                            hoverFillColor: Colors.yellow
                            pressedFillColor: Colors.omnitrix
                            selectedFillColor: Colors.omnitrix
                            idleContentGlowColor: Colors.omnitrix
                            hoverContentGlowColor: Colors.omnitrix
                            pressedContentGlowColor: Colors.omnitrix
                            selectedContentGlowColor: Colors.omnitrix
                            idleSoftGlowColor: Colors.omnitrix
                            hoverSoftGlowColor: Colors.omnitrix
                            pressedSoftGlowColor: Colors.omnitrix
                            selectedSoftGlowColor: Colors.omnitrix
                            contentGlowIdleOpacity: 0.72
                            contentGlowSelectedOpacity: 1.0
                            softGlowIdleOpacity: 0.48
                            softGlowSelectedOpacity: 1.0
                            wideGlowEnabled: true
                            idleWideGlowColor: Colors.omnitrix
                            hoverWideGlowColor: Colors.omnitrix
                            pressedWideGlowColor: Colors.omnitrix
                            selectedWideGlowColor: Colors.omnitrix
                            Accessible.name: root.scanLive?"Pause automatic scans":"Play automatic scans"
                            acceptedButtons: Qt.LeftButton
                            keyboardActivationSignal: "leftClicked"
                            onLeftClicked: root.setScanMode(root.scanLive?"PAUSED":"LIVE")
                        }
                        ActionButton {
                            objectName: "cpuplusScanStop"
                            width: 28
                            height: 28
                            anchors.verticalCenter: parent.verticalCenter
                            label: "■"
                            labelPixelSize: 22
                            contentPadding: 1
                            accentColor: Colors.red
                            selected: root.scanMode==="STOPPED"
                            idleForegroundColor: Colors.red
                            hoverForegroundColor: Colors.red
                            pressedForegroundColor: Colors.black
                            selectedForegroundColor: Colors.black
                            idleBorderColor: Colors.red
                            hoverBorderColor: Colors.red
                            pressedBorderColor: Colors.black
                            selectedBorderColor: Colors.black
                            hoverFillColor: Colors.yellow
                            pressedFillColor: Colors.red
                            selectedFillColor: Colors.red
                            idleContentGlowColor: Colors.red
                            hoverContentGlowColor: Colors.red
                            pressedContentGlowColor: Colors.red
                            selectedContentGlowColor: Colors.red
                            idleSoftGlowColor: Colors.red
                            hoverSoftGlowColor: Colors.red
                            pressedSoftGlowColor: Colors.red
                            selectedSoftGlowColor: Colors.red
                            contentGlowIdleOpacity: 0.72
                            contentGlowPressedOpacity: 1.0
                            contentGlowSelectedOpacity: 1.0
                            softGlowIdleOpacity: 0.48
                            softGlowPressedOpacity: 1.0
                            softGlowSelectedOpacity: 1.0
                            wideGlowEnabled: true
                            idleWideGlowColor: Colors.red
                            hoverWideGlowColor: Colors.red
                            pressedWideGlowColor: Colors.red
                            selectedWideGlowColor: Colors.red
                            wideGlowPressedOpacity: 1.0
                            wideGlowSelectedOpacity: 1.0
                            Accessible.name: "Stop automatic scans; reload manually"
                            acceptedButtons: Qt.LeftButton
                            keyboardActivationSignal: "leftClicked"
                            onLeftClicked: root.setScanMode("STOPPED")
                        }
                        Item {
                            width: Math.max(0,parent.width-66)
                            height: parent.height
                            SelectorSlider {
                                objectName: "cpuplusScanFrequencySlider"
                                anchors.centerIn: parent
                                width: 32
                                height: parent.width
                                rotation: 90
                                horizontalStepPresentation: true
                                selectorProfile: "step"
                                minimumValue: 5
                                maximumValue: 60
                                valueStep: 5
                                valueDecimals: 0
                                valueSuffix: "s"
                                currentValue: root.scanIntervalSeconds
                                enabledSlider: true
                                accentColor: Colors.white
                                valueFillColor: Colors.omnitrix
                                handleColor: Colors.white
                                handleGradientBaseColor: Colors.white
                                handleGradientAccentColor: Colors.white
                                handleGlowColor: Colors.white
                                activityGlowColor: Colors.white
                                onValueRequested: value=>root.setScanInterval(value)
                            }
                        }
                    }
                }
            }
            displayedState: root.status==="READING"?"READING":!root.scanLive?(root.scanMode==="STOPPED"?"MANUAL":"PAUSED"):root.status==="OBSERVED"?"LIVE":root.lastGoodSample?"CACHE STALE":"WAITING"
            providerLabel: "LOCAL LINUX // PROCFS"
            currentAge: root.scanLastSuccessMs ? Math.max(0,Math.floor((root.scanClockMs-root.scanLastSuccessMs)/1000))+"s" : "--"
            showLocation: false
            serviceRows: root.scanRows
            reasonHeading: "LAST ATTEMPT // SOURCE RESULTS"
            ageHeading: "READ // "
            reason: root.scanReason+"\n"+root.scanRows.map(x=>x.label+" // "+x.reason).join("\n")
            footnote: "DISPLAY RETAINS LAST VALID SNAPSHOT; STALE DATA NEVER AUTHORIZES AN OPERATION. LIVE controls memory polling only; shared system telemetry and independent diagnostics retain their owners."
            onCloseRequested: root.scanDiagnosticsOpen=false
        }
    }
    NeonScrollBar { flickable: scroll; visible: root.visible && scroll.visible && scrollable && scroll.interactive && !root.scanDiagnosticsOpen }
    Rectangle {
        objectName: "cpuplusMemoryDiagnosticsInfoPopup"
        visible: root.diagnosticInfoOpen && root.visible && root.diagnosticSubject!=="ALL"
        z: 401
        x: 5
        y: workHeader.y+diagnosticCapacityHeader.y+diagnosticCapacityHeader.dividerBottom+3
        width: Math.max(0,root.width-10)
        height: Math.min(Math.max(0,root.height-y),memoryHelpText.implicitHeight+12)
        color: Colors.black
        border.color: Colors.yellow
        clip: true
        GohuText {
            id: memoryHelpText
            width: Math.max(0,parent.width-12)
            x: 6
            y: 6
            text: root.diagnosticSubject==="SWAP"
                ? "Read-only swap movement, memory pressure and zram allocation. Capacity and policy controls are separate."
                : "Read-only Quickshell memory capture: resident, proportional and private memory; swap and host RAM context. Capacity and policy controls are separate."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }
}
