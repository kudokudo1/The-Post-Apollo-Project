import QtQuick
import Quickshell
import qs.services.input
import "../../components"

// Three-bay Mouse & Touchpad view for CPU++ SETTINGS.
// Currently only guarded, real Sway scroll_factor controls are activated.
// This component can be mounted without modifying any shared scrollbar code.
Item {
    id: mousePane
    property string area: "devices" // devices | factor | apply
    property bool panelVisible: visible

    onPanelVisibleChanged: {
        if (panelVisible && area === "devices"
                && !KittyScrollSettings.terminalMode)
            SwayScrollSettings.refresh();
    }

    Flickable {
        id: scroll
        visible: !KittyScrollSettings.terminalMode
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
                visible: mousePane.area === "devices"
                width: parent.width
                spacing: 10

                GohuText {
                    width: parent.width
                    text: "SWAY // CONNECTED POINTERS"
                    font.pixelSize: 12
                    color: Colors.cyan
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "KITTY // TERMINAL SCROLL"
                    labelPixelSize: 10
                    available: !SwayScrollSettings.busy
                    onLeftClicked: KittyScrollSettings.chooseMode(true)
                }
                GohuText {
                    width: parent.width
                    text: "Select an exact device. A touchpad and a mouse can have different scroll factors."
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: SwayScrollSettings.querying ? "READING DEVICES" : "REFRESH SWAY INPUTS"
                    labelPixelSize: 10
                    available: !SwayScrollSettings.busy
                    onLeftClicked: SwayScrollSettings.refresh()
                }
                Repeater {
                    model: SwayScrollSettings.devices
                    delegate: Column {
                        id: itemRow
                        required property var modelData
                        width: body.width
                        spacing: 4
                        ActionButton {
                            width: parent.width
                            height: 38
                            label: (itemRow.modelData.kind === "touchpad"
                                    ? "TOUCHPAD // " : "MOUSE // ")
                                   + itemRow.modelData.name
                            labelPixelSize: 10
                            labelMinimumPixelSize: 7
                            selected: SwayScrollSettings.selectedId === itemRow.modelData.identifier
                            available: !SwayScrollSettings.busy
                            onLeftClicked: SwayScrollSettings.selectDevice(
                                itemRow.modelData.identifier)
                        }
                        GohuText {
                            width: parent.width
                            text: "CURRENT // " + Number(itemRow.modelData.factor).toFixed(2) + "×"
                            font.pixelSize: 9
                            color: Colors.white
                        }
                    }
                }
                GohuText {
                    visible: SwayScrollSettings.devices.length === 0
                    width: parent.width
                    text: "NO SUPPORTED POINTERS // " + SwayScrollSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: mousePane.area === "factor"
                width: parent.width
                spacing: 11
                GohuText {
                    width: parent.width
                    text: "SCROLL SENSITIVITY // SWAY"
                    color: Colors.cyan
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: SwayScrollSettings.selectedDevice
                          ? String(SwayScrollSettings.selectedDevice.name)
                          : "SELECT A POINTER DEVICE"
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LIVE // " + (SwayScrollSettings.selectedDevice
                          ? Number(SwayScrollSettings.selectedDevice.factor).toFixed(2)
                          : "?") + "×"
                    font.pixelSize: 15
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "STAGED // " + SwayScrollSettings.stagedFactor.toFixed(2) + "×"
                    font.pixelSize: 15
                    color: Colors.yellow
                }
                GohuText {
                    width: parent.width
                    text: "Choose a scroll factor. Nothing changes until you confirm it in the right panel."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Flow {
                    id: factorFlow
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [0.25,0.5,0.75,1,1.25,1.5,1.75,2,2.5,3,4,5,6]
                        ActionButton {
                            required property real modelData
                            width: (factorFlow.width - factorFlow.spacing * 2) / 3
                            height: 33
                            label: modelData.toFixed(2) + "×"
                            labelPixelSize: 10
                            selected: Math.abs(SwayScrollSettings.stagedFactor
                                               - modelData) < 0.001
                            available: SwayScrollSettings.selectedDevice !== null
                                       && !SwayScrollSettings.busy
                            onLeftClicked: SwayScrollSettings.stageFactor(modelData)
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "NORMAL // 1.00×. START BY TRYING 1.50× OR 2.00×."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: mousePane.area === "apply"
                width: parent.width
                spacing: 12
                GohuText {
                    width: parent.width
                    text: "SWAY // REAL INPUT CONTROL"
                    font.pixelSize: 12
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    text: "VERIFY // " + SwayScrollSettings.hostStatus.toUpperCase()
                    font.pixelSize: 10
                    color: SwayScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: SwayScrollSettings.savedFactor === null
                          ? "SAVED DEVICE PROFILE // NONE"
                          : "SAVED PROFILE // "
                            + Number(SwayScrollSettings.savedFactor).toFixed(2) + "×"
                    font.pixelSize: 10
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    visible: SwayScrollSettings.savedFactor !== null
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "STAGE SAVED PROFILE"
                    labelPixelSize: 10
                    available: !SwayScrollSettings.busy
                    onLeftClicked: SwayScrollSettings.stageSavedFactor()
                }
                ActionButton {
                    visible: SwayScrollSettings.canRestore
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "STAGE PREVIOUS VALUE"
                    labelPixelSize: 10
                    available: !SwayScrollSettings.busy
                    onLeftClicked: SwayScrollSettings.stageRestore()
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "PREPARE LIVE SCROLL"
                    labelPixelSize: 10
                    selected: SwayScrollSettings.confirmationRequired
                    available: SwayScrollSettings.canApply
                    onLeftClicked: SwayScrollSettings.prepareApply()
                }
                ActionButton {
                    visible: SwayScrollSettings.confirmationRequired
                    width: parent.width
                    height: visible ? 35 : 0
                    label: "CONFIRM APPLY TO SWAY"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: !SwayScrollSettings.busy
                    onLeftClicked: SwayScrollSettings.confirmApply()
                }
                ActionButton {
                    visible: SwayScrollSettings.confirmationRequired
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    onLeftClicked: SwayScrollSettings.cancelApply()
                }
                GohuText {
                    width: parent.width
                    text: SwayScrollSettings.feedback
                    font.pixelSize: 10
                    color: SwayScrollSettings.hostError.length
                           ? Colors.orange : Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    visible: SwayScrollSettings.hostError.length > 0
                    text: "ERROR // " + SwayScrollSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LIVE SWAY ONLY. SAVED PREFERENCES ARE NOT AUTOMATICALLY APPLIED AFTER REBOOT YET."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "KITTY / ZELLIJ-SPECIFIC SCROLLING IS A SEPARATE NEXT CONTROL."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
    CpuPlusSettingsKittyScrollPane {
        anchors.fill: parent
        area: mousePane.area
        visible: KittyScrollSettings.terminalMode
    }
    NeonScrollBar {
        flickable: scroll
        visible: mousePane.panelVisible
                 && !KittyScrollSettings.terminalMode && scrollable
    }
}
