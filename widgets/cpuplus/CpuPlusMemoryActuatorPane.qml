import QtQuick
import Quickshell.Io
import qs.services.memory
import qs.services.diagnostics
import "../../components"
import "CpuPlusMemorySnapshot.js" as Snapshot
import "CpuPlusProfilePreview.js" as Profiles
import "CpuPlusProfileCatalog.js" as Catalog

// Demand-loaded by SYSTEM memory/swap selection. No privileged operations.
Item {
    id: root
    // Borrowed session: this view does not own its lifecycle or launch paths.
    property var recoverySession: null
    property var sample: null
    property string status: "READING"
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property var pendingSample: null
    function finish() {
        if (!received || !exited) return;
        sample = exitOk ? pendingSample : null;
        status = sample ? "OBSERVED" : "UNAVAILABLE";
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
        sample = null;
        status = "READING";
        probe.running = true;
    }
    Component.onCompleted: refresh()
    Connections {
        target: MemoryOperation
        function onRevisionChanged() { root.refresh(); }
    }
    Timer {
        interval: 10000
        repeat: true
        running: root.visible
        onTriggered: root.refresh()
    }
    Process {
        id: probe
        running: false
        command: ["/usr/bin/cat", "/proc/meminfo", "/proc/swaps",
                  "/proc/pressure/memory", "/proc/sys/vm/swappiness"]
        stdout: StdioCollector {
            onStreamFinished: {
                root.pendingSample = Snapshot.parseSnapshot(this.text);
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
    readonly property var ramDetailRows: Snapshot.ramDetailRows(sample)
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
        const label=token(row.label,ink)+token(" // ",white);
        if(row.value===null)return label+token("UNAVAILABLE",Colors.orange);
        const parts=(row.value/1048576).toFixed(2).split(".");
        return label+token(parts[0],ink)+token(".",white)+token(parts[1],ink)+token(" GiB",white);
    }
    function selectCapDetailSubject(subject) {
        if(page!=="CAP"||capSection!==2||!["RAM","SWAP"].includes(subject))return;
        capDetailSubject=subject;
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
                contentGlowEnabled: false
                softGlowEnabled: false
                onLeftClicked: root.selectMenu(index)
            }
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
        anchors.topMargin: 4
        spacing: 3
        visible: root.fixedWorkPage
        height: visible ? implicitHeight : 0
        GohuText {
            width: parent.width
            text: "MEMORY // " + root.menuTitles[root.menuIndex]
            color: Colors.magenta
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            spacing: 4
            GohuText {
                width: Math.max(0,parent.width-72-parent.spacing)
                height: Math.max(26,implicitHeight)
                text: "SOURCE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 10
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.Wrap
            }
            ActionButton {
                objectName: "cpuplusWorkRefresh"
                width: 72
                height: 26
                label: "REFRESH"
                contentPadding: 2
                accentColor: Colors.yellow
                idleFillColor: Colors.yellow
                idleForegroundColor: Colors.magenta
                idleBorderColor: Colors.orange
                available: !probe.running && root.status !== "READING"
                onLeftClicked: root.refresh()
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
        Rectangle { width: parent.width; height: 1; color: Colors.cyan }
        GohuText {
            width: parent.width
            text: MemoryOperation.busy ? "OPERATION // IN PROGRESS"
                : "AUTH // EXPLICIT ONE-SHOT ONLY"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
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

        Row {
            width: parent.width
            height: 25
            spacing: 5
            GohuText {
                width: Math.max(0, parent.width - refreshCap.width - parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "LIVE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            ActionButton {
                id: refreshCap
                objectName: "cpuplusCapRefresh"
                accentColor: Colors.yellow
                idleFillColor: Colors.yellow
                idleForegroundColor: Colors.magenta
                idleBorderColor: Colors.orange
                width: 68
                height: parent.height
                label: "REFRESH"
                contentPadding: 2
                available: !probe.running
                onLeftClicked: root.refresh()
            }
        }
        GohuText {
            width: parent.width
            text: root.sample ? "RAM AVAIL // " + root.gib(root.sample.available)
                + " / " + root.gib(root.sample.total) : "RAM // UNAVAILABLE"
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
                opacity: root.sample ? 0.22 : 0
            }
            Rectangle {
                x: 3; y: 3
                height: Math.max(0, parent.height - 6)
                width: root.sample && root.sample.total > 0
                    ? Math.max(0, parent.width - 6) * root.sample.available / root.sample.total : 0
                color: Colors.cyan
                opacity: 0.85
            }
        }
        CpuPlusSwapComposition {
            width: parent.width
            sample: root.sample
            capacity: root.capacity
            compact: true
        }
        Rectangle { width: parent.width; height: 1; color: Colors.cyan }
        Grid {
            width: parent.width
            columns: 3
            spacing: 4
            Repeater {
                model: [
                    {label:"ACTUAL DISK",value:root.capacity ? root.gib(root.capacity.actualKiB) : "—",accent:Colors.cyan},
                    {label:"TARGET DISK",value:root.stagedGiB + " GiB",accent:Colors.yellow},
                    {label:"TOTAL PLAN",value:root.capacity ? root.gib(root.capacity.projectedKiB) : "—",accent:Colors.yellow}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(0, (parent.width - 8) / 3)
                    height: 40
                    border.width: 1
                    border.color: modelData.accent
                    color: Colors.black
                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 2
                        GohuText {
                            width: parent.width
                            text: modelData.label
                            color: Colors.white
                            font.pixelSize: 10
                            fontSizeMode: Text.HorizontalFit
                            minimumPixelSize: 8
                            horizontalAlignment: Text.AlignHCenter
                        }
                        GohuText {
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
            GohuText {
                width: parent.width
                text: !root.capacity ? "WAITING FOR LIVE CAPACITY"
                    : root.capacity.direction === "unchanged" ? "TARGET MATCHES ACTIVE CAPACITY"
                    : root.capacity.direction === "expand" && root.capacity.baseActive && !root.capacity.extensionActive
                        ? "EXPANSION // SEPARATE TEMPORARY SWAP"
                    : root.capacity.active ? "PREVIEW ONLY // RESIZE NOT AVAILABLE YET"
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
                    height: 28
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
        anchors.top: root.page === "CAP" ? capInstrument.bottom : root.fixedWorkPage ? workHeader.bottom : menuRail.bottom
        anchors.bottom: footer.top
        visible: root.page !== "CAP" || root.capSection !== 0
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.implicitHeight + 18)
        Column {
            id: body
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 17)
            spacing: 10
            GohuText {
                visible: root.page !== "CAP" && !root.fixedWorkPage
                text: "MEMORY // " + root.menuTitles[root.menuIndex]
                color: Colors.magenta
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.WordWrap
            }
            GohuText {
                visible: root.page !== "CAP" && !root.fixedWorkPage
                text: "SOURCE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 10
            }
            ActionButton {
                width: parent.width
                height: 30
                visible: root.page !== "CAP" && root.page !== "POL" && !root.fixedWorkPage
                label: "REFRESH"
                accentColor: Colors.yellow
                idleFillColor: Colors.yellow
                idleForegroundColor: Colors.magenta
                idleBorderColor: Colors.orange
                available: !probe.running
                onLeftClicked: root.refresh()
            }
            Repeater {
                model: !root.sample ? []
                    : root.page === "DIAG" ? [
                    "PHYSICAL // " + root.gib(root.sample.total),
                    "AVAILABLE // " + root.gib(root.sample.available),
                    "SWAP USED // " + root.gib(root.sample.swap - root.sample.free)
                        + " / " + root.gib(root.sample.swap),
                    "PRESSURE SOME / FULL (10s) // " + root.sample.some.toFixed(2)
                        + "% / " + root.sample.full.toFixed(2) + "%"
                    ] : []
                delegate: GohuText {
                    required property string modelData
                    width: body.width
                    text: modelData
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
            Repeater {
                model: root.sample && root.page === "DIAG"
                    ? root.sample.rows : []
                delegate: GohuText {
                    required property var modelData
                    width: body.width
                    textFormat: Text.PlainText
                    text: modelData.kind + " // " + modelData.name + "\n"
                          + root.gib(modelData.used) + " / " + root.gib(modelData.size)
                          + " // PRIORITY " + modelData.priority
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "PROC"
                visible: active
                sourceComponent: CpuPlusProcessPane { headerTarget: workHeader; footerTarget: workFooter }
            }
            Loader {
                width: parent.width
                height: active && item ? item.implicitHeight : 0
                active: root.page === "DIAG"
                visible: active
                sourceComponent: CpuPlusDiagnosticsPane { headerTarget: workHeader; footerTarget: workFooter }
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
                spacing: 6
                visible: root.page === "CAP" && root.capSection === 2
                GohuText {
                    width: parent.width
                    text: "DETAILS // LIVE "+root.capDetailSubject
                    color: Colors.magenta
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                Column {
                    objectName: "cpuplusCapRamDetails"
                    width: parent.width
                    spacing: 4
                    visible: root.capDetailSubject==="RAM"
                    GohuText {
                        width: parent.width
                        text: root.sample?"KERNEL USABLE RAM // "+root.gib(root.sample.total):"RAM SNAPSHOT UNAVAILABLE"
                        color: Colors.cyan
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    Grid {
                        id: ramCardGrid
                        objectName: "cpuplusRamCardGrid"
                        width: parent.width
                        columns: width >= 440 ? 2 : 1
                        spacing: 4
                        Repeater {
                            model: root.page==="CAP"&&root.capSection===2&&root.capDetailSubject==="RAM"?root.ramDetailRows:[]
                            delegate: Rectangle {
                                required property var modelData
                                objectName: "cpuplusRamMetricCard"
                                width: Math.max(0,(ramCardGrid.width-(ramCardGrid.columns-1)*ramCardGrid.spacing)/ramCardGrid.columns)
                                height: ramCardContent.implicitHeight+10
                                color: Colors.black
                                border.color: root.ramDatasetColor(modelData.label)
                                Column {
                                    id: ramCardContent
                                    x: 5
                                    y: 5
                                    width: Math.max(0,parent.width-10)
                                    spacing: 3
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
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }
                                        // One existing safe effect per visible dataset.
                                        TextHashGlow {
                                            objectName: "cpuplusRamMetricGlow"
                                            safeSource: ramMetricText.visible ? ramMetricText : null
                                            requestedVisible: ramMetricText.visible
                                            foregroundColor: Colors.white
                                            preferredGlowColor: root.ramDatasetGlow(modelData.label)
                                        }
                                    }
                                    Rectangle {
                                        objectName: "cpuplusRamMetricBar"
                                        width: parent.width
                                        height: 5
                                        visible: modelData.fraction!==null
                                        color: Colors.black
                                        border.color: root.ramDatasetColor(modelData.label)
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.leftMargin: 1
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: Math.max(0,parent.width-2)*(modelData.fraction===null?0:modelData.fraction)
                                            height: parent.height-2
                                            color: root.ramDatasetColor(modelData.label)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: root.sample?"PSI AVG10 // SOME "+root.sample.some+"% / FULL "+root.sample.full+"%":"PSI UNAVAILABLE"
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                        width: parent.width
                        text: "INDEPENDENT KERNEL COUNTERS // OVERLAP; DO NOT ADD. AVAILABLE IS AN ESTIMATE, NOT FREE RAM. NO DIMM ATTRIBUTION."
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
                Repeater {
                    model: root.page === "CAP" && root.capSection === 2 && root.capDetailSubject==="SWAP" && root.sample ? root.sample.rows : []
                    delegate: Rectangle {
                        required property var modelData
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
                            GohuText {
                                width: parent.width
                                textFormat: Text.PlainText
                                text: modelData.kind + " // " + modelData.name
                                color: Colors.yellow
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                            GohuText {
                                width: parent.width
                                textFormat: Text.PlainText
                                text: root.gib(modelData.used) + " / " + root.gib(modelData.size)
                                    + " // PRIORITY " + modelData.priority
                                color: Colors.white
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "RAM bright = estimated available. Swap bright = used, dim = free. ZRAM is logical compressed swap, not additional physical RAM. Target changes do not alter the live bars."
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "Disk swap targets reserve storage. Zero and reduction remain previews until supported by the authorized capacity backend."
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
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
                                objectName: "cpuplusPolicyRefresh"
                                width: parent.width
                                height: 30
                                label: "REFRESH"
                                accentColor: Colors.yellow
                                idleFillColor: Colors.yellow
                                idleForegroundColor: Colors.magenta
                                idleBorderColor: Colors.orange
                                contentPadding: 2
                                labelFontSizeMode: Text.HorizontalFit
                                available: !probe.running
                                onLeftClicked: root.refresh()
                            }
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
    NeonScrollBar { flickable: scroll; visible: root.visible && scroll.visible && scrollable }
}
