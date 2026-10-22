import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "../services/hub/ApolloHubTimePolicy.js" as LocalTimePolicy

// TimeW M1: standalone temporal window foundation.
// No timers, activity recording, screenshots or restoration are active here.
// The clock dock and shell wiring are intentionally separate integration steps.
PanelWindow {
    id: timew

    property bool menuOpen: false
    property bool keyboardActive: true
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false

    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)

    // Reuse FinanceW's tested chassis geometry until the operator has a live
    // TimeW preview to measure. This remains a design choice, not a new rule.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12
    // TimeW identity is white. Universal magenta header, cyan dividers and
    // destructive red Close keep their independent semantic roles.
    readonly property color semanticColor: Colors.white

    // Presentation choice is local to TimeW; it does not change the Clock
    // dock or Hub preference. The Hub helper is pure and owns no clock tick.
    property bool use24Hour: true
    readonly property var localTimeSnapshot:
        LocalTimePolicy.snapshot(localClock.date.getTime(), use24Hour)

    readonly property var modes: [
        { id: "clock", name: "CLOCK" },
        { id: "calc", name: "CALC" },
        { id: "tools", name: "TOOLS" },
        { id: "machine", name: "MACHINE" }
    ]
    property int selectedModeIndex: 0
    readonly property string selectedMode: modes[selectedModeIndex].id
    readonly property string selectedName: modes[selectedModeIndex].name

    function toggle() {
        menuOpen = !menuOpen;
    }

    function chooseMode(index) {
        if (index >= 0 && index < modes.length)
            selectedModeIndex = index;
    }

    function cycleMainMode(direction) {
        const length = modes.length;
        const next = (selectedModeIndex + (direction < 0 ? -1 : 1)
                      + length) % length;
        chooseMode(next);
    }

    function restoreKeyboardFocus() {
        if (standardKeysAvailable)
            keyboardAnchor.forceActiveFocus();
    }

    onMenuOpenChanged: {
        if (menuOpen)
            Qt.callLater(restoreKeyboardFocus);
    }
    onStandardKeysAvailableChanged: {
        if (standardKeysAvailable)
            Qt.callLater(restoreKeyboardFocus);
    }

    // The window stays mapped to avoid the existing layer-shell remap crash.
    // A zero-sized closed mask prevents invisible pointer interception.
    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2
    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        standardKeysAvailable ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: standardKeysAvailable

    // Match the right dock's 8px top inset. The earlier formula adding the
    // dock's 50px height placed the window too low in the live screenshot.
    // Keep the existing frame glow gutter and compensate only by moving the
    // owning PanelWindow up; visual acceptance remains a separate check.
    anchors {
        top: true
        bottom: false
        left: false
        right: true
    }
    margins {
        top: 8
        right: 13
    }
    mask: Region {
        x: timew.glowGutter
        y: timew.glowGutter
        width: timew.menuOpen ? timew.frameWidth : 0
        height: timew.menuOpen ? timew.frameHeight : 0
    }

    SystemClock {
        id: localClock
        precision: SystemClock.Seconds
    }

    Item {
        id: keyboardAnchor
        anchors.fill: parent
        z: -1000
        enabled: timew.standardKeysAvailable
        focus: timew.standardKeysAvailable

        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if (!timew.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape)
                event.accepted = true;
        }
        Keys.onPressed: function(event) {
            if (!timew.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Escape) {
                timew.menuOpen = false;
            } else if (event.key === Qt.Key_Tab
                       || event.key === Qt.Key_Backtab) {
                const reverse = event.key === Qt.Key_Backtab
                    || (event.modifiers & Qt.ShiftModifier) !== 0;
                timew.cycleMainMode(reverse ? -1 : 1);
            } else {
                return;
            }
            event.accepted = true;
        }
    }

    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: timew.standardKeysAvailable
        onActivated: timew.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: timew.standardKeysAvailable
        onActivated: timew.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: timew.standardKeysAvailable
        onActivated: timew.menuOpen = false
    }

    WindowPanelFrame {
        anchors.fill: parent
        anchors.margins: timew.glowGutter
        visible: timew.menuOpen
        glowVisible: timew.menuOpen
        glowColor: timew.semanticColor
        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: timew.semanticColor
        borderWidth: 1
        radius: 0

        Column {
            id: chassis
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            Row {
                id: header
                width: parent.width
                height: 42
                spacing: 8

                GohuText {
                    width: parent.width - stateIndicator.width
                           - closeButton.width - header.spacing * 2
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 18
                    font.weight: 700
                    color: Colors.magenta
                    text: "TIME // W"
                }

                Rectangle {
                    id: stateIndicator
                    width: 85
                    height: 32
                    color: "transparent"
                    border.width: 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        font.pixelSize: 11
                        color: timew.semanticColor
                        text: timew.selectedMode === "clock"
                              ? "LOCAL" : "PLANNED"
                    }
                }

                ActionButton {
                    id: closeButton
                    width: 35
                    height: 32
                    label: "×"
                    labelPixelSize: 22
                    contentPadding: 4
                    trackLabelGlowLocally: true
                    accentColor: Colors.red
                    destructive: true
                    idleForegroundColor: Colors.red
                    hoverForegroundColor: Colors.red
                    selectedForegroundColor: Colors.red
                    keyboardSelectedForegroundColor: Colors.red
                    hoverBorderColor: Colors.red
                    selectedBorderColor: Colors.red
                    keyboardSelectedBorderColor: Colors.red
                    idleContentGlowColor: Colors.red
                    hoverContentGlowColor: Colors.red
                    selectedContentGlowColor: Colors.red
                    keyboardSelectedContentGlowColor: Colors.red
                    softGlowEnabled: true
                    idleSoftGlowColor: Colors.red
                    hoverSoftGlowColor: Colors.red
                    pressedSoftGlowColor: Colors.red
                    onLeftClicked: timew.menuOpen = false
                }
            }

            Rectangle {
                id: headerDivider
                width: parent.width
                height: 2
                color: Colors.cyan
            }

            Row {
                id: modeStrip
                width: parent.width
                height: 55
                spacing: 6

                Repeater {
                    model: timew.modes.length

                    ModeButton {
                        width: (modeStrip.width
                                - (timew.modes.length - 1) * modeStrip.spacing)
                               / timew.modes.length
                        height: modeStrip.height
                        bordered: false
                        textOnly: true
                        labelFontSize: 11
                        trackDefaultGlowsLocally: true
                        idlePrimaryColor: timew.semanticColor
                        selected: timew.selectedModeIndex === index
                        keyboardActive: timew.standardKeysAvailable
                        keyboardSelected: timew.selectedModeIndex === index
                        labelText: timew.modes[index].name
                        onTriggered: timew.chooseMode(index)
                    }
                }
            }

            Rectangle {
                id: page
                width: parent.width
                height: Math.max(0, chassis.height - header.height
                                 - headerDivider.height - modeStrip.height
                                 - chassis.spacing * 3)
                color: "transparent"
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    GohuText {
                        text: timew.selectedName + " // TIMEW"
                        color: timew.semanticColor
                        font.pixelSize: 18
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        color: Colors.cyan
                        opacity: 0.5
                    }

                    Column {
                        id: localClockPane
                        visible: timew.selectedMode === "clock"
                        width: parent.width
                        spacing: 10

                        Row {
                            width: parent.width
                            height: 34
                            spacing: 8

                            GohuText {
                                width: Math.max(0, parent.width
                                                - hourFormatButton.width
                                                - parent.spacing)
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: timew.localTimeSnapshot.displayTime
                                color: timew.semanticColor
                                font.pixelSize: timew.use24Hour ? 22 : 19
                                elide: Text.ElideRight
                            }

                            ActionButton {
                                id: hourFormatButton
                                width: 60
                                height: 30
                                label: timew.use24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                trackLabelGlowLocally: true
                                accentColor: timew.semanticColor
                                onLeftClicked: timew.use24Hour = !timew.use24Hour
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: timew.localTimeSnapshot.dateLabel
                            color: Colors.white
                            font.pixelSize: 18
                        }

                        GohuText {
                            width: parent.width
                            text: timew.localTimeSnapshot.utcOffsetLabel
                            color: Colors.orange
                            font.pixelSize: 11
                        }

                        GohuText {
                            text: timew.localTimeSnapshot.state === "ready"
                                  ? "LOCAL CLOCK // SYSTEM TIME"
                                  : "LOCAL CLOCK // UNAVAILABLE"
                            color: Colors.orange
                            font.pixelSize: 11
                        }
                    }

                    GohuText {
                        visible: timew.selectedMode !== "clock"
                        text: timew.selectedMode === "calc"
                              ? "TIME CALCULATOR // NOT CONNECTED"
                              : timew.selectedMode === "tools"
                              ? "STOPWATCH + TIMERS // NOT CONNECTED"
                              : "DESKTOP CHECKPOINTS // NOT CONNECTED"
                        color: Colors.orange
                        font.pixelSize: 11
                    }

                    GohuText {
                        visible: timew.selectedMode === "machine"
                        text: "NO SCREENSHOTS OR RESTORATION ACTIVE"
                        color: Colors.white
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: "FOUNDATION PREVIEW // UI ONLY"
                        color: Colors.white
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
