import QtQuick
import QtQuick.Window
import Quickshell
import "../../widgets" as FinanceWidgets

// M24: a SEPARATE Qt test window hosting the REAL Market quota pane.
// All numbers come from disposable M20 SQLite -> M21 reader fixtures.
// Quickshell.Io Process is replaced in a TEMPORARY import directory and
// cannot call real Quickshell, the canonical ledger or any provider.
Window {
    id: fixture
    objectName: "marketM24VisualFixture"
    width: 750
    height: 645
    minimumWidth: 350
    minimumHeight: 380
    visible: true
    color: "#16051F"
    title: "FINANCEW MARKET M24 // ISOLATED TEST // NOT LIVE QUOTA"

    property string lowPayload: ""
    property string fullPayload: ""
    property string zeroPayload: ""
    property string absentPayload: ""
    property string unavailablePayload: ""
    property string selectedCase: "LOW"
    property int backCount: 0
    readonly property int requestCount: Quickshell.callCount
    readonly property string lastCommand: Quickshell.lastCommand
    readonly property bool paneOpened: realPane.active && realPane.visible

    function payloadFor(choice) {
        switch (choice) {
        case "LOW": return lowPayload;
        case "FULL": return fullPayload;
        case "ZERO": return zeroPayload;
        case "ABSENT": return absentPayload;
        case "UNAVAILABLE": return unavailablePayload;
        default: return "";
        }
    }

    function openCase() {
        const reply = payloadFor(selectedCase);
        if (!reply || reply.indexOf("FINANCE_QUOTA_STATUS ") !== 0)
            return false;
        // Fake process never executes. Each scenario restarts the same REAL
        // reader service in a detached test window; the canonical UI is
        // untouched, with no M21 production test mode or bypass.
        Quickshell.nextPayload = reply;
        realPane.active = false;
        realPane.visible = true;
        realPane.active = true;
        return true;
    }
    function simulateBack() {
        realPane.active = false;
        realPane.visible = false;
        backCount += 1;
    }

    Rectangle {
        id: testBanner
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        color: "#301034"
        border.color: "#F3A851"
        border.width: 2
        Text {
            anchors.centerIn: parent
            width: parent.width - 16
            text: "M24 DISPOSABLE SQLITE TEST // NOT YOUR REAL QUOTA OR API ACCOUNT"
            color: "#F3A851"
            font.pixelSize: 12
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    Row {
        id: controls
        anchors.top: testBanner.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 10
        height: 32
        spacing: 6
        Repeater {
            model: ["LOW", "FULL", "ZERO", "ABSENT", "UNAVAILABLE"]
            delegate: Rectangle {
                required property string modelData
                width: Math.max(46, (controls.width - 24) / 5)
                height: controls.height
                color: fixture.selectedCase === modelData
                    ? "#432746" : "#1B0623"
                border.width: 1
                border.color: fixture.selectedCase === modelData
                    ? "#F3A851" : "#55CFCA"
                Text {
                    anchors.centerIn: parent
                    text: modelData
                    color: "#DCF3FA"
                    font.pixelSize: controls.width < 570 ? 8 : 11
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        fixture.selectedCase = modelData;
                        fixture.openCase();
                    }
                }
            }
        }
    }

    FinanceWidgets.FinanceMarketQuotaStatusPane {
        id: realPane
        x: 9
        y: controls.y + controls.height + 8
        width: parent.width - 18
        height: Math.max(180, bottomText.y - y - 8)
        visible: false
        active: false
        onExitRequested: fixture.simulateBack()
    }

    Rectangle {
        id: closedIndicator
        x: realPane.x
        y: realPane.y
        width: realPane.width
        height: realPane.height
        color: "#16051F"
        visible: !realPane.visible
        Text {
            anchors.centerIn: parent
            width: parent.width - 25
            text: "BACK TO STOCKS was received by the test harness.\n" +
                  "Choose a fixture case above to reopen the REAL quota pane."
            color: "#55CFCA"
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            font.pixelSize: 13
        }
    }

    Text {
        id: bottomText
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        text: "TEMP SQLITE + REAL M20/M21 READ // FAKE QUICKSHELL PROCESS // " +
              "NO PROVIDER REQUESTS"
        color: "#F3A851"
        font.pixelSize: 9
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }
}
