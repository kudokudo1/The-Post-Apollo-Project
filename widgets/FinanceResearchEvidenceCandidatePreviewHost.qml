import QtQuick
import "../services/finance" as FinanceServices

// Research M7: isolated source-preview composition, NOT mounted in FinanceW.
// The existing FinanceW SEC and Crawl readers are passed in by the owner.
// No new provider actor, no investigation writer and no live menu changes.
Item {
    id: host
    property bool active: false
    property var secFeed: null
    property var crawlFeed: null

    FinanceServices.FinanceResearchCandidatePreviewService {
        id: previewService
        monitoring: host.active
        secFeed: host.secFeed
        crawlFeed: host.crawlFeed
    }

    Connections {
        target: host.secFeed
        ignoreUnknownSignals: true
        function onSnapshotChanged() { previewService.clear(); }
        function onSelectedCikChanged() { previewService.clear(); }
        function onStateChanged() { previewService.clear(); }
    }
    Connections {
        target: host.crawlFeed
        ignoreUnknownSignals: true
        function onSnapshotChanged() { previewService.clear(); }
        function onStateChanged() { previewService.clear(); }
    }

    FinanceResearchEvidenceCandidatePicker {
        id: picker
        anchors.fill: parent
        controllerConnected: host.active
        candidatePreview: previewService.candidatePreview
        loadState: previewService.state
        statusMessage: previewService.message
        onPreviewRequested: previewService.refresh()
    }
}
