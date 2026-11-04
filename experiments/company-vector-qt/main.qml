import QtQuick 6.5
import QtQuick.Window 6.5
import QtLocation 6.5
import QtPositioning 6.5
import MapLibre 3.0

// Isolated standalone proof, not loaded by shell.qml.
// Offline mode uses explicitly synthetic geometry, not real roads or hubs.
// Online mode only activates with the C++ --online argument.
Window {
    id: root
    visible: true
    width: 1000
    height: 700
    color: "#1B0623"
    title: "POST-APOLLO // COMPANY VECTOR RENDERER PROBE"
    property var flint: QtPositioning.coordinate(43.0125, -83.6875)
    property var nationwide: QtPositioning.coordinate(39.83, -98.58)
    // Regression viewports are examples distributed across regions.
    // They do not limit global data or authorize company coverage.
    property var sampleViews: [
        {label:"USA",lat:39.83,lon:-98.58,zoom:4},
        {label:"PACIFIC",lat:37.7749,lon:-122.4194,zoom:12},
        {label:"MIDWEST",lat:41.8781,lon:-87.6298,zoom:12},
        {label:"NORTHEAST",lat:40.7128,lon:-74.0060,zoom:12},
        {label:"RURAL",lat:38.297,lon:-80.50,zoom:12},
        {label:"CANADA",lat:43.65,lon:-79.38,zoom:12},
        {label:"MEXICO",lat:32.525,lon:-117.02,zoom:12},
        {label:"ALASKA",lat:61.2181,lon:-149.9003,zoom:12},
        {label:"HAWAII",lat:21.3099,lon:-157.8581,zoom:12},
        {label:"FLINT",lat:43.0125,lon:-83.6875,zoom:12},
        {label:"SUBURB",lat:42.576,lon:-83.144,zoom:16},
        {label:"VILLAGE",lat:38.319,lon:-80.655,zoom:15},
        {label:"NEIGHBORHOOD",lat:43.655,lon:-79.383,zoom:16},
        {label:"BORDER",lat:42.324,lon:-83.030,zoom:14}
    ]

    property var syntheticMarker: null
    property var fixtureMarkers: []
    property var ownerLocalMarkers: []

    function installOwnerLocalMarkers() {
        if (!probeOwnerLocalMode || !probeOwnerLocalHubs
                || ownerLocalMarkers.length>0
                || !mapView.map || !mapView.map.mapReady) return;
        var created=[];
        for(var i=0;i<probeOwnerLocalHubs.length;i++) {
            var record=probeOwnerLocalHubs[i];
            var instance=ownerReportedHubTemplate.createObject(mapView.map, {
                coordinate: QtPositioning.coordinate(record.latitude,record.longitude)
            });
            if(!instance) {
                console.warn("OWNER_LOCAL_MARKER_CREATE_FAILED");
                return;
            }
            mapView.map.addMapItem(instance);
            created.push(instance);
        }
        ownerLocalMarkers=created;
        // Count only; never log coordinates, local IDs or organization names.
        console.log("OWNER_LOCAL_MARKERS_ADDED count="+ownerLocalMarkers.length);
    }
    property int motionTick: 0

    function installFixtureMarkers() {
        if (!probeFixtureHubs || probeFixtureHubs.length===0 ||
                fixtureMarkers.length>0 || !mapView.map || !mapView.map.mapReady)
            return;
        var created=[];
        for(var i=0;i<probeFixtureHubs.length;i++) {
            var record=probeFixtureHubs[i];
            var instance=fixtureHubTemplate.createObject(mapView.map,{
                coordinate: QtPositioning.coordinate(record.latitude,record.longitude),
                fixtureId: record.id,
                displayLabel: record.label
            });
            if(!instance) {
                console.warn("FIXTURE_MARKER_CREATE_FAILED");
                return;
            }
            mapView.map.addMapItem(instance);
            created.push(instance);
        }
        fixtureMarkers=created;
        console.log("FIXTURE_MARKERS_ADDED count="+fixtureMarkers.length);
    }

    function installSyntheticMarker() {
        if (!probeMockHub || syntheticMarker !== null || !mapView.map
                || !mapView.map.mapReady) return;
        // QtLocation anchors a MapQuickItem to geographic coordinates.
        // The source is a deliberate test fixture, not a provider record.
        var item = mockHubTemplate.createObject(mapView.map);
        if (item === null) {
            console.warn("SYNTHETIC_MARKER_CREATE_FAILED");
            return;
        }
        mapView.map.addMapItem(item);
        syntheticMarker = item;
        console.log("SYNTHETIC_MARKER_ADDED"); 
    }

    Component.onCompleted: {
        // Run only after QML has instantiated MapView. The public sample
        // names select regression cameras, not a region-locked data source.
        if (probeOnline && probeSample !== "")
            Qt.callLater(function(){ root.goToSample(probeSample); });
        if (probeMockHub)
            Qt.callLater(function(){ root.installSyntheticMarker(); });
        if (probeFixtureHubs && probeFixtureHubs.length)
            Qt.callLater(function(){ root.installFixtureMarkers(); });
        if (probeOwnerLocalMode)
            Qt.callLater(function(){ root.installOwnerLocalMarkers(); });
    }

    function goToSample(label) {
        for(var i=0;i<sampleViews.length;i++) {
            var p=sampleViews[i];
            if (p.label!==label) continue;
            mapView.map.center=QtPositioning.coordinate(p.lat,p.lon);
            mapView.map.zoomLevel=p.zoom;
            return;
        }
    }

    Plugin {
        id: mapPlugin
        name: "maplibre"
        PluginParameter {
            name: "maplibre.map.styles"
            value: probeStyleUrl
        }
    }

    MapView {
        id: mapView
        anchors.fill: parent
        map.plugin: mapPlugin
        map.center: probeOnline ? root.nationwide : root.flint
        map.zoomLevel: probeOnline ? 4 : 10
        MapLibre.style: Style {}
    }

    Connections {
        target: mapView.map
        function onMapReadyChanged() {
            if (mapView.map.mapReady)
                Qt.callLater(function() {
                    root.installSyntheticMarker();
                    root.installFixtureMarkers();
                    root.installOwnerLocalMarkers();
                });
        }
    }

    Component {
        id: mockHubTemplate
        MapQuickItem {
            coordinate: QtPositioning.coordinate(43.655, -79.383)
            anchorPoint.x: 10
            anchorPoint.y: 10
            autoFadeIn: false
            sourceItem: Item {
                width: 140
                height: 38
                Rectangle {
                    x: 0; y: 0
                    width: 20; height: 20; radius: 10
                    color: "#1B0623"
                    border.width: 3
                    border.color: "#ED981A"
                }
                Rectangle {
                    x: 27; y: 1
                    width: 108; height: 22
                    color: "#1B0623"
                    border.width: 1
                    border.color: "#C74EC7"
                    Text {
                        anchors.centerIn: parent
                        text: "DEMO HUB"
                        color: "#F2BE4E"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
            }
        }
    }

    // Owner-only *reported* local locations. No names, no real organization
    // grants, no automatic camera pan, no event logs containing local IDs.
    Component {
        id: ownerReportedHubTemplate
        MapQuickItem {
            anchorPoint.x: 9
            anchorPoint.y: 9
            autoFadeIn: false
            sourceItem: Item {
                width: 120
                height: 26
                Rectangle {
                    width: 18
                    height: 18
                    radius: 9
                    color: "#1B0623"
                    border.width: 3
                    border.color: "#ED981A"
                }
                Rectangle {
                    x: 24
                    width: 95
                    height: 24
                    color: "#1B0623"
                    border.width: 1
                    border.color: "#C74EC7"
                    Text {
                        anchors.centerIn: parent
                        text: "REPORTED HUB"
                        font.pixelSize: 10
                        color: "#F2BE4E"
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: console.log("OWNER_LOCAL_REPORTED_MARKER_SELECTED")
                }
            }
        }
    }

    // A fixed public Toronto fixture validates record -> geographic marker.
    // It does not read CompanyHubDirectory or define service coverage.
    Component {
        id: fixtureHubTemplate
        MapQuickItem {
            id: pin
            property string fixtureId: ""
            property string displayLabel: ""
            anchorPoint.x: 7
            anchorPoint.y: 7
            autoFadeIn: false
            sourceItem: Item {
                width: 115
                height: 33
                Rectangle {
                    width: 14
                    height: 14
                    radius: 7
                    color: "#1B0623"
                    border.width: 2
                    border.color: "#ED981A"
                }
                Rectangle {
                    x: 18
                    width: 95
                    height: 24
                    color: "#1B0623"
                    border.width: 1
                    border.color: "#C74EC7"
                    Text {
                        anchors.centerIn: parent
                        color: "#F2BE4E"
                        font.pixelSize: 10
                        text: pin.displayLabel
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: console.log("FIXTURE_MARKER_SELECTED "+pin.fixtureId)
                }
            }
        }
    }

    // Fixed automated motion from a known public map coordinate. The Qt
    // C++ process samples frameSwapped intervals, not mouse or user location.
    Timer {
        id: beginMotion
        interval: 8000
        repeat: false
        running: probeBenchMotion
        onTriggered: {
            root.motionTick=0;
            motionDriver.start();
            console.log("BENCH_MOTION_STARTED");
        }
    }
    Timer {
        id: motionDriver
        interval: 33
        repeat: true
        running: false
        onTriggered: {
            root.motionTick += 1;
            var t=root.motionTick/28;
            mapView.map.center=QtPositioning.coordinate(
                43.655+Math.sin(t)*0.0018,
                -79.383+Math.cos(t)*0.0025);
            mapView.map.zoomLevel=15.6+0.25*Math.sin(t/2);
            if (root.motionTick>=150) {
                motionDriver.stop();
                console.log("BENCH_MOTION_DONE steps="+root.motionTick);
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 54
        color: "#1B0623"
        border.color: "#55CFCA"
        border.width: 1
        z: 10
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: "🏙  COMPANY // VECTOR PROOF"
            color: "#F2BE4E"
            font.pixelSize: 20
            font.bold: true
        }
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: probeOwnerLocalMode ? "OWNER-LOCAL REPORTED HUBS // NOT VERIFIED"
                : probeStyledOnline ? "POST-APOLLO VECTOR // ONLINE"
                : probeOnline ? "ONLINE VECTOR // REFERENCE"
                : "OFFLINE SYNTHETIC FIXTURE"
            color: "#C74EC7"
            font.pixelSize: 13
        }
    }

    Flickable {
        id: cameraRail
        anchors.top: parent.top
        anchors.topMargin: 72
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 50
        anchors.right: parent.right
        anchors.rightMargin: 12
        width: 92
        clip: true
        z: 10
        contentWidth: width
        contentHeight: cameraColumn.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: cameraColumn
            width: cameraRail.width
            spacing: 5
            Repeater {
                model: probeOnline
                    ? ["+", "−", "USA", "PACIFIC", "MIDWEST",
                       "NORTHEAST", "RURAL", "CANADA", "MEXICO",
                       "ALASKA", "HAWAII", "FLINT", "SUBURB",
                       "VILLAGE", "NEIGHBORHOOD", "BORDER"]
                    : ["+", "−", "FLINT"]

                Rectangle {
                    required property string modelData
                    width: cameraColumn.width - 4
                    height: 32
                    color: "#1B0623"
                    border.color: "#5B5FD4"
                    border.width: 2
                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 4
                        horizontalAlignment: Text.AlignHCenter
                        color: "#DCF3FA"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        text: parent.modelData
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (modelData === "+")
                                mapView.map.zoomLevel=Math.min(18,mapView.map.zoomLevel+1);
                            else if (modelData === "−")
                                mapView.map.zoomLevel=Math.max(2,mapView.map.zoomLevel-1);
                            else root.goToSample(modelData);
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 42
        color: "#1B0623"
        border.color: "#55CFCA"
        border.width: 1
        z: 10
        Text {
            anchors.centerIn: parent
            color: "#DCF3FA"
            font.pixelSize: 12
            text: probeOnline
                ? "© OpenStreetMap contributors · © OpenMapTiles · OpenFreeMap | VIEWPORT DISCLOSED · NOT COMPANY COVERAGE"
                : "SYNTHETIC VECTOR GEOMETRY · NOT REAL STREETS OR COMPANY COVERAGE"
        }
    }
}
