import QtQuick
import Quickshell
import "../../components"

// Stage 8F: passive browsing of the existing bounded desktop-entry index.
// No launch, full desktop scan, external navigation or process control.
Item {
    id: appsExplore
    property var appsSnapshot: null
    // AppControl already owns and refreshes its ProcessTelemetry.
    property var processSnapshot: null
    property var processActionGate: null
    signal inputFocusChanged(bool focused)
    property bool appControlAvailable: false
    signal openAppControlRequested()
    property string selectedView: "catalog"
    property string selectedId: ""
    readonly property int densityLevel: height >= 300 ? 3 : 2
    readonly property string catalogState:
        appsSnapshot && appsSnapshot.state
        ? String(appsSnapshot.state) : "unavailable"
    readonly property bool catalogReady: catalogState === "ready"
    readonly property var entries:
        catalogReady && appsSnapshot && Array.isArray(appsSnapshot.items)
        ? appsSnapshot.items : []
    readonly property int shownCount: entries.length
    readonly property int installedCount:
        appsSnapshot && typeof appsSnapshot.installedCount === "number"
        && isFinite(appsSnapshot.installedCount)
        ? Math.max(0, Math.floor(appsSnapshot.installedCount)) : 0
    readonly property int matchCount:
        appsSnapshot && typeof appsSnapshot.matchCount === "number"
        && isFinite(appsSnapshot.matchCount)
        ? Math.max(0, Math.floor(appsSnapshot.matchCount)) : 0
    readonly property bool truncated:
        catalogReady && appsSnapshot.truncated === true
    readonly property string catalogQuery:
        appsSnapshot && typeof appsSnapshot.query === "string"
        ? appsSnapshot.query : ""
    readonly property var selectedEntry: {
        if (!catalogReady || selectedId === "")
            return null;
        for (let i = 0; i < entries.length; ++i) {
            const entry = entries[i];
            if (entry && entry.id === selectedId)
                return entry;
        }
        return null;
    }
    readonly property bool detailReady: selectedEntry !== null
    readonly property bool detailMode: selectedView === "details"
    readonly property bool runningMode: selectedView === "running"
    readonly property string statusLine:
        runningMode ? processExplore.statusLine
        : detailMode ? (detailReady
                      ? "APPS // DETAILS ONLY // NO APP LAUNCHED"
                      : "APPS // SELECTED ENTRY UNAVAILABLE")
        : !catalogReady ? "APPS // " + catalogState.toUpperCase()
        : shownCount === 0 ? "APPS // NO MATCHES"
        : truncated ? "APPS // FIRST " + shownCount + " OF "
                      + matchCount + " MATCHES // READ ONLY"
        : "APPS // " + shownCount + " BROWSE RESULTS // READ ONLY"

    function inspectEntry(item) {
        if (!catalogReady || !item || typeof item.id !== "string")
            return;
        const id = item.id;
        if (!entries.some(function(entry) {
            return entry && entry.id === id;
        }))
            return;
        selectedId = id;
        selectedView = "details";
    }

    Row {
        id: selector
        width: parent.width
        height: appsExplore.densityLevel === 3 ? 30 : 26
        spacing: 5
        ActionButton {
            width: Math.max(1, (selector.width - selector.spacing * 2) / 3)
            height: parent.height
            label: "CATALOG"
            selected: !appsExplore.detailMode
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: appsExplore.selectedView = "catalog"
        }
        ActionButton {
            width: Math.max(1, (selector.width - selector.spacing * 2) / 3)
            height: parent.height
            label: "DETAILS"
            selected: appsExplore.detailMode
            available: appsExplore.detailReady
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: appsExplore.selectedView = "details"
        }
        ActionButton {
            width: Math.max(1, (selector.width - selector.spacing * 2) / 3)
            height: parent.height
            label: "RUNNING"
            selected: appsExplore.runningMode
            trackLabelGlowLocally: true
            softGlowEnabled: false
            onLeftClicked: appsExplore.selectedView = "running"
        }
    }

    ApolloHubProcessesExplore {
        id: processExplore
        visible: appsExplore.runningMode
        processSnapshot: appsExplore.processSnapshot
        processActionGate: appsExplore.processActionGate
        onInputFocusChanged: function(focused) {
            appsExplore.inputFocusChanged(focused);
        }
        anchors.top: selector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }

    Item {
        id: catalogPane
        visible: !appsExplore.detailMode && !appsExplore.runningMode
        anchors.top: selector.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        GohuText {
            id: countLine
            width: parent.width
            height: 18
            font.pixelSize: 10
            color: appsExplore.catalogReady ? Colors.cyan : Colors.orange
            elide: Text.ElideRight
            text: "INDEX // " + appsExplore.installedCount + " INSTALLED // "
                  + appsExplore.matchCount + " MATCHES // "
                  + appsExplore.shownCount + " SHOWN"
        }
        GohuText {
            id: limitLine
            anchors.top: countLine.bottom
            anchors.topMargin: 2
            width: parent.width
            height: 15
            font.pixelSize: 10
            color: Colors.orange
            elide: Text.ElideRight
            text: appsExplore.truncated
                  ? "FIRST " + appsExplore.shownCount + " OF "
                    + appsExplore.matchCount + " MATCHES"
                  : appsExplore.catalogQuery.length > 0
                    ? "FILTERED // " + appsExplore.catalogQuery
                    : "TAP APP TO INSPECT // NEVER LAUNCHES"
        }
        ListView {
            id: appList
            anchors.top: limitLine.bottom
            anchors.topMargin: 5
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            clip: true
            spacing: 3
            boundsBehavior: Flickable.StopAtBounds
            visible: appsExplore.catalogReady && appsExplore.shownCount > 0
            model: appsExplore.entries
            delegate: Rectangle {
                id: appRow
                required property var modelData
                width: appList.width
                height: appsExplore.densityLevel === 3 ? 40 : 33
                radius: 0
                color: appRow.modelData.id === appsExplore.selectedId
                       ? Colors.black : "transparent"
                border.width: appRow.modelData.id === appsExplore.selectedId ? 1 : 0
                border.color: Colors.magenta
                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onTapped: appsExplore.inspectEntry(appRow.modelData)
                }
                Image {
                    id: appIcon
                    anchors.left: parent.left
                    anchors.leftMargin: 3
                    anchors.verticalCenter: parent.verticalCenter
                    width: 21
                    height: 21
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    source: Quickshell.iconPath(
                        appRow.modelData.icon || "application-x-executable",
                        "application-x-executable")
                }
                GohuText {
                    anchors.left: appIcon.right
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.top: parent.top
                    height: 19
                    font.pixelSize: 13
                    color: Colors.white
                    elide: Text.ElideRight
                    text: String(appRow.modelData.name || "UNKNOWN")
                }
                GohuText {
                    anchors.left: appIcon.right
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 14
                    font.pixelSize: 10
                    color: Colors.cyan
                    elide: Text.ElideRight
                    text: String(appRow.modelData.genericName
                                 || appRow.modelData.id || "")
                }
            }
        }
        GohuText {
            anchors.centerIn: appList
            width: appList.width
            height: 25
            visible: !appList.visible
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            color: Colors.orange
            text: !appsExplore.catalogReady
                  ? "CATALOG // " + appsExplore.catalogState.toUpperCase()
                  : "NO MATCHES"
        }
    }

    Item {
        visible: appsExplore.detailMode
        anchors.top: selector.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        Column {
            width: parent.width
            height: childrenRect.height
            anchors.centerIn: parent
            spacing: appsExplore.densityLevel === 3 ? 12 : 7
            Image {
                width: appsExplore.densityLevel === 3 ? 44 : 32
                height: width
                anchors.horizontalCenter: parent.horizontalCenter
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                source: Quickshell.iconPath(
                    appsExplore.detailReady && appsExplore.selectedEntry.icon
                    ? appsExplore.selectedEntry.icon : "application-x-executable",
                    "application-x-executable")
            }
            GohuText {
                width: parent.width
                height: appsExplore.densityLevel === 3 ? 34 : 26
                font.pixelSize: appsExplore.densityLevel === 3 ? 22 : 18
                color: appsExplore.detailReady ? Colors.white : Colors.orange
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: appsExplore.detailReady
                      ? String(appsExplore.selectedEntry.name) : "APP NOT IN INDEX"
            }
            GohuText {
                width: parent.width
                height: 23
                font.pixelSize: 12
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: appsExplore.detailReady
                      ? "TYPE // " + String(appsExplore.selectedEntry.genericName || "UNSPECIFIED")
                      : "SELECT AN APP IN CATALOG"
            }
            GohuText {
                width: parent.width
                height: 23
                font.pixelSize: 11
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideMiddle
                text: appsExplore.detailReady
                      ? "DESKTOP ID // " + String(appsExplore.selectedEntry.id)
                      : "DESKTOP ID // UNAVAILABLE"
            }
            GohuText {
                width: parent.width
                height: 20
                font.pixelSize: 11
                color: Colors.orange
                horizontalAlignment: Text.AlignHCenter
                text: "READ ONLY // NO APP LAUNCHED"
            }
            Row {
                width: parent.width
                height: 29
                spacing: 5
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "RUNNING CONTROLS"
                    labelPixelSize: 10
                    available: true
                    trackLabelGlowLocally: true
                    softGlowEnabled: false
                    // Deliberate navigation into the original owner window;
                    // does NOT target a PID or freeze/kill anything.
                    onLeftClicked: appsExplore.selectedView = "running"
                }
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "BACK TO CATALOG"
                    labelPixelSize: 10
                    trackLabelGlowLocally: true
                    softGlowEnabled: false
                    onLeftClicked: appsExplore.selectedView = "catalog"
                }
            }
        }
    }
}
