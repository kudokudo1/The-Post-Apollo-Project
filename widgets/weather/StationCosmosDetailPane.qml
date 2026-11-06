import QtQuick
import "../../components"
import "StationCosmosDetailPolicy.js" as Details

// C6 // Complete inspectable provider records in one stationary subject bay.
// Item selection + DATA 1/3..3/3 replace long scrolling reports.
// Raw SKY/ISS/ECLIPSE sources remain owned by StationSky.
Rectangle {
    id: detailsPane
    objectName: "cosmos-c6-record-detail"
    color: Colors.black
    clip: true
    property string kind: ""
    property var celestialSource: null
    property var issSource: null
    property var eclipseSource: null
    property string sourceStatus: "SOURCE WAITING"
    property bool starsAsNav: false
    property int selectedIndex: 0
    property int factPage: 0

    readonly property var snapshot:
        celestialSource && celestialSource.ready ? celestialSource.snapshot : null
    readonly property var records: Details.records(
        kind, snapshot,
        issSource && issSource.ready ? issSource : null,
        eclipseSource && eclipseSource.ready ? eclipseSource : null,
        starsAsNav)
    readonly property int recordCount: records.length
    readonly property var selectedRecord:
        selectedIndex >= 0 && selectedIndex < records.length
        ? records[selectedIndex] : null
    readonly property var facts: Details.fields(
        kind, selectedRecord,
        ({snapshot:snapshot, eclipse:eclipseSource}), starsAsNav)
    readonly property var visibleFacts: Details.page(facts,factPage)
    readonly property string selectedName:
        Details.rowName(kind,selectedRecord,starsAsNav)
    readonly property int renderedFactCount: factGridRepeater.count

    onKindChanged: { selectedIndex=0; factPage=0; starsAsNav=false; }
    onStarsAsNavChanged: { selectedIndex=0; factPage=0; }
    onRecordCountChanged: {
        if (selectedIndex >= recordCount)
            selectedIndex = Math.max(0,recordCount-1);
    }

    GohuText {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 19
        color: Colors.magenta
        font.pixelSize: 11
        elide: Text.ElideRight
        text: kind === "planets" ? "PLANETS // USNO CURRENT SKY"
            : kind === "stars" ? "STARS // USNO NAVIGATION SNAPSHOT"
            : kind === "iss" ? "ISS // GEOMETRIC PASS PREDICTIONS"
            : "ECLIPSES // NASA GSFC GLOBAL CALENDAR"
    }

    Row {
        id: recordControls
        anchors.top: header.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        height: 24
        spacing: 4

        ActionButton {
            width: 56
            height: 23
            contentPadding: 1
            label: "PREV"
            labelPixelSize: 9
            available: detailsPane.recordCount > 1
            onClicked: detailsPane.selectedIndex = (detailsPane.selectedIndex
                - 1 + detailsPane.recordCount) % detailsPane.recordCount
        }
        ActionButton {
            width: 56
            height: 23
            contentPadding: 1
            label: "NEXT"
            labelPixelSize: 9
            available: detailsPane.recordCount > 1
            onClicked: detailsPane.selectedIndex = (detailsPane.selectedIndex
                + 1) % detailsPane.recordCount
        }
        QuietText {
            width: Math.max(1,recordControls.width-120
                            -(detailsPane.kind === "stars" ? 100 : 0))
            height: 23
            verticalAlignment: Text.AlignVCenter
            text: detailsPane.recordCount > 0
                ? (detailsPane.selectedIndex+1)+"/"+detailsPane.recordCount
                  + " // ALL RECORDS"
                : "0 RECORDS"
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        ActionButton {
            visible: detailsPane.kind === "stars"
            width: visible ? 96 : 0
            height: 23
            contentPadding: 1
            label: detailsPane.starsAsNav ? "NAV STARS" : "ANCHORS"
            labelPixelSize: 9
            selected: true
            accentColor: Colors.magenta
            onClicked: detailsPane.starsAsNav = !detailsPane.starsAsNav
        }
    }
    Rectangle {
        id: mainReading
        anchors.top: recordControls.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        height: 37
        color: Colors.dark
        border.width: 1
        border.color: detailsPane.recordCount ? Colors.magenta : Colors.orange
        Column {
            anchors.fill: parent
            anchors.margins: 4
            spacing: 2
            GohuText {
                width: parent.width
                text: detailsPane.recordCount
                    ? detailsPane.selectedName : detailsPane.sourceStatus
                color: detailsPane.recordCount ? Colors.white : Colors.orange
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                text: detailsPane.recordCount
                    ? (detailsPane.kind === "stars"
                       ? "CURRENT USNO NAV STAR SAMPLE"
                       : detailsPane.kind === "planets"
                       ? "ALTITUDE + AZIMUTH // OBSERVATION"
                       : detailsPane.kind === "iss"
                       ? "RISE / PEAK / SET // PREDICTION"
                       : "DATE + TYPE // GLOBAL EVENT ONLY")
                    : "NO PROVIDER RECORDS TO INSPECT"
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }
    Grid {
        id: factGrid
        anchors.top: mainReading.bottom
        anchors.topMargin: 4
        anchors.bottom: factControls.top
        anchors.bottomMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        columns: 2
        spacing: 5
        Repeater {
            id: factGridRepeater
            model: detailsPane.recordCount > 0 ? 4 : 0
            delegate: Rectangle {
                objectName: "cosmos-c6-observation-cell"
                required property int index
                readonly property var factData:
                    detailsPane.visibleFacts && detailsPane.visibleFacts.length > index
                    ? detailsPane.visibleFacts[index] : null
                width: Math.max(1,(factGrid.width-factGrid.spacing)/2)
                height: Math.max(1,(factGrid.height-factGrid.spacing)/2)
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                Column {
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 4
                    SecondaryText {
                        width: parent.width
                        text: factData ? factData.label : "--"
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: factData ? factData.value : "--"
                        color: Colors.white
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
    Row {
        id: factControls
        anchors.bottom: sourceNote.top
        anchors.bottomMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        height: 23
        spacing: 4
        ActionButton {
            width: 68
            height: 23
            contentPadding: 1
            label: "DATA <"
            labelPixelSize: 9
            available: detailsPane.recordCount > 0
            onClicked: detailsPane.factPage = (detailsPane.factPage+2)%3
        }
        ActionButton {
            width: 68
            height: 23
            contentPadding: 1
            label: "DATA >"
            labelPixelSize: 9
            available: detailsPane.recordCount > 0
            onClicked: detailsPane.factPage = (detailsPane.factPage+1)%3
        }
        QuietText {
            height: 23
            width: Math.max(1,factControls.width-144)
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 9
            color: Colors.yellow
            text: "DETAIL "+(detailsPane.factPage+1)+"/3 // "
                +(detailsPane.recordCount > 0 ? detailsPane.sourceStatus : "--")
            elide: Text.ElideRight
        }
    }
    QuietText {
        id: sourceNote
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 14
        color: Colors.orange
        font.pixelSize: 8
        text: Details.disclaimer(detailsPane.kind,detailsPane.starsAsNav)
        elide: Text.ElideRight
    }
}
