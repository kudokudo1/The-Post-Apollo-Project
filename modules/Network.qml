import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import Quickshell.Networking

Rectangle {
    id: networkDock

    implicitHeight: 50
    implicitWidth: root.implicitWidth + 8
    color: Colors.black

    RowLayout {
        id: root

        spacing: 7

        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter

        property var wifiDevice: Networking.devices.values.find(d => d.type === DeviceType.Wifi)

        property var active: wifiDevice ? wifiDevice.networks.values.find(n => n.connected) : null

        property int signalPercent: 0
        property string linkSpeed: "0"

        readonly property real signal: root.signalPercent / 100

        property bool wifiEnabled: false
        property bool ethernetMode: false

        property var ethernetDevice: Networking.devices.values.find(d => d.type === DeviceType.Ethernet)

        property var ethernetActive: ethernetDevice ? ethernetDevice.networks.values.find(n => n.connected) : null

        property string ethernetName: ""
        property string ethernetSpeed: "0"
        property bool ethernetConnected: false

        readonly property bool signalWeak: root.wifiEnabled && root.active && root.signal < 0.25

        readonly property bool signalLow: root.wifiEnabled && root.active && root.signal >= 0.25 && root.signal < 0.50

        readonly property bool signalMedium: root.wifiEnabled && root.active && root.signal >= 0.50 && root.signal < 0.75

        readonly property bool signalStrong: root.wifiEnabled && root.active && root.signal >= 0.75

        property color networkColor: {
            if (!root.wifiEnabled)
                return Colors.white;

            if (!root.active)
                return Colors.white;

            if (root.signal < 0.25)
                return Colors.yellow;

            if (root.signal < 0.50)
                return Colors.orange;

            if (root.signal < 0.75)
                return Colors.cyan;

            return Colors.magenta;
        }

        property color networkGlowColor: {
            if (!root.wifiEnabled)
                return Colors.white;

            if (!root.active)
                return Colors.cyan;

            return root.networkColor;
        }

        // =========================================
        // WIFI ENABLED
        // =========================================

        Process {
            id: wifiEnabledProcess

            command: ["nmcli", "radio", "wifi"]

            stdout: StdioCollector {
                onStreamFinished: {
                    root.wifiEnabled = text.trim() === "enabled";
                }
            }
        }

        // =========================================
        // WIFI SIGNAL
        // =========================================

        Process {
            id: wifiSignalProcess

            command: ["nmcli", "-t", "-f", "IN-USE,SIGNAL", "dev", "wifi"]

            stdout: StdioCollector {
                onStreamFinished: {
                    const match = text.split("\n").find(line => line.startsWith("*:"));

                    root.signalPercent = match ? parseInt(match.split(":")[1]) : 0;
                }
            }
        }

        // =========================================
        // ETHERNET
        // =========================================

        Process {
            id: ethernetProcess

            command: ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]

            stdout: StdioCollector {
                onStreamFinished: {
                    const lines = text.trim().split("\n");

                    const ethernetLine = lines.find(line => line.includes(":ethernet:"));

                    if (!ethernetLine) {
                        root.ethernetConnected = false;
                        root.ethernetName = "";
                        return;
                    }

                    const parts = ethernetLine.split(":");

                    root.ethernetName = parts[0] || "";
                    root.ethernetConnected = parts[2] === "connected";
                }
            }
        }

        // =========================================
        // WIFI LINK SPEED
        // =========================================

        Process {
            id: wifiLinkProcess

            command: ["bash", "-c", "iw dev $(iw dev | awk '$1==\"Interface\"{print $2; exit}') link"]

            stdout: StdioCollector {
                onStreamFinished: {
                    const match = text.match(/rx bitrate:\s*([\d.]+)\s*MBit\/s/);

                    root.linkSpeed = match ? Math.round(parseFloat(match[1])) : "0";
                }
            }
        }

        // =========================================
        // ETHERNET SPEED
        // =========================================

        Process {
            id: ethernetSpeedProcess

            command: ["bash", "-c", "ethtool " + root.ethernetName + " 2>/dev/null"]

            stdout: StdioCollector {
                onStreamFinished: {
                    const match = text.match(/Speed:\s*([^\s]+)/);

                    if (match) {
                        root.ethernetSpeed = match[1].replace("Mb/s", "").replace("Gb/s", "000");
                    } else {
                        root.ethernetSpeed = "0";
                    }
                }
            }
        }

        // =========================================
        // UPDATE TIMER
        // =========================================

        Timer {
            interval: 500
            running: true
            repeat: true

            onTriggered: {
                wifiEnabledProcess.running = true;
                wifiSignalProcess.running = true;
                wifiLinkProcess.running = true;
                ethernetProcess.running = true;

                ethernetSpeedProcess.running = root.ethernetName !== "";
            }
        }

        Component.onCompleted: {
            wifiEnabledProcess.running = true;
            wifiSignalProcess.running = true;
            wifiLinkProcess.running = true;
            ethernetProcess.running = true;
        }

        // =========================================
        // NETWORK ICON
        // =========================================

        Item {
            id: networkIconContainer

            implicitWidth: networkIconRow.implicitWidth
            implicitHeight: networkIconRow.implicitHeight

            Layout.alignment: Qt.AlignVCenter

            RowLayout {
                id: networkIconRow

                spacing: 0

                anchors.fill: parent

                property int iconSize: 20

                // =====================================
                // ETHERNET ECG ICON
                // =====================================

                Item {
                    id: ethernetIcon

                    visible: root.ethernetMode

                    implicitWidth: networkIconRow.iconSize
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    Canvas {
                        id: ethernetWave

                        anchors.fill: parent

                        property real phase: 0

                        onPaint: {
                            const ctx = getContext("2d");

                            ctx.clearRect(0, 0, width, height);

                            const centerY = height / 2;
                            const amplitude = height * 0.42;

                            ctx.beginPath();

                            for (let x = 0; x <= width; x++) {
                                const t = (x + phase) % width;

                                let y = centerY;

                                if (t >= 5 && t < 8) {
                                    y = centerY - amplitude * 0.15;
                                } else if (t >= 8 && t < 10) {
                                    y = centerY - amplitude;
                                } else if (t >= 10 && t < 12) {
                                    y = centerY + amplitude * 0.55;
                                } else if (t >= 12 && t < 15) {
                                    y = centerY;
                                } else if (t >= 15 && t < 19) {
                                    y = centerY - amplitude * 0.25;
                                } else if (t >= 19 && t < 23) {
                                    y = centerY + amplitude * 0.20;
                                }

                                if (x === 0)
                                    ctx.moveTo(x, y);
                                else
                                    ctx.lineTo(x, y);
                            }

                            ctx.strokeStyle = Colors.white;
                            ctx.lineWidth = 1.5;
                            ctx.stroke();
                        }

                        NumberAnimation on phase {
                            from: 0
                            to: ethernetWave.width
                            duration: 900
                            loops: Animation.Infinite
                        }

                        onPhaseChanged: {
                            requestPaint();
                        }
                    }

                    Text {
                        id: ethernetPulse

                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter

                        text: "•"

                        font.pixelSize: 8
                        color: Colors.cyan

                        layer.enabled: true

                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 8
                            samples: 15
                            color: Colors.cyan
                        }
                    }
                }

                // =====================================
                // WIFI OFF
                // =====================================

                Item {
                    id: wifiOffIcon

                    visible: !root.ethernetMode && !root.wifiEnabled

                    implicitWidth: networkIconRow.iconSize
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    Text {
                        anchors.centerIn: parent

                        text: "° ๋࣭ ⭑⋆.°"

                        font.pixelSize: 15
                        color: Colors.white
                    }
                }

                // =====================================
                // DISCONNECTED
                // =====================================

                Item {
                    id: disconnectedIcon

                    visible: !root.ethernetMode && root.wifiEnabled && !root.active

                    implicitWidth: networkIconRow.iconSize
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    Text {
                        anchors.centerIn: parent

                        text: "🛰"

                        font.pixelSize: 18
                        color: Colors.white
                    }
                }

                // =====================================
                // WEAK
                // =====================================

                Item {
                    id: weakSignalIcon

                    visible: !root.ethernetMode && root.signalWeak

                    implicitWidth: networkIconRow.iconSize
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    Text {
                        anchors.centerIn: parent

                        text: "🛰"

                        font.pixelSize: 18
                        color: Colors.cyan
                    }
                }

                // =====================================
                // LOW
                // =====================================

                Item {
                    id: lowSignalIcon

                    visible: !root.ethernetMode && root.signalLow

                    implicitWidth: lowSignalRow.implicitWidth
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    RowLayout {
                        id: lowSignalRow

                        anchors.centerIn: parent

                        spacing: 0

                        Text {
                            text: "˓"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "🛰"
                            font.pixelSize: 18
                            color: Colors.cyan
                        }

                        Text {
                            text: "˒"
                            font.pixelSize: 18
                            color: Colors.white
                        }
                    }
                }

                // =====================================
                // MEDIUM
                // =====================================

                Item {
                    id: mediumSignalIcon

                    visible: !root.ethernetMode && root.signalMedium

                    implicitWidth: mediumSignalRow.implicitWidth
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    RowLayout {
                        id: mediumSignalRow

                        anchors.centerIn: parent

                        spacing: 0

                        Text {
                            text: "("
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "˓"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "🛰"
                            font.pixelSize: 18
                            color: Colors.cyan
                        }

                        Text {
                            text: "˒"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: ")"
                            font.pixelSize: 18
                            color: Colors.white
                        }
                    }
                }

                // =====================================
                // STRONG
                // =====================================

                Item {
                    id: strongSignalIcon

                    visible: !root.ethernetMode && root.signalStrong

                    implicitWidth: strongSignalRow.implicitWidth
                    implicitHeight: networkIconRow.iconSize

                    Layout.alignment: Qt.AlignVCenter

                    RowLayout {
                        id: strongSignalRow

                        anchors.centerIn: parent

                        spacing: 0

                        Text {
                            text: "("
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "﹙"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "˓"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "🛰"
                            font.pixelSize: 18
                            color: Colors.cyan
                        }

                        Text {
                            text: "˒"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: "﹚"
                            font.pixelSize: 18
                            color: Colors.white
                        }

                        Text {
                            text: ")"
                            font.pixelSize: 18
                            color: Colors.white
                        }
                    }
                }
            }

            layer.enabled: true

            layer.effect: DropShadow {
                anchors.fill: networkIconRow

                source: networkIconRow

                radius: 14
                samples: 15

                z: 2

                opacity: networkDockMouse.pressed ? 0.6 : networkDockMouse.containsMouse ? 0.8 : 1.0

                color: root.networkGlowColor

                transparentBorder: true
            }
        }

        // =========================================
        // NETWORK TEXT
        // =========================================

        RowLayout {
            id: networkTextRow

            spacing: 0

            Layout.alignment: Qt.AlignVCenter

            Text {
                id: networkOpen

                text: "("

                font.pixelSize: 20
                color: Colors.white
            }

            Text {
                id: networkText

                text: root.active ? root.active.name : "Disconnected"

                font.pixelSize: 20

                color: root.networkColor

                Layout.preferredWidth: implicitWidth
                Layout.minimumWidth: implicitWidth
                Layout.maximumWidth: implicitWidth

                elide: Text.ElideNone

                layer.enabled: true

                layer.effect: DropShadow {
                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 10
                    samples: 15

                    color: root.networkGlowColor
                }
            }

            Text {
                id: networkClose

                text: ")"

                font.pixelSize: 20
                color: Colors.white
            }

            // =====================================
            // CENTER-ALIGNED DATA COLUMN
            // =====================================

            ColumnLayout {
                id: networkDataColumn

                spacing: -3

                Layout.alignment: Qt.AlignVCenter

                // Fixed width gives both rows the exact same
                // center point.
                Layout.preferredWidth: 65
                Layout.minimumWidth: 65
                Layout.maximumWidth: 65

                Text {
                    id: networkSignalText

                    text: root.signalPercent + "%"

                    font.pixelSize: 15
                    color: Colors.white

                    // Fill the entire column.
                    Layout.fillWidth: true

                    // Center the actual text inside the column.
                    horizontalAlignment: Text.AlignHCenter

                    layer.enabled: true

                    layer.effect: DropShadow {
                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 8
                        samples: 15

                        color: root.networkGlowColor
                    }
                }

                Text {
                    id: networkSpeedText

                    text: root.linkSpeed + " Mb/s"

                    font.pixelSize: 15
                    color: Colors.white

                    // Fill the entire column.
                    Layout.fillWidth: true

                    // Center the actual text inside the column.
                    horizontalAlignment: Text.AlignHCenter

                    layer.enabled: true

                    layer.effect: DropShadow {
                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 8
                        samples: 15

                        color: root.networkGlowColor
                    }
                }
            }
        }
    }

    // =============================================
    // MOUSE
    // =============================================

    MouseArea {
        id: networkDockMouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {
            if (mouse.button === Qt.LeftButton) {
                Quickshell.execDetached(["nm-connection-editor"]);
            }

            if (mouse.button === Qt.RightButton) {
                root.ethernetMode = !root.ethernetMode;
            }
        }
    }

    // =============================================
    // SHADOWS
    // =============================================

    RectangularShadow {
        anchors.fill: parent

        spread: 3

        z: -1

        opacity: networkDockMouse.pressed ? 0.6 : networkDockMouse.containsMouse ? 0.5 : 0.4

        color: root.networkGlowColor
    }

    RectangularShadow {
        anchors.fill: parent

        spread: 10

        z: 1

        opacity: networkDockMouse.pressed ? 0.12 : networkDockMouse.containsMouse ? 0.09 : 0.07

        color: root.networkGlowColor
    }
}
