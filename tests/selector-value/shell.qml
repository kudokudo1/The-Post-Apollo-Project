import QtQuick
import Quickshell
import "../fixtures" as Fixtures

// Optional standalone Quickshell config for manual F2 inspection.
// It is deliberately NOT loaded by the normal Post-Apollo shell.
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
