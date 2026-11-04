import QtQuick
import "../../components"

// One admission point for all seven EXISTING local-store refresh commands.
// Never interrupts writes, retries conflicts, saves data or refreshes a
// verified Identity Center organization/session.
Column {
    id: refreshPanel
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null

    property bool refreshInProgress: false
    property string lastRefreshResult: ""
    property int acceptedRefreshCount: 0
    spacing: 5

    function sources() {
        return [
            {id:"directory", name:"Organizations / Branches", store:directoryStore},
            {id:"portfolio", name:"Portfolios", store:portfolioStore},
            {id:"structure", name:"Structure", store:structureStore},
            {id:"functionLocation", name:"Function / Location", store:functionLocationStore},
            {id:"branchLocation", name:"Branch / Location", store:branchLocationStore},
            {id:"reporting", name:"Reporting", store:reportingStore},
            {id:"social", name:"Social Associations", store:socialLinksStore}
        ];
    }
    function stateOf(store) {
        return store && store.state !== undefined
            ? String(store.state) : "unavailable";
    }
    function codeOf(store) {
        return store && store.errorCode ? String(store.errorCode) : "";
    }
    readonly property string stateSignature: sources().map(function(entry) {
        return entry.id + ":" + refreshPanel.stateOf(entry.store)
            + ":" + refreshPanel.codeOf(entry.store);
    }).join("|")
    readonly property int busyCount: sources().filter(function(entry) {
        return refreshPanel.stateOf(entry.store) === "saving"
            || refreshPanel.stateOf(entry.store) === "loading";
    }).length
    readonly property int loadingCount: sources().filter(function(entry) {
        return refreshPanel.stateOf(entry.store) === "loading";
    }).length
    readonly property int missingCount: sources().filter(function(entry) {
        return !entry.store || typeof entry.store.refresh !== "function";
    }).length
    readonly property var failures: sources().filter(function(entry) {
        return refreshPanel.stateOf(entry.store) === "error";
    }).map(function(entry) {
        return entry.name + " (" +
            (refreshPanel.codeOf(entry.store) || "UNAVAILABLE") + ")";
    })
    readonly property bool canRefresh: !refreshInProgress
        && missingCount === 0 && busyCount === 0
        && sources().every(function(entry) {
            const state = refreshPanel.stateOf(entry.store);
            return state === "ready" || state === "error";
        })
    readonly property string displayedResult:
        busyCount > 0
        ? "REFRESH BUSY // " + busyCount + " local store(s) loading or saving."
        : missingCount > 0
        ? "REFRESH UNAVAILABLE // " + missingCount + " store(s) not connected."
        : lastRefreshResult !== "" ? lastRefreshResult
        : "REFRESH READY // Reload all seven local organization stores."

    function requestRefresh() {
        if (!canRefresh) {
            // Repeated presses during an accepted operation never queue
            // duplicate reads and must not erase its progress status.
            if (!refreshInProgress)
                lastRefreshResult = "REFRESH NOT STARTED // Wait for idle stores.";
            return false;
        }
        const sourcesNow = sources();
        refreshInProgress = true;
        acceptedRefreshCount = 0;
        const rejected = [];
        for (const source of sourcesNow) {
            let accepted = false;
            try {
                accepted = source.store.refresh() === true;
            } catch (error) {
                accepted = false;
            }
            if (accepted)
                acceptedRefreshCount += 1;
            else
                rejected.push(source.name);
        }
        if (rejected.length > 0) {
            lastRefreshResult = "REFRESH PARTIAL // " + acceptedRefreshCount +
                "/7 started; rejected: " + rejected.join(", ") + ". No automatic retry.";
        } else {
            lastRefreshResult = "REFRESH STARTED // 7 local stores reloading.";
        }
        if (acceptedRefreshCount === 0)
            refreshInProgress = false;
        return rejected.length === 0;
    }
    function checkCompletion() {
        if (!refreshInProgress)
            return;
        // Re-read each current source directly: bindings for derived counts
        // may be a tick behind their underlying QML store-state notify.
        const current = sources().map(function(entry) {
            return refreshPanel.stateOf(entry.store);
        });
        if (current.some(function(state) {
            return state === "saving" || state === "loading";
        }))
            return;
        if (!current.every(function(state) {
            return state === "ready" || state === "error";
        }))
            return;
        refreshInProgress = false;
        if (failures.length > 0) {
            lastRefreshResult = "REFRESH ENDED WITH ERRORS // " +
                failures.join(" / ") + ". Review before retry.";
        } else if (acceptedRefreshCount === 7) {
            lastRefreshResult = "REFRESH COMPLETE // All seven local stores reloaded.";
        } else {
            lastRefreshResult = "REFRESH PARTIAL // " + acceptedRefreshCount +
                "/7 requests accepted. Check rejected stores before retry.";
        }
    }
    onStateSignatureChanged: Qt.callLater(refreshPanel.checkCompletion)

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "REFRESH LOCAL ORGANIZATION RECORDS"
        color: Colors.cyan
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    ActionButton {
        objectName: "orgRefreshAllButton"
        width: 150
        height: 28
        label: "REFRESH ALL"
        labelPixelSize: 9
        interactive: refreshPanel.canRefresh
        onTriggered: refreshPanel.requestRefresh()
    }
    Text {
        objectName: "orgRefreshAllResult"
        width: parent.width
        text: refreshPanel.displayedResult
        color: refreshPanel.failures.length > 0
            ? Colors.orange : Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Refresh reads existing local records. It cannot overwrite an " +
              "in-progress save, repair a conflict or grant company access."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
