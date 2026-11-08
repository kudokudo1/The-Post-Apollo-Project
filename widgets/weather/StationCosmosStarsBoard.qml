import QtQuick
import "../../components"

// C27 // Fixed USNO current-sky instrument, followed by a bounded sample
// catalogue. This is an azimuth/altitude plot of the returned navigational
// stars, NOT a full-sky star chart or an optical visibility forecast.
Item {
    id: starBoard
    objectName: "cosmos-c27-stars-board"
    clip: true
    property var celestialSource: null
    property string sourceStatus: "SOURCE WAITING"
    property bool inspecting: false
    property bool visualPlaying: true
    property bool showArchive: false

    readonly property var snapshot:
        celestialSource && celestialSource.ready ? celestialSource.snapshot : null
    readonly property var stars: snapshot && snapshot.stars ? snapshot.stars : []
    readonly property var constellations:
        snapshot && snapshot.constellations ? snapshot.constellations : []
    readonly property var featuredAnchor:
        constellations.length > 0 ? constellations[0] : null
    readonly property var featuredStar: stars.length > 0 ? stars[0] : null

    // Keep the existing C6 detail contract and all of its twelve facts.
    // Nothing is fetched twice or rewritten by this presentation component.
    StationCosmosDetailPane {
        id: starDetails
        anchors.fill: parent
        z: 5
        visible: starBoard.inspecting
        kind: "stars"
        celestialSource: starBoard.celestialSource
        sourceStatus: starBoard.sourceStatus
    }
    property alias starsAsNav: starDetails.starsAsNav
    property alias selectedIndex: starDetails.selectedIndex
    readonly property int recordCount: starDetails.recordCount
    readonly property var facts: starDetails.facts
    readonly property int renderedFactCount: starDetails.renderedFactCount

    function inspectAnchor(index) {
        starsAsNav = false;
        if (index < 0 || index >= recordCount) return;
        selectedIndex = index;
        inspecting = true;
    }
    function inspectStar(index) {
        starsAsNav = true;
        if (index < 0 || index >= recordCount) return;
        selectedIndex = index;
        inspecting = true;
    }

    Column {
        id: fixedSkyHeader
        objectName: "cosmos-c27-sky-now-sticky-header"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        Row {
            objectName: "cosmos-c32-sky-visual-controls"
            height: 18
            width: parent.width
            spacing: 4
            GohuText {
                width: Math.max(1,parent.width-228)
                text: "SKY NOW // USNO NAV STARS"
                font.pixelSize: 10
                color: Colors.magenta
                elide: Text.ElideRight
            }
            QuietText {
                width: 89
                text: starBoard.snapshot
                    ? String(starBoard.snapshot.date || "--") + " "
                      + String(starBoard.snapshot.time || "--") + " UTC"
                    : starBoard.sourceStatus
                font.pixelSize: 8
                color: Colors.cyan
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
            ActionButton {
                objectName: "cosmos-c32-sky-photo-toggle"
                width: 43
                height: 18
                contentPadding: 0
                labelPixelSize: 8
                accentColor: Colors.orange
                label: starBoard.showArchive ? "SKY" : "PHOTO"
                onClicked: starBoard.showArchive = !starBoard.showArchive
            }
            ActionButton {
                objectName: "cosmos-c32-sky-play-pause"
                width: 42
                height: 18
                contentPadding: 0
                labelPixelSize: 8
                accentColor: Colors.cyan
                label: starBoard.visualPlaying ? "PAUSE" : "PLAY"
                onClicked: starBoard.visualPlaying = !starBoard.visualPlaying
            }
            ActionButton {
                objectName: "cosmos-c32-hubble-next"
                visible: starBoard.showArchive
                width: visible ? 31 : 0
                height: 18
                contentPadding: 0
                labelPixelSize: 8
                accentColor: Colors.magenta
                label: "NEXT"
                onClicked: skyMotion.nextArchive()
            }
        }

        Row {
            id: skyInstrumentRow
            objectName: "cosmos-c27-sky-instrument-row"
            width: parent.width
            height: 117
            spacing: 6

            Rectangle {
                id: skyPlotPanel
                objectName: "cosmos-c27-sky-plot-frame"
                width: Math.max(1,(skyInstrumentRow.width-6)*0.55)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta
                clip: true

                StationCosmosStarsVisual {
                    id: skyMotion
                    objectName: "cosmos-c32-sky-image-panel"
                    anchors.fill: parent
                    playing: starBoard.visualPlaying && !starBoard.inspecting
                    showArchive: starBoard.showArchive
                }
                QuietText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 5
                    z: 2
                    width: parent.width-10
                    height: 11
                    text: starBoard.showArchive ? "HUBBLE // ARCHIVAL IMAGES"
                        : "HORIZON // AZIMUTH · ALTITUDE"
                    font.pixelSize: 8
                    color: Colors.cyan
                    elide: Text.ElideRight
                }
                Canvas {
                    id: skyCompass
                    objectName: "cosmos-c27-sky-position-plot"
                    visible: !starBoard.showArchive
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    width: Math.min(96,Math.max(40,parent.height-18))
                    height: width
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const c = width/2;
                        const r = Math.max(1,c-10);
                        ctx.strokeStyle = "#55CFCA";
                        ctx.lineWidth = 1;
                        for (let k=1;k<=2;k++) {
                            ctx.beginPath();
                            ctx.arc(c,c,r*k/2,0,Math.PI*2);
                            ctx.stroke();
                        }
                        ctx.strokeStyle = "#5B5FD4";
                        ctx.beginPath();
                        ctx.moveTo(c,4); ctx.lineTo(c,height-4);
                        ctx.moveTo(4,c); ctx.lineTo(width-4,c);
                        ctx.stroke();
                        ctx.fillStyle = "#F2BE4E";
                        ctx.font = "8px monospace";
                        ctx.fillText("N",c-3,7);
                        ctx.fillText("E",width-8,c-3);
                        ctx.fillText("S",c-3,height-2);
                        ctx.fillText("W",2,c-3);
                    }
                }
                Repeater {
                    model: Math.min(60,starBoard.stars.length)
                    delegate: Rectangle {
                        id: plottedStar
                        objectName: "cosmos-c27-plotted-usno-star"
                        required property int index
                        readonly property var starData: starBoard.stars[index]
                        readonly property real alt: Number(starData ? starData.altitude : NaN)
                        readonly property real az: Number(starData ? starData.azimuth : NaN)
                        readonly property real radiusAtAltitude:
                            Math.max(1,skyCompass.width/2-10)
                            * (90-Math.max(0,Math.min(90,alt)))/90
                        readonly property real azRadians: az*Math.PI/180
                        visible: !starBoard.showArchive
                            && isFinite(alt) && isFinite(az)
                        x: skyCompass.x + skyCompass.width/2
                            + Math.sin(azRadians)*radiusAtAltitude - width/2
                        y: skyCompass.y + skyCompass.height/2
                            - Math.cos(azRadians)*radiusAtAltitude - height/2
                        width: index === 0 ? 8 : 6
                        height: width
                        radius: width/2
                        color: index === 0 ? Colors.yellow : Colors.cyan
                        border.width: 1
                        border.color: Colors.black
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: starBoard.inspectStar(plottedStar.index)
                        }
                    }
                }
            }

            Rectangle {
                id: featuredSkyPanel
                objectName: "cosmos-c27-featured-star-reading"
                width: Math.max(1,skyInstrumentRow.width-skyPlotPanel.width-6)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                clip: true
                Column {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 4
                    SecondaryText {
                        width: parent.width
                        text: "FEATURED // CONSTELLATION ANCHOR"
                        font.pixelSize: 8
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        height: 18
                        font.pixelSize: 13
                        text: starBoard.featuredAnchor
                            ? String(starBoard.featuredAnchor.anchorStar || "--")
                            : "--"
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        height: 12
                        font.pixelSize: 9
                        text: starBoard.featuredAnchor
                            ? String(starBoard.featuredAnchor.name || "--") : "NO ANCHOR IN SAMPLE"
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }
                    Row {
                        width: parent.width
                        height: 26
                        spacing: 5
                        Column {
                            width: Math.max(1,(parent.width-5)/2)
                            spacing: 2
                            SecondaryText { text: "ALT // HC"; font.pixelSize: 8 }
                            GohuText {
                                font.pixelSize: 12
                                color: Colors.yellow
                                text: starBoard.featuredAnchor
                                    && isFinite(Number(starBoard.featuredAnchor.anchorAltitude))
                                    ? Number(starBoard.featuredAnchor.anchorAltitude).toFixed(1)+"°"
                                    : "--"
                            }
                        }
                        Column {
                            width: Math.max(1,(parent.width-5)/2)
                            spacing: 2
                            SecondaryText { text: "AZ // ZN"; font.pixelSize: 8 }
                            GohuText {
                                font.pixelSize: 12
                                color: Colors.cyan
                                text: starBoard.featuredAnchor
                                    && isFinite(Number(starBoard.featuredAnchor.anchorAzimuth))
                                    ? Number(starBoard.featuredAnchor.anchorAzimuth).toFixed(1)+"°"
                                    : "--"
                            }
                        }
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 8
                        text: "SELECT ANCHOR TO INSPECT"
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: starBoard.featuredAnchor !== null
                    cursorShape: Qt.PointingHandCursor
                    onClicked: starBoard.inspectAnchor(0)
                }
            }
        }

        Row {
            id: summaryMetrics
            width: parent.width
            height: 29
            spacing: 4
            Repeater {
                model: [
                    {label:"NAV STARS",value:String(starBoard.stars.length)},
                    {label:"ANCHOR GROUPS",value:String(starBoard.constellations.length)},
                    {label:"DISPLAY",value:"USNO SAMPLE"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(summaryMetrics.width-8)/3)
                    height: summaryMetrics.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        SecondaryText {
                            text: modelData.label
                            font.pixelSize: 8
                        }
                        GohuText {
                            text: modelData.value
                            color: Colors.white
                            font.pixelSize: 10
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: starCatalogFrame
        objectName: "cosmos-c27-star-catalog-frame"
        anchors.top: fixedSkyHeader.bottom
        anchors.topMargin: 5
        anchors.bottom: skySourceCaveat.top
        anchors.bottomMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        clip: true

        GohuText {
            id: catalogTitle
            anchors.left: parent.left
            anchors.leftMargin: 5
            anchors.right: parent.right
            anchors.rightMargin: 5
            anchors.top: parent.top
            anchors.topMargin: 4
            height: 13
            color: Colors.magenta
            font.pixelSize: 9
            text: "NAVIGATION STAR CATALOG // SELECT TO INSPECT"
            elide: Text.ElideRight
        }
        QuietText {
            anchors.centerIn: parent
            visible: starBoard.stars.length === 0
            width: Math.max(1,parent.width-18)
            text: starBoard.sourceStatus === "SOURCE RECEIVED"
                ? "NO NAVIGATION STARS IN USNO SAMPLE"
                : starBoard.sourceStatus
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }
        Flickable {
            id: starCatalogScroll
            objectName: "cosmos-c27-star-catalog-scroll"
            anchors.top: catalogTitle.bottom
            anchors.topMargin: 3
            anchors.left: parent.left
            anchors.leftMargin: 5
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 5
            clip: true
            contentWidth: width
            contentHeight: starRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: starRows
                width: starCatalogScroll.width
                spacing: 4
                Repeater {
                    model: starBoard.stars.length
                    delegate: Rectangle {
                        objectName: "cosmos-c27-star-catalog-record"
                        required property int index
                        readonly property var datum: starBoard.stars[index]
                        width: starRows.width
                        height: 36
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        Row {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 5
                            Column {
                                width: Math.max(1,parent.width*0.53)
                                spacing: 3
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 10
                                    color: Colors.white
                                    text: datum ? String(datum.name || "--") : "--"
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    text: datum ? String(datum.constellation || "--")
                                        + " // #" + String(datum.navStarNumber || "--") : "--"
                                    elide: Text.ElideRight
                                }
                            }
                            Column {
                                width: Math.max(1,parent.width*0.43)
                                spacing: 3
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 9
                                    color: Colors.yellow
                                    text: datum
                                        && isFinite(Number(datum.altitude))
                                        ? "ALT "+Number(datum.altitude).toFixed(1)+"°" : "ALT --"
                                    elide: Text.ElideRight
                                }
                                QuietText {
                                    width: parent.width
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    text: datum
                                        && isFinite(Number(datum.azimuth))
                                        ? "AZ "+Number(datum.azimuth).toFixed(1)+"° // "
                                          + String(datum.direction || "--") : "AZ --"
                                    elide: Text.ElideRight
                                }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: starBoard.inspectStar(index)
                        }
                    }
                }
            }
        }
        NeonScrollBar {
            flickable: starCatalogScroll
            geometryHost: starCatalogFrame
            handleStyle: "star"
            visible: scrollable
        }
    }

    QuietText {
        id: skySourceCaveat
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 12
        color: Colors.orange
        font.pixelSize: 8
        text: "USNO NAV STAR SAMPLE // NOT FULL SKY OR OPTICAL VISIBILITY"
        elide: Text.ElideRight
    }

    ActionButton {
        objectName: "cosmos-c27-star-back"
        visible: starBoard.inspecting
        z: 6
        anchors.top: parent.top
        anchors.right: parent.right
        width: 100
        height: 19
        contentPadding: 1
        label: "BACK TO SKY"
        labelPixelSize: 8
        onClicked: starBoard.inspecting = false
    }
}
