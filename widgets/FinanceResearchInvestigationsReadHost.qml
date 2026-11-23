import QtQuick
import "../services/finance" as FinanceServices

// Research M4a: isolated preview host, not mounted in FinanceW.
// No create/attach/remove signals are connected to any writer.
Item {
    id: host
    property bool active: false

    FinanceServices.FinanceResearchInvestigationReadService {
        id: readService
        monitoring: host.active
    }

    FinanceResearchInvestigationsPane {
        id: investigationPane
        anchors.fill: parent
        controllerConnected: host.active
        writeEnabled: false // HARD HOLD: M2 storage recovery/security review pending
        loadState: readService.state
        statusMessage: readService.message
        investigations: readService.investigations
        onLoadRequested: readService.load()
    }
}
