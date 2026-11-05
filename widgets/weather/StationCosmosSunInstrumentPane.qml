import QtQuick
import "../../components"

// Focused single-viewport NOAA instruments. StationSpace sourceOnly owns
// ALL fetchers and SUVI URL state; this component only draws their data.
Rectangle {
    id: solarFocus
    color: Colors.black
    clip: true

    property string modeRoute: ""
    property var sourceSpace: null
    property var spaceService: null
    readonly property string mode: modeRoute.split("/").slice(-1)[0]
    readonly property var xray: sourceSpace ? sourceSpace.xrayObservation : null
    readonly property var flares: sourceSpace ? sourceSpace.flareObservation : null
    readonly property var cycle: sourceSpace ? sourceSpace.cycleObservation : null

    function reading(value, digits) {
        return value !== null && value !== undefined
               && isFinite(Number(value))
               ? Number(value).toFixed(digits) : "--";
    }
    function flareInk(letter) {
        return letter === "X" ? Colors.magenta
             : letter === "M" ? Colors.orange
             : letter === "C" ? Colors.yellow : Colors.cyan;
    }

    Loader {
        anchors.fill: parent
        sourceComponent: solarFocus.mode === "suvi" ? suviMode
            : solarFocus.mode === "xray" ? xrayMode
            : solarFocus.mode === "flares" ? flareMode
            : solarFocus.mode === "cycle" ? cycleMode
            : unavailableMode
    }

    Component {
        id: suviMode
        Column {
            anchors.fill: parent
            spacing: 6
            Row {
                id: imageControls
                width: parent.width
                height: 25
                spacing: 5
                Repeater {
                    model: [
                        {name:"195 Å",key:"195"},
                        {name:"THERMAL",key:"map"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(imageControls.width-94)/2)
                        height: 25
                        label: modelData.name
                        labelPixelSize: 10
                        contentPadding: 1
                        selected: !!solarFocus.sourceSpace
                            && solarFocus.sourceSpace.solarImageMode === modelData.key
                        onClicked: {
                            if (solarFocus.sourceSpace)
                                solarFocus.sourceSpace.selectSolarImageMode(modelData.key);
                        }
                    }
                }
                ActionButton {
                    width: 84
                    height: 25
                    label: "REFRESH"
                    labelPixelSize: 9
                    contentPadding: 1
                    accentColor: Colors.orange
                    onClicked: {
                        if (solarFocus.sourceSpace)
                            solarFocus.sourceSpace.refreshSolarImage();
                    }
                }
            }
            Row {
                id: imageBody
                width: parent.width
                height: Math.max(0,parent.height-imageControls.height-6)
                spacing: 8
                Rectangle {
                    id: imageFrame
                    width: Math.max(1,Math.min(imageBody.height,imageBody.width*0.58))
                    height: imageBody.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta
                    clip: true
                    Image {
                        anchors.fill: parent
                        anchors.margins: 3
                        source: solarFocus.sourceSpace
                            ? solarFocus.sourceSpace.solarImageUrl : ""
                        asynchronous: true
                        cache: false
                        fillMode: Image.PreserveAspectFit
                        onStatusChanged: {
                            if (!solarFocus.sourceSpace) return;
                            if (status === Image.Ready) {
                                solarFocus.sourceSpace.solarImageLastLoadedMs = Date.now();
                                solarFocus.sourceSpace.solarImageError = "";
                            } else if (status === Image.Error) {
                                solarFocus.sourceSpace.solarImageError =
                                    "SUVI IMAGE LOAD FAILED";
                            }
                        }
                    }
                }
                Column {
                    width: Math.max(1,imageBody.width-imageFrame.width-imageBody.spacing)
                    spacing: 8
                    GohuText {
                        width: parent.width
                        text: solarFocus.sourceSpace
                              ? solarFocus.sourceSpace.solarImageInfo.title
                              : "NOAA SWPC // SUVI"
                        color: Colors.yellow
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: solarFocus.sourceSpace
                              ? solarFocus.sourceSpace.solarImageInfo.detail
                              : "SOURCE NOT CONNECTED"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    QuietText {
                        width: parent.width
                        text: solarFocus.sourceSpace
                            && solarFocus.sourceSpace.solarImageError !== ""
                            ? solarFocus.sourceSpace.solarImageError
                            : "LATEST NOAA IMAGE // NOT LOCAL AIR TEMPERATURE"
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    Component {
        id: xrayMode
        Column {
            anchors.fill: parent
            spacing: 7
            GohuText {
                text: "GOES X-RAY // LIVE OBSERVATION"
                color: Colors.magenta
                font.pixelSize: 12
            }
            Row {
                width: parent.width
                height: 79
                spacing: 7
                Repeater {
                    model: [
                        {name:"LONG BAND // 0.1-0.8 NM",
                         value:solarFocus.xray && solarFocus.xray.ready
                           ? solarFocus.xray.classEquivalent.label : "--",
                         detail:solarFocus.xray && solarFocus.xray.ready
                           ? solarFocus.reading(solarFocus.xray.fluxLong,9)+" W/M²"
                           : "NO SAMPLE"},
                        {name:"SHORT BAND // 0.05-0.4 NM",
                         value:solarFocus.xray && solarFocus.xray.ready
                           ? solarFocus.reading(solarFocus.xray.fluxShort,9) : "--",
                         detail:"W/M² // GOES XRS"}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(parent.width-7)/2)
                        height: 79
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 5
                            SecondaryText {text:modelData.name;font.pixelSize:9}
                            GohuText {
                                text:modelData.value
                                font.pixelSize:22
                                color:Colors.white
                            }
                            QuietText {text:modelData.detail;font.pixelSize:9}
                        }
                    }
                }
            }
            QuietText {
                text: solarFocus.xray && solarFocus.xray.ready
                    ? "SAMPLE "+solarFocus.xray.sampleUtc
                      +" // "+(solarFocus.xray.sampleFresh ? "FRESH" : "STALE")
                    : "NOAA GOES XRS // WAITING OR UNAVAILABLE"
                color: Colors.orange
                font.pixelSize:9
            }
            Item {
                width: parent.width
                height: Math.max(1,parent.height-140)
                Row {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: parent.height
                    spacing: 3
                    Repeater {
                        model:solarFocus.xray && solarFocus.xray.ready
                            ? solarFocus.xray.trend : []
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.max(1,(parent.width-11*parent.spacing)/12)
                            height: Math.max(3,(parent.height-3)*modelData.level)
                            color: solarFocus.flareInk(modelData.classLetter)
                        }
                    }
                }
            }
        }
    }

    Component {
        id: flareMode
        Column {
            anchors.fill: parent
            spacing: 7
            GohuText {
                text:"GOES X-RAY FLARE EVENTS // 7-DAY FEED"
                color:Colors.magenta
                font.pixelSize:12
            }
            Row {
                width:parent.width
                height:73
                spacing:7
                Rectangle {
                    width:Math.max(1,parent.width*0.48)
                    height:73
                    color:Colors.dark
                    border.width:1
                    border.color:Colors.magenta
                    Column {
                        anchors.fill:parent
                        anchors.margins:6
                        spacing:4
                        SecondaryText {text:"LATEST DETECTED PEAK";font.pixelSize:9}
                        GohuText {
                            text:solarFocus.flares && solarFocus.flares.latest
                                ? solarFocus.flares.latest.classLabel : "--"
                            font.pixelSize:26
                            color:Colors.orange
                        }
                    }
                }
                Rectangle {
                    width:Math.max(1,parent.width*0.52-7)
                    height:73
                    color:Colors.dark
                    border.width:1
                    border.color:Colors.cyan
                    Column {
                        anchors.fill:parent
                        anchors.margins:6
                        spacing:5
                        SecondaryText {text:"LAST 24 HOURS";font.pixelSize:9}
                        GohuText {
                            text:solarFocus.flares && solarFocus.flares.ready
                                ? solarFocus.flares.count24h
                                    +" EVENTS // "+solarFocus.flares.cPlus24h+" C+"
                                : "-- EVENTS"
                            font.pixelSize:14
                            color:Colors.white
                        }
                    }
                }
            }
            Row {
                id: flareCards
                width:parent.width
                height:Math.max(0,parent.height-116)
                spacing:6
                Repeater {
                    model:solarFocus.flares && solarFocus.flares.ready
                        ? solarFocus.flares.events : []
                    delegate: Rectangle {
                        required property var modelData
                        width:Math.max(1,(flareCards.width-12)/3)
                        height:Math.max(1,flareCards.height)
                        color:Colors.dark
                        border.width:1
                        border.color:solarFocus.flareInk(modelData.classLetter)
                        Column {
                            anchors.fill:parent
                            anchors.margins:6
                            spacing:5
                            GohuText {
                                text:modelData.classLabel
                                font.pixelSize:17
                                color:solarFocus.flareInk(modelData.classLetter)
                            }
                            QuietText {
                                width:parent.width
                                text:modelData.satellite
                                font.pixelSize:9
                                elide:Text.ElideRight
                            }
                            QuietText {
                                width:parent.width
                                text:modelData.peakUtc
                                font.pixelSize:9
                                wrapMode:Text.WordWrap
                            }
                        }
                    }
                }
            }
            QuietText {
                text:solarFocus.flares && solarFocus.flares.ready
                    ? "NOAA GOES // OBSERVED EVENT PEAKS, NOT ALERTS"
                    : "GOES EVENTS // WAITING OR UNAVAILABLE"
                color:Colors.cyan
                font.pixelSize:9
            }
        }
    }

    Component {
        id: cycleMode
        Column {
            anchors.fill:parent
            spacing:7
            GohuText {
                text:"SOLAR CYCLE // NOAA MONTHLY PREDICTIONS"
                color:Colors.magenta
                font.pixelSize:12
            }
            Grid {
                id: cycleGrid
                width:parent.width
                columns:2
                spacing:7
                Repeater {
                    model: [
                        {name:"MODEL MONTH",
                         value:solarFocus.cycle && solarFocus.cycle.ready
                           ? solarFocus.cycle.summary.modelMonth : "--"},
                        {name:"PREDICTED SUNSPOT NUMBER",
                         value:solarFocus.cycle && solarFocus.cycle.ready
                           ? solarFocus.reading(solarFocus.cycle.summary.predictedSsn,1) : "--"},
                        {name:"PREDICTED F10.7 // SFU",
                         value:solarFocus.cycle && solarFocus.cycle.ready
                           ? solarFocus.reading(solarFocus.cycle.summary.predictedFlux,1) : "--"},
                        {name:"PREDICTED CYCLE PEAK",
                         value:solarFocus.cycle && solarFocus.cycle.ready
                           ? solarFocus.cycle.summary.peakMonth : "--"}
                    ]
                    delegate:Rectangle {
                        required property var modelData
                        width:Math.max(1,(cycleGrid.width-7)/2)
                        height:Math.max(58,(solarFocus.height-47)/2)
                        color:Colors.dark
                        border.width:1
                        border.color:Colors.yellow
                        Column {
                            anchors.fill:parent
                            anchors.margins:7
                            spacing:7
                            SecondaryText {
                                width:parent.width
                                text:modelData.name
                                font.pixelSize:9
                                elide:Text.ElideRight
                            }
                            GohuText {
                                width:parent.width
                                text:modelData.value
                                color:Colors.white
                                font.pixelSize:17
                                elide:Text.ElideRight
                            }
                        }
                    }
                }
            }
            QuietText {
                text:solarFocus.cycle && solarFocus.cycle.ready
                    ? "NOAA PREDICTION // NOT LIVE SOLAR FLUX"
                    : "NOAA MODEL // WAITING OR UNAVAILABLE"
                color:Colors.cyan
                font.pixelSize:9
            }
        }
    }

    Component {
        id: unavailableMode
        QuietText {
            text:"SOLAR INSTRUMENT UNAVAILABLE"
            color:Colors.orange
            font.pixelSize:12
        }
    }
}
