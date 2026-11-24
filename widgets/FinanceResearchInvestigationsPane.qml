import QtQuick
import "../components"

// Research M3: isolated investigation screen, no file access or side effects.
// Its future controller must supply validated rows and explicit write callbacks.
Item {
    id: pane
    property var investigations: []
    property string loadState: "preview" // preview, loading, ready, pending, failed
    property string statusMessage: "INTERFACE PREVIEW // STORAGE NOT CONNECTED"
    property bool controllerConnected: false
    property bool writeEnabled: false
    property bool scratchEnabled: false // optional in-memory workflow, never writer authority
    property bool scratchAppendReady: false // validated prepared SEC citation only
    property string scratchId: ""
    property string selectedId: ""
    property string draftTitle: ""
    property string draftQuestion: ""
    property string draftSource: "manual"
    property string draftEvidenceTitle: ""
    property string draftEvidenceUrl: ""
    property string draftEvidenceSummary: ""
    property string armedRemoveId: ""
    property bool showNewForm: false
    readonly property bool wide: width >= 640
    readonly property var selectedInvestigation: {
        for (let i = 0; i < investigations.length; ++i) {
            if (investigations[i].id === selectedId)
                return investigations[i];
        }
        return null;
    }
    readonly property bool canCreate: controllerConnected && writeEnabled && loadState === "ready"
        && draftTitle.trim().length > 0 && draftTitle.length <= 160
        && draftQuestion.trim().length > 0 && draftQuestion.length <= 1000
    readonly property bool canCreateScratch: scratchEnabled && controllerConnected
        && scratchId === ""
        && draftTitle.trim().length > 0 && draftTitle.trim().length <= 160
        && draftQuestion.trim().length > 0 && draftQuestion.trim().length <= 1000
    readonly property bool canAttach: controllerConnected && writeEnabled && loadState === "ready"
        && selectedInvestigation !== null
        && draftEvidenceTitle.trim().length > 0 && draftEvidenceTitle.length <= 160
        && draftEvidenceSummary.trim().length > 0 && draftEvidenceSummary.length <= 2000
        && /^https:\/\/[^\s]+$/.test(draftEvidenceUrl)
    signal loadRequested()
    signal createRequested(string title, string question)
    signal createScratchRequested(string title, string question)
    signal discardScratchRequested()
    signal appendScratchRequested(string title, string summary, string url)
    signal attachRequested(string investigationId, string source, string title,
                           string summary, string url)
    signal removeRequested(string investigationId, string evidenceId)
    onInvestigationsChanged: {
        if (!investigations.some(function(x) { return x.id === selectedId; }))
            selectedId = investigations.length ? investigations[0].id : "";
        armedRemoveId = "";
    }
    onSelectedIdChanged: {
        armedRemoveId = "";
        draftEvidenceTitle = "";
        draftEvidenceSummary = "";
        draftEvidenceUrl = "";
    }

    NeonScrollPaneV2 {
        id: scroll
        anchors.fill: parent
        availableExtent: height
        contentExtent: body.implicitHeight + 18
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
                text: "RESEARCH // INVESTIGATIONS"
                font.pixelSize: 13
                font.bold: true
                color: Colors.magenta
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                text: pane.statusMessage
                color: pane.loadState === "failed" ? Colors.red : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                text: "LOCAL RESEARCH ONLY // SOURCES ARE NOT VERIFIED FINANCIAL ADVICE"
                color: Colors.cyan
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                spacing: 6
                ActionButton {
                    width: 95
                    height: 28
                    label: "LOAD CASES"
                    labelPixelSize: 9
                    available: pane.controllerConnected && pane.loadState !== "loading" && pane.loadState !== "pending"
                    onLeftClicked: pane.loadRequested()
                }
                ActionButton {
                    width: 100
                    height: 28
                    label: pane.scratchEnabled
                        ? (pane.showNewForm ? "CANCEL" : "NEW SCRATCH")
                        : (pane.showNewForm ? "CANCEL NEW" : "NEW CASE")
                    labelPixelSize: 9
                    available: pane.controllerConnected
                        && (pane.scratchEnabled ? pane.scratchId === ""
                            : pane.writeEnabled && pane.loadState === "ready")
                    accentColor: Colors.magenta
                    onLeftClicked: pane.showNewForm = !pane.showNewForm
                }
                GohuText {
                    text: "CASES " + pane.investigations.length
                    font.pixelSize: 10
                    color: Colors.white
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            ActionButton {
                width: 115
                height: 28
                label: "DISCARD SCRATCH"
                labelPixelSize: 9
                accentColor: Colors.red
                visible: pane.scratchEnabled && pane.scratchId !== ""
                available: visible
                onLeftClicked: pane.discardScratchRequested()
            }
            Rectangle {
                width: parent.width
                height: newForm.implicitHeight + 16
                visible: pane.showNewForm
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                Column {
                    id: newForm
                    x: 8
                    y: 8
                    width: parent.width - 16
                    spacing: 7
                    GohuText {
                        text: pane.scratchEnabled
                            ? "SCRATCH INVESTIGATION // MEMORY ONLY"
                            : "NEW INVESTIGATION"
                        color: Colors.magenta
                        font.pixelSize: 11
                    }
                    Rectangle {
                        width: parent.width
                        height: 31
                        color: Colors.dark
                        border.color: Colors.cyan
                        TextInput {
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Colors.white
                            font.pixelSize: 11
                            clip: true
                            text: pane.draftTitle
                            onTextEdited: pane.draftTitle = text
                        }
                    }
                    GohuText {
                        text: "RESEARCH QUESTION"
                        font.pixelSize: 9
                        color: Colors.white
                    }
                    Rectangle {
                        width: parent.width
                        height: 65
                        color: Colors.dark
                        border.color: Colors.cyan
                        TextEdit {
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Colors.white
                            font.pixelSize: 11
                            wrapMode: TextEdit.Wrap
                            clip: true
                            text: pane.draftQuestion
                            onTextChanged: if (activeFocus) pane.draftQuestion = text
                        }
                    }
                    ActionButton {
                        width: 115
                        height: 29
                        label: pane.scratchEnabled ? "CREATE SCRATCH" : "CREATE CASE"
                        accentColor: Colors.magenta
                        available: pane.scratchEnabled
                            ? pane.canCreateScratch : pane.canCreate
                        onLeftClicked: {
                            if (pane.scratchEnabled) {
                                // This signal is local only; never route to createRequested.
                                pane.createScratchRequested(
                                    pane.draftTitle.trim(), pane.draftQuestion.trim());
                            } else {
                                // Only a verified writer could clear the persistent form.
                                pane.createRequested(
                                    pane.draftTitle.trim(), pane.draftQuestion.trim());
                            }
                        }
                    }
                }
            }
            Grid {
                width: parent.width
                columns: pane.wide ? 2 : 1
                columnSpacing: 9
                rowSpacing: 9
                Rectangle {
                    width: pane.wide ? (body.width - 9) / 2 : body.width
                    height: Math.max(160, casesList.implicitHeight + 20)
                    color: Colors.black
                    border.color: Colors.cyan
                    Column {
                        id: casesList
                        x: 9
                        y: 9
                        width: parent.width - 18
                        spacing: 7
                        GohuText {
                            text: pane.scratchId !== ""
                                ? "INVESTIGATIONS // SCRATCH UNSAVED"
                                : "SAVED INVESTIGATIONS"
                            color: Colors.cyan
                            font.pixelSize: 11
                            font.bold: true
                        }
                        GohuText {
                            visible: pane.investigations.length === 0
                            width: parent.width
                            text: pane.scratchEnabled
                                ? "NO CASES YET // USE NEW SCRATCH"
                                : "NO INVESTIGATIONS LOADED"
                            color: Colors.orange
                            font.pixelSize: 10
                        }
                        Repeater {
                            model: pane.investigations
                            delegate: ActionButton {
                                required property var modelData
                                width: casesList.width
                                height: 37
                                label: modelData.id === pane.scratchId
                                    ? "[UNSAVED] " + modelData.title
                                    : modelData.title
                                labelItem.textFormat: Text.PlainText
                                labelPixelSize: 10
                                selected: pane.selectedId === modelData.id
                                onLeftClicked: pane.selectedId = modelData.id
                            }
                        }
                    }
                }
                Rectangle {
                    width: pane.wide ? (body.width - 9) / 2 : body.width
                    height: Math.max(160, caseDetail.implicitHeight + 20)
                    color: Colors.black
                    border.color: Colors.magenta
                    Column {
                        id: caseDetail
                        x: 9
                        y: 9
                        width: parent.width - 18
                        spacing: 8
                        GohuText {
                            width: parent.width
                            text: pane.selectedInvestigation
                                ? (pane.selectedId === pane.scratchId
                                   ? "SCRATCH // UNSAVED // " : "")
                                  + pane.selectedInvestigation.title
                                : "SELECT AN INVESTIGATION"
                            color: Colors.magenta
                            font.pixelSize: 11
                            font.bold: true
                            wrapMode: Text.WordWrap
                            textFormat: Text.PlainText
                        }
                        GohuText {
                            width: parent.width
                            text: pane.selectedInvestigation ? pane.selectedInvestigation.question : "Cases open here without leaving FinanceW."
                            color: Colors.white
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                            textFormat: Text.PlainText
                        }
                        GohuText {
                            width: parent.width
                            text: "SOURCES " + (pane.selectedInvestigation ? pane.selectedInvestigation.evidence.length : 0)
                            color: Colors.cyan
                            font.pixelSize: 10
                        }
                        Repeater {
                            model: pane.selectedInvestigation ? pane.selectedInvestigation.evidence : []
                            delegate: Rectangle {
                                id: evidenceRow
                                required property var modelData
                                width: caseDetail.width
                                height: sourceInfo.implicitHeight + 16
                                color: Colors.dark
                                border.color: Colors.cyan
                                Column {
                                    id: sourceInfo
                                    x: 8
                                    y: 8
                                    width: parent.width - 16
                                    spacing: 5
                                    GohuText {
                                        width: parent.width
                                        text: evidenceRow.modelData.title
                                        font.pixelSize: 10
                                        color: Colors.white
                                        wrapMode: Text.WordWrap
                                        textFormat: Text.PlainText
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: (pane.selectedId === pane.scratchId
                                ? "UNSAVED SCRATCH // " : "")
                                + evidenceRow.modelData.source + " // "
                                + evidenceRow.modelData.observedAt
                                        font.pixelSize: 9
                                        color: Colors.orange
                                        wrapMode: Text.WordWrap
                                        textFormat: Text.PlainText
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: evidenceRow.modelData.summary
                                        font.pixelSize: 9
                                        color: Colors.white
                                        wrapMode: Text.WordWrap
                                        textFormat: Text.PlainText
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: evidenceRow.modelData.url
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                        wrapMode: Text.WrapAnywhere
                                        textFormat: Text.PlainText
                                    }
                                    ActionButton {
                                        width: 142
                                        height: 27
                                        label: pane.armedRemoveId === evidenceRow.modelData.id ? "CONFIRM REMOVE" : "REMOVE SOURCE"
                                        labelPixelSize: 9
                                        accentColor: Colors.red
                                        available: pane.controllerConnected && pane.writeEnabled && pane.loadState === "ready"
                                        onLeftClicked: {
                                            if (pane.armedRemoveId !== evidenceRow.modelData.id) {
                                                pane.armedRemoveId = evidenceRow.modelData.id;
                                                return;
                                            }
                                            pane.armedRemoveId = "";
                                            pane.removeRequested(pane.selectedId, evidenceRow.modelData.id);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "ATTACH SOURCE // SELECT A CASE FIRST"
                font.pixelSize: 11
                font.bold: true
                color: Colors.orange
            }
            Row {
                spacing: 5
                ActionButton {
                    width: 95
                    height: 28
                    label: "MANUAL URL"
                    selected: pane.draftSource === "manual"
                    available: pane.controllerConnected && pane.writeEnabled
                    onLeftClicked: pane.draftSource = "manual"
                }
                ActionButton {
                    width: 95
                    height: 28
                    // A manually typed URL is not proof of a retrieved SEC snapshot.
                    label: "SEC IMPORT LATER"
                    selected: false
                    available: false
                }
            }
            Repeater {
                model: [
                    {field: "draftEvidenceTitle", title: "SOURCE TITLE", max: 160},
                    {field: "draftEvidenceUrl", title: "HTTPS SOURCE URL", max: 1000},
                    {field: "draftEvidenceSummary", title: "FACTUAL NOTE", max: 2000}
                ]
                delegate: Column {
                    required property var modelData
                    width: body.width
                    spacing: 4
                    GohuText {
                        text: modelData.title
                        font.pixelSize: 9
                        color: Colors.white
                    }
                    Rectangle {
                        width: parent.width
                        height: 30
                        color: Colors.dark
                        border.color: Colors.cyan
                        TextInput {
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Colors.white
                            font.pixelSize: 10
                            clip: true
                            text: String(pane[modelData.field])
                            onTextEdited: pane[modelData.field] = text
                            maximumLength: modelData.max
                        }
                    }
                }
            }
            ActionButton {
                width: 148
                height: 29
                label: "ADD TO SCRATCH"
                labelPixelSize: 9
                accentColor: Colors.cyan
                visible: pane.scratchEnabled && pane.selectedId === pane.scratchId
                    && pane.scratchId !== ""
                available: visible && pane.controllerConnected
                    && pane.scratchAppendReady
                onLeftClicked: pane.appendScratchRequested(
                    pane.draftEvidenceTitle, pane.draftEvidenceSummary,
                    pane.draftEvidenceUrl)
            }
            ActionButton {
                width: 125
                height: 29
                label: "ATTACH SOURCE"
                available: pane.canAttach
                onLeftClicked: pane.attachRequested(pane.selectedId,pane.draftSource,
                    pane.draftEvidenceTitle.trim(),pane.draftEvidenceSummary.trim(),
                    pane.draftEvidenceUrl.trim())
            }
            GohuText {
                width: parent.width
                text: pane.scratchEnabled
                    ? "MEMORY ONLY // BACK OR LEAVING RESEARCH DISCARDS SCRATCH AND DRAFT. "
                      + "ATTACH SOURCE REMAINS DISABLED // SEC INDEX IS NOT VERIFIED CONTENT."
                    : "PREVIEW IS READ-ONLY UNTIL A REVIEWED CONTROLLER ENABLES WRITES // MANUAL LINKS ARE NOT VERIFIED SEC FEED RESULTS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
    }
}
