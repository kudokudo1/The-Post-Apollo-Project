import QtQuick

// CAMERA M2 // Native zoomable image viewer. The original file is read-only:
// wheel zooms around the pointer; drag pans while enlarged. No bitmap edits,
// no background write, no permanently rendered pixel cache.
Item {
    id: viewer

    property url source: ""
    property real zoom: 1.0
    readonly property real minZoom: 1.0
    readonly property real maxZoom: 8.0
    readonly property real fitScale:
        photo.status === Image.Ready && photo.implicitWidth > 0
        && photo.implicitHeight > 0
        ? Math.min(Math.max(1, viewport.width - 8) / photo.implicitWidth,
                   Math.max(1, viewport.height - 8) / photo.implicitHeight)
        : 1

    function reset() {
        zoom = 1.0;
        viewport.contentX = 0;
        viewport.contentY = 0;
    }

    onSourceChanged: reset()

    // Preserve the picture point underneath the cursor, rather than snapping
    // the image to an unrelated corner whenever the wheel is turned.
    function changeZoom(multiplier, pointerX, pointerY) {
        if (!viewer.source || photo.status !== Image.Ready)
            return;
        const next = Math.max(minZoom, Math.min(maxZoom, zoom * multiplier));
        if (Math.abs(next - zoom) < 0.0001)
            return;
        const x = Math.max(0, Math.min(viewport.width, Number(pointerX)));
        const y = Math.max(0, Math.min(viewport.height, Number(pointerY)));
        const oldW = Math.max(viewport.width, photo.width);
        const oldH = Math.max(viewport.height, photo.height);
        const fractionX = (viewport.contentX + x) / oldW;
        const fractionY = (viewport.contentY + y) / oldH;
        zoom = next;
        Qt.callLater(function() {
            const newW = Math.max(viewport.width, photo.width);
            const newH = Math.max(viewport.height, photo.height);
            viewport.contentX = Math.max(0, Math.min(
                newW - viewport.width, fractionX * newW - x));
            viewport.contentY = Math.max(0, Math.min(
                newH - viewport.height, fractionY * newH - y));
        });
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 1
        border.color: "#55CFCA"
    }

    Flickable {
        id: viewport
        anchors.fill: parent
        anchors.margins: 3
        clip: true
        interactive: viewer.zoom > 1.001
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: Math.max(width, photo.width)
        contentHeight: Math.max(height, photo.height)

        Image {
            id: photo
            source: viewer.source
            asynchronous: true
            cache: false
            smooth: true
            fillMode: Image.PreserveAspectFit
            width: Math.max(1, implicitWidth * viewer.fitScale * viewer.zoom)
            height: Math.max(1, implicitHeight * viewer.fitScale * viewer.zoom)
            x: (viewport.contentWidth - width) / 2
            y: (viewport.contentHeight - height) / 2
        }

        WheelHandler {
            id: zoomWheel
            target: null
            onWheel: function(event) {
                const amount = event.angleDelta.y !== 0
                    ? event.angleDelta.y : event.pixelDelta.y;
                if (amount === 0)
                    return;
                viewer.changeZoom(amount > 0 ? 1.25 : 0.8,
                                  event.x, event.y);
                event.accepted = true;
            }
        }
    }
}
