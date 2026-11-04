import QtQuick
import "../components"
import "CompanyCoveragePolicy.js" as Geo
import "weather/StationNaturalEarthLand110.js" as Land
import "weather/StationNaturalEarthContext110.js" as Context

// Company Network Coverage M1: real geographic *reference* map.
// Natural Earth is public domain and already pinned by Weather Station.
// Neither Natural Earth boundaries nor capital markers imply service coverage.
// All company coverage, partner, workforce and client data remains absent.
Item {
    id: root

    property string regionKey: "lower48"
    property string selectedCode: ""
    property string serviceFamily: "ALL SERVICES"
    property string statusFilter: "ALL STATUS"
    property bool showReferencePoints: true
    property real zoom: 1
    property real centerLon: -96
    property real centerLat: 37

    readonly property bool compactLayout: width < 640
    readonly property var selectedState: Geo.stateForCode(selectedCode)
    readonly property var bounds: Geo.regions[Geo.regionKey(regionKey)]

    function applyView(next) {
        zoom = next.zoom;
        centerLon = next.centerLon;
        centerLat = next.centerLat;
    }

    function setRegion(key) {
        regionKey = Geo.regionKey(key);
        applyView(Geo.defaultView(regionKey));
        selectedCode = "";
        stateSearch.text = "";
    }

    function chooseState(state) {
        if (!state) return;
        if (regionKey !== state[5])
            setRegion(state[5]);
        selectedCode = state[0];
    }

    function cycleService() {
        var i=Geo.serviceFamilies.indexOf(serviceFamily);
        serviceFamily=Geo.serviceFamilies[(i+1)%Geo.serviceFamilies.length];
    }

    function cycleStatus() {
        var i=Geo.statusFilters.indexOf(statusFilter);
        statusFilter=Geo.statusFilters[(i+1)%Geo.statusFilters.length];
    }

    function zoomBy(direction,x,y) {
        applyView(Geo.zoomAt(regionKey, zoom, centerLon, centerLat,
                             x, y, mapCanvas.width, mapCanvas.height, direction));
    }

    onRegionKeyChanged: mapCanvas.requestPaint()
    onSelectedCodeChanged: mapCanvas.requestPaint()
    onZoomChanged: mapCanvas.requestPaint()
    onCenterLonChanged: mapCanvas.requestPaint()
    onCenterLatChanged: mapCanvas.requestPaint()
    onShowReferencePointsChanged: mapCanvas.requestPaint()

    Column {
        id: column
        anchors.fill: parent
        spacing: 8

        Row {
            width: parent.width
            height: 27
            spacing: 10

            GohuText {
                text: "COVERAGE // UNITED STATES"
                font.pixelSize: root.compactLayout ? 13 : 18
                font.bold: true
                color: Colors.yellow
                anchors.verticalCenter: parent.verticalCenter
            }

            GohuText {
                text: "REFERENCE ONLY"
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.7
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            id: regionsRow
            width: parent.width
            height: 33
            spacing: 7

            Repeater {
                model: [
                    { id:"lower48",name:"LOWER 48 + DC" },
                    { id:"alaska",name:"ALASKA" },
                    { id:"hawaii",name:"HAWAII" }
                ]
                ModeButton {
                    required property var modelData
                    width: modelData.id === "lower48" ? 138 : 88
                    height: regionsRow.height
                    textOnly: true
                    labelText: modelData.name
                    labelFontSize: 10
                    selected: root.regionKey === modelData.id
                    idlePrimaryColor: Colors.white
                    hoverPrimaryColor: Colors.blue
                    selectedPrimaryColor: Colors.blue
                    perimeterGlowColor: Colors.blue
                    bordered: false
                    onTriggered: root.setRegion(modelData.id)
                }
            }
        }

        Row {
            id: filtersRow
            width: parent.width
            height: 31
            spacing: 8

            ModeButton {
                width: root.compactLayout ? 152 : 190
                height: filtersRow.height
                textOnly: true
                labelText: "SERVICE: " + root.serviceFamily
                labelFontSize: 10
                bordered: false
                idlePrimaryColor: Colors.white
                hoverPrimaryColor: Colors.yellow
                selectedPrimaryColor: Colors.yellow
                perimeterGlowColor: Colors.blue
                onTriggered: root.cycleService()
            }

            ModeButton {
                width: root.compactLayout ? 134 : 174
                height: filtersRow.height
                textOnly: true
                labelText: "STATUS: " + root.statusFilter
                labelFontSize: 10
                bordered: false
                idlePrimaryColor: Colors.white
                hoverPrimaryColor: Colors.yellow
                selectedPrimaryColor: Colors.yellow
                perimeterGlowColor: Colors.blue
                onTriggered: root.cycleStatus()
            }
        }

        Row {
            id: mapRow
            width: parent.width
            spacing: 10
            height: Math.max(130, column.height - 27 - 33 - 31 - 50 - column.spacing * 4)

            Rectangle {
                id: mapSurface
                width: parent.width - (detailPanel.visible ? detailPanel.width + mapRow.spacing : 0)
                height: mapRow.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue
                clip: true

                Canvas {
                    id: mapCanvas
                    anchors.fill: parent
                    anchors.margins: 1

                    function intersects(points, limits) {
                        var lowLon=Infinity, highLon=-Infinity;
                        var lowLat=Infinity, highLat=-Infinity;
                        for (var k=0;k<points.length;k++) {
                            var point=points[k];
                            if (point[0]<lowLon) lowLon=point[0];
                            if (point[0]>highLon) highLon=point[0];
                            if (point[1]<lowLat) lowLat=point[1];
                            if (point[1]>highLat) highLat=point[1];
                        }
                        return !(highLon<limits.west || lowLon>limits.east
                            || highLat<limits.south || lowLat>limits.north);
                    }

                    function drawLine(ctx, points, closeLine) {
                        if (!points || points.length<2) return;
                        var start=Geo.project(points[0][0],points[0][1],width,height,
                            root.regionKey,root.zoom,root.centerLon,root.centerLat);
                        ctx.beginPath();
                        ctx.moveTo(start.x,start.y);
                        for (var j=1;j<points.length;j++) {
                            var p=Geo.project(points[j][0],points[j][1],width,height,
                                root.regionKey,root.zoom,root.centerLon,root.centerLat);
                            ctx.lineTo(p.x,p.y);
                        }
                        if (closeLine) ctx.closePath();
                    }

                    onPaint: {
                        var ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        ctx.fillStyle="#16051F";
                        ctx.fillRect(0,0,width,height);

                        // Real Natural Earth geography, deliberately neutral.
                        // Only recorded company service polygons may receive
                        // active/partner/planned coverage fills in later phases.
                        var polygons=Land.polygons || [];
                        ctx.fillStyle="#251530";
                        ctx.strokeStyle="#536185";
                        ctx.lineWidth=1;
                        for (var i=0;i<polygons.length;i++) {
                            var rings=polygons[i];
                            for (var j=0;j<rings.length;j++) {
                                if (!intersects(rings[j],root.bounds)) continue;
                                drawLine(ctx,rings[j],true);
                                ctx.fill();
                                ctx.stroke();
                            }
                        }

                        ctx.strokeStyle="#467D92";
                        ctx.globalAlpha=0.65;
                        ctx.lineWidth=0.75;
                        var internal=Context.admin1Lines || [];
                        for (var a=0;a<internal.length;a++) {
                            if (!intersects(internal[a].line,root.bounds)) continue;
                            drawLine(ctx,internal[a].line,false);
                            ctx.stroke();
                        }
                        ctx.globalAlpha=1;

                        // Capital markers are *navigation anchors*, not hubs.
                        if (root.showReferencePoints) {
                            var points=Geo.visibleStates(root.regionKey,"");
                            for (var n=0;n<points.length;n++) {
                                var row=points[n];
                                var xy=Geo.project(row[3],row[4],width,height,
                                    root.regionKey,root.zoom,root.centerLon,root.centerLat);
                                if (!xy.visible) continue;
                                var active=row[0]===root.selectedCode;
                                ctx.beginPath();
                                ctx.arc(xy.x,xy.y,active?6:2.9,0,2*Math.PI);
                                ctx.fillStyle=active?"#F2BE4E":"#DCF3FA";
                                ctx.fill();
                                ctx.strokeStyle=active?"#C74EC7":"#5B5FD4";
                                ctx.lineWidth=active?2:1;
                                ctx.stroke();
                            }
                        }
                    }

                    Component.onCompleted: requestPaint()
                }

                MouseArea {
                    id: mapMouse
                    anchors.fill: mapCanvas
                    z: 1
                    acceptedButtons: Qt.LeftButton
                    hoverEnabled: true
                    property real lastX: 0
                    property real lastY: 0
                    property bool dragged: false

                    onPressed: function(mouse) {
                        lastX=mouse.x;
                        lastY=mouse.y;
                        dragged=false;
                    }

                    onPositionChanged: function(mouse) {
                        if (!(mouse.buttons & Qt.LeftButton)) return;
                        var dx=mouse.x-lastX, dy=mouse.y-lastY;
                        if (Math.abs(dx)+Math.abs(dy)>1.5) dragged=true;
                        if (dragged)
                            root.applyView(Geo.pan(root.regionKey,root.zoom,
                                root.centerLon,root.centerLat,dx,dy,
                                mapCanvas.width,mapCanvas.height));
                        lastX=mouse.x;
                        lastY=mouse.y;
                    }

                    onReleased: function(mouse) {
                        if (dragged) return;
                        var closest=Geo.nearestState(root.regionKey,mouse.x,mouse.y,
                            mapCanvas.width,mapCanvas.height,root.zoom,
                            root.centerLon,root.centerLat,13);
                        if (closest) root.chooseState(closest);
                    }

                    onWheel: function(wheel) {
                        if (!wheel.angleDelta.y) return;
                        root.zoomBy(wheel.angleDelta.y>0?1:-1,wheel.x,wheel.y);
                        wheel.accepted=true;
                    }
                }

                Column {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 10
                    spacing: 5
                    z: 2

                    ActionButton {
                        width: 30
                        height: 30
                        label: "+"
                        labelPixelSize: 16
                        accentColor: Colors.blue
                        onLeftClicked: root.zoomBy(1,mapCanvas.width/2,mapCanvas.height/2)
                    }
                    ActionButton {
                        width: 30
                        height: 30
                        label: "−"
                        labelPixelSize: 16
                        accentColor: Colors.blue
                        onLeftClicked: root.zoomBy(-1,mapCanvas.width/2,mapCanvas.height/2)
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    text: root.bounds.label + "  //  " + Math.round(root.zoom*100) + "%"
                    color: Colors.white
                    font.pixelSize: 10
                }
            }

            Rectangle {
                id: detailPanel
                visible: !root.compactLayout
                width: 218
                height: mapRow.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue

                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    GohuText {
                        width: parent.width
                        text: "STATE DIRECTORY"
                        font.bold: true
                        font.pixelSize: 13
                        color: Colors.yellow
                    }

                    Rectangle {
                        width: parent.width
                        height: 31
                        color: Colors.black
                        border.color: Colors.cyan
                        border.width: 1

                        TextInput {
                            id: stateSearch
                            anchors.fill: parent
                            anchors.leftMargin: 7
                            anchors.rightMargin: 5
                            verticalAlignment: TextInput.AlignVCenter
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 12
                            color: Colors.white
                            selectByMouse: true
                            clip: true
                            Keys.onEscapePressed: function(event) {
                                if (text.length) {
                                    text="";
                                    event.accepted=true;
                                }
                            }
                        }

                        GohuText {
                            visible: !stateSearch.text.length && !stateSearch.activeFocus
                            text: "FIND STATE / CAPITAL"
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.45
                        }
                    }

                    GohuText {
                        text: root.selectedState
                              ? root.selectedState[1] + " // " + root.selectedState[0]
                              : "SELECT STATE"
                        font.bold: true
                        font.pixelSize: 12
                        color: Colors.magenta
                        width: parent.width
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text: root.selectedState
                              ? "CAPITAL REFERENCE: " + root.selectedState[2]
                              : "Select a marker or directory row."
                        font.pixelSize: 10
                        color: Colors.white
                        wrapMode: Text.WordWrap
                    }

                    GohuText {
                        width: parent.width
                        text: "SERVICE COVERAGE: UNVERIFIED"
                        font.pixelSize: 10
                        color: Colors.yellow
                        wrapMode: Text.WordWrap
                    }

                    Flickable {
                        width: parent.width
                        height: Math.max(20, detailPanel.height - 156)
                        clip: true
                        contentWidth: width
                        contentHeight: stateRows.height
                        flickableDirection: Flickable.VerticalFlick
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: stateRows
                            width: parent.width
                            spacing: 3

                            Repeater {
                                model: Geo.visibleStates(root.regionKey,stateSearch.text)
                                Rectangle {
                                    id: stateRow
                                    required property var modelData
                                    width: stateRows.width
                                    height: 25
                                    color: root.selectedCode===modelData[0]
                                        ? Colors.yellow : Colors.black
                                    border.width: 1
                                    border.color: root.selectedCode===modelData[0]
                                        ? Colors.magenta : Colors.blue

                                    GohuText {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 10
                                        text: modelData[0] + "  " + modelData[1]
                                        color: root.selectedCode===stateRow.modelData[0]
                                            ? Colors.black : Colors.white
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.chooseState(stateRow.modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Row {
            width: parent.width
            height: 50
            spacing: 10

            GohuText {
                width: parent.width
                text: (root.selectedState
                        ? root.selectedState[1] + " // " : "NO STATE SELECTED // ")
                    + "No company service areas, workforce or partner records connected. "
                    + "County/city coverage awaits verified data. "
                    + "Reference markers are state capitals, NOT provider hubs."
                font.pixelSize: 11
                color: Colors.white
                wrapMode: Text.WordWrap
            }
        }
    }
}
