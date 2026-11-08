import QtQuick
import "../../components"

// C26 // NASA GSFC eclipse terminal: permanent solar/lunar summaries over
// one bounded catalog. The existing twelve-fact inspector remains available
// only by selecting a record, without changing the widget's outer size.
Item {
    id: eclipseBoard
    objectName: "cosmos-c26-eclipse-board"
    clip: true
    property var eclipseSource: null
    property string sourceStatus: "SOURCE WAITING"
    property bool inspecting: false
    property bool motionPlaying: true
    property bool showArchive: false

    StationCosmosDetailPane {
        id: eclipseDetails
        anchors.fill: parent
        z: 5
        visible: eclipseBoard.inspecting
        kind: "eclipses"
        eclipseSource: eclipseBoard.eclipseSource
        sourceStatus: eclipseBoard.sourceStatus
    }

    // Read-only interface retains C6 native source/record acceptance.
    readonly property int recordCount: eclipseDetails.recordCount
    readonly property var records: eclipseDetails.records
    readonly property var facts: eclipseDetails.facts
    readonly property int renderedFactCount: eclipseDetails.renderedFactCount
    property alias selectedIndex: eclipseDetails.selectedIndex

    function inspectRecord(index) {
        if (index < 0 || index >= recordCount) return;
        selectedIndex = index;
        inspecting = true;
    }
    function inspectFeatured(row) {
        if (!row) return;
        for (let i=0;i<records.length;i++) {
            const item = records[i];
            if (item && item.date === row.date
                && item.event === row.event && item.body === row.body) {
                inspectRecord(i);
                return;
            }
        }
    }

    Column {
        id: fixedEclipseHeader
        objectName: "cosmos-c26-eclipse-sticky-header"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5

        Row {
            objectName: "cosmos-c31-eclipse-visual-controls"
            width: parent.width
            height: 18
            spacing: 5
            GohuText {
                text: "ECLIPSES // NASA GSFC"
                width: Math.max(1,parent.width-199)
                color: Colors.magenta
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            QuietText {
                width: 100
                text: eclipseBoard.eclipseSource && eclipseBoard.eclipseSource.ready
                    ? "GLOBAL UTC // " + eclipseBoard.recordCount + " EVENTS"
                    : eclipseBoard.sourceStatus
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
            ActionButton {
                objectName: "cosmos-c31-archive-toggle"
                width: 42
                height: 18
                contentPadding: 0
                labelPixelSize: 8
                label: eclipseBoard.showArchive ? "SCENE" : "PHOTO"
                accentColor: Colors.orange
                onClicked: eclipseBoard.showArchive = !eclipseBoard.showArchive
            }
            ActionButton {
                objectName: "cosmos-c31-motion-play-pause"
                width: 42
                height: 18
                contentPadding: 0
                labelPixelSize: 8
                label: eclipseBoard.motionPlaying ? "PAUSE" : "PLAY"
                accentColor: Colors.cyan
                onClicked: eclipseBoard.motionPlaying = !eclipseBoard.motionPlaying
            }
        }

        Row {
            id: eclipseFeaturedRow
            objectName: "cosmos-c26-eclipse-highlight-row"
            width: parent.width
            height: 103
            spacing: 6
            Repeater {
                model: 2
                delegate: Rectangle {
                    id: eclipseHighlight
                    objectName: "cosmos-c26-eclipse-highlight"
                    required property int index
                    readonly property var record:
                        eclipseBoard.eclipseSource && eclipseBoard.eclipseSource.ready
                        ? (index === 0 ? eclipseBoard.eclipseSource.nextSolar
                                       : eclipseBoard.eclipseSource.nextLunar)
                        : null
                    width: Math.max(1,(eclipseFeaturedRow.width-eclipseFeaturedRow.spacing)/2)
                    height: eclipseFeaturedRow.height
                    color: Colors.dark
                    border.width: 1
                    border.color: index === 0 ? Colors.orange : Colors.cyan
                    clip: true

                    Row {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 4
                        StationCosmosEclipseMotion {
                            objectName: "cosmos-c31-featured-eclipse-motion"
                            width: Math.min(87, Math.max(1,parent.width*0.43))
                            height: parent.height
                            body: eclipseHighlight.index === 0 ? "SOLAR" : "LUNAR"
                            eventRecord: eclipseHighlight.record
                            playing: eclipseBoard.motionPlaying && !eclipseBoard.inspecting
                            showArchive: eclipseBoard.showArchive
                        }
                        Item {
                            width: Math.max(1,parent.width-Math.min(87,parent.width*0.43)-4)
                            height: parent.height
                            Column {
                                anchors.fill: parent
                                spacing: 5
                                SecondaryText {
                                    width: parent.width
                                    text: eclipseHighlight.index === 0 ? "NEXT SOLAR" : "NEXT LUNAR"
                                    color: Colors.cyan
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: eclipseHighlight.record
                                        ? String(eclipseHighlight.record.event || "ECLIPSE")
                                        : "NO EVENT IN WINDOW"
                                    color: eclipseHighlight.index === 0
                                        ? Colors.orange : Colors.white
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: eclipseHighlight.record
                                        ? String(eclipseHighlight.record.date || "--") + " UTC"
                                        : "DATE --"
                                    color: Colors.white
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    text: eclipseHighlight.record
                                        && eclipseHighlight.record.daysUntil !== undefined
                                        && eclipseHighlight.record.daysUntil !== null
                                        ? "IN " + eclipseHighlight.record.daysUntil + " DAYS"
                                        : "DAYS --"
                                    color: Colors.cyan
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    text: "CLICK TO INSPECT"
                                    color: Colors.orange
                                    font.pixelSize: 8
                                    elide: Text.ElideRight
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: eclipseHighlight.record !== null
                                cursorShape: Qt.PointingHandCursor
                                onClicked: eclipseBoard.inspectFeatured(eclipseHighlight.record)
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: eclipseCatalogFrame
        objectName: "cosmos-c26-eclipse-catalog-frame"
        anchors.top: fixedEclipseHeader.bottom
        anchors.topMargin: 6
        anchors.bottom: eclipseSourceCaveat.top
        anchors.bottomMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        clip: true

        GohuText {
            id: eclipseCatalogTitle
            anchors.left: parent.left
            anchors.leftMargin: 6
            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.top: parent.top
            anchors.topMargin: 4
            height: 13
            color: Colors.magenta
            font.pixelSize: 9
            text: "ECLIPSE CALENDAR // SELECT EVENT TO INSPECT"
            elide: Text.ElideRight
        }

        QuietText {
            anchors.centerIn: parent
            width: Math.max(1,parent.width-24)
            visible: !eclipseBoard.eclipseSource
                || !eclipseBoard.eclipseSource.ready
                || eclipseBoard.recordCount === 0
            text: eclipseBoard.sourceStatus === "SOURCE RECEIVED"
                ? "NO ECLIPSES IN THE SOURCE WINDOW"
                : eclipseBoard.sourceStatus
            color: Colors.orange
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        Flickable {
            id: eclipseScroll
            objectName: "cosmos-c26-eclipse-catalog-scroll"
            anchors.top: eclipseCatalogTitle.bottom
            anchors.topMargin: 3
            anchors.left: parent.left
            anchors.leftMargin: 5
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 5
            clip: true
            contentWidth: width
            contentHeight: eclipseRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: eclipseRows
                width: eclipseScroll.width
                spacing: 4
                Repeater {
                    model: eclipseBoard.recordCount
                    delegate: Rectangle {
                        objectName: "cosmos-c26-eclipse-event-card"
                        required property int index
                        readonly property var eventData:
                            index < eclipseBoard.records.length ? eclipseBoard.records[index] : null
                        width: eclipseRows.width
                        height: 39
                        color: Colors.dark
                        border.width: 1
                        border.color: eclipseBoard.selectedIndex === index
                            ? Colors.yellow
                            : eventData && eventData.body === "SOLAR"
                                ? Colors.orange : Colors.cyan
                        Row {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 6
                            Column {
                                width: Math.max(1,parent.width*0.57)
                                spacing: 3
                                GohuText {
                                    width: parent.width
                                    text: eventData ? String(eventData.event || "--") : "--"
                                    color: Colors.white
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    text: eventData ? String(eventData.body || "--")
                                        + " // " + String(eventData.phase || "--") : "--"
                                    color: Colors.cyan
                                    font.pixelSize: 8
                                    elide: Text.ElideRight
                                }
                            }
                            Column {
                                width: Math.max(1,parent.width*0.39)
                                spacing: 3
                                GohuText {
                                    width: parent.width
                                    text: eventData ? String(eventData.date || "--") : "--"
                                    color: Colors.orange
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    text: eventData && eventData.daysUntil !== undefined
                                        && eventData.daysUntil !== null
                                        ? "IN " + eventData.daysUntil + " DAYS"
                                        : "DAYS --"
                                    color: Colors.cyan
                                    font.pixelSize: 8
                                    elide: Text.ElideRight
                                }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: eclipseBoard.inspectRecord(index)
                        }
                    }
                }
            }
        }
        NeonScrollBar {
            flickable: eclipseScroll
            geometryHost: eclipseCatalogFrame
            handleStyle: "star"
            visible: scrollable
        }
    }

    QuietText {
        id: eclipseSourceCaveat
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 12
        text: "GLOBAL EVENT // LOCAL VISIBILITY + CONTACTS NOT CALCULATED"
        color: Colors.orange
        font.pixelSize: 8
        elide: Text.ElideRight
    }

    ActionButton {
        objectName: "cosmos-c26-eclipse-back"
        visible: eclipseBoard.inspecting
        z: 6
        anchors.top: parent.top
        anchors.right: parent.right
        width: 100
        height: 19
        contentPadding: 1
        label: "BACK TO EVENTS"
        labelPixelSize: 8
        onClicked: eclipseBoard.inspecting = false
    }
}
