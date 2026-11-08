import QtQuick
import "../../components"

// C33 // Reusable full *subject-stage* photo focus; never changes PanelWindow
// geometry, switches desktop windows, or starts another image provider.
// Caller supplies the active archival source/credit and gallery callbacks.
Rectangle {
    id: photoFocus
    objectName: "cosmos-c33-photo-focus"
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true
    focus: visible

    property string sourceUrl: ""
    property string photoTitle: "ARCHIVAL IMAGE"
    property string credit: ""
    // C34 // Archived photos and periodically refreshed NOAA source images
    // share controls but must not share an inaccurate "ARCHIVAL" label
    // or stale cache behavior.
    property bool archival: true
    property bool canNext: false
    property bool canPlay: false
    property bool playing: false
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property real minZoom: 1
    readonly property real maxZoom: 4

    signal closeRequested()
    signal nextRequested()
    signal playRequested()

    function setZoom(next) {
        const numeric=Number(next);
        if (!isFinite(numeric)) return;
        zoom=Math.max(minZoom,Math.min(maxZoom,numeric));
        if (zoom===1) {
            panX=0;
            panY=0;
        } else {
            clampPan();
        }
    }
    function clampPan() {
        const maxX=Math.max(0,photoViewport.width*(zoom-1)/2);
        const maxY=Math.max(0,photoViewport.height*(zoom-1)/2);
        panX=Math.max(-maxX,Math.min(maxX,panX));
        panY=Math.max(-maxY,Math.min(maxY,panY));
    }
    function resetView() {
        zoom=1;
        panX=0;
        panY=0;
    }
    onVisibleChanged: {
        if (visible) {
            resetView();
            forceActiveFocus();
        }
    }
    onSourceUrlChanged: resetView()
    Keys.onEscapePressed: function(event) {
        photoFocus.closeRequested();
        event.accepted=true;
    }

    Rectangle {
        id: photoToolbar
        objectName: "cosmos-c33-photo-toolbar"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 25
        color: Colors.dark
        z: 3
        Row {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 4

            ActionButton {
                objectName: "cosmos-c33-photo-back"
                width: 60
                height: 19
                label: "BACK"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.magenta
                onClicked: photoFocus.closeRequested()
            }
            GohuText {
                width: Math.max(1,parent.width-60-4
                    -(photoFocus.canNext ? 42+4 : 0)
                    -(photoFocus.canPlay ? 48+4 : 0)-31-25-25-31-4*4)
                height: 19
                text: photoFocus.photoTitle
                font.pixelSize: 10
                color: Colors.white
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            ActionButton {
                objectName: "cosmos-c33-photo-prev-zoom"
                width: 25
                height: 19
                label: "-"
                labelPixelSize: 11
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: photoFocus.setZoom(photoFocus.zoom-0.5)
            }
            ActionButton {
                objectName: "cosmos-c33-photo-next-zoom"
                width: 25
                height: 19
                label: "+"
                labelPixelSize: 11
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: photoFocus.setZoom(photoFocus.zoom+0.5)
            }
            ActionButton {
                objectName: "cosmos-c33-photo-fit"
                width: 31
                height: 19
                label: "FIT"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.yellow
                onClicked: photoFocus.resetView()
            }
            ActionButton {
                objectName: "cosmos-c33-photo-play"
                visible: photoFocus.canPlay
                width: visible ? 48 : 0
                height: 19
                label: photoFocus.playing ? "PAUSE" : "PLAY"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: photoFocus.playRequested()
            }
            ActionButton {
                objectName: "cosmos-c33-photo-next"
                visible: photoFocus.canNext
                width: visible ? 42 : 0
                height: 19
                label: "NEXT"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.orange
                onClicked: photoFocus.nextRequested()
            }
        }
    }

    Item {
        id: photoViewport
        objectName: "cosmos-c33-photo-viewport"
        anchors.top: photoToolbar.bottom
        anchors.bottom: photoCaption.top
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true

        Image {
            id: expandedPhoto
            objectName: "cosmos-c33-photo-image"
            source: photoFocus.visible ? photoFocus.sourceUrl : ""
            asynchronous: true
            cache: photoFocus.archival
            smooth: true
            fillMode: Image.PreserveAspectFit
            width: Math.max(1,photoViewport.width*photoFocus.zoom)
            height: Math.max(1,photoViewport.height*photoFocus.zoom)
            x: (photoViewport.width-width)/2+photoFocus.panX
            y: (photoViewport.height-height)/2+photoFocus.panY
            visible: status===Image.Ready
        }

        QuietText {
            anchors.centerIn: parent
            width: Math.max(1,parent.width-20)
            text: expandedPhoto.status===Image.Error
                ? (photoFocus.archival ? "ARCHIVAL IMAGE OFFLINE" : "NOAA IMAGE UNAVAILABLE")
                : (photoFocus.archival ? "LOADING ARCHIVAL IMAGE" : "LOADING NOAA IMAGE")
            font.pixelSize: 10
            color: Colors.orange
            horizontalAlignment: Text.AlignHCenter
            visible: expandedPhoto.status!==Image.Ready
            elide: Text.ElideRight
        }

        MouseArea {
            id: imageGesture
            objectName: "cosmos-c33-photo-gesture"
            anchors.fill: parent
            enabled: expandedPhoto.status===Image.Ready
            cursorShape: photoFocus.zoom>1
                ? Qt.OpenHandCursor : Qt.PointingHandCursor
            property real pressX: 0
            property real pressY: 0
            property real startPanX: 0
            property real startPanY: 0
            onPressed: function(mouse) {
                pressX=mouse.x;
                pressY=mouse.y;
                startPanX=photoFocus.panX;
                startPanY=photoFocus.panY;
            }
            onPositionChanged: function(mouse) {
                if (!pressed || photoFocus.zoom<=1) return;
                photoFocus.panX=startPanX+mouse.x-pressX;
                photoFocus.panY=startPanY+mouse.y-pressY;
                photoFocus.clampPan();
            }
            onWheel: function(wheel) {
                if (wheel.angleDelta.y===0) return;
                photoFocus.setZoom(photoFocus.zoom+(wheel.angleDelta.y>0?0.25:-0.25));
                wheel.accepted=true;
            }
            onDoubleClicked: photoFocus.resetView()
        }
    }

    Rectangle {
        id: photoCaption
        objectName: "cosmos-c33-photo-credit"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 21
        color: Colors.dark
        z: 3
        QuietText {
            anchors.fill: parent
            anchors.margins: 4
            text: photoFocus.photoTitle + " // " + photoFocus.credit
                  + (photoFocus.archival ? " // ARCHIVAL, NOT LIVE"
                      : " // NOAA SOURCE SNAPSHOT, NOT CONTINUOUS VIDEO")
            color: Colors.yellow
            font.pixelSize: 9
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }
}
