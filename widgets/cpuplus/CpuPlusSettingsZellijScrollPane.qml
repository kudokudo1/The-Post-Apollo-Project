import QtQuick
import Quickshell
import qs.services.input
import "../../components"

// Reuses Mouse & Touchpad's three existing bays. Zellij exposes real
// mouse/mode/buffer options, NOT a numeric wheel-scroll speed multiplier.
Item {
    id: zellijPane
    property string area: "devices" // devices | factor | apply
    property bool panelVisible: visible

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.implicitHeight + 18)
        Column {
            id: body
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 17)
            spacing: 11

            Column {
                visible: zellijPane.area === "devices"
                width: parent.width
                spacing: 9
                GohuText {
                    width: parent.width
                    text: "ZELLIJ // PANE SCROLL"
                    font.pixelSize: 12
                    color: Colors.cyan
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "BACK TO KITTY SCROLL"
                    labelPixelSize: 10
                    available: !ZellijScrollSettings.busy
                    onLeftClicked: ZellijScrollSettings.close()
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: ZellijScrollSettings.busy
                           ? "INSPECTING CONFIG" : "REFRESH ZELLIJ CONFIG"
                    labelPixelSize: 9
                    available: !ZellijScrollSettings.busy
                    onLeftClicked: ZellijScrollSettings.refresh()
                }
                GohuText {
                    width: parent.width
                    text: "CONFIG // " + ZellijScrollSettings.hostStatus.toUpperCase()
                    color: ZellijScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "FILE // " + ZellijScrollSettings.configPath
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WrapAnywhere
                }
                GohuText {
                    width: parent.width
                    text: "MOUSE MODE // ZELLIJ HANDLES MOUSE EVENTS WHEN ENABLED."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "HOLD SHIFT WHILE SCROLLING TO LET KITTY HANDLE MOUSE INPUT WHEN ZELLIJ CAPTURES IT."
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "ZELLIJ SCROLL MODE // UP/DOWN = LINE; PAGEUP/PAGEDOWN = PAGE; D/U = HALF PAGE IN DEFAULT SCROLL KEYMAP."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "CUSTOM KEYBINDS MAY DIFFER. CONFIG OPTIONS DO NOT OVERRIDE RUNNING PROGRAMS' OWN MOUSE HANDLERS."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: zellijPane.area === "factor"
                width: parent.width
                spacing: 10
                GohuText {
                    width: parent.width
                    text: "ZELLIJ // INPUT BEHAVIOR"
                    color: Colors.cyan
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "MOUSE INPUT CAPTURE"
                    color: Colors.white
                    font.pixelSize: 10
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [{label:"ON",value:"true"}, {label:"OFF",value:"false"}]
                        ActionButton {
                            required property var modelData
                            width: (parent.width - 6) / 2
                            height: 32
                            label: modelData.label
                            labelPixelSize: 10
                            selected: ZellijScrollSettings.stagedMouse === modelData.value
                            available: !ZellijScrollSettings.busy
                            onLeftClicked: ZellijScrollSettings.stage("mouse",modelData.value)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "CTRL + WHEEL RESIZES FOCUSED PANE"
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [{label:"ON",value:"true"}, {label:"OFF",value:"false"}]
                        ActionButton {
                            required property var modelData
                            width: (parent.width - 6) / 2
                            height: 32
                            label: modelData.label
                            labelPixelSize: 10
                            selected: ZellijScrollSettings.stagedResize === modelData.value
                            available: !ZellijScrollSettings.busy
                            onLeftClicked: ZellijScrollSettings.stage("resize",modelData.value)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "SCROLLING AUTO-ENTERS / EXITS SCROLL MODE"
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [{label:"ON",value:"true"}, {label:"OFF",value:"false"}]
                        ActionButton {
                            required property var modelData
                            width: (parent.width - 6) / 2
                            height: 32
                            label: modelData.label
                            labelPixelSize: 10
                            selected: ZellijScrollSettings.stagedSync === modelData.value
                            available: !ZellijScrollSettings.busy
                            onLeftClicked: ZellijScrollSettings.stage("sync",modelData.value)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "SCROLLBACK ROWS PER PANE // "
                          + ZellijScrollSettings.stagedBuffer
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Flow {
                    id: bufferChoices
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [1000,5000,10000,20000,50000,100000]
                        ActionButton {
                            required property int modelData
                            width: (bufferChoices.width - 6) / 2
                            height: 32
                            label: modelData.toLocaleString()
                            labelPixelSize: 9
                            selected: ZellijScrollSettings.stagedBuffer === modelData
                            available: !ZellijScrollSettings.busy
                            onLeftClicked: ZellijScrollSettings.stage("buffer",modelData)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "BUFFER SIZE CHANGES HISTORY CAPACITY, NOT SCROLL SPEED. LARGE BUFFERS USE MORE MEMORY."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: zellijPane.area === "apply"
                width: parent.width
                spacing: 11
                GohuText {
                    width: parent.width
                    text: "ZELLIJ // CONFIG CONTROL"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "STATUS // " + ZellijScrollSettings.hostStatus.toUpperCase()
                    color: ZellijScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "MOUSE " + ZellijScrollSettings.stagedMouse.toUpperCase()
                          + " // CTRL RESIZE " + ZellijScrollSettings.stagedResize.toUpperCase()
                          + " // MODE SYNC " + ZellijScrollSettings.stagedSync.toUpperCase()
                          + " // ROWS " + ZellijScrollSettings.stagedBuffer
                    color: Colors.yellow
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "PREPARE ZELLIJ OPTIONS"
                    labelPixelSize: 10
                    selected: ZellijScrollSettings.confirmRequired
                    available: ZellijScrollSettings.canPrepare
                    onLeftClicked: ZellijScrollSettings.prepare()
                }
                ActionButton {
                    visible: ZellijScrollSettings.confirmRequired
                    width: parent.width
                    height: visible ? 35 : 0
                    label: "CONFIRM SAVE KDL"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: !ZellijScrollSettings.busy
                    onLeftClicked: ZellijScrollSettings.confirm()
                }
                ActionButton {
                    visible: ZellijScrollSettings.confirmRequired
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    onLeftClicked: ZellijScrollSettings.cancel()
                }
                GohuText {
                    width: parent.width
                    text: ZellijScrollSettings.feedback
                    color: ZellijScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    visible: ZellijScrollSettings.hostError.length > 0
                    text: "ERROR // " + ZellijScrollSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "FIRST SAVE BACKS UP CONFIG.KDL. EXTERNAL OPTIONS OR SYMLINKS ARE REFUSED, NEVER OVERWRITTEN."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "CONFIG SAVED IS NOT RUNTIME VERIFIED. MOUSE MODE AND BUFFER SIZE MAY REQUIRE A NEW ZELLIJ SESSION."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "NO NUMERIC ZELLIJ WHEEL SPEED EXISTS. USE KITTY SCROLL MULTIPLIERS FOR ITS NATIVE SCROLLBACK."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    NeonScrollBar {
        flickable: scroll
        visible: zellijPane.panelVisible && scrollable
    }
}
