import QtQuick
import Quickshell
import "../../components"

// The B6 catalog is read-only. A separate explicit user tap resolves an
// installed DesktopEntry by its exact ID and requests launch through Qt's
// existing Quickshell DesktopEntry API. Browsing never executes programs.
Item {
    id: appsMini

    property var appsSnapshot: null
    property string launchFeedback: ""

    // Only a deliberate left-click on a visible installed app may execute.
    // The catalog itself carries metadata, not commands or launch handles.
    function launchApp(item) {
        if (!catalogReady || !item || typeof item.id !== "string")
            return false;
        const id = item.id;
        if (!entries.some(function(candidate) {
            return candidate && candidate.id === id;
        }))
            return false;
        const target = DesktopEntries.byId(id);
        if (!target || target.id !== id || target.noDisplay === true
                || typeof target.execute !== "function") {
            launchFeedback = "APP UNAVAILABLE";
            return false;
        }
        try {
            target.execute();
            // An accepted request is not proof that a window opened.
            launchFeedback = "LAUNCH REQUESTED";
            return true;
        } catch (error) {
            launchFeedback = "LAUNCH FAILED";
            console.warn("APOLLO HUB APP LAUNCH:", String(error));
            return false;
        }
    }

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
        launchFeedback.length > 0 ? "APPS // " + launchFeedback
        : catalogReady
        ? (shownCount === 0 ? "APPS // NO MATCHES"
           : "APPS // " + shownCount + " SHOWN // CLICK TO LAUNCH")
        : "APPS // " + catalogState.toUpperCase()

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
        // Scrolling only browses; direct user taps request one exact-ID
        // application launch. No selection or opening-time autostart.
        delegate: Item {
            id: appEntry
            required property var modelData
            width: appGrid.cellWidth
            height: appGrid.cellHeight

            HoverHandler {
                id: appHover
            }
            Rectangle {
                anchors.fill: parent
                color: appHover.hovered ? Colors.orange : "transparent"
                opacity: 0.13
            }
            TapHandler {
                acceptedButtons: Qt.LeftButton
                onTapped: appsMini.launchApp(appEntry.modelData)
            }

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
