import QtQuick
import "../../components"
import "StationCosmosVisualPolicy.js" as CosmosVisual
import "StationSkyTwilightPolicy.js" as TwilightPolicy

// M30-A // MAGICK overview is a fixed-viewport dashboard, not two full
// scrolling SKY screens. The single source-only SKY owns the existing USNO
// Moon actor; forecast and calibrated solar calculations are read-only.
// The JPL engine is never automatically started here.
Rectangle {
    id: deck
    color: Colors.black
    clip: true

    property var weatherService: null
    property var celestialSource: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property real gutter: 6
    readonly property var moonModel: CosmosVisual.moonDisplay(
        !!observationOwner.moonObservation
            && observationOwner.moonObservation.ready,
        observationOwner.moonObservation
            ? observationOwner.moonObservation.ephemeris : null,
        observationOwner.astronomySummary
    )
    readonly property var solarModel: CosmosVisual.solarArc(
        observationOwner.astronomySummary.date,
        weatherService ? weatherService.latitude : "",
        weatherService ? weatherService.longitude : "",
        observationOwner.moonCivilOffsetMinutes,
        function(minute, date, latitude, longitude, offset) {
            return TwilightPolicy.solarPosition(
                date, minute, latitude, longitude, offset);
        }
    )

    // Keep the already-established SKY provider/date/offset contract without
    // mounting its full scroll surface or adding a second USNO collector.
    StationSky {
        id: observationOwner
        sourceOnly: true
        width: 1
        height: 1
        opacity: 0
        visible: deck.visible
        subjectRoute: "cosmos/moon/ephemeris"
        weatherService: deck.weatherService
        runtimeNowMs: deck.runtimeNowMs
    }

    Rectangle {
        id: hero
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(72, Math.round(deck.height * 0.38))
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 9
            anchors.topMargin: 6
            text: "CELESTIAL // SOLAR DAY ARC"
            font.pixelSize: 11
            color: Colors.magenta
        }
        ActionButton {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: 7
            anchors.topMargin: 5
            width: 69
            height: 22
            label: "CHARTS"
            labelPixelSize: 9
            accentColor: Colors.cyan
            onClicked: deck.routeRequested("magick/astrology/charts")
        }
        Canvas {
            id: solarCanvas
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: heroFooter.top
            anchors.leftMargin: 9
            anchors.rightMargin: 9
            anchors.topMargin: 29
            anchors.bottomMargin: 2
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                const w = Math.max(1,width-2), h = Math.max(1,height-2);
                ctx.strokeStyle = String(Colors.cyan);
                ctx.globalAlpha = 0.35;
                ctx.beginPath();
                ctx.moveTo(0, h/2);
                ctx.lineTo(w, h/2);
                ctx.stroke();
                ctx.globalAlpha = 1;
                if (!deck.solarModel.ready) return;
                const rows = deck.solarModel.rows;
                ctx.strokeStyle = String(Colors.orange);
                ctx.lineWidth = 1.8;
                ctx.beginPath();
                for (let i=0; i<rows.length; i++) {
                    const x = CosmosVisual.positionX(rows[i].minute,w);
                    const y = CosmosVisual.positionY(rows[i].altitude,h);
                    if (i===0) ctx.moveTo(x,y);
                    else ctx.lineTo(x,y);
                }
                ctx.stroke();
            }
            Connections {
                target: deck
                function onSolarModelChanged() { solarCanvas.requestPaint(); }
            }
        }
        QuietText {
            id: heroFooter
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 9
            anchors.rightMargin: 9
            anchors.bottomMargin: 4
            height: 12
            font.pixelSize: 8
            elide: Text.ElideRight
            text: deck.solarModel.ready
                  ? "CALIBRATED LOCAL SOLAR POSITION // "
                    + deck.solarModel.date
                  : "SOLAR MODEL WAITING // LOCATION, DATE OR OFFSET UNAVAILABLE"
            color: deck.solarModel.ready ? Colors.cyan : Colors.yellow
        }
    }

    Row {
        id: instrumentRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: hero.bottom
        anchors.bottom: interpretation.top
        anchors.topMargin: deck.gutter
        anchors.bottomMargin: deck.gutter
        spacing: deck.gutter

        Rectangle {
            id: lunarCard
            width: Math.max(0,(instrumentRow.width - deck.gutter)/2)
            height: instrumentRow.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 7
                anchors.topMargin: 5
                text: "MOON // PHASE"
                font.pixelSize: 10
                color: Colors.cyan
            }
            ActionButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 5
                width: 43
                height: 19
                label: "OPEN"
                labelPixelSize: 8
                accentColor: Colors.cyan
                onClicked: deck.routeRequested("magick/lunar-solar/moon")
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                anchors.topMargin: 24
                anchors.bottomMargin: 5
                spacing: 7

                Canvas {
                    id: moonCanvas
                    width: Math.min(parent.height,68)
                    height: width
                    anchors.verticalCenter: parent.verticalCenter
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const radius=Math.max(1,Math.min(width,height)/2-3);
                        const cx=width/2,cy=height/2;
                        ctx.beginPath();
                        ctx.arc(cx,cy,radius,0,Math.PI*2);
                        ctx.fillStyle=String(Colors.black);
                        ctx.fill();
                        ctx.strokeStyle=String(Colors.cyan);
                        ctx.lineWidth=1;
                        ctx.stroke();
                        const m=deck.moonModel;
                        if (!m.ready || m.illumination===null
                            || !m.directionKnown) return;
                        ctx.fillStyle=String(Colors.yellow);
                        for(let y=-radius;y<radius;y+=1) {
                            const row=CosmosVisual.illuminatedSpan(
                                m.illumination,m.waxing,y+0.5,radius);
                            if(row) ctx.fillRect(cx+row.left,cy+y,
                                Math.max(0,row.right-row.left),1);
                        }
                    }
                    Connections {
                        target: deck
                        function onMoonModelChanged() { moonCanvas.requestPaint(); }
                    }
                }
                Column {
                    width: Math.max(0,parent.width - moonCanvas.width - 7)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    GohuText {
                        width: parent.width
                        text: deck.moonModel.illumination===null
                              ? "--" : Math.round(deck.moonModel.illumination)+"%"
                        font.pixelSize: 19
                        color: Colors.yellow
                    }
                    QuietText {
                        width: parent.width
                        text: deck.moonModel.phaseLabel
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        text: deck.moonModel.source
                        font.pixelSize: 8
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Rectangle {
            id: solarCard
            width: lunarCard.width
            height: instrumentRow.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange
            clip: true

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 7
                anchors.topMargin: 5
                text: "SUN // DAYLIGHT"
                font.pixelSize: 10
                color: Colors.orange
            }
            ActionButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 5
                width: 43
                height: 19
                label: "OPEN"
                labelPixelSize: 8
                accentColor: Colors.orange
                onClicked: deck.routeRequested("magick/planetary/hours")
            }
            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 8
                anchors.rightMargin: 7
                anchors.topMargin: 29
                anchors.bottomMargin: 5
                spacing: 5
                GohuText {
                    width: parent.width
                    text: "RISE " + observationOwner.astronomySummary.sunrise
                          + "  /  SET " + observationOwner.astronomySummary.sunset
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    text: deck.weatherService && deck.weatherService.ready
                          ? "WEATHER // " + deck.weatherService.tempF
                            + "°F  CLOUD " + deck.weatherService.cloudCover + "%"
                          : "WEATHER CONTEXT // WAITING"
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    text: deck.solarModel.ready
                          ? "LOCAL SOLAR ARC // READY"
                          : "SOLAR ARC // UNAVAILABLE"
                    font.pixelSize: 8
                    color: deck.solarModel.ready ? Colors.cyan : Colors.yellow
                    elide: Text.ElideRight
                }
            }
        }
    }

    Rectangle {
        id: interpretation
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.max(39,Math.round(deck.height*0.17))
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta
        clip: true

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.topMargin: 5
            text: "MAGICK // INTERPRETIVE CONTEXT"
            font.pixelSize: 10
            color: Colors.magenta
        }
        QuietText {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.rightMargin: 67
            anchors.topMargin: 22
            text: "TRADITIONS / CORRESPONDENCES // NOT CONNECTED"
            font.pixelSize: 8
            elide: Text.ElideRight
        }
        ActionButton {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 6
            width: 54
            height: 23
            label: "OPEN"
            labelPixelSize: 9
            accentColor: Colors.magenta
            onClicked: deck.routeRequested("magick/planetary/correspondences")
        }
    }
}
