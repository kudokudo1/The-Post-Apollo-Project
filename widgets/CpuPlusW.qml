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
    property int selectedModeIndex: 0
    property int thermalSelectedIndex: 0
    property int systemSelectedIndex: 0

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
    // Copied from AppControl's canonical THERMAL composition so the
    // two surfaces speak the same visual language.
    // ============================================================

    Component {
        id: thermalIconComponent

        Item {
            id: thermalIconRoot

            property color iconColor: Colors.orange
            property color glowColor: Colors.orange
            property real iconScale: 1.0
            property real glowOpacity: 0.46
            property bool pressed: false

            opacity: 1.0
            implicitWidth: 59 * iconScale
            implicitHeight: 24 * iconScale
            width: implicitWidth
            height: implicitHeight

            Item {
                id: thermalIconScaledContent

                width: 59
                height: 24

                anchors.centerIn: parent

                scale: thermalIconRoot.iconScale
                transformOrigin: Item.Center
                opacity: 1.0

                GohuText {
                    id: thermalIconTopLeftStar

                    x: 15
                    y: -3

                    text: "⋆"

                    font.pixelSize: 7

                    opacity: 1.0

                    color:
                        thermalIconRoot.pressed
                        ? Colors.black
                        : thermalIconRoot.iconColor
                }

                DropShadow {
                    anchors.fill: thermalIconTopLeftStar
                    source: thermalIconTopLeftStar

                    visible: !thermalIconRoot.pressed

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 4
                    samples: 5

                    opacity: thermalIconRoot.glowOpacity
                    color: thermalIconRoot.glowColor

                    transparentBorder: true
                }

                Row {
                    id: thermalIconOuterRow

                    anchors.centerIn: parent

                    spacing: 1

                    Row {
                        id: thermalIconLeftCoreRow

                        anchors.verticalCenter: parent.verticalCenter

                        spacing: -9

                        Item {
                            width: thermalIconLeft.implicitWidth
                            height: 24

                            GohuText {
                                id: thermalIconLeft

                                anchors.verticalCenter: parent.verticalCenter

                                text: "₊˚⊹"

                                font.pixelSize: 13
                                font.letterSpacing: -1.6

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconLeft
                                source: thermalIconLeft

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }

                        Item {
                            width: thermalIconCore.implicitWidth
                            height: 24

                            Text {
                                id: thermalIconCore

                                anchors.verticalCenter: parent.verticalCenter

                                text: "🌡"

                                font.family: "Noto Sans Symbols2"
                                font.pixelSize: 20
                                font.weight: Font.Bold

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconCore
                                source: thermalIconCore

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity * 0.76
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }
                    }

                    Item {
                        width: thermalIconRight.implicitWidth
                        height: 24

                        GohuText {
                            id: thermalIconRight

                            anchors.verticalCenter: parent.verticalCenter

                            text: "๋࣭⭑"

                            font.pixelSize: 13

                            opacity: 1.0

                            color:
                                thermalIconRoot.pressed
                                ? Colors.black
                                : thermalIconRoot.iconColor
                        }

                        DropShadow {
                            anchors.fill: thermalIconRight
                            source: thermalIconRight

                            visible: !thermalIconRoot.pressed

                            horizontalOffset: 0
                            verticalOffset: 0

                            radius: 5
                            samples: 5

                            opacity: thermalIconRoot.glowOpacity
                            color: thermalIconRoot.glowColor

                            transparentBorder: true
                        }
                    }
                }
            }
        }
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
    focusable: true
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
        closeGlowOpacity: 0.38
        wideGlowSpread: 12
        wideGlowOpacity: 0.12

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

                Rectangle {
                    id: modeButton

                    required property int index
                    required property var modelData

                    readonly property bool isSelected:
                        index === cpuPlusWindow.selectedModeIndex

                    readonly property bool isHovered:
                        modeMouse.containsMouse

                    readonly property bool isPressed:
                        modeMouse.pressed

                    readonly property color contentColor:
                        isPressed
                        ? Colors.black
                        : isSelected
                        ? Colors.magenta
                        : isHovered
                        ? Colors.orange
                        : Colors.cyan

                    width:
                        (
                            modeButtonRow.width
                            - modeButtonRow.spacing
                              * (cpuPlusWindow.modes.length - 1)
                        )
                        / cpuPlusWindow.modes.length

                    height: parent.height

                    scale:
                        isPressed
                        ? 0.99
                        : isHovered
                        ? 1.025
                        : isSelected
                        ? 1.01
                        : 1.0

                    color:
                        isPressed
                        ? Colors.magenta
                        : isHovered || isSelected
                        ? Colors.yellow
                        : Colors.black

                    border.width: 1
                    border.color:
                        isHovered || isPressed || isSelected
                        ? Colors.orange
                        : Colors.cyan

                    Behavior on scale {
                        NumberAnimation {
                            duration: 90
                            easing.type: Easing.OutQuad
                        }
                    }

                    Column {
                        width: parent.width
                        anchors.centerIn: parent

                        spacing: 1

                        Item {
                            width: parent.width
                            height: 29

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
                                    item.glowColor = Qt.binding(function() {
                                        return modeButton.isHovered
                                               ? Colors.orange
                                               : Colors.cyan;
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

                                layer.enabled: !modeButton.isPressed
                                layer.effect: DropShadow {
                                    horizontalOffset: 0
                                    verticalOffset: 0

                                    radius:
                                        modeButton.isHovered
                                        ? 14
                                        : modeButton.isSelected
                                        ? 12
                                        : 10
                                    samples: 11

                                    opacity:
                                        modeButton.isHovered
                                        ? 0.82
                                        : 0.58

                                    color:
                                        modeButton.isHovered
                                        ? Colors.orange
                                        : Colors.cyan

                                    transparentBorder: true
                                }
                            }
                        }

                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter

                            text: modelData.name

                            font.pixelSize: 10
                            color: modeButton.contentColor
                        }
                    }

                    MouseArea {
                        id: modeMouse

                        anchors.fill: parent

                        hoverEnabled: true

                        onClicked: {
                            if (modelData.name === "FAVORITES") {
                                cpuPlusWindow.favoritesFaceClickPulse = true;
                                favoritesFaceClickPulseTimer.restart();
                            }

                            cpuPlusWindow.selectMode(index);
                        }
                    }

                    // Orange glow is invariant; only its reach/intensity changes.
                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 6
                            : modeButton.isSelected
                            ? 4
                            : 2

                        z: -1

                        opacity:
                            modeButton.isPressed
                            ? 0.62
                            : modeButton.isHovered
                            ? 0.56
                            : modeButton.isSelected
                            ? 0.46
                            : 0.10

                        color: Colors.orange
                    }

                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 16
                            : modeButton.isSelected
                            ? 11
                            : 7

                        z: -2

                        opacity:
                            modeButton.isPressed
                            ? 0.16
                            : modeButton.isHovered
                            ? 0.14
                            : modeButton.isSelected
                            ? 0.11
                            : 0.035

                        color: Colors.orange
                    }
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
                            item.glowColor = Qt.binding(function() {
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
                                        item.glowColor = Qt.binding(function() {
                                            return subModeButton.isSelected
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
                                        item.glowColor = Qt.binding(function() {
                                            return monitorRowButton.isHovered
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
