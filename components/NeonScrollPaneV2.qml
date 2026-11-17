import QtQuick

// ScrollPane V2 // the viewport and proportional rail share one stable host.
// The parent picks the available area; this component never stretches the
// rail across adjacent panels or silently changes the external window size.
Item {
    id: root
    default property alias contentData: scrollContents.data
    property alias flickable: viewport
    property alias scrollBar: rail

    property string viewportPolicy: "fill" // fill | split | fixed
    property real availableExtent: 0
    property real splitFraction: 0.46
    property real fixedExtent: 210
    property real minimumSplitExtent: 120
    readonly property bool validPolicy:
        viewportPolicy === "fill" || viewportPolicy === "split"
        || viewportPolicy === "fixed"
    readonly property real preferredExtent: {
        const available = Math.max(0, availableExtent);
        if (!validPolicy || viewportPolicy === "fill")
            return available;
        const requested = viewportPolicy === "split"
            ? Math.round(available * Math.max(0, Math.min(1, splitFraction)))
            : Math.max(0, fixedExtent);
        return Math.min(available, Math.max(minimumSplitExtent, requested));
    }

    property real contentExtent: 0
    property int contentGutter: 22
    property string handleStyle: "bar"
    property int rightInset: 2
    implicitHeight: preferredExtent

    Flickable {
        id: viewport
        objectName: "neonScrollPaneViewport"
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        contentWidth: width
        contentHeight: Math.max(0, root.contentExtent)
        Item {
            id: scrollContents
            width: viewport.width
            height: Math.max(0, root.contentExtent)
        }
    }

    NeonScrollBar {
        id: rail
        objectName: "neonScrollPaneTrack"
        flickable: viewport
        mountingParent: root
        geometryHost: root
        geometryMode: "box"
        handleStyle: root.handleStyle
        rightInset: root.rightInset
        visible: root.visible && scrollable
    }
}
