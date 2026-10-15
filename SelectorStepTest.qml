import QtQuick
import Quickshell
import "components"
import "tests/fixtures" as Fixtures

// Dedicated root-level Quickshell entry point (never loaded in shell.qml).
// Keeping the file at configuration root preserves Quickshell's import paths.
FloatingWindow {
    id: stepTestWindow
    title: "POST_APOLLO_SELECTOR_STEP_TEST"
    width: 780
    height: 455
    visible: true
    color: "#1B0623"

    Fixtures.SelectorSliderStepDemo {
        anchors.centerIn: parent
    }
}
