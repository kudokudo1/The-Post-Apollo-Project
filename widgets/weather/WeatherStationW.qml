import QtQuick
import Quickshell
import Quickshell.Wayland
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

PanelWindow {
    id: weatherStation

    property var weatherService: null
    property var spaceService: null

    property bool menuOpen: false

    property string activeDomain: "sky"
    property string currentView: "home"

    readonly property var domains: [
        {
            "id": "ground",
            "name": "GROUND",
            "symbol": "⌁"
        },
        {
            "id": "sky",
            "name": "SKY",
            "symbol": "☁"
        },
        {
            "id": "space",
            "name": "SPACE",
            "symbol": "✦"
        }
    ]

    readonly property var views: [
        {
            "id": "map",
            "name": "MAP",
            "symbol": "⌖"
        },
        {
            "id": "news",
            "name": "NEWS",
            "symbol": "▤"
        },
        {
            "id": "radio",
            "name": "RADIO",
            "symbol": "◉"
        },
        {
            "id": "terminal",
            "name": "TERMINAL",
            "symbol": ">_"
        }
    ]

    readonly property string activeDomainName: {
        for (let i = 0; i < domains.length; i++) {
            if (domains[i].id === activeDomain)
                return domains[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentViewName: {
        if (currentView === "home")
            return "HOME";

        for (let i = 0; i < views.length; i++) {
            if (views[i].id === currentView)
                return views[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentContext: {
        if (currentView === "home")
            return "HOME";

        return activeDomainName + " // " + currentViewName;
    }

    implicitWidth: menuOpen ? 1000 : 0

    implicitHeight: menuOpen ? 700 : 0

    visible: true
    color: "transparent"

    WlrLayershell.layer: WlrLayer.Overlay

    // Weather Station ALWAYS owns keyboard focus
    // while the menu is open.
    WlrLayershell.keyboardFocus: weatherStation.menuOpen ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

    anchors {
        top: true
        bottom: false
        right: true
        left: false
    }

    margins {
        top: 0
        bottom: 0
        right: 20
        left: 0
    }

    // Mouse can still pass through the Star Map
    // display area while Kitty is visible.
    mask: Region {
        width: weatherStation.menuOpen ? 1000 : 0

        height: weatherStation.menuOpen ? 700 : 0

        Region {
            x: modeRail.width + terminalView.bayX

            y: header.height + terminalView.bayY

            width: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayWidth : 0

            height: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayHeight : 0

            intersection: Intersection.Subtract
        }
    }

    function open() {
        menuOpen = true;
    }

    function close() {
        terminalView.closeTerminal();
        menuOpen = false;
    }

    function toggle() {
        if (menuOpen)
            close();
        else
            open();
    }

    WindowPanelFrame {
        id: stationBackground

        width: 1000
        height: 700

        anchors.right: parent.right
        anchors.bottom: parent.bottom

        visible: weatherStation.menuOpen

        fillVisible: false
        borderVisible: false

        glowColor: Colors.cyan
        closeGlowSpread: 4
        closeGlowOpacity: 0.30
        wideGlowSpread: 14
        wideGlowOpacity: 0.10

        // ─────────────────────────────────────────
        // HEADER
        // ─────────────────────────────────────────

        Rectangle {
            id: header

            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right

            height: 62

            color: Colors.black

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 22

                text: "✦ WEATHER STATION ✦"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: Colors.cyan
            }

            Text {
                anchors.centerIn: parent

                text: weatherStation.currentContext

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 18

                color: Colors.orange
            }

            Text {
                id: observatoryButton

                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                anchors.rightMargin: 22

                text: "[ □ ]"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: observatoryMouse.pressed ? Colors.magenta : observatoryMouse.containsMouse ? Colors.orange : Colors.cyan

                MouseArea {
                    id: observatoryMouse

                    anchors.fill: parent
                    hoverEnabled: true
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }
        }

        // ─────────────────────────────────────────
        // NAVIGATION
        // ─────────────────────────────────────────

        Rectangle {
            id: modeRail

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left

            width: 160

            color: Colors.black

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right

                width: 2

                color: Colors.cyan
            }

            Column {
                id: railColumn

                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right

                anchors.topMargin: 14

                spacing: 6

                Rectangle {
                    id: homeButton

                    width: railColumn.width
                    height: 48

                    readonly property bool selected: weatherStation.currentView === "home"

                    color: homeMouse.pressed ? Colors.magenta : selected ? Colors.yellow : Colors.black

                    Row {
                        anchors.centerIn: parent
                        spacing: 10

                        Text {
                            text: "⌂"

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 18

                            color: homeMouse.pressed ? Colors.black : homeButton.selected ? Colors.orange : homeMouse.containsMouse ? Colors.orange : Colors.cyan
                        }

                        Text {
                            text: "HOME"

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 18

                            color: homeMouse.pressed ? Colors.black : homeButton.selected ? Colors.orange : homeMouse.containsMouse ? Colors.orange : Colors.cyan
                        }
                    }

                    MouseArea {
                        id: homeMouse

                        anchors.fill: parent
                        hoverEnabled: true

                        onClicked: {
                            weatherStation.currentView = "home";
                        }
                    }
                }

                Item {
                    width: 1
                    height: 7
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "DOMAIN"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.domains

                    delegate: Rectangle {
                        id: domainButton

                        required property int index
                        required property var modelData

                        readonly property bool selected: weatherStation.activeDomain === modelData.id

                        width: railColumn.width
                        height: 48

                        color: domainMouse.pressed ? Colors.magenta : selected ? Colors.yellow : Colors.black

                        Row {
                            anchors.centerIn: parent
                            spacing: 10

                            Text {
                                text: domainButton.modelData.symbol

                                font.family: "GohuFont 11 Nerd Font Mono"

                                font.pixelSize: 18

                                color: domainMouse.pressed ? Colors.black : domainButton.selected ? Colors.orange : domainMouse.containsMouse ? Colors.orange : Colors.cyan
                            }

                            Text {
                                text: domainButton.modelData.name

                                font.family: "GohuFont 11 Nerd Font Mono"

                                font.pixelSize: 18

                                color: domainMouse.pressed ? Colors.black : domainButton.selected ? Colors.orange : domainMouse.containsMouse ? Colors.orange : Colors.cyan
                            }
                        }

                        MouseArea {
                            id: domainMouse

                            anchors.fill: parent
                            hoverEnabled: true

                            onClicked: {
                                weatherStation.activeDomain = domainButton.modelData.id;
                            }
                        }
                    }
                }

                Item {
                    width: railColumn.width
                    height: 17

                    Rectangle {
                        anchors.centerIn: parent

                        width: parent.width - 28
                        height: 2

                        color: Colors.cyan
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "VIEW"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.views

                    delegate: Rectangle {
                        id: viewButton

                        required property int index
                        required property var modelData

                        readonly property bool selected: weatherStation.currentView === modelData.id

                        width: railColumn.width
                        height: 48

                        color: viewMouse.pressed ? Colors.magenta : selected ? Colors.yellow : Colors.black

                        Row {
                            anchors.centerIn: parent
                            spacing: 10

                            Text {
                                text: viewButton.modelData.symbol

                                font.family: "GohuFont 11 Nerd Font Mono"

                                font.pixelSize: 18

                                color: viewMouse.pressed ? Colors.black : viewButton.selected ? Colors.orange : viewMouse.containsMouse ? Colors.orange : Colors.cyan
                            }

                            Text {
                                text: viewButton.modelData.name

                                font.family: "GohuFont 11 Nerd Font Mono"

                                font.pixelSize: 18

                                color: viewMouse.pressed ? Colors.black : viewButton.selected ? Colors.orange : viewMouse.containsMouse ? Colors.orange : Colors.cyan
                            }
                        }

                        MouseArea {
                            id: viewMouse

                            anchors.fill: parent
                            hoverEnabled: true

                            onClicked: {
                                weatherStation.currentView = viewButton.modelData.id;
                            }
                        }
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // MAIN VIEW
        // ─────────────────────────────────────────

        Rectangle {
            id: mainView

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: modeRail.right
            anchors.right: parent.right

            color: weatherStation.currentView === "terminal" ? "transparent" : Colors.black

            clip: true

            Loader {
                anchors.fill: parent

                visible: weatherStation.currentView !== "terminal"

                sourceComponent: weatherStation.currentView === "home" ? homeViewComponent : placeholderViewComponent
            }

            StationTerminal {
                id: terminalView

                anchors.fill: parent

                visible: weatherStation.currentView === "terminal"

                stationOpen: weatherStation.menuOpen

                targetScreen: weatherStation.screen

                stationWidth: stationBackground.width

                stationHeight: stationBackground.height

                stationRightMargin: 20
                stationBottomMargin: 90

                stationHeaderHeight: header.height

                stationRailWidth: modeRail.width
            }
        }

        Component {
            id: homeViewComponent

            StationHome {
                activeDomain: weatherStation.activeDomain

                weatherService: weatherStation.weatherService

                spaceService: weatherStation.spaceService

                onDomainRequested: function (domain) {
                    weatherStation.activeDomain = domain;
                }
            }
        }

        Component {
            id: placeholderViewComponent

            Rectangle {
                color: Colors.black

                Column {
                    anchors.centerIn: parent

                    spacing: 12

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.activeDomainName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 20

                        color: Colors.cyan
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.currentViewName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 28

                        color: Colors.orange
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: {
                            if (weatherStation.currentView === "map")
                                return "map display offline...";

                            if (weatherStation.currentView === "news")
                                return "news receiver offline...";

                            if (weatherStation.currentView === "radio")
                                return "radio receiver offline...";

                            return "";
                        }

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: Colors.white
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // FOOTER
        // ─────────────────────────────────────────

        Rectangle {
            id: footer

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            height: 62

            color: Colors.black

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 20

                text: weatherStation.weatherService && weatherStation.weatherService.ready ? "◉ WEATHER LINK ONLINE" : "◉ SYSTEM ONLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }

            Text {
                anchors.centerIn: parent

                text: "MEDIA BAY // IDLE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.white
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                anchors.rightMargin: 20

                text: weatherStation.activeDomainName

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }
        }
    }

    Shortcut {
        sequence: "Escape"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }

    Shortcut {
        sequence: "Meta+Shift+Q"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }
}
