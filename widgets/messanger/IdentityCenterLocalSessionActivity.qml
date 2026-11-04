import QtQuick
import "../../components"

// Observable CURRENT QML session only. No persisted audit log.
// Sources report outcomes only after their original operations complete.
Column {
    id: activity
    property var saveFeedback: null
    property var refreshPanel: null
    property var backupPanel: null
    property bool recordingEnabled: true

    property var entries: []
    property int nextSequence: 1
    property bool showAll: false
    readonly property int entryCount: entries.length
    readonly property var visibleEntries: showAll ? entries : entries.slice(0, 6)
    spacing: 6

    function appendEvent(kind, source, detail) {
        if (!recordingEnabled)
            return false;
        const allowed = ["saved", "failure", "conflict", "unconfirmed",
                         "loaded", "refresh", "backup", "validation", "listing"];
        if (!allowed.includes(kind))
            return false;
        const entry = {
            sequence: nextSequence++,
            observedAt: Qt.formatDateTime(new Date(), "HH:mm:ss"),
            kind: String(kind),
            source: String(source).slice(0, 100),
            detail: String(detail).slice(0, 320)
        };
        entries = [entry].concat(entries).slice(0, 40);
        return true;
    }

    Connections {
        target: activity.saveFeedback
        function onActivityObserved(kind, source, detail) {
            activity.appendEvent(kind, source, detail);
        }
    }
    Connections {
        target: activity.refreshPanel
        function onActivityObserved(kind, detail) {
            activity.appendEvent(kind, "Refresh All", detail);
        }
    }
    Connections {
        target: activity.backupPanel
        function onActivityObserved(kind, detail) {
            activity.appendEvent(kind, "Private Backups", detail);
        }
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "CURRENT SESSION ACTIVITY // OBSERVED OUTCOMES"
        font.pixelSize: 11
        font.bold: true
        color: Colors.white
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Only outcomes observed while this Settings view exists. " +
              "No past edit timeline, actor identity or server audit log is stored. " +
              "Times indicate when this screen observed a result."
        font.pixelSize: 9
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 6
        IdentityCenterLocalActionButton {
            role: "navigate"
            objectName: "orgSessionShowAll"
            width: 155
            height: 28
            label: activity.showAll ? "SHOW RECENT SIX" : "SHOW SESSION EVENTS"
            labelPixelSize: 9
            interactive: activity.entryCount > 6
            onTriggered: activity.showAll = !activity.showAll
        }
        IdentityCenterLocalActionButton {
            role: "danger"
            objectName: "orgSessionClearView"
            width: 151
            height: 28
            label: "CLEAR SESSION VIEW"
            labelPixelSize: 9
            interactive: activity.entryCount > 0
            onTriggered: {
                activity.entries = [];
                activity.showAll = false;
            }
        }
    }
    Text {
        width: parent.width
        text: "OBSERVED EVENTS // " + activity.entryCount +
              " (at most 40 held in this view)"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: activity.entryCount === 0
        text: "No completed local operations observed in this session yet."
        font.pixelSize: 10
        color: Colors.white
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: activity.visibleEntries
        delegate: Column {
            id: activityRow
            required property var modelData
            width: activity.width
            spacing: 3
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.2
            }
            Text {
                width: parent.width
                font.pixelSize: 10
                font.bold: true
                color: activityRow.modelData.kind === "failure"
                        || activityRow.modelData.kind === "conflict"
                        || activityRow.modelData.kind === "unconfirmed"
                       ? Colors.red
                       : activityRow.modelData.kind === "saved"
                         || activityRow.modelData.kind === "validation"
                         || activityRow.modelData.kind === "refresh"
                         ? Colors.green
                       : activityRow.modelData.kind === "backup"
                         ? Colors.yellow
                       : Colors.white
                text: activityRow.modelData.observedAt +
                      " // " + activityRow.modelData.kind.toUpperCase() +
                      " // " + activityRow.modelData.source
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                font.pixelSize: 9
                color: Colors.white
                text: activityRow.modelData.detail
                wrapMode: Text.WordWrap
            }
        }
    }
}
