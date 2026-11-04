import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "CompanyStreetMath.js" as Mercator

// Opt-in street-level overlay: viewport-only OSM tiles, persisted cache.
// No request is sent until the operator confirms online street mode.
// The Python adapter sees only map viewport coordinates, never hub metadata.
Item {
    id: street
    property bool active: false
    property bool pickingLocation: false
    property var hubRows: []
    property string selectedHubId: ""
    property real centerLon: -96
    property real centerLat: 37
    property int zoomLevel: 10
    property var tiles: []
    property string tileStatus: "STREETS OFF"
    property string tileError: ""
    property string responseText: ""
    property bool pendingRefresh: false

    signal locationPicked(real longitude, real latitude)
    signal hubPicked(string id)

    function focusAt(lon,lat,zoom) {
        if (!isFinite(Number(lon)) || !isFinite(Number(lat))) return;
        centerLon = Math.max(-180,Math.min(180,Number(lon)));
        centerLat = Math.max(-85.05112878,Math.min(85.05112878,Number(lat)));
        zoomLevel = Mercator.zoomLevel(zoom);
        tiles = [];
        if(active) refreshDelay.restart();
    }

    function nudgeZoom(delta,x,y) {
        var next=Mercator.zoomAt(x,y,width,height,zoomLevel,
                                  centerLon,centerLat,delta);
        centerLon=next.lon;
        centerLat=next.lat;
        zoomLevel=next.zoom;
        refreshDelay.restart();
    }

    function requestTiles() {
        if(!active || !visible || width<100 || height<100)
            return false;
        if(fetcher.running) {
            pendingRefresh=true;
            return false;
        }
        pendingRefresh=false;
        responseText="";
        tileStatus="FETCHING VISIBLE STREET TILES";
        tileError="";
        requestData=JSON.stringify({
            enable:true, lon:centerLon, lat:centerLat,
            zoom:zoomLevel, width:Math.floor(width), height:Math.floor(height)
        });
        fetcher.running=true;
        return true;
    }

    property string requestData: ""

    onActiveChanged: {
        if(active) refreshDelay.restart();
        else {
            refreshDelay.stop();
            pendingRefresh=false;
            tiles=[];
            tileStatus="STREETS OFF";
        }
    }
    onWidthChanged: if(active) refreshDelay.restart()
    onHeightChanged: if(active) refreshDelay.restart()
    onCenterLonChanged: if(active) refreshDelay.restart()
    onCenterLatChanged: if(active) refreshDelay.restart()
    onZoomLevelChanged: if(active) refreshDelay.restart()

    Timer {
        id: refreshDelay
        interval: 650
        repeat: false
        onTriggered: street.requestTiles()
    }

    Process {
        id: fetcher
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/company/CompanyStreetTiles.py")]
        stdinEnabled: true
        stdout: StdioCollector {
            onStreamFinished: street.responseText=String(text||"")
        }
        onStarted: fetcher.write(street.requestData+"\n")
        onExited: function(exitCode) {
            var response=null;
            try {response=JSON.parse(street.responseText);} catch(e) {}
            if(!street.active) return;
            if(exitCode===0 && response && response.ok===true) {
                street.tiles=response.tiles||[];
                street.tileStatus=response.partial
                    ? "PARTIAL STREET TILES" : "STREET DETAIL READY";
                street.tileError="";
            } else {
                street.tileStatus="STREET TILES UNAVAILABLE";
                street.tileError=response && response.error
                    ? response.error : "FETCH_UNAVAILABLE";
            }
            // A pan/zoom during a running fetch must get a fresh viewport
            // request after completion; never lose that update silently.
            if(street.pendingRefresh && street.active) refreshDelay.restart();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#13091E"
    }

    Item {
        id: tilePlane
        anchors.fill: parent
        clip: true
        Repeater {
            model: street.tiles
            Image {
                required property var modelData
                readonly property var tilePosition: Mercator.tilePosition(
                    modelData.x,modelData.y,modelData.z,street.width,street.height,
                    street.centerLon,street.centerLat)
                x: tilePosition.x
                y: tilePosition.y
                width: 256
                height: 256
                asynchronous: true
                cache: true
                fillMode: Image.Stretch
                source: "file://" + modelData.path
            }
        }
    }

    MouseArea {
        id: pointer
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        z: 1
        property real lastX: 0
        property real lastY: 0
        property bool moved: false

        onPressed: function(mouse) {
            lastX=mouse.x;
            lastY=mouse.y;
            moved=false;
        }
        onPositionChanged: function(mouse) {
            if(!(mouse.buttons & Qt.LeftButton))return;
            var dx=mouse.x-lastX,dy=mouse.y-lastY;
            if(Math.abs(dx)+Math.abs(dy)>1.2)moved=true;
            if(moved) {
                var next=Mercator.pan(dx,dy,street.width,street.height,
                    street.zoomLevel,street.centerLon,street.centerLat);
                if(next) {
                    street.centerLon=next.lon;
                    street.centerLat=next.lat;
                }
            }
            lastX=mouse.x;
            lastY=mouse.y;
        }
        onReleased: function(mouse) {
            if(moved)return;
            var point=Mercator.invert(mouse.x,mouse.y,street.width,street.height,
                street.zoomLevel,street.centerLon,street.centerLat);
            if(street.pickingLocation && point)
                street.locationPicked(point.lon,point.lat);
        }
        onWheel: function(wheel) {
            if(!wheel.angleDelta.y) return;
            street.nudgeZoom(wheel.angleDelta.y>0?1:-1,wheel.x,wheel.y);
            wheel.accepted=true;
        }
    }

    Repeater {
        model: street.hubRows.filter(function(hub){return !hub.archived;})
        Rectangle {
            id: hubPin
            required property var modelData
            readonly property var location: Mercator.screen(
                modelData.longitude,modelData.latitude,
                street.width,street.height,
                street.zoomLevel,street.centerLon,street.centerLat)
            x: location.x-width/2
            y: location.y-height/2
            width: street.selectedHubId===modelData.id ? 16 : 12
            height: width
            radius: width/2
            color: "#16051F"
            border.width: street.selectedHubId===modelData.id ? 3 : 2
            border.color: street.selectedHubId===modelData.id ? Colors.magenta : Colors.orange
            z: 2
            visible: location.x>=0 && location.x<=street.width
                && location.y>=0 && location.y<=street.height

            MouseArea {
                anchors.fill: parent
                enabled: !street.pickingLocation
                onClicked: street.hubPicked(hubPin.modelData.id)
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 8
        z: 4
        width: Math.min(parent.width-84, 315)
        height: 34
        color: "#1B0623"
        border.color: Colors.blue

        GohuText {
            anchors.centerIn: parent
            font.pixelSize: 10
            color: street.tileError ? Colors.red : Colors.white
            text: street.pickingLocation ? "PICK HUB LOCATION ON STREET MAP"
                : street.tileStatus+" // Z"+street.zoomLevel
            elide: Text.ElideRight
        }
    }

    Column {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 8
        spacing: 5
        z: 4
        ActionButton {
            width: 32; height: 32
            label: "+"
            labelPixelSize: 17
            accentColor: Colors.blue
            onLeftClicked: street.nudgeZoom(1,street.width/2,street.height/2)
        }
        ActionButton {
            width: 32; height: 32
            label: "−"
            labelPixelSize: 17
            accentColor: Colors.blue
            onLeftClicked: street.nudgeZoom(-1,street.width/2,street.height/2)
        }
        ActionButton {
            width: 32; height: 32
            label: "↻"
            labelPixelSize: 17
            accentColor: Colors.cyan
            onLeftClicked: refreshDelay.restart()
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 6
        width: attribution.implicitWidth+16
        height: 23
        color: "#1B0623"
        border.color: Colors.blue
        z: 5

        GohuText {
            id: attribution
            anchors.centerIn: parent
            color: Colors.white
            font.pixelSize: 11
            text: "© OpenStreetMap contributors"
        }
    }
}
