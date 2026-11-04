import QtQuick
import "../../components"
import "StationCosmosVisualPolicy.js" as CosmosVisual
import "StationSkyTwilightPolicy.js" as TwilightPolicy
import "StationMagickCelestialVisualPolicy.js" as CelestialVisual

// M30-B // The overview is a compact astro hero plus lunar/solar instruments.
// The single source-only SKY owns the existing USNO Moon actor. The solar
// calculation stays inside SUN, and the root-owned JPL process only runs after
// the explicit hero CALCULATE click. No invented planetary positions or readings.
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
    // Only a provenance-validated M4 payload can place bodies on the ring.
    // Empty rings are visual framing, never claimed computed positions.
    readonly property var chartModel: CelestialVisual.model(
        deck.celestialSource && deck.celestialSource.ready
        ? deck.celestialSource.visualData : null)
    readonly property var chartPositions:
        CelestialVisual.wheelPositions(
            chartModel, chartModel.ready ? chartModel.sampleCount-1 : -1)

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
        height: Math.max(0,Math.round(deck.height * 0.59))
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta
        clip: true

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 9
            anchors.topMargin: 6
            width: Math.max(0,parent.width-194)
            text: "MAGICK // CELESTIAL CHART"
            font.pixelSize: 11
            color: Colors.magenta
            elide: Text.ElideRight
        }
        Row {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 4
            anchors.rightMargin: 6
            spacing: 5
            ActionButton {
                width: 91
                height: 22
                label: deck.celestialSource && deck.celestialSource.loading
                       ? "CALCULATING" : "CALCULATE"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: !!deck.celestialSource
                           && deck.celestialSource.active
                           && deck.celestialSource.configured
                           && !deck.celestialSource.loading
                // One root-owned JPL Process. Deliberately no autoplay.
                onClicked: deck.celestialSource.refresh()
            }
            ActionButton {
                width: 57
                height: 22
                label: "CHARTS"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onClicked: deck.routeRequested("magick/astrology/charts")
            }
        }

        Row {
            id: heroInstrument
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: heroFooter.top
            anchors.leftMargin: 9
            anchors.rightMargin: 9
            anchors.topMargin: 29
            anchors.bottomMargin: 3
            spacing: 12

            Canvas {
                id: celestialCanvas
                width: Math.min(heroInstrument.height,112)
                height: heroInstrument.height
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");
                    ctx.clearRect(0,0,width,height);
                    const cx=width/2,cy=height/2;
                    const radius=Math.max(1,Math.min(width,height)/2-4);
                    // Rings and cardinal guides are a coordinate framework.
                    // They never represent fabricated orbital observations.
                    ctx.strokeStyle=String(Colors.magenta);
                    ctx.lineWidth=1;
                    ctx.globalAlpha=0.65;
                    for (let ring=1;ring<=2;ring++) {
                        ctx.beginPath();
                        ctx.arc(cx,cy,radius*ring/2,0,Math.PI*2);
                        ctx.stroke();
                    }
                    ctx.globalAlpha=0.40;
                    ctx.beginPath();
                    ctx.moveTo(cx-radius,cy);
                    ctx.lineTo(cx+radius,cy);
                    ctx.moveTo(cx,cy-radius);
                    ctx.lineTo(cx,cy+radius);
                    ctx.stroke();
                    ctx.globalAlpha=1;
                    if (!deck.chartModel.ready)return;
                    const positions=deck.chartPositions;
                    for(let i=0;i<positions.length;i++) {
                        const point=positions[i];
                        const x=cx+(point.x-0.5)*2.0*radius;
                        const y=cy+(point.y-0.5)*2.0*radius;
                        ctx.beginPath();
                        ctx.arc(x,y,3.5,0,Math.PI*2);
                        ctx.fillStyle=String(point.color);
                        ctx.fill();
                    }
                }
                Connections {
                    target: deck
                    function onChartModelChanged() {
                        celestialCanvas.requestPaint();
                    }
                }
            }
            Column {
                width: Math.max(0,heroInstrument.width-celestialCanvas.width-12)
                anchors.verticalCenter: parent.verticalCenter
                spacing: 5
                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: deck.chartModel.ready ? Colors.cyan : Colors.yellow
                    text: deck.chartModel.ready
                          ? "SOURCE-VERIFIED CELESTIAL POSITIONS"
                          : "AWAITING CALCULATION"
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.white
                    text: deck.celestialSource
                          ? deck.celestialSource.pairLabel
                            + " // " + deck.celestialSource.targetDayUtc
                          : "JPL SOURCE NOT CONNECTED"
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    text: deck.celestialSource
                          ? deck.celestialSource.statusText
                          : "JPL CALCULATION OWNER UNAVAILABLE"
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 8
                    color: Colors.cyan
                    text: "GEOCENTRIC // TRUE ECLIPTIC"
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            id: heroFooter
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 9
            anchors.rightMargin: 7
            anchors.bottomMargin: 4
            height: 22
            spacing: 6
            QuietText {
                width: Math.max(0,parent.width-65)
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 8
                color: Colors.yellow
                text: "TRADITIONS / CORRESPONDENCES // NOT CONNECTED"
                elide: Text.ElideRight
            }
            ActionButton {
                width: 59
                height: 21
                label: "LENS"
                labelPixelSize: 9
                accentColor: Colors.magenta
                onClicked: deck.routeRequested("magick/planetary/correspondences")
            }
        }
    }

    Row {
        id: instrumentRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: hero.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: deck.gutter
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

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 7
                anchors.rightMargin: 7
                anchors.topMargin: 26
                anchors.bottomMargin: 5
                spacing: 6

                Canvas {
                    id: solarCanvas
                    width: Math.max(45,parent.width*0.42)
                    height: parent.height
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const w=Math.max(1,width-2),h=Math.max(1,height-2);
                        ctx.strokeStyle=String(Colors.cyan);
                        ctx.globalAlpha=0.35;
                        ctx.beginPath();
                        ctx.moveTo(0,h/2);
                        ctx.lineTo(w,h/2);
                        ctx.stroke();
                        ctx.globalAlpha=1;
                        if(!deck.solarModel.ready)return;
                        ctx.strokeStyle=String(Colors.orange);
                        ctx.lineWidth=1.6;
                        ctx.beginPath();
                        const rows=deck.solarModel.rows;
                        for(let i=0;i<rows.length;i++){
                            const x=CosmosVisual.positionX(rows[i].minute,w);
                            const y=CosmosVisual.positionY(rows[i].altitude,h);
                            if(i===0)ctx.moveTo(x,y);
                            else ctx.lineTo(x,y);
                        }
                        ctx.stroke();
                    }
                    Connections {
                        target: deck
                        function onSolarModelChanged() {
                            solarCanvas.requestPaint();
                        }
                    }
                }

                Column {
                    width: Math.max(0,parent.width-solarCanvas.width-6)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    GohuText {
                        width: parent.width
                        text: "RISE " + observationOwner.astronomySummary.sunrise
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: "SET  " + observationOwner.astronomySummary.sunset
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width
                        text: deck.solarModel.ready
                              ? "SOLAR ARC // READY"
                              : "SOLAR ARC // WAITING"
                        color: deck.solarModel.ready ? Colors.cyan : Colors.yellow
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

}
