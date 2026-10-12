import Quickshell
import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../components"
import "appcontrol"
import "cpuplus"
import "thermal"

PanelWindow {
    id: cpuPlusWindow

    property var appControlWindow
    required property var systemTelemetry
    required property var fanControl

    property bool menuOpen: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false
    property int selectedModeIndex: 0
    property int thermalSelectedIndex: 0
    property int systemSelectedIndex: 0

    // TEMPORARY CPU++ ONLY GLOW PROBE.
    // POST_APOLLO_CPU_GLOW_TEST=C|D selects the cold-start sampler BEFORE
    // ModeButton instances are built. An absent/unrecognized value defaults
    // to BASE (0). The in-menu selector remains changeable at runtime.
    // 0 BASE, 1 A: both off, 2 B: reattach after close,
    // 3 C: icon sampler only, 4 D: caption sampler only,
    // 5 E: both sampled glows ON but whole-button scale locked at 1.0.
    readonly property string glowStartupChoice:
        String(Quickshell.env("POST_APOLLO_CPU_GLOW_TEST") || "")
        .trim().toUpperCase()
    property int modeGlowExperiment:
        glowStartupChoice === "C" ? 3
        : glowStartupChoice === "D" ? 4
        : glowStartupChoice === "E" ? 5
        : 0

    // Target-list submodes. THERMAL mirrors AppControl's TEMP/FAN split.
    // SYSTEM extends the same interaction pattern to hardware categories.
    property int thermalSubMode: 0 // 0 = temperature, 1 = fans
    property string systemSubMode: "ALL"

    readonly property var thermalSubModes: [
        { name: "TEMP", key: 0, symbol: "🌡" },
        { name: "FAN", key: 1, symbol: "✇" }
    ]

    readonly property var systemSubModes: [
        { name: "ALL", key: "ALL", symbol: "🖳" },
        { name: "CPU", key: "CPU", symbol: "" },
        { name: "MEM", key: "MEMORY", symbol: "" },
        { name: "GPU", key: "GPU", symbol: "󰢮" },
        { name: "DISK", key: "STORAGE", symbol: "" },
        { name: "NET", key: "NETWORK", symbol: "🛰" },
        { name: "", key: "__SPACER_LEFT__", symbol: "", spacer: true },
        { name: "SWAP", key: "SWAP", symbol: "⇄" },
        { name: "", key: "__SPACER_RIGHT__", symbol: "", spacer: true }
    ]

    // Rail-face animation state, matching AppControl's FAVORITES behavior.
    property bool favoritesFaceClickPulse: false
    property bool favoritesFaceBlinking: false
    property bool favoritesFaceDoubleBlinkPending: false

    readonly property var thermalRows:
        systemTelemetry && Array.isArray(systemTelemetry.thermalRows)
        ? systemTelemetry.thermalRows
        : []

    readonly property var fanRows:
        systemTelemetry && Array.isArray(systemTelemetry.fanRows)
        ? systemTelemetry.fanRows
        : []

    readonly property var systemRows:
        systemTelemetry && Array.isArray(systemTelemetry.systemRows)
        ? systemTelemetry.systemRows
        : []

    readonly property var modes: [
        {
            name: "FAVORITES",
            symbol: "(˵✧ᴗ✧˵)",
            kind: "text"
        },
        {
            name: "PROCESS",
            symbol: "(-_•)︻デ═一",
            kind: "text"
        },
        {
            name: "THERMAL",
            symbol: "",
            kind: "thermal"
        },
        {
            name: "SYSTEM",
            symbol: "🖳",
            kind: "text"
        }
    ]

    function open() {
        menuOpen = true;
        scheduleFavoritesFaceBlink();

        if (selectedModeIndex === 2 || selectedModeIndex === 3)
            refreshSharedMonitors();
    }

    function close() {
        menuOpen = false;
        favoritesFaceBlinkTimer.stop();
        favoritesFaceBlinkEndTimer.stop();
        favoritesFaceSecondBlinkGapTimer.stop();
        favoritesFaceSecondBlinkEndTimer.stop();
        favoritesFaceClickPulseTimer.stop();
        favoritesFaceBlinking = false;
        favoritesFaceClickPulse = false;
    }

    function toggle() {
        menuOpen = !menuOpen;

        if (menuOpen) {
            scheduleFavoritesFaceBlink();

            if (selectedModeIndex === 2 || selectedModeIndex === 3)
                refreshSharedMonitors();
        } else {
            favoritesFaceBlinkTimer.stop();
            favoritesFaceBlinkEndTimer.stop();
            favoritesFaceSecondBlinkGapTimer.stop();
            favoritesFaceSecondBlinkEndTimer.stop();
            favoritesFaceClickPulseTimer.stop();
            favoritesFaceBlinking = false;
            favoritesFaceClickPulse = false;
        }
    }

    function selectMode(index) {
        selectedModeIndex = Math.max(
            0,
            Math.min(modes.length - 1, Number(index || 0))
        );

        if (selectedModeIndex === 2 || selectedModeIndex === 3) {
            monitorSelectorScroll.contentY = 0;
            sharedInstrumentScroll.contentY = 0;
            refreshSharedMonitors();
        }
    }

    function refreshSharedMonitors() {
        if (systemTelemetry)
            systemTelemetry.refresh();
    }

    function selectedMonitorRows() {
        if (selectedModeIndex === 2) {
            const sourceRows =
                thermalSubMode === 1 ? fanRows : thermalRows;

            return sourceRows.filter(function(entry) {
                const isFan = entry && entry.sensorKind === "fan";
                return thermalSubMode === 1 ? isFan : !isFan;
            });
        }

        if (selectedModeIndex === 3) {
            if (systemSubMode === "ALL")
                return systemRows;

            return systemRows.filter(function(entry) {
                return String(entry && entry.category || "").toUpperCase()
                       === systemSubMode;
            });
        }

        return [];
    }

    function selectThermalSubMode(mode) {
        thermalSubMode = Number(mode) === 1 ? 1 : 0;
        thermalSelectedIndex = 0;
        monitorSelectorScroll.contentY = 0;
        sharedInstrumentScroll.contentY = 0;
        refreshSharedMonitors();
    }

    function selectSystemSubMode(category) {
        const next = String(category || "ALL").toUpperCase();
        if (next.indexOf("__SPACER_") === 0)
            return;

        systemSubMode = next;
        systemSelectedIndex = 0;
        monitorSelectorScroll.contentY = 0;
        sharedInstrumentScroll.contentY = 0;
        refreshSharedMonitors();
    }

    function selectedMonitorIndex() {
        return selectedModeIndex === 2
               ? thermalSelectedIndex
               : systemSelectedIndex;
    }

    function selectMonitorRow(index) {
        const rows = selectedMonitorRows();
        if (!rows || rows.length <= 0)
            return;

        const next = Math.max(
            0,
            Math.min(rows.length - 1, Number(index || 0))
        );

        if (selectedModeIndex === 2)
            thermalSelectedIndex = next;
        else if (selectedModeIndex === 3)
            systemSelectedIndex = next;
    }

    function selectedMonitorEntry() {
        const rows = selectedMonitorRows();

        if (!rows || rows.length <= 0)
            return null;

        const index = Math.max(
            0,
            Math.min(rows.length - 1, selectedMonitorIndex())
        );

        return rows[index] || null;
    }

    function monitorEntryTitle(entry) {
        return String(
            entry && (entry.label || entry.name) || "UNKNOWN"
        ).toUpperCase();
    }

    function monitorEntryMetric(entry) {
        if (!entry)
            return "";

        if (entry._thermalRecord) {
            if (entry.sensorKind === "fan") {
                if (entry.rpmAvailable === false)
                    return "RPM N/A";

                return Number(entry.rpm || 0).toFixed(0) + " RPM";
            }

            return Number(entry.tempC || 0).toFixed(1) + "°C";
        }

        return String(entry.metric || entry.secondary || "");
    }

    function monitorEntryIcon(entry) {
        if (!entry)
            return "";

        if (appControlWindow && appControlWindow.monitorResultIcon)
            return appControlWindow.monitorResultIcon(entry);

        if (entry._thermalRecord)
            return entry.sensorKind === "fan" ? "【✇】" : "₊˚⊹🌡 ๋࣭⭑";

        if (entry._systemRecord) {
            const category = String(entry.category || "").toUpperCase();
            if (category === "CPU") return "";
            if (category === "MEMORY") return "";
            if (category === "GPU") return "󰢮";
            if (category === "STORAGE") return "";
            if (category === "NETWORK") return "🛰";
            if (category === "SWAP") return "⇄";
            return "🖳";
        }

        return "";
    }

    function monitorEntryAccent(entry) {
        if (!entry)
            return Colors.cyan;

        if (entry._thermalRecord)
            return thermalController.thermalAccent(entry);

        if (entry._systemRecord && appControlWindow
                && appControlWindow.systemIconAccent)
            return appControlWindow.systemIconAccent(entry);

        return Colors.cyan;
    }

    function monitorIdentityMetric(entry) {
        if (!entry)
            return "";

        if (entry._thermalRecord) {
            if (entry.sensorKind === "fan") {
                const rpm =
                    entry.rpmAvailable === false
                    ? "RPM N/A"
                    : Number(entry.rpm || 0).toFixed(0) + " RPM";

                return rpm + " • " + String(entry.chip || "FAN");
            }

            const c = Number(entry.tempC || 0);
            const f = (c * 9 / 5) + 32;

            return f.toFixed(1)
                   + "°F / "
                   + c.toFixed(1)
                   + "°C • "
                   + String(entry.chip || "SENSOR");
        }

        if (entry._systemRecord) {
            return String(entry.category || "SYSTEM")
                   + " • "
                   + String(entry.metric || entry.secondary || "");
        }

        return "";
    }

    function monitorIdentityRole(entry) {
        return String(entry && entry.role || "");
    }

    function monitorIdentityDetail(entry) {
        if (!entry)
            return "";

        if (entry._thermalRecord)
            return "SOURCE • " + String(entry.source || "UNKNOWN");

        if (entry._systemRecord)
            return String(entry.detail || entry.secondary || "");

        return "";
    }

    function monitorIdentityPurpose(entry) {
        if (!entry || !entry._thermalRecord)
            return "";

        return String(thermalController.thermalSimplePurpose(entry) || "");
    }

    function scheduleFavoritesFaceBlink() {
        if (!menuOpen)
            return;

        favoritesFaceBlinkTimer.interval =
            6500 + Math.floor(Math.random() * 6000);
        favoritesFaceBlinkTimer.restart();
    }

    Timer {
        id: favoritesFaceBlinkTimer
        repeat: false

        onTriggered: {
            cpuPlusWindow.favoritesFaceDoubleBlinkPending =
                Math.random() < 0.38;
            cpuPlusWindow.favoritesFaceBlinking = true;
            favoritesFaceBlinkEndTimer.restart();
        }
    }

    Timer {
        id: favoritesFaceBlinkEndTimer
        interval: 170
        repeat: false

        onTriggered: {
            cpuPlusWindow.favoritesFaceBlinking = false;

            if (cpuPlusWindow.favoritesFaceDoubleBlinkPending) {
                cpuPlusWindow.favoritesFaceDoubleBlinkPending = false;
                favoritesFaceSecondBlinkGapTimer.restart();
            } else {
                cpuPlusWindow.scheduleFavoritesFaceBlink();
            }
        }
    }

    Timer {
        id: favoritesFaceSecondBlinkGapTimer
        interval: 125
        repeat: false

        onTriggered: {
            cpuPlusWindow.favoritesFaceBlinking = true;
            favoritesFaceSecondBlinkEndTimer.restart();
        }
    }

    Timer {
        id: favoritesFaceSecondBlinkEndTimer
        interval: 170
        repeat: false

        onTriggered: {
            cpuPlusWindow.favoritesFaceBlinking = false;
            cpuPlusWindow.scheduleFavoritesFaceBlink();
        }
    }

    Timer {
        id: favoritesFaceClickPulseTimer
        interval: 420
        repeat: false

        onTriggered: cpuPlusWindow.favoritesFaceClickPulse = false
    }

    // ============================================================
    // SHARED THERMAL ICON
    // AppControl and CPU++ use the same widgets/thermal/ThermalIcon.qml
    // source; do not duplicate its glyph/effect implementation here.
    // ============================================================

    // Reuse the AppControl/CPU++ shared glyph construction.
    // All positioners own slots; the thermal composition owns its effects.
    Component {
        id: thermalIconComponent
        ThermalIcon { }
    }

    // ============================================================
    // WINDOW
    // AppControlW: 834 wide x 674 tall
    // CPU++:       1000 wide x 834 tall
    //
    // Lower body:
    //   390px shared instrument
    //   260px target/selector
    //   ~326px CPU++ actuator surface
    //
    // The wider chassis deliberately gives target names, monitor icons,
    // filters, and future actuator controls room to breathe.
    // ============================================================

    implicitWidth: 1000
    implicitHeight: 834

    anchors {
        top: true
        right: true
    }

    // Keep the established CPU++ right-edge position. Growing the chassis
    // now expands it leftward into the available DP-5 workspace.
    margins {
        top: -3
        right: 220
    }

    color: "transparent"
    surfaceFormat.opaque: false
    focusable: !relationshipFocusModeActive || relationshipFocused
    visible: menuOpen

    // ============================================================
    // OUTER CHASSIS GLOW
    // Structural glow remains orange at every interaction state.
    // ============================================================

    WindowPanelFrame {
        id: background

        anchors.fill: parent
        anchors.margins: 12

        fillVisible: false
        borderVisible: false

        glowColor: Colors.orange
        closeGlowSpread: 6
        closeGlowOpacity: relationshipFocusModeActive
                          ? (relationshipFocused ? 0.68 : 0.12) : 0.38
        wideGlowSpread: 12
        wideGlowOpacity: relationshipFocusModeActive
                         ? (relationshipFocused ? 0.22 : 0.03) : 0.12

        z: -20
    }

    // ============================================================
    // TOP MODE SELECTOR
    // ============================================================

    Rectangle {
        id: modeRail

        height: 110

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.topMargin: 12

        // Swapped with the CPU++ native control panel.
        color: Colors.dark

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.22
            color: Colors.orange
        }

        GohuText {
            id: modeRailHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 14
            anchors.topMargin: 8

            text: "CPU++"

            font.pixelSize: 15
            color: Colors.magenta
        }

        // Temporary test controls; do not replace the normal Main Mode rail.
        // Selecting B requires a close and reopen to exercise the detach.
        Row {
            id: sampledGlowTestControls
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: 12
            anchors.topMargin: 6
            spacing: 5
            z: 5

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: "GLOW TEST //"
                font.pixelSize: 10
                color: Colors.cyan
            }

            Repeater {
                model: [
                    { value: 0, label: "BASE" },
                    { value: 1, label: "A / OFF" },
                    { value: 2, label: "B / REATTACH" },
                    { value: 3, label: "C / ICON" },
                    { value: 4, label: "D / LABEL" },
                    { value: 5, label: "E / FIXED" }
                ]

                Rectangle {
                    required property var modelData
                    width: Math.max(64, sampledGlowTestLabel.implicitWidth + 14)
                    height: 20
                    color: cpuPlusWindow.modeGlowExperiment === modelData.value
                           ? Colors.yellow : Colors.black
                    border.width: 1
                    border.color: cpuPlusWindow.modeGlowExperiment === modelData.value
                                  ? Colors.magenta : Colors.cyan

                    GohuText {
                        id: sampledGlowTestLabel
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: 10
                        color: cpuPlusWindow.modeGlowExperiment === modelData.value
                               ? Colors.black : Colors.cyan
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: cpuPlusWindow.modeGlowExperiment = modelData.value
                    }
                }
            }
        }

        Rectangle {
            id: modeRailHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: modeRailHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 5

            height: 2

            color: Colors.cyan

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.34
                color: Colors.cyan
            }
        }

        Row {
            id: modeButtonRow

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 8

            height: 58
            spacing: 8

            Repeater {
                model: cpuPlusWindow.modes

                ModeButton {
                    id: modeButton

                    required property int index
                    required property var modelData

                    selected: index === cpuPlusWindow.selectedModeIndex
                    bordered: true
                    customArtwork: true

                    // Each inactive sampler loses its source reference;
                    // merely setting its opacity to zero is insufficient.
                    // B retains the original close/reopen detach experiment.
                    readonly property bool sampledTextActive:
                        cpuPlusWindow.modeGlowExperiment !== 1
                        && (cpuPlusWindow.modeGlowExperiment !== 2
                            || cpuPlusWindow.menuOpen)
                    readonly property bool sampledPrimaryActive:
                        sampledTextActive
                        && cpuPlusWindow.modeGlowExperiment !== 4
                    readonly property bool sampledCaptionActive:
                        sampledTextActive
                        && cpuPlusWindow.modeGlowExperiment !== 3
                    customPrimaryGlowSource:
                        sampledPrimaryActive ? textModeIcon : null
                    customLabelGlowSource:
                        sampledCaptionActive ? modeCaption : null
                    primaryGlowEnabled:
                        sampledPrimaryActive && modelData.kind !== "thermal"
                    labelGlowEnabled: sampledCaptionActive
                    readonly property bool isSelected: selected
                    readonly property bool isHovered: hovered
                    readonly property bool isPressed: pressed
                    readonly property color contentColor: primaryColor

                    width:
                        (
                            modeButtonRow.width
                            - modeButtonRow.spacing
                              * (cpuPlusWindow.modes.length - 1)
                        )
                        / cpuPlusWindow.modes.length

                    height: parent.height

                    // E tests whether scaling the button around a live
                    // sampled text effect causes texture/geometry scattering.
                    // It keeps BOTH icon + caption glows enabled.
                    scale:
                        cpuPlusWindow.modeGlowExperiment === 5
                        ? 1.0
                        : isPressed
                        ? 0.99
                        : isHovered
                        ? 1.025
                        : isSelected
                        ? 1.01
                        : 1.0

                    // The close halo and front wash extend beyond the face.
                    clip: false

                    Behavior on scale {
                        NumberAnimation {
                            duration: 90
                            easing.type: Easing.OutQuad
                        }
                    }

                    onTriggered: {
                        if (modelData.name === "FAVORITES") {
                            cpuPlusWindow.favoritesFaceClickPulse = true;
                            favoritesFaceClickPulseTimer.restart();
                        }
                        cpuPlusWindow.selectMode(index);
                    }

                    Column {
                        width: parent.width
                        anchors.centerIn: parent
                        clip: false

                        spacing: 1

                        Item {
                            id: modeIconSlot
                            width: parent.width
                            height: 29
                            clip: false

                            Loader {
                                id: thermalModeIcon

                                anchors.centerIn: parent

                                visible: modelData.kind === "thermal"
                                sourceComponent:
                                    visible
                                    ? thermalIconComponent
                                    : undefined

                                onLoaded: {
                                    item.iconScale = 0.82;
                                    item.iconColor = Qt.binding(function() {
                                        return modeButton.contentColor;
                                    });
                                    item.pressed = Qt.binding(function() {
                                        return modeButton.isPressed;
                                    });
                                    item.glowOpacity = 0.46;
                                }
                            }

                            GohuText {
                                id: textModeIcon

                                anchors.centerIn: parent
                                width: parent.width - 8
                                horizontalAlignment: Text.AlignHCenter

                                visible: modelData.kind !== "thermal"
                                opacity: 1.0

                                text:
                                    modelData.name === "FAVORITES"
                                    ? (
                                          modeButton.isHovered
                                          || modeButton.isPressed
                                          || cpuPlusWindow.favoritesFaceClickPulse
                                          ? "(˶ˆᗜˆ˵)"
                                          : cpuPlusWindow.favoritesFaceBlinking
                                          ? "(˵-ᴗ-˵)"
                                          : "(˵✧ᴗ✧˵)"
                                      )
                                    : modelData.name === "PROCESS"
                                    ? (
                                          modeButton.isPressed
                                          ? "(=ᗜ=)デ╾━ ๋࣭⭑"
                                          : modeButton.isHovered
                                            || modeButton.isSelected
                                          ? "ദ്ദി(-_•)︻デ═一"
                                          : "(-_•)︻デ═一"
                                      )
                                    : modelData.symbol

                                font.pixelSize:
                                    modelData.name === "PROCESS"
                                    ? 15
                                    : modelData.name === "FAVORITES"
                                    ? 17
                                    : 18
                                fontSizeMode: Text.HorizontalFit
                                minimumPixelSize: 10

                                color: modeButton.contentColor
                            }

                            // AppControl's icon carries the strong state glow.
                            // The sampled source is disconnected during reload.
                            
                        }

                        // AppControl hierarchy: secondary mode name stays dim
                        // white while the icon takes the primary state color.
                        // Column lays out a semantic caption slot, not its
                        // source-attached glow as an independent child.
                        Item {
                            id: modeCaptionSlot
                            width: modeCaption.implicitWidth
                            height: modeCaption.implicitHeight
                            anchors.horizontalCenter: parent.horizontalCenter
                            clip: false

                            QuietText {
                                id: modeCaption
                                anchors.centerIn: parent

                                text: modelData.name
                                font.pixelSize: 10
                                color: modeButton.isPressed
                                       ? Colors.black : Colors.white
                                quietOpacity:
                                    modeButton.isPressed ? 0.42
                                    : modeButton.isHovered || modeButton.isSelected
                                    ? 0.48 : 0.34
                            }

                            
                        }
                    }

                    

                    // MODE halo recipe: close orange perimeter behind the
                    // face, wide wash IN FRONT, matching AppControl.
                    

                    
                }
            }
        }
    }

    // ============================================================
    // TWO-BODY MONITOR ADAPTER + SHARED REFRESH PACEMAKER
    // ============================================================

    ThermalController {
        id: thermalController

        telemetry: cpuPlusWindow.systemTelemetry
        fanControl: cpuPlusWindow.fanControl
    }

    CpuPlusMonitorHost {
        id: monitorHost

        appControlWindow: cpuPlusWindow.appControlWindow
        cpuPlusWindow: cpuPlusWindow
        thermalController: thermalController
    }

    Timer {
        id: sharedMonitorRefreshTimer

        interval: 1900
        repeat: true

        running:
            cpuPlusWindow.menuOpen
            && (cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3)

        onTriggered: cpuPlusWindow.refreshSharedMonitors()
    }

    // ============================================================
    // SHARED APPCONTROL INSTRUMENT BAY
    // ============================================================

    Rectangle {
        id: sharedInstrumentPane

        width: 390

        anchors.left: parent.left
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.leftMargin: 12
        anchors.bottomMargin: 12

        color: Qt.rgba(
            Colors.black.r,
            Colors.black.g,
            Colors.black.b,
            0.95
        )

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: sharedInstrumentHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 16
            anchors.topMargin: 16

            text:
                cpuPlusWindow.selectedModeIndex === 2
                ? "THERMAL MONITOR"
                : cpuPlusWindow.selectedModeIndex === 3
                ? "SYSTEM MONITOR"
                : "SHARED INSTRUMENT"

            font.pixelSize: 13
            color: Colors.magenta
        }

        Rectangle {
            id: sharedHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedInstrumentHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2

            color:
                cpuPlusWindow.selectedModeIndex === 2
                ? Colors.orange
                : Colors.cyan

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.38
                color: parent.color
            }
        }

        Item {
            id: selectedMonitorIdentity

            readonly property var entry:
                cpuPlusWindow.selectedMonitorEntry()

            readonly property bool showingThermal:
                !!entry && !!entry._thermalRecord

            readonly property bool showingSystem:
                !!entry && !!entry._systemRecord

            readonly property bool showingTemperature:
                showingThermal
                && entry.sensorKind !== "fan"

            visible:
                (cpuPlusWindow.selectedModeIndex === 2
                 || cpuPlusWindow.selectedModeIndex === 3)
                && entry !== null

            height: visible ? 122 : 0

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedHeaderLine.bottom

            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 8

            Row {
                id: selectedMonitorIdentityTop

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top

                height: 54
                spacing: 12

                Item {
                    id: selectedMonitorIdentityIconBox

                    width: 54
                    height: 54

                    Loader {
                        id: selectedMonitorThermalIcon

                        anchors.centerIn: parent

                        active:
                            selectedMonitorIdentity.showingTemperature

                        visible: active

                        sourceComponent:
                            active ? thermalIconComponent : undefined

                        onLoaded: {
                            item.iconScale = 1.08;
                            item.iconColor = Qt.binding(function() {
                                return cpuPlusWindow.monitorEntryAccent(
                                    selectedMonitorIdentity.entry
                                );
                            });
                            item.glowOpacity = 0.50;
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        width: parent.width

                        visible:
                            !selectedMonitorIdentity.showingTemperature

                        horizontalAlignment: Text.AlignHCenter

                        text:
                            cpuPlusWindow.monitorEntryIcon(
                                selectedMonitorIdentity.entry
                            )

                        font.pixelSize:
                            selectedMonitorIdentity.showingSystem
                            ? (
                                  String(
                                      selectedMonitorIdentity.entry
                                      && selectedMonitorIdentity.entry.category
                                      || ""
                                  ).toUpperCase() === "NETWORK"
                                  ? 26 : 31
                              )
                            : 23

                        fontSizeMode: Text.HorizontalFit
                        minimumPixelSize: 10

                        color:
                            cpuPlusWindow.monitorEntryAccent(
                                selectedMonitorIdentity.entry
                            )

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 8
                            samples: 7
                            opacity: 0.58
                            color:
                                cpuPlusWindow.monitorEntryAccent(
                                    selectedMonitorIdentity.entry
                                )
                            transparentBorder: true
                        }
                    }
                }

                Column {
                    width:
                        Math.max(
                            0,
                            parent.width
                            - selectedMonitorIdentityIconBox.width
                            - parent.spacing
                        )

                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3

                    GohuText {
                        width: parent.width

                        text:
                            cpuPlusWindow.monitorEntryTitle(
                                selectedMonitorIdentity.entry
                            )

                        font.pixelSize: 15
                        color:
                            cpuPlusWindow.monitorEntryAccent(
                                selectedMonitorIdentity.entry
                            )

                        elide: Text.ElideRight

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 7
                            samples: 7
                            opacity: 0.48
                            color:
                                cpuPlusWindow.monitorEntryAccent(
                                    selectedMonitorIdentity.entry
                                )
                            transparentBorder: true
                        }
                    }

                    GohuText {
                        width: parent.width

                        text:
                            cpuPlusWindow.monitorIdentityMetric(
                                selectedMonitorIdentity.entry
                            )

                        font.pixelSize: 10
                        color: Colors.white
                        opacity: 0.92
                        elide: Text.ElideRight
                    }
                }
            }

            GohuText {
                id: selectedMonitorIdentityRole

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: selectedMonitorIdentityTop.bottom
                anchors.topMargin: 5

                text:
                    cpuPlusWindow.monitorIdentityRole(
                        selectedMonitorIdentity.entry
                    )

                font.pixelSize: 9
                color: Colors.white
                opacity: 0.50
                elide: Text.ElideRight
            }

            GohuText {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: selectedMonitorIdentityRole.bottom
                anchors.topMargin: 3

                text:
                    cpuPlusWindow.monitorIdentityPurpose(
                        selectedMonitorIdentity.entry
                    )

                visible: text.length > 0

                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight

                font.pixelSize: 9
                color: Colors.white
                opacity: 0.42
                lineHeightMode: Text.ProportionalHeight
                lineHeight: 1.10
            }

            GohuText {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                text:
                    cpuPlusWindow.monitorIdentityDetail(
                        selectedMonitorIdentity.entry
                    )

                font.pixelSize: 8
                color:
                    selectedMonitorIdentity.showingThermal
                    ? Colors.orange
                    : Colors.cyan

                opacity: 0.68
                elide: Text.ElideMiddle
            }
        }

        Item {
            id: sharedStateHeader

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: selectedMonitorIdentity.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 8

            height: 30

            GohuText {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 8

                text:
                    cpuPlusWindow.selectedModeIndex === 2
                    ? "THERMAL STATE"
                    : cpuPlusWindow.selectedModeIndex === 3
                    ? "SYSTEM STATE"
                    : "INSTRUMENT STATE"

                font.pixelSize: 13
                color:
                    cpuPlusWindow.selectedModeIndex === 2
                    ? Colors.orange
                    : Colors.cyan

                layer.enabled: true
                layer.effect: DropShadow {
                    radius: 10
                    samples: 9
                    opacity: 0.84
                    color:
                        cpuPlusWindow.selectedModeIndex === 2
                        ? Colors.orange
                        : Colors.cyan
                    transparentBorder: true
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                height: 1
                color:
                    cpuPlusWindow.selectedModeIndex === 2
                    ? Colors.orange
                    : Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 2
                    z: -1
                    opacity: 0.30
                    color: parent.color
                }
            }
        }

        Flickable {
            id: sharedInstrumentScroll

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedStateHeader.bottom
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 10
            anchors.bottomMargin: 8

            clip: true
            contentWidth: width
            contentHeight:
                cpuPlusWindow.selectedModeIndex === 2
                ? Math.max(
                      height,
                      thermalMonitorBody.implicitHeight
                  )
                : cpuPlusWindow.selectedModeIndex === 3
                ? Math.max(
                      height,
                      systemMonitorBody.implicitHeight
                  )
                : height

            Item {
                width: sharedInstrumentScroll.width
                height: sharedInstrumentScroll.contentHeight

                ThermalMonitorView {
                    id: thermalMonitorBody

                    width: parent.width
                    controller: monitorHost
                    thermalController: thermalController
                }

                SystemMonitorView {
                    id: systemMonitorBody

                    width: parent.width
                    controller: monitorHost
                }

                GohuText {
                    anchors.centerIn: parent

                    visible:
                        cpuPlusWindow.selectedModeIndex !== 2
                        && cpuPlusWindow.selectedModeIndex !== 3

                    text:
                        cpuPlusWindow.selectedModeIndex === 0
                        ? "FAVORITES BAY"
                        : "PROCESS BAY"

                    font.pixelSize: 14
                    color: Colors.magenta
                    opacity: 0.62
                }
            }
        }
    }

    // ============================================================
    // TARGET BAY
    // ============================================================

    Rectangle {
        id: targetPane

        width: 260

        anchors.left: sharedInstrumentPane.right
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.bottomMargin: 12

        color: Colors.black

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: targetHeader

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 16

            text:
                cpuPlusWindow.selectedModeIndex === 2
                ? "THERMAL TARGET"
                : cpuPlusWindow.selectedModeIndex === 3
                ? "SYSTEM TARGET"
                : "TARGET"

            font.pixelSize: 12
            color: Colors.magenta
        }

        Rectangle {
            id: targetHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: targetHeader.bottom
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2
            color:
                cpuPlusWindow.selectedModeIndex === 2
                ? Colors.orange
                : Colors.cyan

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.38
                color: parent.color
            }
        }

        Item {
            id: targetSubModeStrip

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: targetHeaderLine.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 7

            height:
                cpuPlusWindow.selectedModeIndex === 2
                ? 52
                : cpuPlusWindow.selectedModeIndex === 3
                ? 92
                : 0

            visible:
                cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3

            Flow {
                anchors.fill: parent
                spacing: 4

                Repeater {
                    model:
                        cpuPlusWindow.selectedModeIndex === 2
                        ? cpuPlusWindow.thermalSubModes
                        : cpuPlusWindow.systemSubModes

                    Rectangle {
                        id: subModeButton

                        required property int index
                        required property var modelData

                        readonly property bool isSelected:
                            cpuPlusWindow.selectedModeIndex === 2
                            ? cpuPlusWindow.thermalSubMode === Number(modelData.key)
                            : cpuPlusWindow.systemSubMode === String(modelData.key)

                        readonly property bool isHovered:
                            subModeMouse.containsMouse

                        readonly property bool isPressed:
                            subModeMouse.pressed

                        readonly property bool isSpacer:
                            !!modelData.spacer

                        width:
                            cpuPlusWindow.selectedModeIndex === 2
                            ? (targetSubModeStrip.width - 4) / 2
                            : (targetSubModeStrip.width - 8) / 3

                        height:
                            cpuPlusWindow.selectedModeIndex === 2
                            ? 38
                            : 27

                        color:
                            isSpacer
                            ? "transparent"
                            : isPressed
                            ? Colors.magenta
                            : isHovered || isSelected
                            ? Colors.yellow
                            : Colors.dark

                        border.width:
                            isSpacer ? 0 : 1

                        border.color:
                            isSelected
                            ? Colors.magenta
                            : isHovered || isPressed
                            ? Colors.orange
                            : cpuPlusWindow.selectedModeIndex === 2
                              && Number(modelData.key) === 1
                            ? Colors.omnitrix
                            : Colors.orange

                        Row {
                            anchors.centerIn: parent
                            spacing: 4

                            Item {
                                anchors.verticalCenter: parent.verticalCenter

                                width:
                                    cpuPlusWindow.selectedModeIndex === 2
                                    && Number(subModeButton.modelData.key) === 0
                                    ? 48 : 28

                                height: parent.height

                                Loader {
                                    anchors.centerIn: parent

                                    visible:
                                        cpuPlusWindow.selectedModeIndex === 2
                                        && Number(subModeButton.modelData.key) === 0

                                    sourceComponent:
                                        visible ? thermalIconComponent : undefined

                                    onLoaded: {
                                        item.iconScale = 0.76;
                                        item.iconColor = Qt.binding(function() {
                                            return subModeButton.isPressed
                                                   ? Colors.black
                                                   : subModeButton.isSelected
                                                   ? Colors.magenta
                                                   : Colors.orange;
                                        });
                                        item.pressed = Qt.binding(function() {
                                            return subModeButton.isPressed;
                                        });
                                        item.glowOpacity = 0.54;
                                    }
                                }

                                GohuText {
                                    anchors.centerIn: parent

                                    visible:
                                        !(cpuPlusWindow.selectedModeIndex === 2
                                          && Number(subModeButton.modelData.key) === 0)

                                    text: String(subModeButton.modelData.symbol || "")

                                    font.pixelSize:
                                        cpuPlusWindow.selectedModeIndex === 3
                                        ? (
                                              String(subModeButton.modelData.key)
                                              === "ALL" ? 15
                                              : String(subModeButton.modelData.key)
                                                === "NETWORK" ? 16
                                              : 17
                                          )
                                        : 20

                                    color:
                                        subModeButton.isPressed
                                        ? Colors.black
                                        : subModeButton.isSelected
                                        ? Colors.magenta
                                        : subModeButton.isHovered
                                        ? Colors.orange
                                        : cpuPlusWindow.selectedModeIndex === 2
                                          && Number(subModeButton.modelData.key) === 1
                                        ? Colors.omnitrix
                                        : Colors.cyan

                                    layer.enabled: !subModeButton.isPressed
                                    layer.effect: DropShadow {
                                        radius: 7
                                        samples: 7
                                        opacity: 0.60
                                        color:
                                            subModeButton.isHovered
                                            ? Colors.orange
                                            : subModeButton.isSelected
                                            ? Colors.magenta
                                            : cpuPlusWindow.selectedModeIndex === 2
                                              && Number(subModeButton.modelData.key) === 1
                                            ? Colors.omnitrix
                                            : Colors.cyan
                                        transparentBorder: true
                                    }
                                }
                            }

                            GohuText {
                                anchors.verticalCenter: parent.verticalCenter

                                text: String(modelData.name || "")
                                font.pixelSize: 8

                                color:
                                    subModeButton.isPressed
                                    ? Colors.black
                                    : subModeButton.isSelected
                                    ? Colors.magenta
                                    : subModeButton.isHovered
                                    ? Colors.orange
                                    : Colors.white
                            }
                        }

                        MouseArea {
                            id: subModeMouse

                            anchors.fill: parent
                            enabled: !subModeButton.isSpacer
                            hoverEnabled: enabled

                            onClicked: {
                                if (cpuPlusWindow.selectedModeIndex === 2)
                                    cpuPlusWindow.selectThermalSubMode(modelData.key);
                                else
                                    cpuPlusWindow.selectSystemSubMode(modelData.key);
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: isHovered || isSelected ? 4 : 2
                            z: -1
                            opacity:
                                subModeButton.isSpacer
                                ? 0.0
                                : subModeButton.isHovered
                                  || subModeButton.isSelected
                                ? 0.42 : 0.12
                            color:
                                isSelected
                                ? Colors.magenta
                                : isHovered
                                ? Colors.orange
                                : Colors.cyan
                        }
                    }
                }
            }
        }

        Flickable {
            id: monitorSelectorScroll

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: targetSubModeStrip.bottom
            anchors.bottom: parent.bottom

            anchors.leftMargin: 6
            anchors.rightMargin: 19
            anchors.bottomMargin: 8
            anchors.topMargin: 8

            visible:
                cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3

            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: monitorSelectorColumn.implicitHeight

            function clampContentY() {
                const maxY =
                    Math.max(0, contentHeight - height);

                contentY =
                    Math.max(
                        0,
                        Math.min(maxY, contentY)
                    );
            }

            onContentHeightChanged: {
                clampContentY();
            }

            onHeightChanged: {
                clampContentY();
            }

            Column {
                id: monitorSelectorColumn

                width: monitorSelectorScroll.width
                spacing: 1

                Repeater {
                    model: cpuPlusWindow.selectedMonitorRows()

                    onModelChanged: {
                        monitorSelectorScroll.contentY = 0;
                    }

                    Rectangle {
                        id: monitorRowButton

                        required property int index
                        required property var modelData

                        readonly property bool isSelected:
                            index === cpuPlusWindow.selectedMonitorIndex()
                        readonly property bool isHovered:
                            monitorRowMouse.containsMouse
                        readonly property bool isPressed:
                            monitorRowMouse.pressed

                        readonly property color foreground:
                            isPressed
                            ? Colors.black
                            : isSelected
                            ? Colors.magenta
                            : isHovered
                            ? Colors.orange
                            : Colors.cyan

                        width: monitorSelectorColumn.width
                        height: 50

                        color:
                            isPressed
                            ? Colors.magenta
                            : isSelected || isHovered
                            ? Colors.yellow
                            : Colors.dark

                        border.width:
                            isHovered || isPressed
                            ? 1 : 0

                        border.color: Colors.orange

                        scale:
                            isPressed
                            ? 0.99
                            : isHovered
                            ? 1.015
                            : 1.0

                        Behavior on scale {
                            NumberAnimation {
                                duration: 90
                                easing.type: Easing.OutQuad
                            }
                        }

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
                            anchors.topMargin: 3
                            anchors.bottomMargin: 3
                            spacing: 6

                            Item {
                                id: monitorRowIconBox

                                readonly property bool showingSystemIcon:
                                    !!monitorRowButton.modelData
                                    && !!monitorRowButton.modelData._systemRecord

                                readonly property bool showingTemperatureIcon:
                                    !showingSystemIcon
                                    && !!monitorRowButton.modelData
                                    && !!monitorRowButton.modelData._thermalRecord
                                    && monitorRowButton.modelData.sensorKind !== "fan"

                                width:
                                    showingSystemIcon
                                    ? 54
                                    : showingTemperatureIcon
                                    ? 56
                                    : 42

                                height: parent.height

                                Loader {
                                    id: targetTemperatureIconLoader

                                    anchors.centerIn: parent

                                    active:
                                        monitorRowIconBox.showingTemperatureIcon

                                    visible: active

                                    sourceComponent:
                                        active ? thermalIconComponent : undefined

                                    onLoaded: {
                                        item.iconScale = 0.86;
                                        item.iconColor = Qt.binding(function() {
                                            return monitorRowButton.isPressed
                                                   ? Colors.black
                                                   : monitorRowButton.isHovered
                                                     || monitorRowButton.isSelected
                                                   ? Colors.orange
                                                   : cpuPlusWindow.monitorEntryAccent(
                                                         monitorRowButton.modelData
                                                     );
                                        });
                                        item.pressed = Qt.binding(function() {
                                            return monitorRowButton.isPressed;
                                        });
                                        item.glowOpacity = 0.52;
                                    }
                                }

                                GohuText {
                                    anchors.centerIn: parent
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter

                                    visible:
                                        !monitorRowIconBox.showingTemperatureIcon

                                    text:
                                        cpuPlusWindow.monitorEntryIcon(
                                            monitorRowButton.modelData
                                        )

                                    font.pixelSize:
                                        monitorRowButton.modelData
                                        && monitorRowButton.modelData._thermalRecord
                                        ? 17
                                        : String(
                                              monitorRowButton.modelData
                                              && monitorRowButton.modelData.category
                                              || ""
                                          ).toUpperCase() === "NETWORK"
                                        ? 25
                                        : 31

                                    fontSizeMode: Text.HorizontalFit
                                    minimumPixelSize: 8

                                    color:
                                        monitorRowButton.isPressed
                                        ? Colors.black
                                        : monitorRowButton.isHovered
                                          || monitorRowButton.isSelected
                                        ? Colors.orange
                                        : cpuPlusWindow.monitorEntryAccent(
                                              monitorRowButton.modelData
                                          )

                                    layer.enabled: !monitorRowButton.isPressed
                                    layer.effect: DropShadow {
                                        radius: 6
                                        samples: 5
                                        opacity:
                                            monitorRowButton.isHovered
                                            || monitorRowButton.isSelected
                                            ? 0.62
                                            : 0.44

                                        color:
                                            monitorRowButton.isHovered
                                            || monitorRowButton.isSelected
                                            ? Colors.orange
                                            : cpuPlusWindow.monitorEntryAccent(
                                                  monitorRowButton.modelData
                                              )

                                        transparentBorder: true
                                    }
                                }
                            }

                            Column {
                                width:
                                    Math.max(
                                        0,
                                        parent.width
                                        - monitorRowIconBox.width
                                        - parent.spacing
                                    )
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 3

                                GohuText {
                                    width: parent.width

                                    text:
                                        cpuPlusWindow.monitorEntryTitle(
                                            monitorRowButton.modelData
                                        )

                                    font.pixelSize: 10
                                    color: monitorRowButton.foreground
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width

                                    text:
                                        cpuPlusWindow.monitorEntryMetric(
                                            monitorRowButton.modelData
                                        )

                                    font.pixelSize: 8
                                    color: monitorRowButton.foreground
                                    opacity: 0.88
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        MouseArea {
                            id: monitorRowMouse

                            anchors.fill: parent
                            hoverEnabled: true

                            onClicked: {
                                cpuPlusWindow.selectMonitorRow(index);
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent

                            spread:
                                monitorRowButton.isHovered
                                ? 6
                                : monitorRowButton.isSelected
                                ? 4
                                : 2

                            z: -1

                            opacity:
                                monitorRowButton.isPressed
                                ? 0.58
                                : monitorRowButton.isHovered
                                ? 0.48
                                : monitorRowButton.isSelected
                                ? 0.38
                                : 0.08

                            color: Colors.orange
                        }
                    }
                }
            }
        }
        // AppControl selector scrollbar geometry.
        NeonScrollBar {
            id: targetScrollTrack

            flickable: monitorSelectorScroll

            x: parent.width - width - 3
            y: monitorSelectorScroll.y + 2
            height: Math.max(0, monitorSelectorScroll.height - 2)
            z: 300

            barAreaWidth: 10
            railWidth: 10
            barHandleWidth: 6
            minimumHandleHeight: 30
            scrollThreshold: 0

            railColor:
                cpuPlusWindow.selectedModeIndex === 2
                ? Colors.orange
                : Colors.cyan
            railOpacity: 0.90
            railRadius: 0
            railGlowSpread: 2
            railGlowOpacity: 0.24

            handleColor: Colors.magenta
            handleOpacity: 0.90
            barHandleRadius: 0
            handleBorderWidth: 0
            barGlowIdleSpread: 2
            barGlowHoverSpread: 2
            barGlowIdleOpacity: 0.28
            barGlowHoverOpacity: 0.28

            preserveDragOffset: true
            wheelEnabled: false
            pointerCursorShape: Qt.ArrowCursor

            visible:
                (cpuPlusWindow.selectedModeIndex === 2
                 || cpuPlusWindow.selectedModeIndex === 3)
                && scrollable
        }

    }

    // ============================================================
    // CPU++ ACTUATOR BAY
    //
    // Intentionally kept structurally empty for now. This bay is reserved
    // for controls that mutate machine state; informational filler does not
    // belong here.
    // ============================================================

    Rectangle {
        id: actuatorPane

        anchors.left: targetPane.right
        anchors.right: parent.right
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.rightMargin: 12
        anchors.bottomMargin: 12

        color: Colors.dark

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: actuatorHeader

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 16

            text: "CPU++ ACTUATORS"

            font.pixelSize: 12
            color: Colors.magenta
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: actuatorHeader.bottom
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2
            color: Colors.cyan

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.38
                color: Colors.cyan
            }
        }
    }
}
