import QtQuick
import "../../components"
import "StationCosmosPlanetSummaryPolicy.js" as Summary

// C41 // Details when a body was not in the instantaneous USNO CelNav
// sample. These are real, source-dated MRST events, NOT current bearings.
Rectangle {
    id: dated
    objectName: "cosmos-c41-dated-planet-details"
    color: Colors.black
    clip: true
    property var datedRows: []
    property string civilDate: ""
    property string selectedPlanet: "ALL"
    property bool sourceReady: false
    property string sourceStatus: "USNO MRST WAITING"
    readonly property string resolvedName:
        Summary.selectedName(selectedPlanet,[],datedRows)
    readonly property var selectedRow: sourceReady
        ? Summary.datedRow(datedRows,resolvedName,civilDate) : null
    readonly property var facts: Summary.datedFacts(
        selectedRow,civilDate,resolvedName)
    readonly property int renderedFactCount: factRepeater.count
    GohuText {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 19
        font.pixelSize: 11
        color: Colors.magenta
        text: "PLANETS // USNO CIVIL-DAY RECORD // " + dated.resolvedName
        elide: Text.ElideRight
    }
    QuietText {
        id: note
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.topMargin: 3
        height: 14
        font.pixelSize: 9
        color: dated.sourceReady ? Colors.cyan : Colors.orange
        text: dated.sourceReady
            ? "DATED RISE / TRANSIT / SET // NOT A CURRENT-SKY POSITION"
            : dated.sourceStatus
        elide: Text.ElideRight
    }
    Grid {
        id: factsGrid
        objectName: "cosmos-c41-dated-fact-grid"
        anchors.top: note.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 4
        columns: 3
        spacing: 3
        Repeater {
            id: factRepeater
            model: dated.facts
            delegate: Rectangle {
                required property var modelData
                objectName: "cosmos-c41-dated-fact"
                width: Math.max(1,(factsGrid.width-2*factsGrid.spacing)/3)
                height: Math.max(1,(factsGrid.height-3*factsGrid.spacing)/4)
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue
                Column {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 2
                    QuietText {
                        width: parent.width
                        height: 12
                        font.pixelSize: 8
                        color: Colors.cyan
                        text: parent.parent.modelData.label
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        height: Math.max(1,parent.height-14)
                        font.pixelSize: 10
                        color: Colors.white
                        text: parent.parent.modelData.value
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
    QuietText {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 15
        font.pixelSize: 8
        text: "USNO MRST // LOCAL CIVIL DATE // NO CURRENT ALTITUDE, AZIMUTH OR VISIBILITY INFERRED"
        color: Colors.orange
        elide: Text.ElideRight
    }
}
