import QtQuick
import Quickshell
import "components"
import "tests/fixtures" as Fixtures

// F2 VALUE standalone shell entry point.
// Keep this QML file at the Quickshell CONFIG ROOT so qmlscanner can
// resolve tests/fixtures/ and components/ without crossing its root.
// Launch explicitly with -p; it is NOT part of normal shell.qml.
FloatingWindow {
    id: valueTestWindow
    title: "POST_APOLLO_SELECTOR_VALUE_TEST"
    width: 590
    height: 410
    visible: true
    color: "#1B0623"

    Fixtures.SelectorSliderValueDemo {
        anchors.centerIn: parent
    }
}
