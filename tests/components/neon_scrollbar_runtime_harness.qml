import QtQuick
import QtQuick.Window
import "../../components" as Shared

Window {
    id: root
    width: 370
    height: 475
    visible: true
    color: "#1B0623"

    // The outer scroll area owns independent scroll content.
    Flickable {
        id: outer
        objectName: "outerPane"
        x: 12; y: 12; width: 315; height: 254
        contentWidth: width; contentHeight: 570
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick

        Flickable {
            id: inner
            objectName: "innerPane"
            x: 12; y: 18; width: 245; height: 150
            contentWidth: width; contentHeight: 600
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            focus: true

            Rectangle {
                width: parent.width
                height: 600
                color: "#16051F"
            }
        }

        Shared.NeonScrollBar {
            id: scrollbar
            objectName: "auditScrollBar"
            flickable: inner
            // Explicit values make the defaults visible to the smoke harness.
            nestedScrollMode: "contain"
            viewportHasEndpointClearance: false
        }
    }

    // Standalone horizontal instance of the same component family.
    Flickable {
        id: horizontalPane
        objectName: "horizontalPane"
        x: 12; y: 315; width: 290; height: 42
        contentWidth: 890; contentHeight: height
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick
        Rectangle { width: 890; height: parent.height; color: "#16051F" }
    }
    Shared.NeonScrollBar {
        id: horizontalBar
        objectName: "horizontalBar"
        flickable: horizontalPane
        orientation: Qt.Horizontal
    }

    // Simulate a real menu Column. The bar is declaratively nested here,
    // then mounted on the surrounding Rectangle to avoid taking a layout row.
    Rectangle {
        id: positionedHost
        objectName: "positionedHost"
        x: 14; y: 378; width: 320; height: 78
        color: "#16051F"
        Column {
            id: positioner
            objectName: "positioner"
            x: 7; y: 11; width: 260
            Flickable {
                id: positionerPane
                objectName: "positionerPane"
                width: parent.width; height: 50
                contentWidth: width; contentHeight: 240
                boundsBehavior: Flickable.StopAtBounds
            }
            Shared.NeonScrollBar {
                id: positionerBar
                objectName: "positionerBar"
                flickable: positionerPane
                handleStyle: "star"
                mountingParent: positionedHost
            }
        }
    }

    // Test target can be driven without direct QML context id lookup.
    property alias innerPane: inner
    property alias outerPane: outer
    property alias auditBar: scrollbar
}
