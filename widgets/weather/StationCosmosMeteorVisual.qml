import QtQuick
import "../../components"

// C29 // Embedded NASA archival photograph plus an IAU-source countdown.
// The 2016 Perseid exposure is an example photograph, NOT a live feed,
// an image of the currently selected shower, or a local viewing forecast.
Rectangle {
    id: visual
    objectName: "cosmos-c29-meteor-visual"
    color: Colors.dark
    border.width: 1
    border.color: Colors.orange
    clip: true

    property var upcomingShowers: []
    property string selectedShowerName: ""
    property bool sourceReady: false

    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property real minZoom: 1
    readonly property real maxZoom: 3
    readonly property var activePeak: {
        const rows = upcomingShowers || [];
        if (selectedShowerName !== "") {
            for (let i = 0; i < rows.length; ++i)
                if (rows[i] && rows[i].name === selectedShowerName)
                    return rows[i];
        }
        return rows.length > 0 ? rows[0] : null;
    }
    readonly property real daysToPeak: {
        const row = activePeak;
        if (!sourceReady || !row || row.daysToPeak === undefined
            || row.daysToPeak === null) return NaN;
        const days = Number(row.daysToPeak);
        return isFinite(days) ? days : NaN;
    }
    readonly property bool hasCountdown: isFinite(daysToPeak)
        && daysToPeak >= 0
    readonly property real remaining30DayFraction: hasCountdown
        ? Math.max(0,Math.min(1,daysToPeak/30)) : 0

    function setZoom(next) {
        zoom = Math.max(minZoom,Math.min(maxZoom,next));
        if (zoom === 1) {
            panX = 0;
            panY = 0;
        } else {
            panX = Math.max(-visual.width*(zoom-1)/2,
                Math.min(visual.width*(zoom-1)/2,panX));
            panY = Math.max(-photoArea.height*(zoom-1)/2,
                Math.min(photoArea.height*(zoom-1)/2,panY));
        }
    }
    function resetView() {
        zoom = 1;
        panX = 0;
        panY = 0;
    }

    Item {
        id: photoArea
        objectName: "cosmos-c29-meteor-photo-viewport"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: dataFooter.top
        clip: true

        Image {
            id: nasaPhoto
            objectName: "cosmos-c29-nasa-archival-photo"
            // NASA/Bill Ingalls, Perseid over Spruce Knob WV, 2016-08-12.
            // Official original: https://science.nasa.gov/resource/perseid-meteor-over-west-virginia/
            // This image is loaded ONLY when COSMOS -> METEORS is visible.
            source: "https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/p/e/perseidwestva1200w.jpg/jcr:content/renditions/cq5dam.web.1280.1280.jpeg"
            asynchronous: true
            cache: true
            fillMode: Image.PreserveAspectCrop
            width: Math.max(1,photoArea.width*visual.zoom)
            height: Math.max(1,photoArea.height*visual.zoom)
            x: (photoArea.width-width)/2+visual.panX
            y: (photoArea.height-height)/2+visual.panY
            visible: status === Image.Ready
            smooth: true
        }

        QuietText {
            anchors.centerIn: parent
            width: Math.max(1,parent.width-10)
            visible: nasaPhoto.status !== Image.Ready
            text: nasaPhoto.status === Image.Error
                ? "NASA PHOTO OFFLINE" : "NASA PHOTO LOADING"
            color: Colors.cyan
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        MouseArea {
            id: photoGesture
            anchors.fill: parent
            enabled: nasaPhoto.status === Image.Ready
            cursorShape: visual.zoom > 1 ? Qt.OpenHandCursor : Qt.PointingHandCursor
            property real startX: 0
            property real startY: 0
            property real originalPanX: 0
            property real originalPanY: 0
            onPressed: function(mouse) {
                startX = mouse.x;
                startY = mouse.y;
                originalPanX = visual.panX;
                originalPanY = visual.panY;
            }
            onPositionChanged: function(mouse) {
                if (!pressed || visual.zoom <= 1) return;
                const maxX = photoArea.width*(visual.zoom-1)/2;
                const maxY = photoArea.height*(visual.zoom-1)/2;
                visual.panX = Math.max(-maxX,
                    Math.min(maxX,originalPanX+mouse.x-startX));
                visual.panY = Math.max(-maxY,
                    Math.min(maxY,originalPanY+mouse.y-startY));
            }
            onWheel: function(wheel) {
                if (wheel.angleDelta.y === 0) return;
                visual.setZoom(visual.zoom+(wheel.angleDelta.y>0?0.25:-0.25));
                wheel.accepted = true;
            }
            onDoubleClicked: visual.resetView()
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 19
            color: "#C81B0623"
            z: 2
            Row {
                anchors.fill: parent
                anchors.margins: 2
                spacing: 2
                QuietText {
                    width: Math.max(1,parent.width-90)
                    text: "NASA // ARCHIVE 2016"
                    color: Colors.yellow
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
                Repeater {
                    model: [
                        {label:"+",delta:0.5},
                        {label:"-",delta:-0.5},
                        {label:"FIT",delta:0}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: modelData.delta===0 ? 32 : 22
                        height: 16
                        label: modelData.label
                        labelPixelSize: 8
                        contentPadding: 0
                        accentColor: Colors.cyan
                        onClicked: modelData.delta===0
                            ? visual.resetView()
                            : visual.setZoom(visual.zoom+modelData.delta)
                    }
                }
            }
        }
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 17
            color: "#D01B0623"
            z: 2
            QuietText {
                anchors.fill: parent
                anchors.margins: 3
                color: Colors.cyan
                font.pixelSize: 8
                text: "PERSEID PHOTO // NASA / BILL INGALLS"
                elide: Text.ElideRight
            }
        }
    }

    Rectangle {
        id: dataFooter
        objectName: "cosmos-c29-peak-countdown"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 31
        color: Colors.black
        border.width: 1
        border.color: Colors.magenta
        Column {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 3
            QuietText {
                width: parent.width
                height: 10
                color: Colors.yellow
                font.pixelSize: 8
                text: visual.hasCountdown
                    ? "PEAK IN " + visual.daysToPeak.toFixed(1) + " D // 30D WINDOW"
                    : "IAU PEAK COUNTDOWN // UNAVAILABLE"
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: 6
                color: Colors.dark
                border.color: Colors.blue
                border.width: 1
                Rectangle {
                    id: countdownFill
                    objectName: "cosmos-c29-source-countdown-fill"
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: parent.width*visual.remaining30DayFraction
                    color: Colors.orange
                    Behavior on width {
                        NumberAnimation {
                            duration: 350
                            easing.type: Easing.OutCubic
                        }
                    }
                }
            }
        }
    }
}
