import QtQuick
import "../../components"

// Stage 8D: passive Level 2 projection of Hub's normalized link snapshot.
// The parent still owns the same single Quickshell.Networking observation.
Item {
    id: networkExplore
    property var networkSnapshot: null
    property string selectedView: "status"
    readonly property int densityLevel: height >= 300 ? 3 : 2
    readonly property string networkState:
        networkSnapshot && networkSnapshot.state
        ? String(networkSnapshot.state) : "unavailable"
    readonly property bool connected:
        networkState === "connected" && networkSnapshot !== null
        && networkSnapshot.connected === true
    readonly property string transport:
        connected ? String(networkSnapshot.transport || "none") : "none"
    readonly property bool networkKnown:
        networkState === "connected" || networkState === "disconnected"
    readonly property var wifi:
        networkKnown && networkSnapshot && networkSnapshot.wifi
        ? networkSnapshot.wifi : null
    readonly property var ethernet:
        networkKnown && networkSnapshot && networkSnapshot.ethernet
        ? networkSnapshot.ethernet : null
    readonly property bool wifiPresent: wifi !== null && wifi.present === true
    readonly property bool wifiConnected: wifiPresent && wifi.connected === true
    readonly property bool ethernetPresent:
        ethernet !== null && ethernet.present === true
    readonly property bool ethernetConnected:
        ethernetPresent && ethernet.connected === true
    readonly property string wifiName:
        wifiConnected && typeof wifi.networkName === "string"
        && wifi.networkName.length > 0 ? wifi.networkName : "NETWORK NAME UNKNOWN"
    readonly property string wifiInterface:
        wifiPresent && typeof wifi.interfaceName === "string"
        && wifi.interfaceName.length > 0 ? wifi.interfaceName : "UNKNOWN"
    readonly property string ethernetInterface:
        ethernetPresent && typeof ethernet.interfaceName === "string"
        && ethernet.interfaceName.length > 0 ? ethernet.interfaceName : "UNKNOWN"
    readonly property string signalText: {
        if (!wifiConnected)
            return "--";
        const value = wifi.signalPercent;
        return typeof value === "number" && isFinite(value)
               && value >= 0 && value <= 100
               ? String(value) + "%" : "--";
    }
    readonly property string wifiSpeedText: {
        if (!wifiConnected || transport !== "wifi"
                || networkSnapshot.linkSpeedApproximate !== true)
            return "--";
        const value = networkSnapshot.linkSpeedMbps;
        return typeof value === "number" && isFinite(value)
               && value > 0 ? String(value) + " Mb/s" : "--";
    }
    readonly property string wifiLinkText:
        !networkKnown ? "UNKNOWN" : !wifiPresent ? "NOT PRESENT"
        : wifiConnected ? "CONNECTED" : "DISCONNECTED"
    readonly property string ethernetLinkText:
        !networkKnown ? "UNKNOWN" : !ethernetPresent ? "NOT PRESENT"
        : ethernetConnected ? "CONNECTED" : "DISCONNECTED"
    readonly property string statusLine:
        "NETWORK // " + selectedView.toUpperCase()
        + " // " + (connected ? "LOCAL LINK CONNECTED"
            : networkState.toUpperCase()) + " // INTERNET UNVERIFIED"
    readonly property string heading:
        selectedView === "wifi" ? "WI-FI // LOCAL LINK"
        : selectedView === "ethernet" ? "ETHERNET // LOCAL LINK"
        : "NETWORK // STATUS"
    readonly property string primary:
        selectedView === "wifi"
        ? (!networkKnown ? "UNAVAILABLE" : !wifiPresent ? "NOT PRESENT"
           : wifiConnected ? "CONNECTED" : "DISCONNECTED")
        : selectedView === "ethernet"
        ? (!networkKnown ? "UNAVAILABLE" : !ethernetPresent ? "NOT PRESENT"
           : ethernetConnected ? "CONNECTED" : "DISCONNECTED")
        : !networkKnown ? "UNAVAILABLE"
        : !connected ? "NO LOCAL LINK"
        : transport === "ethernet" ? "ETHERNET"
        : transport === "wifi" ? "WI-FI" : "NO LOCAL LINK"
    readonly property string detailOne:
        selectedView === "wifi"
        ? "SSID // " + (wifiConnected ? wifiName : "--")
        : selectedView === "ethernet"
        ? "INTERFACE // " + ethernetInterface
        : "ACTIVE // " + (connected ? transport.toUpperCase() : "NONE")
    readonly property string detailTwo:
        selectedView === "wifi"
        ? "INTERFACE // " + wifiInterface
        : selectedView === "ethernet"
        ? "WIRED SPEED // NOT OBSERVED"
        : "WI-FI LINK // " + wifiLinkText
    readonly property string detailThree:
        selectedView === "wifi"
        ? "SIGNAL // " + signalText
        : selectedView === "ethernet"
        ? "LINK // " + ethernetLinkText
        : "ETHERNET LINK // " + ethernetLinkText
    readonly property string detailFour:
        selectedView === "wifi"
        ? "WI-FI RX LINK RATE // " + wifiSpeedText + " (APPROX)"
        : "INTERNET // UNVERIFIED"

    Row {
        id: viewSelector
        width: parent.width
        height: networkExplore.densityLevel === 3 ? 32 : 27
        spacing: 4
        Repeater {
            model: ["STATUS", "WI-FI", "ETHERNET"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(1, (viewSelector.width
                                    - 2 * viewSelector.spacing) / 3)
                height: viewSelector.height
                label: modelData
                labelPixelSize: 11
                selected: (modelData === "WI-FI" ? "wifi"
                          : modelData.toLowerCase()) === networkExplore.selectedView
                trackLabelGlowLocally: true
                softGlowEnabled: false
                onLeftClicked: networkExplore.selectedView =
                               modelData === "WI-FI" ? "wifi" : modelData.toLowerCase()
            }
        }
    }
    Item {
        anchors.top: viewSelector.bottom
        anchors.topMargin: 6
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        Column {
            width: parent.width
            height: childrenRect.height
            anchors.centerIn: parent
            spacing: networkExplore.densityLevel === 3 ? 12 : 6
            GohuText {
                width: parent.width
                height: networkExplore.densityLevel === 3 ? 31 : 23
                font.pixelSize: networkExplore.densityLevel === 3 ? 18 : 14
                color: Colors.magenta
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: networkExplore.heading
            }
            GohuText {
                width: parent.width
                height: networkExplore.densityLevel === 3 ? 52 : 39
                font.pixelSize: networkExplore.densityLevel === 3 ? 34 : 25
                color: networkExplore.connected ? Colors.white : Colors.orange
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: networkExplore.primary
            }
            Repeater {
                model: [networkExplore.detailOne, networkExplore.detailTwo,
                        networkExplore.detailThree, networkExplore.detailFour]
                delegate: GohuText {
                    required property string modelData
                    width: parent.width
                    height: networkExplore.densityLevel === 3 ? 28 : 22
                    font.pixelSize: networkExplore.densityLevel === 3 ? 15 : 12
                    color: index === 3 ? Colors.orange : Colors.cyan
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: modelData
                }
            }
        }
    }
}
