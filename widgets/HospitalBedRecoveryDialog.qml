import QtQuick
import qs.components
import "../services/hospital/HospitalBedRecoveryPolicy.js" as RecoveryPolicy

// Recovery UI ONLY: never switches Git or launches an agent.
// The host owns Bed selection/worktree operations, prompt draft and retry.
// PX must perform a fresh, fail-closed target preflight before a provider turn.
Item {
    id: root

    property var floorService: null
    property string roomId: ""
    property string expectedRepository: ""
    property string expectedBranch: ""
    property string currentBedPath: ""
    property string currentBedBranch: ""
    property string mismatchCode: ""
    property string pendingDraft: ""
    property bool operationActive: false
    property bool recoveryOpen: false
    property bool moveArmed: false
    property var candidates: []
    property string selectedPath: ""

    readonly property var selectedCandidate: {
        for (let i = 0; i < candidates.length; ++i) {
            if (String(candidates[i].path) === selectedPath)
                return candidates[i];
        }
        return null;
    }
    readonly property var currentBed: {
        const rows = floorService && Array.isArray(floorService.allBeds)
                     ? floorService.allBeds : [];
        for (let i = 0; i < rows.length; ++i) {
            if (String(rows[i].path || "") === currentBedPath)
                return rows[i];
        }
        return null;
    }
    readonly property var movePolicy: RecoveryPolicy.moveEligibility(
        currentBed, expectedRepository, expectedBranch,
        operationActive || Boolean(floorService && floorService.moveRunning)
    )
    readonly property bool scanning: Boolean(floorService && floorService.discovering)

    signal selectBedRequested(var candidate)
    signal createBedRequested(string repository, string branch)
    signal moveBedRequested(string bedPath, string branch)
    signal registerBedRequested()
    signal inspectOnlyRequested()
    signal cancelled()

    visible: recoveryOpen
    focus: recoveryOpen
    Keys.onEscapePressed: function(event) {
        event.accepted = true;
        root.cancel();
    }

    function openFor(code) {
        mismatchCode = String(code || "TARGET_MISMATCH");
        recoveryOpen = true;
        moveArmed = false;
        selectedPath = "";
        scan();
        forceActiveFocus();
    }

    function cancel() {
        moveArmed = false;
        recoveryOpen = false;
        // Parent retains pendingDraft: never clear or send a queued message.
        cancelled();
    }

    function scan() {
        moveArmed = false;
        rebuildCandidates();
        if (floorService && typeof floorService.discover === "function"
                && !floorService.discovering)
            floorService.discover();
    }

    function rebuildCandidates() {
        const rows = floorService && Array.isArray(floorService.allBeds)
                     ? floorService.allBeds : [];
        candidates = RecoveryPolicy.scanCandidates(
            rows, expectedRepository, expectedBranch
        );
        if (!selectedCandidate)
            selectedPath = "";
    }

    onExpectedRepositoryChanged: rebuildCandidates()
    onExpectedBranchChanged: {
        moveArmed = false;
        rebuildCandidates();
    }
    onCurrentBedPathChanged: moveArmed = false
    onOperationActiveChanged: moveArmed = false

    Connections {
        target: root.floorService
        ignoreUnknownSignals: true
        function onFloorsChanged() {
            root.rebuildCandidates();
        }
    }

    // Consume clicks behind the modal. No outside-click auto-dismiss:
    // an unresolved mismatch cannot silently become an executable turn.
    Rectangle {
        anchors.fill: parent
        color: "#D91B0623"

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }
    }

    component RecoveryButton: Rectangle {
        id: control

        property string title: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool armed: false
        signal triggered()

        height: 36
        color: armed ? Colors.orange : Colors.black
        border.width: mouse.containsMouse || armed ? 2 : 1
        border.color: armed ? Colors.red : accent
        opacity: enabledAction ? 1 : 0.38
        radius: 2

        GohuText {
            anchors.centerIn: parent
            text: control.title
            font.pixelSize: 10
            color: control.armed ? Colors.black : control.accent
            elide: Text.ElideRight
            width: parent.width - 14
            horizontalAlignment: Text.AlignHCenter
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: control.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: control.triggered()
        }
    }

    Rectangle {
        id: dialog
        anchors.centerIn: parent
        width: Math.max(280, Math.min(parent.width - 28, 790))
        height: Math.max(260, Math.min(parent.height - 28, 676))
        color: Colors.dark
        border.width: 2
        border.color: Colors.orange
        radius: 4

        Flickable {
            id: scroll
            anchors.fill: parent
            anchors.margins: 18
            clip: true
            contentWidth: width
            contentHeight: layout.implicitHeight
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: layout
                width: scroll.width
                spacing: 11

                Row {
                    width: parent.width
                    spacing: 10

                    GohuText {
                        text: "⚠  HOSPITAL // BED RECOVERY"
                        font.pixelSize: 15
                        color: Colors.orange
                        width: parent.width - 10
                        wrapMode: Text.WordWrap
                    }
                }

                GohuText {
                    width: parent.width
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    text: "DOCTOR EXECUTION PAUSED. No provider turn is allowed until the registered Room and real Git Bed match."
                }

                Rectangle {
                    width: parent.width
                    height: summary.implicitHeight + 20
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.red

                    Column {
                        id: summary
                        width: parent.width - 20
                        anchors.centerIn: parent
                        spacing: 5

                        GohuText {
                            width: parent.width
                            text: "ROOM // " + (root.roomId || "UNKNOWN")
                                  + "  ·  " + (root.expectedRepository || "NO PATIENT")
                            font.pixelSize: 10
                            color: Colors.cyan
                            elide: Text.ElideMiddle
                        }
                        GohuText {
                            width: parent.width
                            text: "EXPECTED // " + (root.expectedBranch || "NO BRANCH")
                            font.pixelSize: 10
                            color: Colors.orange
                            elide: Text.ElideMiddle
                        }
                        GohuText {
                            width: parent.width
                            text: "CURRENT // " + (root.currentBedBranch || "NO BED")
                                  + "  ·  " + (root.currentBedPath || "UNSELECTED")
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideMiddle
                        }
                        GohuText {
                            width: parent.width
                            text: "REFUSED // " + (root.mismatchCode || "TARGET_MISMATCH")
                            font.pixelSize: 9
                            color: Colors.red
                            elide: Text.ElideRight
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 8

                    GohuText {
                        width: parent.width - searchButton.width - 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.scanning
                              ? "SEARCHING LOCAL GIT BEDS..."
                              : "COMPATIBLE BED CANDIDATES // " + root.candidates.length
                        font.pixelSize: 10
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    RecoveryButton {
                        id: searchButton
                        title: root.scanning ? "SCANNING" : "SEARCH AGAIN"
                        width: 140
                        enabledAction: !root.scanning
                        onTriggered: root.scan()
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 132
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    clip: true

                    ListView {
                        id: results
                        anchors.fill: parent
                        anchors.margins: 5
                        model: root.candidates
                        spacing: 4
                        clip: true

                        delegate: Rectangle {
                            id: candidateRow
                            required property var modelData
                            required property int index
                            readonly property var candidate: modelData
                            readonly property bool picked:
                                String(candidate.path || "") === root.selectedPath
                            width: ListView.view.width
                            height: 43
                            color: picked ? Colors.dark : Colors.black
                            border.color: picked ? Colors.orange : Colors.cyan
                            border.width: picked ? 2 : 1

                            Column {
                                anchors.fill: parent
                                anchors.margins: 5
                                spacing: 2

                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 10
                                    color: candidateRow.picked ? Colors.orange : Colors.cyan
                                    text: String(candidateRow.candidate.label || "BED")
                                          + (candidateRow.candidate.isLive ? " // LIVE" : "")
                                          + (candidateRow.candidate.dirty ? " // DIRTY" : "")
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 9
                                    color: Colors.white
                                    text: String(candidateRow.candidate.path || "")
                                    elide: Text.ElideMiddle
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedPath =
                                    String(candidateRow.candidate.path || "")
                            }
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        width: parent.width - 20
                        visible: !root.scanning && root.candidates.length === 0
                        text: "NO MATCH IN KNOWN BEDS // CREATE OR REGISTER A BED"
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        color: Colors.orange
                        font.pixelSize: 10
                    }
                }

                GohuText {
                    width: parent.width
                    text: "Inventory matches are CANDIDATES, not execution clearance. PX must verify the target again before launching a Doctor."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }

                RecoveryButton {
                    width: parent.width
                    title: root.selectedCandidate
                           ? "USE SELECTED BED // KEEP MESSAGE UNSENT"
                           : "SELECT A COMPATIBLE BED ABOVE"
                    accent: Colors.cyan
                    enabledAction: Boolean(root.selectedCandidate)
                    onTriggered: root.selectBedRequested(root.selectedCandidate)
                }

                Row {
                    width: parent.width
                    spacing: 8

                    RecoveryButton {
                        width: (parent.width - 8) / 2
                        title: "CREATE NEW BED"
                        accent: Colors.cyan
                        enabledAction: Boolean(root.expectedRepository
                                               && root.expectedBranch)
                        onTriggered: root.createBedRequested(
                            root.expectedRepository, root.expectedBranch
                        )
                    }

                    RecoveryButton {
                        width: (parent.width - 8) / 2
                        title: "BROWSE / REGISTER BED"
                        accent: Colors.cyan
                        onTriggered: root.registerBedRequested()
                    }
                }

                RecoveryButton {
                    width: parent.width
                    title: root.moveArmed
                           ? "CONFIRM MOVE REQUEST // SAFE CHECKS STILL APPLY"
                           : "FORCE MOVE REQUEST // KEEP GIT SAFETY CHECKS"
                    accent: root.moveArmed ? Colors.orange : Colors.yellow
                    armed: root.moveArmed
                    enabledAction: root.movePolicy.eligible
                    onTriggered: {
                        if (!root.moveArmed) {
                            root.moveArmed = true;
                            return;
                        }
                        root.moveArmed = false;
                        root.moveBedRequested(
                            root.currentBedPath, root.expectedBranch
                        );
                    }
                }

                GohuText {
                    width: parent.width
                    text: root.movePolicy.eligible
                          ? "Movement still requires a fresh dirty/occupancy/worker check. LIVE Beds require the existing second confirmation."
                          : "MOVE UNAVAILABLE // " + root.movePolicy.reason
                            + ". Create a separate Bed instead."
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    color: root.movePolicy.eligible ? Colors.white : Colors.orange
                }

                Row {
                    width: parent.width
                    spacing: 8

                    RecoveryButton {
                        width: (parent.width - 8) / 2
                        title: "VIEW ROOM // NO AI"
                        accent: Colors.cyan
                        onTriggered: root.inspectOnlyRequested()
                    }

                    RecoveryButton {
                        width: (parent.width - 8) / 2
                        title: "CANCEL // KEEP DRAFT"
                        accent: Colors.red
                        onTriggered: root.cancel()
                    }
                }
            }
        }
    }
}
