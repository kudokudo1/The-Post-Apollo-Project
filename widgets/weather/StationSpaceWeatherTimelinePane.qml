import QtQuick

// COSMOS V1 // expands existing SPACE submode with read-only history
// while retaining the original StationSpace instruments below.
Rectangle {
    id: timeline
    color: Colors.black

    property string subjectRoute: ""
    property var spaceService: null
    property var weatherService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0

    readonly property int historyRevision:
        liveHistoryStore ? Number(liveHistoryStore.revision)||0 : 0
    readonly property var windSamples: {
        historyRevision;
        return liveHistoryStore && typeof liveHistoryStore.samples==="function"
             ? liveHistoryStore.samples("space-wind","global",runtimeNowMs)
             : [];
    }
    readonly property var imfSamples: {
        historyRevision;
        return liveHistoryStore && typeof liveHistoryStore.samples==="function"
             ? liveHistoryStore.samples("space-imf","global",runtimeNowMs)
             : [];
    }

    StationInteractiveHistoryChart {
        id: observationChart
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 258
        title: "COSMOS // SOLAR WIND + IMF BZ // OBSERVED HISTORY"
        leftTitle: "SOLAR WIND"
        leftUnit: "KM/S"
        leftField: "solarWindSpeed"
        leftSamples: timeline.windSamples
        rightTitle: "IMF BZ"
        rightUnit: "NT"
        rightField: "bz"
        rightSamples: timeline.imfSamples
        runtimeNowMs: timeline.runtimeNowMs
    }

    // No second source acquisition: this is the unchanged route-filtered
    // original SPACE component with its standard source activation gates.
    StationSpace {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: observationChart.bottom
        anchors.topMargin: 6
        anchors.bottom: parent.bottom
        subjectRoute: timeline.subjectRoute
        spaceService: timeline.spaceService
        weatherService: timeline.weatherService
        liveHistoryStore: timeline.liveHistoryStore
        runtimeNowMs: timeline.runtimeNowMs
    }
}
