import QtQuick
import QtQuick.Window
import "../../components" as Shared

Window {
    id: root
    width: 370
    height: 300
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

    // Test target can be driven without direct QML context id lookup.
    property alias innerPane: inner
    property alias outerPane: outer
    property alias auditBar: scrollbar
}
