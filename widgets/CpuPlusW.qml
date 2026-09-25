import Quickshell
import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../components"
import "appcontrol"
import "cpuplus"

PanelWindow {
    id: cpuPlusWindow

    property var appControlWindow

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
        { name: "SWAP", key: "SWAP", symbol: "⇄" }
    ]

    // Rail-face animation state, matching AppControl's FAVORITES behavior.
    property bool favoritesFaceClickPulse: false
    property bool favoritesFaceBlinking: false
    property bool favoritesFaceDoubleBlinkPending: false

    readonly property var thermalRows:
        appControlWindow && appControlWindow.thermalRows
        ? appControlWindow.thermalRows
        : []

    readonly property var systemRows:
        appControlWindow && appControlWindow.systemRows
        ? appControlWindow.systemRows
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

        if (selectedModeIndex === 2 || selectedModeIndex === 3)
            refreshSharedMonitors();
    }

    function refreshSharedMonitors() {
        if (appControlWindow)
            appControlWindow.refreshKillMonitor();
    }

    function selectedMonitorRows() {
        if (selectedModeIndex === 2) {
            return thermalRows.filter(function(entry) {
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
        refreshSharedMonitors();
    }

    function selectSystemSubMode(category) {
        systemSubMode = String(category || "ALL").toUpperCase();
        systemSelectedIndex = 0;
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

        if (entry._thermalRecord && appControlWindow)
            return appControlWindow.thermalAccent(entry);

        if (entry._systemRecord && appControlWindow
                && appControlWindow.systemIconAccent)
            return appControlWindow.systemIconAccent(entry);

        return Colors.cyan;
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

    RectangularShadow {
        anchors.fill: background

        spread: 6
        z: -20

        opacity: 0.38
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: background

        spread: 12
        z: -21

        opacity: 0.12
        color: Colors.orange
    }

    Rectangle {
        id: background

        anchors.fill: parent
        anchors.margins: 12

        color: "transparent"
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

    CpuPlusMonitorHost {
        id: monitorHost

        appControlWindow: cpuPlusWindow.appControlWindow
        cpuPlusWindow: cpuPlusWindow
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
            id: sharedStateHeader

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedHeaderLine.bottom

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
            anchors.rightMargin: 18
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
                ? 58
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

                        width:
                            cpuPlusWindow.selectedModeIndex === 2
                            ? (targetSubModeStrip.width - 4) / 2
                            : (targetSubModeStrip.width - 8) / 3

                        height:
                            cpuPlusWindow.selectedModeIndex === 2
                            ? 44
                            : 27

                        color:
                            isPressed
                            ? Colors.magenta
                            : isHovered || isSelected
                            ? Colors.yellow
                            : Colors.dark

                        border.width: 1
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
                                              === "NETWORK" ? 20 : 19
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
                            hoverEnabled: true

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
                            opacity: isHovered || isSelected ? 0.42 : 0.12
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

            anchors.margins: 8
            anchors.topMargin: 10

            visible:
                cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3

            clip: true
            contentWidth: width
            contentHeight: monitorSelectorColumn.implicitHeight

            Column {
                id: monitorSelectorColumn

                width: monitorSelectorScroll.width
                spacing: 7

                Repeater {
                    model: cpuPlusWindow.selectedMonitorRows()

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
                        height:
                            modelData && modelData._systemRecord
                            ? 64 : 56

                        color:
                            isPressed
                            ? Colors.magenta
                            : isSelected || isHovered
                            ? Colors.yellow
                            : Colors.black

                        border.width: 1
                        border.color:
                            isHovered || isPressed || isSelected
                            ? Colors.orange
                            : Colors.cyan

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
                            anchors.margins: 6
                            spacing: 7

                            Item {
                                id: monitorRowIconBox

                                width:
                                    monitorRowButton.modelData
                                    && monitorRowButton.modelData._systemRecord
                                    ? 58 : 42
                                height: parent.height

                                GohuText {
                                    anchors.centerIn: parent
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter

                                    text:
                                        cpuPlusWindow.monitorEntryIcon(
                                            monitorRowButton.modelData
                                        )

                                    font.pixelSize:
                                        monitorRowButton.modelData
                                        && monitorRowButton.modelData._thermalRecord
                                        ? (
                                              monitorRowButton.modelData.sensorKind
                                              === "fan" ? 15 : 10
                                          )
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
    }

    // AppControl selector scrollbar geometry.
    Rectangle {
        id: targetScrollTrack

        width: 10

        anchors.top: targetSubModeStrip.bottom
        anchors.bottom: targetPane.bottom
        anchors.right: targetPane.right

        anchors.topMargin: 10
        anchors.bottomMargin: 8
        anchors.rightMargin: 3

        color:
            cpuPlusWindow.selectedModeIndex === 2
            ? Colors.orange
            : Colors.cyan

        opacity:
            monitorSelectorScroll.contentHeight
            > monitorSelectorScroll.height
            ? 0.90 : 0.0

        visible:
            (cpuPlusWindow.selectedModeIndex === 2
             || cpuPlusWindow.selectedModeIndex === 3)
            && opacity > 0.0

        z: 300

        property real maxContentY:
            Math.max(
                0,
                monitorSelectorScroll.contentHeight
                - monitorSelectorScroll.height
            )

        property real handleTravel:
            Math.max(
                0,
                height - targetScrollHandle.height
            )

        function setScrollFromHandleY(handleY) {
            if (maxContentY <= 0 || handleTravel <= 0)
                return;

            const clampedY =
                Math.max(
                    0,
                    Math.min(handleTravel, handleY)
                );

            monitorSelectorScroll.contentY =
                (clampedY / handleTravel) * maxContentY;
        }

        RectangularShadow {
            anchors.fill: parent
            spread: 2
            z: -1
            opacity: 0.24
            color: parent.color
        }

        Rectangle {
            id: targetScrollHandle

            width: 6
            anchors.horizontalCenter: parent.horizontalCenter

            height:
                Math.max(
                    30,
                    parent.height
                    * Math.min(
                        1.0,
                        monitorSelectorScroll.visibleArea.heightRatio
                    )
                )

            y: {
                if (targetScrollTrack.maxContentY <= 0
                        || targetScrollTrack.handleTravel <= 0)
                    return 0;

                const clampedContentY =
                    Math.max(
                        0,
                        Math.min(
                            targetScrollTrack.maxContentY,
                            monitorSelectorScroll.contentY
                        )
                    );

                return (
                    clampedContentY
                    / targetScrollTrack.maxContentY
                ) * targetScrollTrack.handleTravel;
            }

            color: Colors.magenta

            RectangularShadow {
                anchors.fill: parent
                spread: 2
                z: -1
                opacity: 0.28
                color: Colors.magenta
            }
        }

        MouseArea {
            id: targetScrollMouse

            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton

            property real dragOffset: 0

            onPressed: function(mouse) {
                const handleTop = targetScrollHandle.y;
                const handleBottom =
                    targetScrollHandle.y
                    + targetScrollHandle.height;

                dragOffset =
                    mouse.y >= handleTop
                    && mouse.y <= handleBottom
                    ? mouse.y - handleTop
                    : targetScrollHandle.height / 2;

                targetScrollTrack.setScrollFromHandleY(
                    mouse.y - dragOffset
                );
            }

            onPositionChanged: function(mouse) {
                if (pressed)
                    targetScrollTrack.setScrollFromHandleY(
                        mouse.y - dragOffset
                    );
            }
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
