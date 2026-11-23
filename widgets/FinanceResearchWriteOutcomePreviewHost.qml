import QtQuick
import "../components"

// M4b-T2 preview: compositional UI rehearsal, NOT a persistence controller.
// The read host is unchanged; these buttons only change in-memory demo labels.
Item {
    id: preview
    property bool active: false
    property string demoPhase: "staged"
    property bool draftPresent: true

    readonly property bool demoPending: demoPhase === "inFlight"
    readonly property bool demoFinished:
        demoPhase === "acknowledged" || demoPhase === "reviewRequired"
        || demoPhase === "refused"

    function beginPreview() {
        if (demoPhase !== "staged" || !draftPresent) return false;
        demoPhase = "inFlight";
        return true;
    }
    function acknowledgePreview() {
        if (!demoPending) return false;
        draftPresent = false; // Simulated exact ACK only, never real storage.
        demoPhase = "acknowledged";
        return true;
    }
    function unknownPreview() {
        if (!demoPending) return false;
        // An unconfirmed write must preserve the editor draft.
        draftPresent = true;
        demoPhase = "reviewRequired";
        return true;
    }
    function refusePreview() {
        if (!demoPending) return false;
        draftPresent = true;
        demoPhase = "refused";
        return true;
    }
    function resetPreview() {
        if (demoPending) return false;
        // RESET DEMO is a fresh visual rehearsal, never a storage retry.
        demoPhase = "staged";
        draftPresent = true;
        return true;
    }

    Column {
        id: content
        anchors.fill: parent
        spacing: 7

        FinanceResearchInvestigationsReadHost {
            id: readHost
            width: parent.width
            height: Math.max(0, content.height
                - outcome.implicitHeight - demoActions.implicitHeight - 14)
            active: preview.active
            // Internally: writeEnabled: false. Never expose a write override.
        }
        FinanceResearchWriteOutcomePanel {
            id: outcome
            width: parent.width
            height: implicitHeight
            simulationOnly: true
            readerConnected: false
            exactAcknowledgement: false
            acknowledgedRevision: -1
            phase: preview.demoPhase
        }
        Grid {
            id: demoActions
            width: parent.width
            columns: width >= 700 ? 5 : 2
            columnSpacing: 6
            rowSpacing: 6
            ActionButton {
                width: Math.max(0,(demoActions.width
                    - demoActions.columnSpacing * (demoActions.columns - 1))
                    / demoActions.columns)
                height: 29
                label: "TEST DISPATCH"
                labelPixelSize: 9
                available: preview.demoPhase === "staged" && preview.draftPresent
                onLeftClicked: preview.beginPreview()
            }
            ActionButton {
                width: Math.max(0,(demoActions.width
                    - demoActions.columnSpacing * (demoActions.columns - 1))
                    / demoActions.columns)
                height: 29
                label: "TEST ACK"
                labelPixelSize: 9
                available: preview.demoPending
                onLeftClicked: preview.acknowledgePreview()
            }
            ActionButton {
                width: Math.max(0,(demoActions.width
                    - demoActions.columnSpacing * (demoActions.columns - 1))
                    / demoActions.columns)
                height: 29
                label: "TEST UNKNOWN"
                labelPixelSize: 9
                available: preview.demoPending
                onLeftClicked: preview.unknownPreview()
            }
            ActionButton {
                width: Math.max(0,(demoActions.width
                    - demoActions.columnSpacing * (demoActions.columns - 1))
                    / demoActions.columns)
                height: 29
                label: "TEST REFUSE"
                labelPixelSize: 9
                available: preview.demoPending
                onLeftClicked: preview.refusePreview()
            }
            ActionButton {
                width: Math.max(0,(demoActions.width
                    - demoActions.columnSpacing * (demoActions.columns - 1))
                    / demoActions.columns)
                height: 29
                label: "RESET DEMO"
                labelPixelSize: 9
                available: preview.demoFinished
                onLeftClicked: preview.resetPreview()
            }
        }
    }
}
