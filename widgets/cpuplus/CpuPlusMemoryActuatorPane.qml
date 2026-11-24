import QtQuick
import Quickshell.Io
import qs.services.memory
import qs.services.diagnostics
import "../../components"
import "CpuPlusMemorySnapshot.js" as Snapshot

// Demand-loaded by SYSTEM memory/swap selection. No privileged operations.
Item {
    id: root
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
    function stageCapacity(value) {
        if (page !== "CAP" || capSection !== 0 || !capacity || MemoryOperation.busy
                || !Number.isInteger(value) || value < 0 || value > 64 || value % 4 !== 0)
            return;
        stagedGiB = value;
    }
    function stagePolicy(value) {
        if (page !== "POL" || !sample || MemoryOperation.busy
                || !Number.isInteger(value) || value < 0 || value > 200)
            return;
        stagedSwappiness = value;
    }
    onSampleChanged: {
        adoptActual();
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
        Row {
            width: parent.width
            spacing: 4
            Repeater {
                model: ["TARGET", "ACTIONS", "DETAILS"]
                delegate: ActionButton {
                    required property string modelData
                    required property int index
                    width: Math.max(0, (capInstrument.width - 8) / 3)
                    height: 28
                    label: modelData
                    contentPadding: 2
                    selected: root.capSection === index
                    onLeftClicked: root.selectCapSection(index)
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
    }
    Flickable {
        id: scroll
        objectName: "cpuplusMemoryScroll"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: root.page === "CAP" ? capInstrument.bottom : menuRail.bottom
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
                visible: root.page !== "CAP"
                text: "MEMORY // " + root.menuTitles[root.menuIndex]
                color: Colors.magenta
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.WordWrap
            }
            GohuText {
                visible: root.page !== "CAP"
                text: "SOURCE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 10
            }
            ActionButton {
                width: parent.width
                height: 30
                visible: root.page !== "CAP"
                label: "REFRESH"
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
                active: root.page === "DIAG"
                visible: active
                sourceComponent: CpuPlusDiagnosticsPane {}
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
                    text: "DETAILS // LIVE SWAP DEVICES"
                    color: Colors.magenta
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: root.page === "CAP" && root.capSection === 2 && root.sample ? root.sample.rows : []
                    delegate: GohuText {
                        required property var modelData
                        width: parent.width
                        textFormat: Text.PlainText
                        text: modelData.kind + " // " + modelData.name + "\n"
                            + root.gib(modelData.used) + " / " + root.gib(modelData.size)
                            + " // PRIORITY " + modelData.priority
                        color: Colors.cyan
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
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
                active: root.page === "POL"
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
                    SelectorDial {
                        objectName: "cpuplusSwappinessDial"
                        anchors.horizontalCenter: parent.horizontalCenter
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
                        interactive: root.page === "POL" && root.sample !== null
                                     && root.stagedSwappiness >= 0 && !MemoryOperation.busy
                        enabled: interactive
                        onValueRequested: function(value) { root.stagePolicy(Math.round(value)); }
                    }
                    ActionButton {
                        width: parent.width
                        height: 30
                        label: "RESET TARGET TO ACTUAL"
                        available: root.sample !== null && !MemoryOperation.busy
                        onLeftClicked: root.stagePolicy(root.sample.swappiness)
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
            GohuText {
                width: parent.width
                visible: root.page !== "CAP" && root.page !== "POL" && root.page !== "DIAG"
                text: root.page === "PROC" ? "PROCESS CONTROLS // NOT CONNECTED"
                    : root.page === "AUTO" ? "DEFERRED REQUESTS // NOT CONNECTED"
                    : "PROFILE CONTROLS // NOT CONNECTED"
                color: Colors.orange
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }
    }
    NeonScrollBar { flickable: scroll; visible: root.visible && scroll.visible && scrollable }
}
