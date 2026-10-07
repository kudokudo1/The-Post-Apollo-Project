import QtQuick
import Quickshell
import Quickshell.Io

// Durable Git operation journal foundation.
//
// This service deliberately records operations before it claims to support
// Undo. The first contract is continuity: what operation started, what state
// existed before it, whether it completed, and what state existed afterward.
//
// Undo/recovery strategy is a later layer and must not be inferred from the
// mere existence of a journal record.
Scope {
    id: root

    property string repositoryPath: ""
    property int schemaVersion: 1
    property int maxEntries: 500
    property int serial: 0
    property var entries: []

    signal operationStarted(string operationId, var record)
    signal operationFinished(string operationId, bool success, var record)

    readonly property var repositoryEntries:
        entries.filter(function(record) {
            return String((record || {}).repository || "")
                === String(root.repositoryPath || "");
        })

    function nowIso() {
        return new Date().toISOString();
    }

    function cloneValue(value) {
        if (value === null || typeof value === "undefined")
            return null;

        try {
            return JSON.parse(JSON.stringify(value));
        } catch (error) {
            return String(value);
        }
    }

    function nextOperationId() {
        serial += 1;
        return String(Date.now().toString(36))
            + "-"
            + String(serial.toString(36));
    }

    function entryIndex(operationId) {
        const needle = String(operationId || "");

        for (let i = 0; i < entries.length; ++i) {
            if (String((entries[i] || {}).id || "") === needle)
                return i;
        }

        return -1;
    }

    function beginOperation(kind, beforeState, metadata) {
        const repo = String(repositoryPath || "").trim();
        const operationKind = String(kind || "").trim();

        if (!repo || !operationKind)
            return "";

        const operationId = nextOperationId();
        const record = {
            schemaVersion: schemaVersion,
            id: operationId,
            repository: repo,
            kind: operationKind,
            status: "RUNNING",
            startedAt: nowIso(),
            completedAt: "",
            before: cloneValue(beforeState),
            after: null,
            metadata: cloneValue(metadata || {}),
            detail: "",
            undoState: "NOT_IMPLEMENTED"
        };

        const next = [record].concat(entries);

        if (next.length > maxEntries)
            next.length = maxEntries;

        entries = next;
        persist();
        operationStarted(operationId, cloneValue(record));
        return operationId;
    }

    function completeOperation(operationId, afterState, detail) {
        const index = entryIndex(operationId);

        if (index < 0)
            return false;

        const next = entries.slice();
        const previous = next[index] || {};
        const record = {
            schemaVersion: Number(previous.schemaVersion || schemaVersion),
            id: String(previous.id || operationId),
            repository: String(previous.repository || repositoryPath),
            kind: String(previous.kind || "UNKNOWN"),
            status: "COMPLETE",
            startedAt: String(previous.startedAt || ""),
            completedAt: nowIso(),
            before: cloneValue(previous.before),
            after: cloneValue(afterState),
            metadata: cloneValue(previous.metadata || {}),
            detail: String(detail || ""),
            undoState: "NOT_IMPLEMENTED"
        };

        next[index] = record;
        entries = next;
        persist();
        operationFinished(operationId, true, cloneValue(record));
        return true;
    }

    function failOperation(operationId, afterState, detail) {
        const index = entryIndex(operationId);

        if (index < 0)
            return false;

        const next = entries.slice();
        const previous = next[index] || {};
        const record = {
            schemaVersion: Number(previous.schemaVersion || schemaVersion),
            id: String(previous.id || operationId),
            repository: String(previous.repository || repositoryPath),
            kind: String(previous.kind || "UNKNOWN"),
            status: "FAILED",
            startedAt: String(previous.startedAt || ""),
            completedAt: nowIso(),
            before: cloneValue(previous.before),
            after: cloneValue(afterState),
            metadata: cloneValue(previous.metadata || {}),
            detail: String(detail || ""),
            undoState: "NOT_IMPLEMENTED"
        };

        next[index] = record;
        entries = next;
        persist();
        operationFinished(operationId, false, cloneValue(record));
        return true;
    }

    function load() {
        const raw = String(journalFile.text() || "").trim();

        if (!raw) {
            entries = [];
            return;
        }

        let parsed = null;

        try {
            parsed = JSON.parse(raw);
        } catch (error) {
            entries = [];
            return;
        }

        const source =
            parsed && Array.isArray(parsed.entries)
            ? parsed.entries
            : [];
        const next = [];
        let repairedInterrupted = false;

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const status = String(row.status || "UNKNOWN");
            const record = {
                schemaVersion: Number(row.schemaVersion || schemaVersion),
                id: String(row.id || ""),
                repository: String(row.repository || ""),
                kind: String(row.kind || "UNKNOWN"),
                status:
                    status === "RUNNING"
                    ? "INTERRUPTED"
                    : status,
                startedAt: String(row.startedAt || ""),
                completedAt:
                    status === "RUNNING"
                    ? nowIso()
                    : String(row.completedAt || ""),
                before: cloneValue(row.before),
                after: cloneValue(row.after),
                metadata: cloneValue(row.metadata || {}),
                detail:
                    status === "RUNNING"
                    ? "APPLICATION EXITED BEFORE OPERATION COMPLETION WAS RECORDED"
                    : String(row.detail || ""),
                undoState: String(row.undoState || "NOT_IMPLEMENTED")
            };

            if (status === "RUNNING")
                repairedInterrupted = true;

            next.push(record);

            if (next.length >= maxEntries)
                break;
        }

        entries = next;

        if (repairedInterrupted)
            persist();
    }

    function persist() {
        journalFile.setText(JSON.stringify({
            schemaVersion: schemaVersion,
            entries: entries
        }, null, 2));
    }

    FileView {
        id: journalFile

        path: Qt.resolvedUrl("../../git-operation-journal.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.load()
    }
}
