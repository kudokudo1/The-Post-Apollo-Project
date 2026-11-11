import QtQuick
import Quickshell
import qs.services.input
import "../../components"

// Reusable CPU++ three-bay keyboard settings view. The only preference writer
// is KeyboardLockSettings; host changes require an explicit second click.
Item {
    id: keyboardPane
    property string area: "controls" // controls | status | apply
    property bool panelVisible: visible

    onPanelVisibleChanged: {
        if (panelVisible && area === "status")
            KeyboardLockSettings.inspectHost();
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.implicitHeight + 20)

        Column {
            id: body
            x: 5
            y: 8
            width: Math.max(0, scroll.width - 16)
            spacing: 12

            Column {
                visible: keyboardPane.area === "controls"
                width: parent.width
                spacing: 11
                GohuText {
                    text: "NUM LOCK // STARTUP"
                    color: Colors.cyan
                    font.pixelSize: 13
                }
                Row {
                    id: numChoices
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [
                            {label:"SYSTEM",mode:"system"},
                            {label:"ON",mode:"on"},
                            {label:"OFF",mode:"off"},
                            {label:"REMEMBER",mode:"remember"}
                        ]
                        ActionButton {
                            required property var modelData
                            width: (numChoices.width - 3 * numChoices.spacing) / 4
                            height: 34
                            label: modelData.label
                            labelPixelSize: 9
                            selected: KeyboardLockSettings.numMode === modelData.mode
                            available: KeyboardLockSettings.canEdit
                                       && (modelData.mode !== "remember"
                                           || KeyboardLedObservation.canEdit)
                            onLeftClicked: {
                                if (modelData.mode === "remember"
                                        && !KeyboardLedObservation.monitoringEnabled)
                                    KeyboardLedObservation.setMonitoringEnabled(true);
                                KeyboardLockSettings.choose("num", modelData.mode);
                            }
                        }
                    }
                }
                GohuText {
                    text: "CAPS LOCK // STARTUP"
                    color: Colors.cyan
                    font.pixelSize: 13
                }
                Row {
                    id: capsChoices
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [
                            {label:"SYSTEM",mode:"system"},
                            {label:"ON",mode:"on"},
                            {label:"OFF",mode:"off"},
                            {label:"REMEMBER",mode:"remember"}
                        ]
                        ActionButton {
                            required property var modelData
                            width: (capsChoices.width - 3 * capsChoices.spacing) / 4
                            height: 34
                            label: modelData.label
                            labelPixelSize: 9
                            selected: KeyboardLockSettings.capsMode === modelData.mode
                            available: KeyboardLockSettings.canEdit
                                       && (modelData.mode !== "remember"
                                           || KeyboardLedObservation.canEdit)
                            onLeftClicked: {
                                if (modelData.mode === "remember"
                                        && !KeyboardLedObservation.monitoringEnabled)
                                    KeyboardLedObservation.setMonitoringEnabled(true);
                                KeyboardLockSettings.choose("caps", modelData.mode);
                            }
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "SYSTEM = NO POST-APOLLO OVERRIDE"
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "ON / OFF SET STARTUP DEFAULTS. KEYS CAN STILL TOGGLE."
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "REMEMBER = SAVE OBSERVED CHANGES FOR NEXT SWAY START."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            Column {
                visible: keyboardPane.area === "status"
                width: parent.width
                spacing: 12
                GohuText {
                    width: parent.width
                    text: "PREFERENCES // " + KeyboardLockSettings.storageState.toUpperCase()
                    color: KeyboardLockSettings.storageError ? Colors.orange : Colors.cyan
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "NUM // " + KeyboardLockSettings.numMode.toUpperCase()
                    color: Colors.white
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "CAPS // " + KeyboardLockSettings.capsMode.toUpperCase()
                    color: Colors.white
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "SWAY // " + KeyboardLockSettings.hostStatus.toUpperCase()
                    color: KeyboardLockSettings.profileInstalled ? Colors.omnitrix : Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: KeyboardLockSettings.profileInstalled
                          ? "STARTUP POLICY CONFIRMED IN MANAGED FRAGMENT"
                          : "PREFERENCES NOT CONFIRMED IN SWAY FILE"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "REMEMBER NUM // "
                          + (KeyboardLockSettings.hostRememberNum
                             && KeyboardLockSettings.numMode === "remember"
                             ? (KeyboardLockSettings.rememberSuspended
                                ? "SUSPENDED"
                                : KeyboardLedObservation.monitoringEnabled
                                  ? "ARMED" : "PAUSED // MONITOR OFF")
                             : "NOT ARMED")
                    color: KeyboardLockSettings.hostRememberNum
                           ? Colors.cyan : Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "REMEMBER CAPS // "
                          + (KeyboardLockSettings.hostRememberCaps
                             && KeyboardLockSettings.capsMode === "remember"
                             ? (KeyboardLockSettings.rememberSuspended
                                ? "SUSPENDED"
                                : KeyboardLedObservation.monitoringEnabled
                                  ? "ARMED" : "PAUSED // MONITOR OFF")
                             : "NOT ARMED")
                    color: KeyboardLockSettings.hostRememberCaps
                           ? Colors.cyan : Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    visible: KeyboardLockSettings.rememberSyncing
                    text: "REMEMBER // SAVING STABLE CHANGE"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LED PROXY // NOT VERIFIED XKB STATE"
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LED NUM // " + KeyboardLedObservation.currentNum.toUpperCase()
                          + " // " + KeyboardLedObservation.numStatus.toUpperCase()
                    color: KeyboardLedObservation.currentNum === "unknown"
                           ? Colors.orange : Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LED CAPS // " + KeyboardLedObservation.currentCaps.toUpperCase()
                          + " // " + KeyboardLedObservation.capsStatus.toUpperCase()
                    color: KeyboardLedObservation.currentCaps === "unknown"
                           ? Colors.orange : Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "SAVED LED NUM // "
                          + KeyboardLedObservation.savedNum.toUpperCase()
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "SAVED LED CAPS // "
                          + KeyboardLedObservation.savedCaps.toUpperCase()
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "MONITOR STORE // "
                          + KeyboardLedObservation.storageState.toUpperCase()
                          + (KeyboardLedObservation.storageError.length
                             ? " / " + KeyboardLedObservation.storageError : "")
                    color: KeyboardLedObservation.storageError.length
                           ? Colors.orange : Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: KeyboardLedObservation.monitoringEnabled
                           ? "STOP LED MONITOR" : "START LED MONITOR"
                    labelPixelSize: 10
                    selected: KeyboardLedObservation.monitoringEnabled
                    available: KeyboardLedObservation.canEdit
                    onLeftClicked: KeyboardLedObservation.setMonitoringEnabled(
                        !KeyboardLedObservation.monitoringEnabled)
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: "SAMPLE LED ONCE"
                    labelPixelSize: 10
                    available: !KeyboardLedObservation.sampling
                    onLeftClicked: KeyboardLedObservation.sampleOnce()
                }
                GohuText {
                    width: parent.width
                    text: KeyboardLedObservation.probeError.length
                          ? "LED PROBE // " + KeyboardLedObservation.probeError
                          : "SAVES ONLY STABLE CHANGES // NO KEYSTROKE RECORDING"
                    color: KeyboardLedObservation.probeError.length
                           ? Colors.orange : Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 32
                    label: "REFRESH CONFIG STATUS"
                    labelPixelSize: 10
                    available: !KeyboardLockSettings.inspecting && !KeyboardLockSettings.applying
                    onLeftClicked: KeyboardLockSettings.inspectHost()
                }
            }

            Column {
                visible: keyboardPane.area === "apply"
                width: parent.width
                spacing: 12
                GohuText {
                    width: parent.width
                    text: "SWAY // STARTUP CONFIG"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    text: "Preferences save to Post-Apollo data first. Applying edits only the default user Sway config and one managed include."
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "NO SWAY RELOAD OR KEY INJECTION. CHANGES TAKE EFFECT AT NEXT FULL SWAY START."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "LED MONITOR IS OPT-IN. COPYING NEEDS TWO CONSISTENT "
                          + "FRESH READINGS FROM BOTH LOCK LEDS."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "COPY FRESH LED VALUES"
                    labelPixelSize: 10
                    available: KeyboardLedObservation.canCopyToStartup
                    onLeftClicked: KeyboardLedObservation.copyObservedToStartup()
                }
                GohuText {
                    width: parent.width
                    text: "COPY UPDATES SAVED PREFERENCES ONLY. INSTALL STILL "
                          + "REQUIRES PREPARE AND CONFIRM."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 34
                    label: "PREPARE STARTUP RULES"
                    labelPixelSize: 10
                    available: KeyboardLockSettings.canApply
                    selected: KeyboardLockSettings.confirmRequired
                    onLeftClicked: KeyboardLockSettings.prepareApply(
                        KeyboardLedObservation.currentNum,
                        KeyboardLedObservation.currentCaps,
                        KeyboardLedObservation.fresh
                    )
                }
                ActionButton {
                    visible: KeyboardLockSettings.confirmRequired
                    width: parent.width
                    height: visible ? 34 : 0
                    label: "CONFIRM INSTALL"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: KeyboardLockSettings.canApply
                    onLeftClicked: KeyboardLockSettings.requestApply()
                }
                ActionButton {
                    visible: KeyboardLockSettings.confirmRequired
                    width: parent.width
                    height: visible ? 32 : 0
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    onLeftClicked: KeyboardLockSettings.cancelApply()
                }
                GohuText {
                    width: parent.width
                    text: "REMEMBER IS ARMED ONLY AFTER CONFIRM INSTALL. "
                          + "FIRST LED SAMPLE SETS A BASELINE; LATER STABLE "
                          + "TOGGLES UPDATE ONLY THE MANAGED STARTUP FILE."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: KeyboardLockSettings.feedback
                    color: KeyboardLockSettings.hostError ? Colors.orange : Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    visible: KeyboardLockSettings.hostError.length > 0
                    width: parent.width
                    text: "HOST // " + KeyboardLockSettings.hostError
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    NeonScrollBar {
        flickable: scroll
        visible: keyboardPane.panelVisible && scrollable
    }
}
