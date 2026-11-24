import QtQuick
import Quickshell.Io
import qs.services.memory
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
        if (page !== "CAP" || !capacity || MemoryOperation.busy
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
    property int menuIndex: 0
    readonly property string page: menus[menuIndex]
    function selectMenu(index) {
        if (index < 0 || index >= menus.length || index === menuIndex) return;
        // Hidden confirmation must not survive a trip to another page.
        // Do not cancel or repeat a request already owned by MemoryOperation.
        if (page === "CAP") {
            addControl.armed = false;
            addControl.persistArmed = false;
            addControl.expandArmed = false;
        }
        menuIndex = index;
        scroll.contentY = 0;
    }

    Grid {
        id: menuRail
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        columns: width >= 240 ? 6 : 3
        spacing: 4
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
    Flickable {
        id: scroll
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: menuRail.bottom
        anchors.bottom: footer.top
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
                text: "MEMORY // " + root.menuTitles[root.menuIndex]
                color: Colors.magenta
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.WordWrap
            }
            GohuText {
                text: "SOURCE // " + root.status
                color: root.sample ? Colors.cyan : Colors.orange
                font.pixelSize: 10
            }
            ActionButton {
                width: parent.width
                height: 30
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
            Column {
                width: parent.width
                spacing: 10
                visible: root.page === "CAP"
                enabled: visible
                GohuText {
                    width: parent.width
                    text: "PHYSICAL RAM // KERNEL USABLE"
                    color: Colors.magenta
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: root.sample ? "AVAILABLE // " + root.gib(root.sample.available)
                          + " / " + root.gib(root.sample.total) : "AVAILABLE // UNAVAILABLE"
                    color: Colors.cyan
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: Math.max(0, parent.width - 10)
                    anchors.horizontalCenter: parent.horizontalCenter
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
                GohuText {
                    width: parent.width
                    text: "BRIGHT = ESTIMATED AVAILABLE RAM"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                CpuPlusSwapComposition {
                    width: parent.width
                    sample: root.sample
                    capacity: root.capacity
                }
                Rectangle { width: parent.width; height: 1; color: Colors.cyan }
                GohuText {
                    text: "MANAGED DISK SWAP // CAPACITY"
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: Colors.magenta
                    font.pixelSize: 12
                }
                Row {
                    id: capacityRow
                    width: parent.width
                    spacing: 10
                    SelectorSlider {
                        id: capacitySelector
                        objectName: "cpuplusCapacitySelector"
                        width: 44
                        height: Math.max(180, targetDetails.implicitHeight)
                        selectorProfile: "step"
                        minimumValue: 0
                        maximumValue: 64
                        valueStep: 4
                        valueDecimals: 0
                        valueSuffix: "GiB"
                        currentValue: root.stagedGiB
                        enabledSlider: root.page === "CAP" && root.capacity !== null && !MemoryOperation.busy
                        enabled: enabledSlider
                        sideLabel: "GiB"
                        onValueRequested: function(value) { root.stageCapacity(value); }
                    }
                    Column {
                        id: targetDetails
                        width: Math.max(0, capacityRow.width - capacitySelector.width - capacityRow.spacing)
                        spacing: 8
                        GohuText {
                            text: "TARGET // " + root.stagedGiB + " GiB"
                            width: parent.width
                            wrapMode: Text.WordWrap
                            color: Colors.yellow
                            font.pixelSize: 12
                        }
                        GohuText {
                            width: parent.width
                            text: root.capacity ? "ACTUAL ACTIVE // " + root.gib(root.capacity.actualKiB) : "ACTUAL ACTIVE // UNAVAILABLE"
                            color: Colors.cyan
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                        GohuText {
                            width: parent.width
                            text: root.capacity ? "PROJECTED TOTAL SWAP // " + root.gib(root.capacity.projectedKiB)
                                : "PROJECTED TOTAL SWAP // UNAVAILABLE"
                            color: Colors.yellow
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                        }
                        GohuText {
                            width: parent.width
                            text: !root.capacity ? "WAITING FOR LIVE CAPACITY"
                                : root.capacity.direction === "unchanged" ? "TARGET MATCHES ACTIVE CAPACITY"
                                : root.capacity.direction === "expand" && root.capacity.baseActive && !root.capacity.extensionActive
                                    ? "EXPANSION // ADD SEPARATE TEMPORARY SWAP"
                                : root.capacity.active ? "PREVIEW ONLY // RESIZE NOT AVAILABLE YET"
                                : "Would reserve " + root.stagedGiB + " GiB of storage. Not physical RAM."
                            color: Colors.white
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                        }
                        ActionButton {
                            visible: root.capacity !== null && root.capacity.active && root.capacity.direction !== "unchanged"
                            width: parent.width
                            height: 30
                            label: "RESET TARGET"
                            available: !MemoryOperation.busy
                            onLeftClicked: root.stageCapacity(Math.max(4, Math.min(64, Math.round(root.capacity.actualGiB / 4) * 4)))
                        }
                    }
                }
                CpuPlusMemoryAddControl {
                    id: addControl
                    width: parent.width
                    stagedGiB: root.stagedGiB
                    sample: root.sample
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
                visible: root.page !== "CAP" && root.page !== "POL"
                text: root.page === "PROC" ? "PROCESS CONTROLS // NOT CONNECTED"
                    : root.page === "AUTO" ? "DEFERRED REQUESTS // NOT CONNECTED"
                    : root.page === "DIAG" ? "LIVE SNAPSHOT // EXTENDED DIAGNOSTICS NOT CONNECTED"
                    : "PROFILE CONTROLS // NOT CONNECTED"
                color: Colors.orange
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }
    }
    NeonScrollBar { flickable: scroll; visible: root.visible && scrollable }
}
