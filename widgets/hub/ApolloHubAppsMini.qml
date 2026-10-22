import QtQuick
import Quickshell
import "../../components"

// B6: read-only native DesktopEntries catalog projection.
// This component cannot execute, choose, or launch an application. Launch
// actions require their own separately authorized launcher integration.
Item {
    id: appsMini

    property var appsSnapshot: null

    readonly property string catalogState:
        appsSnapshot && appsSnapshot.state
        ? String(appsSnapshot.state) : "unavailable"
    readonly property bool catalogReady: catalogState === "ready"
    readonly property var entries:
        catalogReady && appsSnapshot && Array.isArray(appsSnapshot.items)
        ? appsSnapshot.items : []
    readonly property int installedCount:
        appsSnapshot && typeof appsSnapshot.installedCount === "number"
        && isFinite(appsSnapshot.installedCount)
        ? Math.max(0, appsSnapshot.installedCount) : 0
    readonly property int matchCount:
        appsSnapshot && typeof appsSnapshot.matchCount === "number"
        && isFinite(appsSnapshot.matchCount)
        ? Math.max(0, appsSnapshot.matchCount) : 0
    readonly property int shownCount: entries.length
    readonly property bool truncated:
        catalogReady && appsSnapshot.truncated === true
    readonly property string catalogQuery:
        appsSnapshot && appsSnapshot.query ? String(appsSnapshot.query) : ""
    readonly property string summaryLine:
        catalogState === "unavailable" ? "APPLICATION INDEX // UNAVAILABLE"
        : catalogState === "empty" ? "APPLICATION INDEX // EMPTY"
        : catalogReady
          ? "INDEX // " + installedCount + " INSTALLED // "
            + matchCount + " MATCHES"
            + (truncated ? " // FIRST " + shownCount : "")
          : "APPLICATION INDEX // " + catalogState.toUpperCase()
    readonly property string statusLine:
        catalogReady
        ? (shownCount === 0 ? "APPS // NO MATCHES // READ ONLY"
           : "APPS // " + shownCount + " SHOWN // READ ONLY")
        : "APPS // " + catalogState.toUpperCase() + " // READ ONLY"

    GohuText {
        id: counter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 16
        font.pixelSize: 10
        color: appsMini.catalogReady ? Colors.cyan : Colors.orange
        elide: Text.ElideRight
        text: appsMini.summaryLine
    }

    GridView {
        id: appGrid
        anchors {
            left: parent.left
            right: parent.right
            top: counter.bottom
            bottom: parent.bottom
        }
        clip: true
        visible: appsMini.catalogReady && appsMini.shownCount > 0
        model: appsMini.entries
        readonly property int columns:
            width >= 660 ? 3 : width >= 370 ? 2 : 1
        cellWidth: Math.max(1, Math.floor(width / columns))
        cellHeight: 27
        flow: GridView.FlowLeftToRight
        boundsBehavior: Flickable.StopAtBounds
        // Scrolling browses metadata; there are deliberately no click or
        // double-click handlers, launch commands, or player-like controls.
        delegate: Item {
            id: appEntry
            required property var modelData
            width: appGrid.cellWidth
            height: appGrid.cellHeight

            Image {
                id: appIcon
                anchors {
                    left: parent.left
                    leftMargin: 2
                    verticalCenter: parent.verticalCenter
                }
                width: 18
                height: 18
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                source: Quickshell.iconPath(
                    appEntry.modelData.icon || "application-x-executable",
                    "application-x-executable")
            }
            GohuText {
                anchors {
                    left: appIcon.right
                    leftMargin: 7
                    right: parent.right
                    rightMargin: 10
                    verticalCenter: parent.verticalCenter
                }
                height: 19
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                font.pixelSize: 12
                color: Colors.white
                text: String(appEntry.modelData.name || "UNKNOWN")
            }
        }
    }

    GohuText {
        anchors.centerIn: appGrid
        width: parent.width
        height: 28
        visible: !appGrid.visible
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 12
        color: Colors.orange
        text: appsMini.catalogReady ? "NO MATCHES"
              : appsMini.catalogState === "empty" ? "NO APPLICATIONS"
              : appsMini.catalogState === "unavailable"
                ? "CATALOG UNAVAILABLE" : "CATALOG " + appsMini.catalogState.toUpperCase()
    }
}
