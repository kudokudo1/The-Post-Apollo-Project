import QtQuick
import "../components"

// Research M7: inspect M6's verified *shape* of an in-memory preview.
// No Process, provider requests, URL launch, editor mutation or storage write.
Item {
    id: picker
    property var candidatePreview: null
    property string loadState: "idle"
    property string statusMessage: "SOURCE CANDIDATES NOT LOADED"
    property bool controllerConnected: false
    property string filterMode: "all" // all, sec, demo
    property string selectedKey: ""

    readonly property var candidates: candidatePreview
        && Array.isArray(candidatePreview.candidates)
        ? candidatePreview.candidates : []
    readonly property var filteredCandidates:
        filterMode === "all" ? candidates
        : candidates.filter(function(item) {
            return filterMode === "sec" ? item.kind === "sec-index"
                   : item.kind === "demo-crawl";
        })
    readonly property var selectedCandidate: {
        for (let i = 0; i < candidates.length; ++i) {
            if (candidates[i].key === selectedKey)
                return candidates[i];
        }
        return null;
    }
    readonly property bool canReload: controllerConnected
        && loadState !== "loading"
    signal previewRequested()

    onCandidatePreviewChanged: {
        // A source refresh or issuer switch invalidates old keys.
        let stillPresent = false;
        for (let i = 0; i < candidates.length; ++i) {
            if (candidates[i].key === selectedKey) {
                stillPresent = true;
                break;
            }
        }
        if (!stillPresent) selectedKey = "";
    }
    onFilterModeChanged: {
        if (selectedCandidate && filterMode !== "all"
                && selectedCandidate.kind !==
                    (filterMode === "sec" ? "sec-index" : "demo-crawl"))
            selectedKey = "";
    }

    NeonScrollPaneV2 {
        id: scroll
        anchors.fill: parent
        availableExtent: height
        contentExtent: body.implicitHeight + 22
        viewportPolicy: "fill"
        handleStyle: "bar"

        Column {
            id: body
            x: 8
            y: 8
            width: Math.max(0, scroll.width - 32)
            spacing: 9

            GohuText {
                width: parent.width
                text: "RESEARCH // EVIDENCE CANDIDATES"
                color: Colors.magenta
                font.pixelSize: 13
                font.bold: true
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: picker.statusMessage
                color: picker.loadState === "failed" ? Colors.red
                    : Colors.orange
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "CURRENT SEC/Crawl SNAPSHOTS ONLY // NO NEW REQUESTS"
                color: Colors.cyan
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                spacing: 5
                ActionButton {
                    width: 105
                    height: 28
                    label: picker.loadState === "loading"
                        ? "VALIDATING" : "BUILD PREVIEW"
                    labelPixelSize: 9
                    available: picker.canReload
                    onLeftClicked: picker.previewRequested()
                }
                ActionButton {
                    width: 51
                    height: 28
                    label: "ALL"
                    labelPixelSize: 9
                    selected: picker.filterMode === "all"
                    onLeftClicked: picker.filterMode = "all"
                }
                ActionButton {
                    width: 56
                    height: 28
                    label: "SEC"
                    labelPixelSize: 9
                    selected: picker.filterMode === "sec"
                    onLeftClicked: picker.filterMode = "sec"
                }
                ActionButton {
                    width: 62
                    height: 28
                    label: "DEMO"
                    labelPixelSize: 9
                    selected: picker.filterMode === "demo"
                    accentColor: Colors.orange
                    onLeftClicked: picker.filterMode = "demo"
                }
            }
            GohuText {
                width: parent.width
                text: "SEC INDEX "
                    + (picker.candidatePreview
                       ? picker.candidatePreview.counts.sec : 0)
                    + " // DEMO "
                    + (picker.candidatePreview
                       ? picker.candidatePreview.counts.demo : 0)
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                visible: picker.filteredCandidates.length === 0
                text: picker.loadState === "loading"
                    ? "VALIDATING EXISTING SNAPSHOTS"
                    : "NO CANDIDATES IN THIS VIEW"
                color: Colors.orange
                font.pixelSize: 10
                textFormat: Text.PlainText
            }
            Repeater {
                model: picker.filteredCandidates
                delegate: ActionButton {
                    id: candidateRow
                    required property var modelData
                    width: body.width
                    height: 36
                    label: modelData.title
                    labelItem.textFormat: Text.PlainText
                    labelPixelSize: 10
                    selected: picker.selectedKey === modelData.key
                    accentColor: modelData.kind === "sec-index"
                        ? Colors.cyan : Colors.orange
                    onLeftClicked: picker.selectedKey = modelData.key
                }
            }
            Rectangle {
                width: body.width
                height: detail.implicitHeight + 18
                color: Colors.black
                border.width: 1
                border.color: picker.selectedCandidate
                    && picker.selectedCandidate.kind === "sec-index"
                    ? Colors.cyan : Colors.orange

                Column {
                    id: detail
                    x: 9
                    y: 9
                    width: Math.max(0, parent.width - 18)
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              ? picker.selectedCandidate.sourceLabel
                              : "SELECT A SOURCE TO REVIEW"
                        color: Colors.magenta
                        font.pixelSize: 11
                        font.bold: true
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              ? picker.selectedCandidate.summary
                              : "Only candidate metadata is shown here."
                        color: Colors.white
                        font.pixelSize: 10
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              ? picker.selectedCandidate.url : ""
                        color: Colors.cyan
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                    }
                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              ? "OBSERVED // "
                                  + picker.selectedCandidate.observedAt
                              : ""
                        color: Colors.white
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              ? picker.selectedCandidate.notice
                              : "NO SOURCE INSPECTED"
                        color: Colors.orange
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: picker.selectedCandidate
                              && picker.selectedCandidate.kind === "demo-crawl"
                              ? "DEMO DATA // CANNOT ATTACH TO FINANCIAL RESEARCH"
                              : "READ ONLY // NO EVIDENCE SAVE AVAILABLE"
                        color: Colors.orange
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "PREVIEW ONLY // SOURCE CONTENT NOT AUTHENTICATED // NO WRITES"
                color: Colors.orange
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
    }
}
