import QtQuick
import Quickshell
import qs.services.input
import "../../components"

// Real native Sway Scroll Lock; Windows-rate autoscroll engine is deliberately
// non-operational until a verified, consented global pointer input bridge exists.
Item {
    id: pane
    property string area: "devices"
    property bool panelVisible: visible

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, contents.implicitHeight + 18)
        Column {
            id: contents
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 17)
            spacing: 11

            Column {
                visible: pane.area === "devices"
                width: parent.width
                spacing: 9
                GohuText {
                    width: parent.width
                    text: "MIDDLE-CLICK // SCROLL MODES"
                    font.pixelSize: 12
                    color: Colors.cyan
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "BACK TO MOUSE SENSITIVITY"
                    labelPixelSize: 10
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.closeModePage()
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: ScrollModeSettings.busy
                           ? "READING POINTERS" : "REFRESH SWAY POINTERS"
                    labelPixelSize: 10
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.inspect()
                }
                GohuText {
                    width: parent.width
                    text: "ONE PHYSICAL POINTER PER MODE. THIS IS NOT THE SAME AS KITTY OR ZELLIJ SCROLL SPEED."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: ScrollModeSettings.devices
                    delegate: Column {
                        id: devRow
                        required property var modelData
                        width: contents.width
                        spacing: 3
                        ActionButton {
                            width: parent.width
                            height: 38
                            label: devRow.modelData.name
                            labelPixelSize: 9
                            labelMinimumPixelSize: 7
                            selected: ScrollModeSettings.selectedId
                                      === devRow.modelData.identifier
                            available: !ScrollModeSettings.busy
                            onLeftClicked: ScrollModeSettings.chooseDevice(
                                devRow.modelData.identifier)
                        }
                        GohuText {
                            width: parent.width
                            text: "SWAY // " + devRow.modelData.scroll_method
                                + " // LOCK "
                                + devRow.modelData.scroll_button_lock.toUpperCase()
                            font.pixelSize: 9
                            color: Colors.white
                            wrapMode: Text.WordWrap
                        }
                    }
                }
                GohuText {
                    visible: ScrollModeSettings.devices.length === 0
                    width: parent.width
                    text: "NO COMPATIBLE POINTER // " + ScrollModeSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
            Column {
                visible: pane.area === "factor"
                width: parent.width
                spacing: 11
                GohuText {
                    width: parent.width
                    text: "MOUSE // SCROLL MODE"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                ActionButton {
                    width: parent.width
                    height: 42
                    label: "NORMAL // OFF"
                    labelPixelSize: 11
                    selected: ScrollModeSettings.stagedMode === "off"
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.chooseMode("off")
                }
                GohuText {
                    width: parent.width
                    text: "RESTORE YOUR EXACT PREVIOUS SWAY POINTER CONFIGURATION. DOES NOT CHANGE IT UNTIL CONFIRMED."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 42
                    label: "SWAY SCROLL LOCK"
                    labelPixelSize: 11
                    selected: ScrollModeSettings.stagedMode === "lock"
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.chooseMode("lock")
                }
                GohuText {
                    width: parent.width
                    text: "MIDDLE-CLICK TO LOCK. MOVING THE MOUSE PRODUCES SCROLL EVENTS. CLICK AGAIN TO UNLOCK; STOP MOVING TO STOP SCROLLING."
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 42
                    label: "UNIVERSAL AUTOSCROLL"
                    labelPixelSize: 11
                    selected: ScrollModeSettings.stagedMode === "auto"
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.chooseMode("auto")
                }
                GohuText {
                    width: parent.width
                    text: "WINDOWS-STYLE ANCHOR AND CONTINUOUS RATE ENGINE. PREVIEW ONLY // GLOBAL INPUT CAPTURE + WAYLAND AXIS INJECTION NOT YET VERIFIED."
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "MODES ARE MUTUALLY EXCLUSIVE. AUTOSCROLL CANNOT ACTIVATE FROM THIS PREVIEW."
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
            }
            Column {
                visible: pane.area === "apply"
                width: parent.width
                spacing: 11
                GohuText {
                    width: parent.width
                    text: "SCROLL MODE // SAFETY"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "SELECTED // " + ScrollModeSettings.stagedMode.toUpperCase()
                    font.pixelSize: 11
                    color: Colors.yellow
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "RECOVERABLE LOCK // "
                          + (ScrollModeSettings.hasSnapshot
                             ? "SAVED FOR " + ScrollModeSettings.activeId
                             : "NONE")
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "SWAY IPC // " + ScrollModeSettings.hostStatus.toUpperCase()
                    color: ScrollModeSettings.hostError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: ScrollModeSettings.stagedMode === "auto"
                        ? "NOT AVAILABLE FOR LIVE USE. NATIVE GLOBAL MIDDLE-CLICK CAPTURE, POINTER ANCHOR OVERLAY AND VIRTUAL SCROLL INJECTION REQUIRE SEPARATE VERIFICATION."
                        : "CHANGES TO PHYSICAL INPUT ARE LIVE SESSION ONLY. THE ORIGINAL SETTINGS ARE SNAPSHOTTED BEFORE APPLYING AND CAN BE RESTORED AFTER A SHELL RESTART."
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 35
                    label: "PREPARE INPUT MODE"
                    labelPixelSize: 10
                    selected: ScrollModeSettings.pendingAction !== ""
                    available: ScrollModeSettings.canPrepare
                    onLeftClicked: ScrollModeSettings.prepare()
                }
                ActionButton {
                    visible: ScrollModeSettings.pendingAction !== ""
                    width: parent.width
                    height: visible ? 35 : 0
                    label: ScrollModeSettings.pendingAction === "enable"
                           ? "CONFIRM SCROLL LOCK"
                           : "CONFIRM RESTORE NORMAL"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: !ScrollModeSettings.busy
                    onLeftClicked: ScrollModeSettings.confirm()
                }
                ActionButton {
                    visible: ScrollModeSettings.pendingAction !== ""
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    onLeftClicked: ScrollModeSettings.cancel()
                }
                GohuText {
                    width: parent.width
                    text: ScrollModeSettings.feedback
                    font.pixelSize: 9
                    color: ScrollModeSettings.hostError.length
                           ? Colors.orange : Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    visible: ScrollModeSettings.hostError.length > 0
                    width: parent.width
                    text: "ERROR // " + ScrollModeSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "IF QUICKSHELL EXITS WHILE LOCKED, REOPEN THIS MENU, REFRESH, SELECT NORMAL AND CONFIRM RESTORE."
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    NeonScrollBar {
        flickable: scroll
        visible: pane.panelVisible && scrollable
    }
}
