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
        // A Flickable normally handles wheel deltas as vertical scrolling.
        // Its content coordinates remain useful for clipping/pan, but pointer
        // input is exclusively owned by the sibling MouseArea below.
        interactive: false
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

    }

    // The viewer owns its wheel/drag surface. MouseArea receives wheel input
    // ahead of the Flickable and deliberately consumes it as zoom, never
    // allowing a vertical scroll to move the picture or its parent gallery.
    // Left-drag is the only action that changes pan (contentX/contentY).
    MouseArea {
        id: zoomPanMouse
        anchors.fill: viewport
        z: 2
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        cursorShape: viewer.zoom > 1.001 ? (pressed ? Qt.ClosedHandCursor
                    : Qt.OpenHandCursor) : Qt.ArrowCursor
        property real dragStartX: 0
        property real dragStartY: 0
        property real panStartX: 0
        property real panStartY: 0

        onPressed: function(mouse) {
            dragStartX = mouse.x;
            dragStartY = mouse.y;
            panStartX = viewport.contentX;
            panStartY = viewport.contentY;
        }
        onPositionChanged: function(mouse) {
            if (!pressed || viewer.zoom <= 1.001)
                return;
            const maxX = Math.max(0, viewport.contentWidth - viewport.width);
            const maxY = Math.max(0, viewport.contentHeight - viewport.height);
            viewport.contentX = Math.max(0, Math.min(
                maxX, panStartX + dragStartX - mouse.x));
            viewport.contentY = Math.max(0, Math.min(
                maxY, panStartY + dragStartY - mouse.y));
        }
        onWheel: function(wheel) {
            // Prevent Flickable's normal wheel-to-scroll fallback even when
            // an image has not finished decoding or is at a zoom boundary.
            wheel.accepted = true;
            const delta = wheel.angleDelta.y !== 0
                ? wheel.angleDelta.y : wheel.pixelDelta.y;
            if (delta === 0)
                return;
            viewer.changeZoom(delta > 0 ? 1.25 : 0.8,
                              wheel.x, wheel.y);
        }
    }
}
