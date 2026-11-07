import QtQuick
import "../../components"
import "StationCosmosSolarDetailPolicy.js" as SolarDetails
import "StationSolarImageViewportPolicy.js" as ImageViewportPolicy

// Focused single-viewport NOAA instruments. StationSpace sourceOnly owns
// ALL fetchers and SUVI URL state; this component only draws their data.
Rectangle {
    id: solarFocus
    color: Colors.black
    clip: true

    property string modeRoute: ""
    property var sourceSpace: null
    property var spaceService: null
    // Enabled by OBSERVATION only. Legacy INDEX SUVI remains unchanged.
    property bool imageInteractive: false
    property bool imageExpanded: false
    property real suviZoom: 1
    property real suviPanX: 0
    property real suviPanY: 0

    function resetSuviView() {
        suviZoom = 1;
        suviPanX = 0;
        suviPanY = 0;
    }

    onImageExpandedChanged: resetSuviView()
    readonly property string mode: modeRoute.split("/").slice(-1)[0]
    readonly property var xray: sourceSpace ? sourceSpace.xrayObservation : null
    readonly property var flares: sourceSpace ? sourceSpace.flareObservation : null
    readonly property var cycle: sourceSpace ? sourceSpace.cycleObservation : null
    property int xrayPage: 0
    property int flareIndex: 0
    property int flareDataPage: 0
    property int cyclePage: 0
    readonly property int flareCount: SolarDetails.flareCount(flares)
    readonly property var selectedFlare: SolarDetails.flareAt(flares,flareIndex)
    readonly property var flareFields: SolarDetails.flarePage(selectedFlare,flareDataPage)
    readonly property var cycleFields: SolarDetails.cyclePage(
        cycle && cycle.ready ? cycle.summary : null,cyclePage,
        spaceService ? spaceService.solarFluxText : "")
    readonly property var xrayFields: SolarDetails.xrayPage(
        xray && xray.ready ? xray : null,xrayPage)
    onModeRouteChanged: {
        xrayPage=0;flareIndex=0;flareDataPage=0;cyclePage=0;
        resetSuviView();
        imageExpanded=false;
    }
    onFlareCountChanged: {
        if (flareIndex >= flareCount) flareIndex = Math.max(0,flareCount-1);
    }

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
                    objectName: "cosmos-c16-suvi-viewport"
                    width: solarFocus.imageInteractive && solarFocus.imageExpanded
                        ? imageBody.width
                        : Math.max(1,Math.min(imageBody.height,imageBody.width*0.58))
                    height: imageBody.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta
                    clip: true
                    readonly property real currentZoom: solarFocus.suviZoom

                    function constrainPan() {
                        var pan = ImageViewportPolicy.clampPan(
                            solarFocus.suviZoom, solarFocus.suviPanX,
                            solarFocus.suviPanY, imageViewport.width,
                            imageViewport.height, focusedSuviImage.paintedWidth,
                            focusedSuviImage.paintedHeight);
                        solarFocus.suviPanX = pan.x;
                        solarFocus.suviPanY = pan.y;
                    }
                    function panBy(dx,dy) {
                        if (!solarFocus.imageInteractive || solarFocus.suviZoom<=1)
                            return;
                        var pan = ImageViewportPolicy.clampPan(
                            solarFocus.suviZoom,solarFocus.suviPanX+dx,
                            solarFocus.suviPanY+dy,imageViewport.width,
                            imageViewport.height,focusedSuviImage.paintedWidth,
                            focusedSuviImage.paintedHeight);
                        solarFocus.suviPanX = pan.x;
                        solarFocus.suviPanY = pan.y;
                    }
                    function zoomAt(factor,focusX,focusY) {
                        if (!solarFocus.imageInteractive) return;
                        var view = ImageViewportPolicy.zoomAt(
                            solarFocus.suviZoom,factor,
                            solarFocus.suviPanX,solarFocus.suviPanY,
                            focusX,focusY,imageViewport.width,
                            imageViewport.height,focusedSuviImage.paintedWidth,
                            focusedSuviImage.paintedHeight);
                        solarFocus.suviZoom = view.zoom;
                        solarFocus.suviPanX = view.x;
                        solarFocus.suviPanY = view.y;
                    }
                    function resetZoom() { solarFocus.resetSuviView(); }
                    onWidthChanged: constrainPan()
                    onHeightChanged: constrainPan()

                    Item {
                        id: imageViewport
                        anchors.fill: parent
                        anchors.margins: 3
                        clip: true
                        Image {
                            id: focusedSuviImage
                            width: parent.width
                            height: parent.height
                            x: solarFocus.suviPanX
                            y: solarFocus.suviPanY
                            scale: solarFocus.suviZoom
                            transformOrigin: Item.Center
                            source: solarFocus.sourceSpace
                                ? solarFocus.sourceSpace.solarImageUrl : ""
                            asynchronous: true
                            cache: false
                            fillMode: Image.PreserveAspectFit
                            onSourceChanged: solarFocus.resetSuviView()
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
                        MouseArea {
                            id: suviPointer
                            objectName: "cosmos-c16-suvi-pan-input"
                            anchors.fill: parent
                            enabled: solarFocus.imageInteractive
                            acceptedButtons: Qt.LeftButton
                            preventStealing: true
                            cursorShape: solarFocus.suviZoom > 1
                                ? Qt.OpenHandCursor : Qt.CrossCursor
                            property real lastX: 0
                            property real lastY: 0
                            onPressed: (mouse) => {
                                lastX = mouse.x;
                                lastY = mouse.y;
                            }
                            onPositionChanged: (mouse) => {
                                if (!pressed || solarFocus.suviZoom <= 1) return;
                                imageFrame.panBy(mouse.x-lastX,mouse.y-lastY);
                                lastX = mouse.x;
                                lastY = mouse.y;
                            }
                            onWheel: (wheel) => {
                                if (wheel.angleDelta.y !== 0)
                                    imageFrame.zoomAt(
                                        wheel.angleDelta.y > 0 ? 1.25 : 0.8,
                                        wheel.x,wheel.y);
                                wheel.accepted = true;
                            }
                            onDoubleClicked: imageFrame.resetZoom()
                        }
                    }
                    ActionButton {
                        objectName: "cosmos-c16-suvi-expand"
                        visible: solarFocus.imageInteractive
                        width: 38
                        height: 19
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 4
                        label: solarFocus.imageExpanded ? "REST" : "EXP"
                        labelPixelSize: 9
                        contentPadding: 1
                        accentColor: Colors.magenta
                        onClicked: solarFocus.imageExpanded = !solarFocus.imageExpanded
                    }
                    Row {
                        id: suviZoomControls
                        objectName: "cosmos-c16-suvi-zoom-controls"
                        visible: solarFocus.imageInteractive
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 3
                        spacing: 2
                        ActionButton {
                            width: 26; height: 19
                            label: "−"; labelPixelSize: 13; contentPadding: 1
                            available: solarFocus.suviZoom > 1
                            accentColor: Colors.cyan
                            onClicked: imageFrame.zoomAt(0.8,
                                imageViewport.width/2,imageViewport.height/2)
                        }
                        ActionButton {
                            width: 26; height: 19
                            label: "+"; labelPixelSize: 13; contentPadding: 1
                            available: solarFocus.suviZoom < 5
                            accentColor: Colors.cyan
                            onClicked: imageFrame.zoomAt(1.25,
                                imageViewport.width/2,imageViewport.height/2)
                        }
                        ActionButton {
                            width: 36; height: 19
                            label: "FIT"; labelPixelSize: 9; contentPadding: 1
                            accentColor: Colors.orange
                            onClicked: imageFrame.resetZoom()
                        }
                    }
                }
                Column {
                    id: imageNotes
                    visible: !solarFocus.imageExpanded || !solarFocus.imageInteractive
                    width: visible
                        ? Math.max(1,imageBody.width-imageFrame.width-imageBody.spacing)
                        : 0
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
                    QuietText {
                        width: parent.width
                        text: solarFocus.sourceSpace
                            ? "CHANNEL // "
                              +solarFocus.sourceSpace.solarImageInfo.shortLabel
                              +" // "+(focusedSuviImage.status === Image.Ready
                                  ? "IMAGE READY" : "IMAGE WAITING")
                            : "CHANNEL --"
                        color: Colors.orange
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        text: solarFocus.sourceSpace
                            && solarFocus.sourceSpace.solarImageLastLoadedMs > 0
                            ? "RECEIVED // "
                              +new Date(solarFocus.sourceSpace.solarImageLastLoadedMs)
                                  .toISOString().slice(0,16).replace("T"," ")+"Z"
                            : "RECEIVED // --"
                        color: Colors.cyan
                        font.pixelSize: 9
                        elide: Text.ElideRight
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
            Row {
                id: xrayModeBar
                width: parent.width
                height: 23
                spacing: 5
                Repeater {
                    model: [{label:"HISTORY",page:0},{label:"SOURCE",page:1}]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(xrayModeBar.width-82)/2)
                        height: 23
                        contentPadding: 1
                        label: modelData.label
                        labelPixelSize: 9
                        selected: solarFocus.xrayPage === modelData.page
                        accentColor: Colors.magenta
                        onClicked: solarFocus.xrayPage = modelData.page
                    }
                }
                ActionButton {
                    width: 70
                    height: 23
                    contentPadding: 1
                    label: "REFRESH"
                    labelPixelSize: 9
                    available: !!solarFocus.xray && !solarFocus.xray.loading
                    onClicked: {
                        if (solarFocus.xray) solarFocus.xray.refresh()
                    }
                }
            }
            Item {
                width: parent.width
                height: Math.max(1,parent.height-171)
                Row {
                    visible: solarFocus.xrayPage === 0
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
                Grid {
                    id: xraySourceGrid
                    visible: solarFocus.xrayPage === 1
                    anchors.fill: parent
                    columns: 2
                    spacing: 5
                    Repeater {
                        model: xraySourceGrid.visible ? 4 : 0
                        delegate: Rectangle {
                            objectName: "cosmos-c6-xray-detail"
                            required property int index
                            readonly property var factData: solarFocus.xrayFields[index]
                            width: Math.max(1,(xraySourceGrid.width-5)/2)
                            height: Math.max(1,(xraySourceGrid.height-5)/2)
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan
                            Column {
                                anchors.fill: parent
                                anchors.margins: 5
                                spacing: 3
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
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }
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
            Column {
                id: flareInspector
                width: parent.width
                height: Math.max(0,parent.height-128)
                spacing: 4
                Row {
                    width: parent.width
                    height: 23
                    spacing: 5
                    ActionButton {
                        width: 59
                        height: 22
                        contentPadding: 1
                        label: "PREV"
                        labelPixelSize: 9
                        available: solarFocus.flareCount > 1
                        onClicked: solarFocus.flareIndex =
                            (solarFocus.flareIndex-1+solarFocus.flareCount)
                            % solarFocus.flareCount
                    }
                    ActionButton {
                        width: 59
                        height: 22
                        contentPadding: 1
                        label: "NEXT"
                        labelPixelSize: 9
                        available: solarFocus.flareCount > 1
                        onClicked: solarFocus.flareIndex =
                            (solarFocus.flareIndex+1)%solarFocus.flareCount
                    }
                    QuietText {
                        height: 22
                        width: Math.max(1,parent.width-281)
                        text: solarFocus.flareCount
                            ? "EVENT "+(solarFocus.flareIndex+1)+"/"+solarFocus.flareCount
                            : "NO EVENT IN FEED"
                        color: Colors.cyan
                        font.pixelSize: 9
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        width: 72
                        height: 22
                        contentPadding: 1
                        label: solarFocus.flareDataPage === 0 ? "TIMES" : "DETAIL"
                        labelPixelSize: 9
                        selected: true
                        accentColor: Colors.magenta
                        available: solarFocus.flareCount > 0
                        onClicked: solarFocus.flareDataPage =
                            solarFocus.flareDataPage === 0 ? 1 : 0
                    }
                    ActionButton {
                        width: 68
                        height: 22
                        contentPadding: 1
                        label: "REFRESH"
                        labelPixelSize: 9
                        available: !!solarFocus.flares && !solarFocus.flares.loading
                        onClicked: {
                            if (solarFocus.flares) solarFocus.flares.refresh()
                        }
                    }
                }
                Grid {
                    id: flareDataGrid
                    width: parent.width
                    height: Math.max(0,flareInspector.height-27)
                    columns: 2
                    spacing: 5
                    Repeater {
                        model: solarFocus.flareCount ? 4 : 0
                        delegate: Rectangle {
                            objectName: "cosmos-c6-flare-detail"
                            required property int index
                            readonly property var factData:
                                solarFocus.flareFields[index]
                            width: Math.max(1,(flareDataGrid.width-5)/2)
                            height: Math.max(1,(flareDataGrid.height-5)/2)
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta
                            Column {
                                anchors.fill: parent
                                anchors.margins: 5
                                spacing: 3
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
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
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
            Row {
                id: cycleModeBar
                width: parent.width
                height: 23
                spacing: 5
                Repeater {
                    model: [
                        {label:"MODEL",page:0},
                        {label:"RANGES",page:1},
                        {label:"OUTLOOK",page:2}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1,(cycleModeBar.width-80)/3)
                        height: 23
                        contentPadding: 1
                        label: modelData.label
                        labelPixelSize: 9
                        selected: solarFocus.cyclePage===modelData.page
                        accentColor: Colors.magenta
                        onClicked: solarFocus.cyclePage=modelData.page
                    }
                }
                ActionButton {
                    width: 65
                    height: 23
                    contentPadding: 1
                    label: "REFRESH"
                    labelPixelSize: 9
                    available: !!solarFocus.cycle && !solarFocus.cycle.loading
                    onClicked: {
                        if (solarFocus.cycle)
                            solarFocus.cycle.refresh(true)
                    }
                }
            }
            Grid {
                id: cycleGrid
                width: parent.width
                height: Math.max(0,parent.height-72)
                columns: 2
                spacing: 7
                Repeater {
                    model: 4
                    delegate: Rectangle {
                        objectName: "cosmos-c6-cycle-detail"
                        required property int index
                        readonly property var factData:
                            solarFocus.cycleFields[index]
                        width: Math.max(1,(cycleGrid.width-7)/2)
                        height: Math.max(1,(cycleGrid.height-7)/2)
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.yellow
                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 6
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
                                font.pixelSize: 14
                                elide: Text.ElideRight
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
