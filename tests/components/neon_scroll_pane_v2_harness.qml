import QtQuick
import QtQuick.Window
import "../../components" as Shared

// Offscreen source-level integration for the real shared ScrollPane V2 type.
// Market's outer list/selected-detail orchestration is separately guarded.
Window {
    id: root
    width: 330
    height: 500
    visible: true
    color: "#160923"
    property string policy: "fill"
    property int countRows: 32
    property bool listActive: true

    Item {
        id: host
        objectName: "marketBody"
        x: 10
        y: 18
        width: Math.max(0, root.width - 20)
        height: Math.max(0, root.height - 100)

        Rectangle {
            id: marketList
            objectName: "marketList"
            width: host.width
            height: pane.preferredExtent
            color: "#200a34"
            visible: root.listActive

            Shared.NeonScrollPaneV2 {
                id: pane
                objectName: "sharedMarketPane"
                anchors.fill: parent
                viewportPolicy: root.policy
                availableExtent: host.height
                splitFraction: 0.46
                fixedExtent: 205
                contentExtent: marketRows.height
                handleStyle: "bar"
                rightInset: 2

                Column {
                    id: marketRows
                    objectName: "marketRows"
                    width: Math.max(0, pane.flickable.width - pane.contentGutter)
                    spacing: 3
                    Repeater {
                        model: root.countRows
                        delegate: Rectangle {
                            width: marketRows.width
                            height: 42
                            color: index % 2 ? "#29133b" : "#321544"
                        }
                    }
                }
            }
        }
    }
}
