import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// Archives are a visible, separate inline destination, not a search filter.
// Delete works on active or archived labels. No backup is required.
// Two-click confirmation, current revision and seven-store references are checked.
Column {
    id: tray
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var unitLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null
    property bool expanded: false
    property bool busy: false
    property string confirmationKey: ""
    property string lastTargetKind: ""
    property var pendingRequest: null
    property string replyText: ""
    property string resultText: ""
    property string resultKind: "neutral"
    readonly property var archivedRecords: collectArchived()
    readonly property int archivedCount: archivedRecords.length
    readonly property bool storesReady: [
        directoryStore, portfolioStore, structureStore, unitLocationStore,
        branchLocationStore, reportingStore, socialLinksStore
    ].every(function(store) { return store && store.state === "ready"; })
    spacing: 6
    onExpandedChanged: confirmationKey = ""

    function rows(store, key) {
        return store && store.state === "ready" && store.saved
            && Array.isArray(store.saved[key]) ? store.saved[key] : [];
    }
    function collectArchived() {
        const found = [];
        const orgRevision = directoryStore && directoryStore.saved
            ? directoryStore.saved.revision : -1;
        const portRevision = portfolioStore && portfolioStore.saved
            ? portfolioStore.saved.revision : -1;
        const unitRevision = structureStore && structureStore.saved
            ? structureStore.saved.revision : -1;
        for (const org of rows(directoryStore, "organizations")) {
            if (org.archived)
                found.push({kind:"organization", id:org.id, orgId:org.id,
                    name:org.name, revision:orgRevision,
                    label:"COMPANY // " + org.name});
            for (const branch of org.branches) {
                if (branch.archived)
                    found.push({kind:"branch", id:branch.id, orgId:org.id,
                        name:branch.name, revision:orgRevision,
                        label:"BRANCH // " + branch.name + " / " + org.name,
                        parentArchived:org.archived});
            }
        }
        for (const p of rows(portfolioStore, "portfolios"))
            if (p.archived)
                found.push({kind:"portfolio", id:p.id, orgId:"",
                    name:p.name, revision:portRevision,
                    label:"PORTFOLIO // " + p.name});
        for (const unit of rows(structureStore, "units"))
            if (unit.archived)
                found.push({kind:"unit", id:unit.id, orgId:unit.orgId,
                    name:unit.name, revision:unitRevision,
                    label:unit.kind.toUpperCase() + " // " + unit.name});
        return found;
    }
    function source(kind) {
        return kind === "organization" || kind === "branch" ? directoryStore
            : kind === "portfolio" ? portfolioStore : structureStore;
    }
    function restore(record) {
        if (busy || !storesReady) return false;
        confirmationKey = "";
        const store = source(record.kind);
        if (record.kind === "organization")
            return store.restoreOrganization(record.id);
        if (record.kind === "branch") {
            if (record.parentArchived) {
                resultKind = "error";
                resultText = "RESTORE PARENT COMPANY FIRST // " + record.name;
                return false;
            }
            return store.restoreBranch(record.orgId, record.id);
        }
        if (record.kind === "portfolio")
            return store.restorePortfolio(record.id);
        const parent = rows(directoryStore, "organizations")
            .find(function(org) { return org.id === record.orgId; });
        if (!parent || parent.archived) {
            resultKind = "error";
            resultText = "RESTORE PARENT COMPANY FIRST // " + record.name;
            return false;
        }
        return store.restoreUnit(record.id);
    }
    function confirmationFor(record) {
        return record.kind + ":" + record.id + ":" + record.revision
            + ":" + record.name;
    }
    function isConfirmed(record) {
        return confirmationKey === confirmationFor(record);
    }
    function cancelDelete() {
        if (busy) return false;
        confirmationKey = "";
        resultText = "";
        lastTargetKind = "";
        return true;
    }
    function requestRemove(record) {
        if (!record || !storesReady || busy)
            return false;
        const key = confirmationFor(record);
        lastTargetKind = record.kind;
        if (confirmationKey !== key) {
            confirmationKey = key;
            resultKind = "warning";
            resultText = "CONFIRM PERMANENT DELETE // " + record.label
                + " // No backup is required or created. This cannot be undone "
                + "with Restore. Click the red confirmation to proceed.";
            return false;
        }
        // The backend rechecks the current revision, identity and dependencies.
        // Neither an archive operation nor a private backup is required.
        pendingRequest = {
            action:"remove", kind:record.kind, id:record.id,
            orgId:record.orgId, expectedName:record.name,
            expectedRevision:record.revision
        };
        confirmationKey = "";
        replyText = "";
        busy = true;
        resultKind = "working";
        resultText = "REMOVING // Waiting for seven-store dependency checks.";
        removalProcess.running = true;
        return true;
    }
    function finishRemove(exitCode) {
        let response = null;
        try { response = JSON.parse(replyText); } catch (e) {}
        busy = false;
        const valid = exitCode === 0 && response && response.ok === true
            && pendingRequest && response.kind === pendingRequest.kind
            && response.id === pendingRequest.id;
        if (!valid) {
            resultKind = "error";
            const code = response && response.error
                ? String(response.error) : "REMOVE_UNAVAILABLE";
            const instructions = {
                REMOVE_BRANCHES_FIRST:"Delete the company's child branches first.",
                REMOVE_UNITS_FIRST:"Delete the company's structure units first.",
                DETACH_PORTFOLIOS_FIRST:"Detach the company from every portfolio.",
                UNLINK_ORGANIZATION_FIRST:"Remove its saved relationships and labels.",
                UNLINK_BRANCH_SOCIAL_FIRST:"Unlink this branch's Social label first.",
                UNLINK_BRANCH_LOCATION_FIRST:"Unlink the branch/location relation.",
                UNLINK_UNIT_LOCATION_FIRST:"Unlink this unit from its location.",
                UNLINK_REPORTING_FIRST:"Remove parent/child reporting links.",
                DETACH_PORTFOLIO_MEMBERS_FIRST:"Detach portfolio members first.",
                REVISION_CONFLICT:"Refresh local records and review before retry.",
                RECORD_CHANGED:"Refresh; this record was renamed."
            };
            resultText = "REMOVE REFUSED // " + code
                + " // " + (instructions[code] || "Existing records preserved.");
            pendingRequest = null;
            return;
        }
        const sourceStore = source(response.kind);
        const reloading = sourceStore && sourceStore.refresh();
        resultKind = "removed";
        resultText = "REMOVED PERMANENTLY // " + response.kind + " " + response.id
            + (reloading ? " // Re-reading local records."
                         : " // Press REFRESH ALL to update the view.");
        pendingRequest = null;
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.yellow
        opacity: 0.55
    }
    Text {
        objectName: "orgArchiveTrayTitle"
        width: parent.width
        text: "ARCHIVE TRAY // " + tray.archivedCount + " ARCHIVED RECORDS"
        color: Colors.yellow
        font.pixelSize: 12
        font.bold: true
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Archived companies, branches, portfolios and structure units live here. " +
              "Archive hides; Restore reactivates. Red X buttons in the editors " +
              "delete active records directly. Backups are optional."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    IdentityCenterLocalActionButton {
        objectName: "orgArchiveTrayToggle"
        role: "manage"
        width: 188
        height: 29
        label: tray.expanded ? "CLOSE ARCHIVE TRAY"
              : "VIEW ARCHIVES // " + tray.archivedCount
        labelPixelSize: 9
        selected: tray.expanded
        onTriggered: tray.expanded = !tray.expanded
    }
    Text {
        width: parent.width
        visible: tray.expanded && !tray.storesReady
        text: "ARCHIVES LOADING // Wait for all seven local stores to be ready."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: tray.expanded && tray.storesReady && tray.archivedCount === 0
        text: "No archived records. Use ARCHIVE on an active record to move it here."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: tray.expanded ? tray.archivedRecords : []
        delegate: Column {
            id: archivedRow
            required property var modelData
            width: tray.width
            spacing: 4
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.yellow
                opacity: 0.25
            }
            Text {
                width: parent.width
                text: "ARCHIVED // " + archivedRow.modelData.label
                color: Colors.yellow
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
            }
            Flow {
                width: parent.width
                height: childrenRect.height
                spacing: 6
                IdentityCenterLocalActionButton {
                    role: "refresh"
                    width: 116
                    height: 28
                    label: "RESTORE"
                    labelPixelSize: 9
                    interactive: tray.storesReady && !tray.busy
                    onTriggered: tray.restore(archivedRow.modelData)
                }
                IdentityCenterLocalActionButton {
                    objectName: "orgArchiveRemoveAction"
                    role: "danger"
                    width: 153
                    height: 28
                    labelPixelSize: 8
                    label: tray.isConfirmed(archivedRow.modelData)
                           ? "CONFIRM REMOVE" : "REMOVE PERMANENTLY"
                    interactive: tray.storesReady && !tray.busy
                    onTriggered: tray.requestRemove(archivedRow.modelData)
                }
            }
        }
    }
    Text {
        objectName: "orgArchiveTrayResult"
        width: parent.width
        visible: resultText !== ""
        text: tray.resultText
        color: tray.resultKind === "error" ? Colors.red
            : tray.resultKind === "removed" ? Colors.green
            : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: tray.expanded
        text: "Backups OPTIONAL. Delete works directly on active or archived labels. " +
              "Children, portfolio members and saved links must be cleared first. " +
              "There is no automatic cascade."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Process {
        id: removalProcess
        objectName: "orgArchiveRemoveProcess"
        running: false
        stdinEnabled: true
        command: ["/usr/bin/python3",
                  Quickshell.shellPath("services/social/SocialLocalOrgArchivedRemoval.py"),
                  "remove"]
        stdout: StdioCollector {
            onStreamFinished: tray.replyText = String(text || "")
        }
        onStarted: {
            removalProcess.write(JSON.stringify(tray.pendingRequest) + "\n");
        }
        onExited: function(exitCode) {
            tray.finishRemove(exitCode);
        }
    }
}
