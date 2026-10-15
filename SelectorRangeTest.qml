import QtQuick
import Quickshell
import "components"
import "tests/fixtures" as Fixtures

// Explicit root-level test entry point. Never imported by production shell.
FloatingWindow {
    id: rangeTestWindow
    title: "POST_APOLLO_SELECTOR_RANGE_TEST"
    width: 915
    height: 475
    visible: true
    color: "#1B0623"

    Fixtures.SelectorSliderRangeDemo {
        anchors.centerIn: parent
    }
}
