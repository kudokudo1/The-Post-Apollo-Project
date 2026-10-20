import QtQuick
import Quickshell
import qs.services.notifications
import "LocalGitJournalNotificationPolicy.js" as JournalPolicy

// Passive fanout from GitOperationJournalService.operationFinished only.
// No refresh/poll, Git command execution, undo or mutation.
Scope {
    id: producer
    required property var operationJournal

    function receive(operationId, success, record) {
        const item = JournalPolicy.payload(operationId, success, record);
        if (!item)
            return;

        // The persistent event ID is derived from the journal operation ID.
        // Repeated signals/reloads cannot create duplicate history entries.
        const rows = NotificationsService.notifications;
        for (let i = 0; i < rows.count; ++i) {
            if (String(rows.get(i).id || "") === item.id)
                return;
        }

        NotificationsService.pushRich({
            "id": item.id,
            "source": "GIT",
            "sourceId": "git-local-journal",
            "category": "internal",
            "severity": item.success ? "normal" : "warning",
            "title": item.success ? "GIT // OPERATION RECORDED COMPLETE"
                                   : "GIT // OPERATION RECORDED FAILED",
            "message": item.message,
            "tags": ["git", "local", "operation-journal"],
            "context": {
                "eventType": "git-journal-" + (item.success ? "complete" : "failed"),
                "origin": "apollo",
                "domain": "git",
                "journalId": String(operationId),
                "repositoryName": item.repository,
                "kind": item.kind,
                "verification": "journal outcome only"
            }
        });
    }

    Connections {
        target: producer.operationJournal
        function onOperationFinished(operationId, success, record) {
            producer.receive(operationId, success, record);
        }
    }
}
