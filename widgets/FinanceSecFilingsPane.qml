import QtQuick
import "../components"
import "FinanceSecEvidencePolicy.js" as EvidencePolicy

// FinanceW Research SEC M2: official EDGAR issuer filings, not trade signals.
// Source dates are filing dates; transaction direction is not inferred.
Item {
    id: pane
    property var secFeed: null
    property var documentFeed: null
    property int selectedIndex: 0
    property string filterMode: "all"
    property var pinnedEvidence: []
    property string pinMessage: "PIN TWO INSPECTED FILINGS TO COMPARE"
    readonly property bool wide: width >= 650
    readonly property var filings: secFeed && secFeed.snapshot ? secFeed.snapshot.filings : []
    readonly property var filteredFilings: EvidencePolicy.filterFilings(filings, filterMode)
    readonly property var selected: selectedIndex >= 0 && selectedIndex < filteredFilings.length
                                     ? filteredFilings[selectedIndex] : null

    function pinCurrentEvidence() {
        if (!secFeed || !secFeed.snapshot || !documentFeed
                || documentFeed.state !== "ready" || !selected)
            return false;
        const slots = EvidencePolicy.pinEvidence(
            pinnedEvidence, selected, documentFeed.snapshot, secFeed.snapshot.cik);
        if (!slots) return false;
        pinnedEvidence = slots;
        pinMessage = slots.length === 2
            ? "TWO FILINGS PINNED // COMPARE AVAILABLE"
            : "ONE FILING PINNED // INSPECT ANOTHER";
        return true;
    }

    function clearEvidence() {
        pinnedEvidence = [];
        pinMessage = "PIN TWO INSPECTED FILINGS TO COMPARE";
    }
    onFilingsChanged: {
        selectedIndex = 0;
        clearEvidence();
        if (documentFeed) documentFeed.clear();
    }
    onFilterModeChanged: {
        selectedIndex = 0;
        if (documentFeed) documentFeed.clear();
    }
    onSelectedIndexChanged: {
        if (documentFeed) documentFeed.clear();
    }

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: refreshButton.left
        anchors.rightMargin: 6
        text: "SEC EDGAR // DISCLOSURES"
        font.pixelSize: 13
        font.bold: true
        color: Colors.orange
        elide: Text.ElideRight
    }

    ActionButton {
        id: refreshButton
        anchors.top: parent.top
        anchors.topMargin: 4
        anchors.right: parent.right
        width: 78
        height: 28
        label: secFeed && secFeed.loading ? "READING" : "REFRESH"
        labelPixelSize: 9
        accentColor: Colors.cyan
        available: secFeed && secFeed.monitoring && !secFeed.loading
        onLeftClicked: secFeed.refresh()
    }

    Row {
        id: issuerRow
        anchors.top: title.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.right: parent.right
        height: 31
        spacing: 5
        ActionButton {
            width: Math.max(70, (issuerRow.width - 10) / 3)
            height: 28
            label: "APPLE"
            labelPixelSize: 9
            selected: secFeed && secFeed.selectedCik === "0000320193"
            accentColor: Colors.cyan
            onLeftClicked: secFeed.selectIssuer("0000320193")
        }
        ActionButton {
            width: Math.max(70, (issuerRow.width - 10) / 3)
            height: 28
            label: "MICROSOFT"
            labelPixelSize: 9
            selected: secFeed && secFeed.selectedCik === "0000789019"
            accentColor: Colors.cyan
            onLeftClicked: secFeed.selectIssuer("0000789019")
        }
        ActionButton {
            width: Math.max(70, (issuerRow.width - 10) / 3)
            height: 28
            label: "NVIDIA"
            labelPixelSize: 9
            selected: secFeed && secFeed.selectedCik === "0001045810"
            accentColor: Colors.cyan
            onLeftClicked: secFeed.selectIssuer("0001045810")
        }
    }

    GohuText {
        id: status
        anchors.top: issuerRow.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        text: secFeed ? secFeed.message : "SEC SOURCE UNAVAILABLE"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: secFeed && secFeed.state === "failed" ? Colors.red : Colors.orange
        wrapMode: Text.WordWrap
    }

    GohuText {
        id: counts
        anchors.top: status.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        text: "FILINGS " + pane.filteredFilings.length + " / " + pane.filings.length
              + "  //  " + (secFeed && secFeed.snapshot ? secFeed.snapshot.issuer : "NO ISSUER DATA")
        textFormat: Text.PlainText
        font.pixelSize: 10
        color: Colors.white
        elide: Text.ElideRight
    }

    Row {
        id: filterRow
        anchors.top: counts.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        height: 27
        spacing: 4
        Repeater {
            model: [
                {key: "all", label: "ALL"},
                {key: "insider", label: "INSIDER"},
                {key: "events", label: "8-K"},
                {key: "owners", label: "OWNERS"},
                {key: "reports", label: "REPORTS"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(46, (filterRow.width - 16) / 5)
                height: 25
                label: modelData.label
                labelPixelSize: 9
                selected: pane.filterMode === modelData.key
                accentColor: Colors.cyan
                onLeftClicked: pane.filterMode = modelData.key
            }
        }
    }

    Item {
        id: body
        anchors.top: filterRow.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 6

        Rectangle {
            id: filingList
            anchors.top: parent.top
            anchors.left: parent.left
            width: pane.wide ? Math.max(230, parent.width * 0.38) : parent.width
            height: pane.wide ? parent.height : Math.max(130, parent.height * 0.48)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            GohuText {
                id: listTitle
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 7
                font.pixelSize: 10
                color: Colors.white
                text: "OFFICIAL FILING INDEX"
            }
            Flickable {
                id: filingScroll
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: listTitle.bottom
                anchors.bottom: parent.bottom
                anchors.margins: 4
                clip: true
                contentWidth: width
                contentHeight: filingRows.height
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: filingRows
                    width: filingScroll.width
                    spacing: 3
                    Repeater {
                        model: pane.filteredFilings
                        delegate: Rectangle {
                            id: filingRow
                            required property var modelData
                            required property int index
                            width: filingRows.width
                            height: 60
                            color: pane.selectedIndex === index ? Colors.dark : Colors.black
                            border.width: 1
                            border.color: pane.selectedIndex === index ? Colors.magenta : Colors.cyan
                            GohuText {
                                anchors.top: parent.top
                                anchors.topMargin: 7
                                anchors.left: parent.left
                                anchors.leftMargin: 6
                                text: filingRow.modelData.form + " // " + filingRow.modelData.category
                                font.pixelSize: 10
                                color: Colors.white
                            }
                            GohuText {
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 6
                                anchors.left: parent.left
                                anchors.leftMargin: 6
                                text: filingRow.modelData.filedAt
                                font.pixelSize: 10
                                color: Colors.orange
                            }
                            GohuText {
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 6
                                anchors.right: parent.right
                                anchors.rightMargin: 6
                                text: filingRow.modelData.accession
                                font.pixelSize: 9
                                color: Colors.cyan
                            }
                            TapHandler {
                                onTapped: pane.selectedIndex = filingRow.index
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            id: detail
            anchors.top: pane.wide ? parent.top : filingList.bottom
            anchors.topMargin: pane.wide ? 0 : 8
            anchors.left: pane.wide ? filingList.right : parent.left
            anchors.leftMargin: pane.wide ? 8 : 0
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true
            FinanceSecDocumentInspector {
                anchors.fill: parent
                filing: pane.selected
                secFeed: pane.secFeed
                documentFeed: pane.documentFeed
                evidenceSlots: pane.pinnedEvidence
                pinMessage: pane.pinMessage
                onPinRequested: pane.pinCurrentEvidence()
                onClearRequested: pane.clearEvidence()
            }
        }
    }

    GohuText {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 25
        text: "SEC DATA.SEC.GOV // PUBLIC SNAPSHOT // NOT LIVE"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: Colors.orange
        elide: Text.ElideRight
    }
}
