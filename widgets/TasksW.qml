import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "hub"
import "tasks"
import qs.services.hub

// TASKS M3: reuses Hub's local checklist editor and single guarded store.
// Other modes remain placeholders. Keep the window mapped with an empty
// input mask while closed to avoid layer-shell remapping crashes.
PanelWindow {
    id: root

    property bool menuOpen: false
    property real dockCenterX: 0
    property real chassisTopY: 0
    signal openGithubProjectsRequested()

    // Reuse the FinanceW/TimeW 9:16 pilot geometry until live review.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12

    // M2: five main modes share one window and one truthful empty-state view.
    // Text-only labels are provisional until the user approves mode artwork.
    readonly property var mainModes: [
        { id: "tasks", label: "TASKS",
          emptyTitle: "NO TASKS LOADED",
          emptyDetail: "LOCAL CHECKLIST" },
        { id: "today", label: "TODAY",
          emptyTitle: "TODAY // NO FEED",
          emptyDetail: "DAILY TASKS // NOT CONNECTED" },
        { id: "projects", label: "PROJECTS",
          emptyTitle: "PROJECTS // NO FEED",
          emptyDetail: "GITHUB PROJECTS // NOT CONNECTED" },
        { id: "planner", label: "PLANNER",
          emptyTitle: "PLANNER // NO FEED",
          emptyDetail: "SCHEDULE // NOT CONNECTED" },
        { id: "sync", label: "SYNC",
          emptyTitle: "SYNC // NO FEED",
          emptyDetail: "SYNC CONTROLS // NOT CONNECTED" }
    ]
    property int selectedMainModeIndex: 0
    readonly property var activeMode: mainModes[selectedMainModeIndex]

    // Keep task storage shared with ApolloHub. This menu does not create a
    // FileView, storage service, or parallel task document.
    readonly property string taskStoreState:
        ApolloHubTodoStore.snapshot
        ? ApolloHubTodoStore.snapshot.state : "loading"
    readonly property string feedStatus:
        activeMode.id === "sync" ? "PREVIEW"
        : activeMode.id !== "tasks" && activeMode.id !== "today"
        && activeMode.id !== "projects"
        && activeMode.id !== "planner" ? "NO FEED"
        : taskStoreState === "ready" || taskStoreState === "empty" ? "LOCAL"
        : taskStoreState === "saving" ? "SAVING"
        : taskStoreState === "loading" ? "READING"
        : taskStoreState === "unsupported" ? "UNSUP"
        : "LOCKED"
    readonly property color feedColor:
        feedStatus === "LOCAL" || feedStatus === "PREVIEW" ? Colors.cyan
        : feedStatus === "SAVING" ? Colors.magenta
        : Colors.orange

    function selectMainMode(index) {
        if (index >= 0 && index < mainModes.length)
            selectedMainModeIndex = index;
    }

    function toggle() {
        menuOpen = !menuOpen;
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    // Align with the Git/Hospital panel top, and clamp to the screen.
    margins {
        top: Math.max(0, Math.round(root.chassisTopY - root.glowGutter))
        left: Math.max(0, Math.min(
            Math.max(0, root.screen ? root.screen.width - root.implicitWidth : 0),
            Math.round(root.dockCenterX - root.implicitWidth / 2)
        ))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    // TextInput needs keyboard focus, but only while the TASKS page is open.
    // OnDemand does not request an indefinite exclusive keyboard lock.
    WlrLayershell.keyboardFocus:
        root.menuOpen && (root.activeMode.id === "tasks"
                          || root.activeMode.id === "projects"
                          || root.activeMode.id === "planner")
        ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: root.menuOpen && (root.activeMode.id === "tasks"
                                 || root.activeMode.id === "projects"
                                 || root.activeMode.id === "planner")

    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.glowGutter
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: tasksFrame
        anchors.fill: parent
        anchors.margins: root.glowGutter
        visible: root.menuOpen

        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0

        glowVisible: root.menuOpen
        glowColor: Colors.cyan

        Rectangle {
            id: tasksHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.right: feedBadge.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: "TASKS // " + root.activeMode.label
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            // Local store health for TASKS; reserved pages have no feed.
            Rectangle {
                id: feedBadge
                width: 68
                height: 26
                anchors.right: closeButton.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.dark
                border.width: 1
                border.color: root.feedColor

                GohuText {
                    anchors.centerIn: parent
                    text: root.feedStatus
                    font.pixelSize: 9
                    color: root.feedColor
                }
            }

            ActionButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 34
                height: 32
                label: "×"
                labelPixelSize: 22
                contentPadding: 4
                accentColor: Colors.red
                destructive: true
                onLeftClicked: root.menuOpen = false
            }
        }

        Rectangle {
            id: tasksDivider
            anchors.top: tasksHeader.bottom
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            height: 2
            color: Colors.cyan
        }

        // Shared main-mode rail, following FinanceW's vertical arrangement.
        // ModeButton owns its hover/selected/click effects; borders are off.
        Column {
            id: mainModeRail
            anchors.top: tasksDivider.bottom
            anchors.topMargin: 12
            anchors.left: parent.left
            anchors.leftMargin: 8
            width: 104
            spacing: 6

            Repeater {
                model: root.mainModes

                ModeButton {
                    required property var modelData
                    required property int index
                    width: mainModeRail.width
                    height: 56
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 12
                    bordered: false
                    selected: root.selectedMainModeIndex === index
                    onTriggered: root.selectMainMode(index)
                }
            }
        }

        // Navigation/content separator, aligned to the existing mode rail.
        // Independent flat glow under a crisp cyan rule, no extra focus target.
        Rectangle {
            id: mainModeRailGlow
            anchors.top: mainModeRail.top
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 14
            anchors.left: mainModeRail.right
            anchors.leftMargin: 5
            width: 6
            color: Colors.cyan
            opacity: 0.12
        }
        Rectangle {
            id: mainModeVerticalDivider
            anchors.top: mainModeRail.top
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 14
            anchors.horizontalCenter: mainModeRailGlow.horizontalCenter
            width: 1
            color: Colors.cyan
        }

        // Shared content frame, with a live local editor only in TASKS mode.
        Item {
            id: mainModeContent
            anchors.top: tasksDivider.bottom
            anchors.topMargin: 12
            anchors.left: mainModeRail.right
            anchors.leftMargin: 16
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 14

            Column {
                visible: root.activeMode.id !== "tasks" && root.activeMode.id !== "today"
                         && root.activeMode.id !== "projects"
                         && root.activeMode.id !== "planner"
                         && root.activeMode.id !== "sync"
                anchors.centerIn: parent
                width: parent.width
                spacing: 12

                GohuText {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: root.activeMode.emptyTitle
                    font.pixelSize: 16
                    font.bold: true
                    color: Colors.white
                }

                GohuText {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: root.activeMode.emptyDetail
                    font.pixelSize: 11
                    color: Colors.cyan
                }
            }

            // The same presentation already used by ApolloHub's To-do tile.
            // Explicit clicks initiate the single store's guarded, atomic
            // asynchronous writes. A pending write is never called "saved".
            ApolloHubTodoMini {
                id: taskEditor
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.min(350, mainModeContent.height * 0.53)
                visible: root.menuOpen && root.activeMode.id === "tasks"
                todoStore: ApolloHubTodoStore
                todoSnapshot: ApolloHubTodoStore.snapshot
                onTaskSelected: function(taskId) {
                    taskDetails.chooseTask(taskId);
                }
            }

            TaskDetailsPane {
                id: taskDetails
                anchors.top: taskEditor.bottom
                anchors.topMargin: 10
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                visible: root.menuOpen && root.activeMode.id === "tasks"
                todoStore: ApolloHubTodoStore
                todoSnapshot: ApolloHubTodoStore.snapshot
            }

            // TODAY is a view of existing due dates, not another task store.
            TaskTodayPane {
                id: taskToday
                anchors.fill: parent
                visible: root.menuOpen && root.activeMode.id === "today"
                todoSnapshot: ApolloHubTodoStore.snapshot
                onOpenTaskRequested: function(taskId) {
                    root.selectMainMode(0);
                    taskDetails.chooseTask(taskId);
                }
            }

            // Local project groups and task assignment share the one Hub
            // task store. These are not remote GitHub Projects records.
            TaskProjectsPane {
                id: taskProjects
                anchors.fill: parent
                visible: root.menuOpen && root.activeMode.id === "projects"
                todoStore: ApolloHubTodoStore
                todoSnapshot: ApolloHubTodoStore.snapshot
                onOpenTaskRequested: function(taskId) {
                    root.selectMainMode(0);
                    taskDetails.chooseTask(taskId);
                }
            }

            // PLANNER M3 is a read-only local calendar over the existing Hub
            // task snapshot. OPEN reuses TASKS details, without new persistence.
            TaskPlannerPane {
                id: taskPlanner
                anchors.fill: parent
                visible: root.menuOpen && root.activeMode.id === "planner"
                todoSnapshot: ApolloHubTodoStore.snapshot
                todoStore: ApolloHubTodoStore
                onOpenTaskRequested: function(taskId) {
                    root.selectMainMode(0);
                    taskDetails.chooseTask(taskId);
                }
            }

            // M9a SYNC Overview exposes local mapping and a navigation route
            // to GitW's EXISTING GitHub Projects surface. No remote service
            // or write capability is attached to this window.
            TaskSyncConnectionsPane {
                id: taskSyncConnections
                anchors.fill: parent
                visible: root.menuOpen && root.activeMode.id === "sync"
                todoSnapshot: ApolloHubTodoStore.snapshot
                onOpenGithubProjectsRequested: root.openGithubProjectsRequested()
            }
        }
    }
}
