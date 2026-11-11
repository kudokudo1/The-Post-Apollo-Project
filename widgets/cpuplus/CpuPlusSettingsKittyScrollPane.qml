import QtQuick
import Quickshell
import qs.services.input
import "../../components"

// Reuses existing CPU++ Mouse Settings bays; no shared host/rail edits.
// Sway device factors and Kitty scrollback factors remain independent.
Item {
    id: kittyPane
    property string area: "devices" // devices | factor | apply
    property bool panelVisible: visible
    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, content.implicitHeight + 16)
        Column {
            id: content
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 17)
            spacing: 11
            Column {
                visible: kittyPane.area === "devices"
                width: parent.width
                spacing: 10
                GohuText {
                    width: parent.width
                    text: "KITTY // TERMINAL SCROLL"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "BACK TO SWAY DEVICE CONTROLS"
                    labelPixelSize: 9
                    onLeftClicked: KittyScrollSettings.chooseMode(false)
                }
                GohuText {
                    width: parent.width
                    text: "KITTY CONTROLS TWO DIFFERENT INPUT STREAMS. THEY DO NOT CHANGE YOUR SYSTEM-WIDE MOUSE FACTOR."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LOW-PRECISION WHEEL // MOUSE WHEEL MULTIPLIER"
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "HIGH-PRECISION // WAYLAND TOUCHPAD AND SMOOTH WHEEL EVENTS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: KittyScrollSettings.busy ? "INSPECTING KITTY" : "REFRESH KITTY CONFIG"
                    labelPixelSize: 10
                    available: !KittyScrollSettings.busy
                    onLeftClicked: KittyScrollSettings.refresh()
                }
                GohuText {
                    width: parent.width
                    text: "CONFIG // " + KittyScrollSettings.hostStatus.toUpperCase()
                    color: KittyScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "KITTY CONFIG PATH // " + KittyScrollSettings.configPath
                    color: Colors.white
                    font.pixelSize: 8
                    wrapMode: Text.WrapAnywhere
                }
                GohuText {
                    width: parent.width
                    text: "ZELLIJ AND OTHER FULL-SCREEN TERMINAL PROGRAMS MAY INTERCEPT OR PROCESS SCROLL EVENTS THEMSELVES."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
            Column {
                visible: kittyPane.area === "factor"
                width: parent.width
                spacing: 10
                GohuText {
                    width: parent.width
                    text: "KITTY // SCROLL SENSITIVITY"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "MOUSE WHEEL // LOW PRECISION"
                    color: Colors.white
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    text: "STAGED // " + KittyScrollSettings.stagedWheel.toFixed(2)
                          + "×   SAVED // "
                          + (KittyScrollSettings.installedWheel < 0
                             ? "UNKNOWN"
                             : KittyScrollSettings.installedWheel.toFixed(2) + "×")
                    color: Colors.yellow
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Flow {
                    id: wheelChoices
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [1,2,3,4,5,6,8,10,12,16]
                        ActionButton {
                            required property real modelData
                            width: (wheelChoices.width - wheelChoices.spacing * 2) / 3
                            height: 32
                            label: modelData.toFixed(2) + "×"
                            labelPixelSize: 9
                            selected: Math.abs(KittyScrollSettings.stagedWheel
                                               - modelData) < 0.001
                            available: !KittyScrollSettings.busy
                            onLeftClicked: KittyScrollSettings.stage("wheel", modelData)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "TOUCHPAD // HIGH PRECISION"
                    color: Colors.white
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    text: "STAGED // " + KittyScrollSettings.stagedTouch.toFixed(2)
                          + "×   SAVED // "
                          + (KittyScrollSettings.installedTouch < 0
                             ? "UNKNOWN"
                             : KittyScrollSettings.installedTouch.toFixed(2) + "×")
                    color: Colors.yellow
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Flow {
                    id: touchChoices
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [0.5,0.75,1,1.25,1.5,2,2.5,3,4,6,8]
                        ActionButton {
                            required property real modelData
                            width: (touchChoices.width - touchChoices.spacing * 2) / 3
                            height: 32
                            label: modelData.toFixed(2) + "×"
                            labelPixelSize: 9
                            selected: Math.abs(KittyScrollSettings.stagedTouch
                                               - modelData) < 0.001
                            available: !KittyScrollSettings.busy
                            onLeftClicked: KittyScrollSettings.stage("touch", modelData)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "STAGED VALUES DO NOT CHANGE KITTY UNTIL YOU CONFIRM IN CONTROL."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
            Column {
                visible: kittyPane.area === "apply"
                width: parent.width
                spacing: 11
                GohuText {
                    width: parent.width
                    text: "KITTY // CONFIG CONTROL"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "STATUS // " + KittyScrollSettings.hostStatus.toUpperCase()
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "WHEEL " + KittyScrollSettings.stagedWheel.toFixed(2)
                          + "×  // TOUCH "
                          + KittyScrollSettings.stagedTouch.toFixed(2) + "×"
                    color: Colors.yellow
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "NO CHANGE TO SWAY, KITTY PROCESS, OR ZELLIJ. ONE-TIME ENROLLMENT MAKES A BACKUP AND ADDS A SINGLE INCLUDE TO KITTY.CONF."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "PREPARE KITTY SCROLL"
                    labelPixelSize: 10
                    selected: KittyScrollSettings.confirmAction !== ""
                    available: KittyScrollSettings.canInstall
                               && KittyScrollSettings.hasChanges
                               && KittyScrollSettings.confirmAction === ""
                    onLeftClicked: KittyScrollSettings.prepare()
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    visible: KittyScrollSettings.confirmAction !== ""
                    label: KittyScrollSettings.confirmAction === "enroll"
                           ? "CONFIRM INCLUDE & SAVE"
                           : "CONFIRM KITTY SAVE"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: !KittyScrollSettings.busy
                    onLeftClicked: KittyScrollSettings.confirm()
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    visible: KittyScrollSettings.confirmAction !== ""
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    onLeftClicked: KittyScrollSettings.cancel()
                }
                GohuText {
                    width: parent.width
                    text: KittyScrollSettings.feedback
                    font.pixelSize: 10
                    color: KittyScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    visible: KittyScrollSettings.hostError.length > 0
                    text: "ERROR // " + KittyScrollSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: KittyScrollSettings.hostStatus === "needs_config"
                        ? "CREATE A KITTY.CONF WITH KITTY CTRL+SHIFT+F2 FIRST."
                        : KittyScrollSettings.hostStatus === "unavailable"
                          ? "UNSAFE OR SYMLINKED CONFIG? NO AUTOMATIC EDITS. INSPECT THE CONFIG MANUALLY."
                          : "KITTY MAY AUTO-RELOAD. OTHERWISE USE CTRL+SHIFT+F5 INSIDE KITTY. TEST IN KITTY'S OWN SCROLLBACK."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "SAVED CONFIGURATION IS NOT PROOF OF LIVE KITTY EFFECT. ZELLIJ MAY HANDLE PANE SCROLLING SEPARATELY."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    NeonScrollBar {
        flickable: scroll
        visible: kittyPane.panelVisible && scrollable
    }
}
