import QtQuick
import "../components"
import "FinanceTransferGuidePolicy.js" as TransferGuidePolicy

// Offline guidance and fictional examples, never a linked account or payment writer.
Item {
    id: guide
    property bool expanded: false
    property int sourceIndex: 0
    property int destinationIndex: 1
    property var preview: null
    readonly property var demoAccounts: TransferGuidePolicy.accounts()
    readonly property var example: TransferGuidePolicy.spendingSummary(
        TransferGuidePolicy.demoActivity())
    readonly property string sourceId: demoAccounts[sourceIndex].id
    readonly property string destinationId: demoAccounts[destinationIndex].id

    width: parent ? parent.width : 0
    height: content.implicitHeight

    function clearPlan() { preview = null; }
    onSourceIndexChanged: clearPlan()
    onDestinationIndexChanged: clearPlan()
    onExpandedChanged: {
        if (!expanded) {
            preview = null;
            amountInput.text = "";
        }
    }

    Column {
        id: content
        width: guide.width
        spacing: 7
        ActionButton {
            width: parent.width
            height: 30
            label: guide.expanded ? "TRANSFER HELP // CLOSE DEMO"
                                  : "TRANSFER HELP // OPEN DEMO"
            labelPixelSize: 9
            accentColor: Colors.cyan
            trackLabelGlowLocally: true
            onLeftClicked: guide.expanded = !guide.expanded
        }
        GohuText {
            width: parent.width
            visible: guide.expanded
            text: "GUIDANCE ONLY // NO ACCOUNTS CONNECTED // NO PAYMENT EXECUTED"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: guide.expanded
            text: "Choose fictional accounts to preview how a real transfer works. Complete real actions in the official provider app."
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.white
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 30
            visible: guide.expanded
            label: "FROM // DEMO " + guide.demoAccounts[guide.sourceIndex].name.toUpperCase()
            labelPixelSize: 9
            accentColor: Colors.magenta
            trackLabelGlowLocally: true
            onLeftClicked: guide.sourceIndex = (guide.sourceIndex + 1) % guide.demoAccounts.length
        }
        ActionButton {
            width: parent.width
            height: 30
            visible: guide.expanded
            label: "TO // DEMO " + guide.demoAccounts[guide.destinationIndex].name.toUpperCase()
            labelPixelSize: 9
            accentColor: Colors.omnitrix
            trackLabelGlowLocally: true
            onLeftClicked: guide.destinationIndex = (guide.destinationIndex + 1) % guide.demoAccounts.length
        }
        Rectangle {
            width: parent.width
            height: 32
            visible: guide.expanded
            color: Colors.black
            border.color: Colors.cyan
            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "AMOUNT $"
                font.pixelSize: 9
                color: Colors.cyan
            }
            TextInput {
                id: amountInput
                anchors.left: parent.left
                anchors.leftMargin: 82
                anchors.right: parent.right
                anchors.rightMargin: 5
                anchors.verticalCenter: parent.verticalCenter
                height: 25
                text: ""
                color: Colors.white
                font.pixelSize: 12
                selectByMouse: true
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextChanged: guide.clearPlan()
            }
        }
        ActionButton {
            width: parent.width
            height: 30
            visible: guide.expanded
            label: "PREVIEW TRANSFER INSTRUCTIONS"
            labelPixelSize: 9
            accentColor: Colors.orange
            trackLabelGlowLocally: true
            onLeftClicked: guide.preview = TransferGuidePolicy.transferPlan(
                guide.sourceId, guide.destinationId, amountInput.text)
        }
        GohuText {
            width: parent.width
            visible: guide.expanded && !!guide.preview
            text: !guide.preview ? ""
                : guide.preview.ok
                  ? guide.preview.amountText + " // " + guide.preview.sourceName
                    + " TO " + guide.preview.destinationName + " // NOT SENT"
                  : guide.preview.error
            textFormat: Text.PlainText
            font.pixelSize: 10
            color: guide.preview && guide.preview.ok ? Colors.cyan : Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: guide.expanded && guide.preview && guide.preview.ok
            text: "FEES // CHECK IN PROVIDER    ARRIVAL // CHECK IN PROVIDER"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: guide.expanded && guide.preview && guide.preview.ok
                   ? guide.preview.steps : []
            delegate: GohuText {
                required property string modelData
                required property int index
                width: content.width
                text: (index + 1) + ". " + modelData
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
        }
        GohuText {
            width: parent.width
            visible: guide.expanded
            text: "FICTIONAL SPENDING EXAMPLE // "
                  + TransferGuidePolicy.moneyText(guide.example.expensesCents)
                  + " SPENT, " + guide.example.matchedInternalTransferPairs
                  + " MATCHED INTERNAL TRANSFER"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.omnitrix
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: guide.expanded
            text: "Sample: $75 moved from Chime to Cash App is not another $75 expense. No real transaction or balance data is read or stored."
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.WordWrap
        }
    }
}
