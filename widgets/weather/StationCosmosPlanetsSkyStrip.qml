import QtQuick
import "../../components"
import "StationCosmosDetailPolicy.js" as Details
import "StationCosmosPlanetDayWheelPolicy.js" as DayWheel
import "StationCosmosPlanetSummaryPolicy.js" as Summary

// C39 // One compact, source-backed current USNO celestial observation.
// The 12-field C6 inspector stays available through DETAILS, not squeezed
// into unreadable cells or replaced by synthetic astronomical predictions.
Rectangle {
    id: strip
    objectName: "cosmos-c39-sky-now-strip"
    clip: true
    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan
    property var celestialSource: null
    property var datedRows: []
    property string civilDate: ""
    property bool datedSourceReady: false
    property string selectedPlanet: "ALL"
    signal planetPicked(string name)
    signal detailsRequested(int index)

    readonly property var snapshot: celestialSource && celestialSource.ready
        ? celestialSource.snapshot : null
    readonly property var records: Details.records("planets",snapshot,null,null,false)
    readonly property int recordCount: records.length
    readonly property int selectablePlanetCount: DayWheel.PLANETS.length
    readonly property var reading: Summary.selection(
        selectedPlanet,records,datedRows,civilDate,
        !!celestialSource && celestialSource.ready,
        datedSourceReady,snapshot ? snapshot.time : "")
    readonly property int currentIndex: {
        if (!recordCount) return -1;
        if (selectedPlanet === "ALL") return 0;
        for (let i=0;i<recordCount;i++) {
            if (String(records[i].name || "").toUpperCase() === selectedPlanet)
                return i;
        }
        return -1;
    }
    readonly property var currentRecord: currentIndex >= 0
        ? records[currentIndex] : null
    readonly property string selectedName: reading.planet
    readonly property string sourceNote: reading.sourceNote
    readonly property bool detailAvailable: reading.detailAvailable
    readonly property string utcSample: snapshot
        ? String(snapshot.time || "--") + "Z" : "--"
    function stepPlanet(delta) {
        const target = DayWheel.adjacentPlanet(selectedPlanet, delta);
        if (target) planetPicked(target);
    }

    Row {
        id: line
        anchors.fill: parent
        anchors.margins: 3
        spacing: 3
        readonly property real unit: Math.max(1,(width-7*spacing))
        ActionButton {
            objectName: "cosmos-c39-sky-prev"
            width: line.unit*0.07
            height: line.height
            label: "◀"
            labelPixelSize: 9
            contentPadding: 0
            available: strip.selectablePlanetCount>0
            onClicked: strip.stepPlanet(-1)
        }
        Column {
            width: line.unit*0.20
            height: line.height
            spacing: 1
            QuietText {
                width: parent.width;height: 10
                text: strip.reading.mode === "current"
                    ? "SKY NOW // USNO" : "CIVIL DAY // USNO"
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width;height: 17
                text: strip.selectedName
                color: Colors.yellow
                font.pixelSize: 11
                elide: Text.ElideRight
            }
        }
        ActionButton {
            objectName: "cosmos-c39-sky-next"
            width: line.unit*0.07
            height: line.height
            label: "▶"
            labelPixelSize: 9
            contentPadding: 0
            available: strip.selectablePlanetCount>0
            onClicked: strip.stepPlanet(1)
        }
        Column {
            width: line.unit*0.13;height: line.height;spacing: 1
            QuietText {
                width: parent.width;height: 10
                text: strip.reading.labels[0];color: Colors.cyan
                font.pixelSize: 8;elide: Text.ElideRight
            }
            GohuText {
                width: parent.width;height: 17
                text: strip.currentRecord
                    ? Details.degrees(strip.currentRecord.altitude)
                    : strip.reading.values[0]
                color: Colors.white;font.pixelSize: 11;elide: Text.ElideRight
            }
        }
        Column {
            width: line.unit*0.13;height: line.height;spacing: 1
            QuietText {
                width: parent.width;height: 10
                text: strip.reading.labels[1];color: Colors.cyan
                font.pixelSize: 8;elide: Text.ElideRight
            }
            GohuText {
                width: parent.width;height: 17
                text: strip.currentRecord
                    ? Details.degrees(strip.currentRecord.azimuth)
                    : strip.reading.values[1]
                color: Colors.white;font.pixelSize: 11;elide: Text.ElideRight
            }
        }
        Column {
            width: line.unit*0.10;height: line.height;spacing: 1
            QuietText {
                width: parent.width;height: 10
                text: strip.reading.labels[2];color: Colors.cyan
                font.pixelSize: 8;elide: Text.ElideRight
            }
            GohuText {
                width: parent.width;height: 17
                text: strip.currentRecord
                    ? Details.text(strip.currentRecord.direction)
                    : strip.reading.values[2]
                color: Colors.white;font.pixelSize: 10;elide: Text.ElideRight
            }
        }
        Column {
            width: line.unit*0.17;height: line.height;spacing: 1
            QuietText {
                width: parent.width;height: 10
                text: strip.sourceNote
                color: strip.currentRecord ? Colors.cyan : Colors.orange
                font.pixelSize: 8;elide: Text.ElideRight
            }
            QuietText {
                width: parent.width;height: 17
                text: strip.reading.stamp
                color: Colors.white;font.pixelSize: 9;elide: Text.ElideRight
            }
        }
        ActionButton {
            objectName: "cosmos-c39-sky-details"
            width: line.unit*0.13
            height: line.height
            label: "DETAILS"
            labelPixelSize: 8
            contentPadding: 0
            accentColor: Colors.magenta
            available: strip.detailAvailable
            onClicked: strip.detailsRequested(strip.currentIndex)
        }
    }
}
