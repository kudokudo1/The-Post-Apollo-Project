import QtQuick
import Quickshell
import Quickshell.Io
import "GitJournalSerialization.js" as JournalCodec
import "GitJournalDelta.js" as DeltaCodec

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
    property var encodedEntries: []
    // Delta writes are initially opt-in; a nonempty existing sidecar always
    // forces replay to prevent silent loss when the option is switched off.
    readonly property bool deltaRequested:
        String(Quickshell.env("POST_APOLLO_GIT_JOURNAL_DELTA") || "").trim() === "1"
    property bool deltaActive: false
    property bool storageReady: false
    property string storageError: ""
    // FileView.setText() returns void. With blockWrites enabled, these
    // statuses are synchronously set by saved()/saveFailed() before it returns.
    property int journalWriteStatus: 0
    property string journalWriteError: ""
    property int deltaWriteStatus: 0
    property string deltaWriteError: ""
    property int checkpointGeneration: 0
    property var deltaRecords: []
    // Internal-only serialized rows; never use this cache as recovery evidence.
    property var encodedDeltaRecords: []
    property int maxDeltaRecords: 48
    property int lastPersistSerializationMs: 0
    property int lastPersistWriteMs: 0
    property int lastPersistReusedCount: 0
    // Most recent mutation phase timings. No record payloads are copied here.
    property var lastMutationProfile: ({})

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

    function markMutationProfile(stage, started, built, published, saved, notified) {
        lastMutationProfile = {
            stage: String(stage),
            recordMs: Math.max(0, built - started),
            entriesMs: Math.max(0, published - built),
            persistMs: Math.max(0, saved - published),
            notifyMs: Math.max(0, notified - saved),
            totalMs: Math.max(0, notified - started)
        };
    }

    function beginOperation(kind, beforeState, metadata) {
        const repo = String(repositoryPath || "").trim();
        const operationKind = String(kind || "").trim();

        if (!repo || !operationKind || !storageReady)
            return "";

        const mutationStarted = Date.now();
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
            recoveryClass:
                String((beforeState || {}).recoveryClass || "EVIDENCE_ONLY"),
            undoState: "NOT_IMPLEMENTED"
        };

        const recordBuiltAt = Date.now();
        const next = [record].concat(entries);

        if (next.length > maxEntries)
            next.length = maxEntries;

        entries = next;
        const entriesPublishedAt = Date.now();
        const saved = persist(record);
        const persistedAt = Date.now();
        if (!saved) {
            markMutationProfile("BEGIN_FAILED", mutationStarted,
                recordBuiltAt, entriesPublishedAt, persistedAt, persistedAt);
            return "";
        }
        operationStarted(operationId, cloneValue(record));
        markMutationProfile("BEGIN", mutationStarted,
            recordBuiltAt, entriesPublishedAt, persistedAt, Date.now());
        return operationId;
    }

    function completedRecoveryClass(previous, afterState) {
        const beforeClass =
            String((previous || {}).recoveryClass || "EVIDENCE_ONLY");
        const afterClass =
            String(
                (afterState || {}).recoveryClass
                || "EVIDENCE_ONLY"
            );

        if (beforeClass === "REF_RECOVERABLE"
                && afterClass === "REF_RECOVERABLE")
            return "REF_RECOVERABLE";

        if (beforeClass === "CONTENT_RECOVERABLE"
                && afterClass === "CONTENT_RECOVERABLE")
            return "CONTENT_RECOVERABLE";

        if (beforeClass === "EXTERNAL_RECOVERABLE"
                && afterClass === "EXTERNAL_RECOVERABLE")
            return "EXTERNAL_RECOVERABLE";

        return "EVIDENCE_ONLY";
    }

    function completeOperation(operationId, afterState, detail) {
        const mutationStarted = Date.now();
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
            recoveryClass:
                completedRecoveryClass(previous, afterState),
            undoState: "NOT_IMPLEMENTED"
        };

        const recordBuiltAt = Date.now();
        next[index] = record;
        entries = next;
        const entriesPublishedAt = Date.now();
        const saved = persist(record);
        const persistedAt = Date.now();
        if (!saved) {
            markMutationProfile("COMPLETE_FAILED", mutationStarted,
                recordBuiltAt, entriesPublishedAt, persistedAt, persistedAt);
            return false;
        }
        operationFinished(operationId, true, cloneValue(record));
        markMutationProfile("COMPLETE", mutationStarted,
            recordBuiltAt, entriesPublishedAt, persistedAt, Date.now());
        return true;
    }

    function failOperation(operationId, afterState, detail) {
        const mutationStarted = Date.now();
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
            recoveryClass: "EVIDENCE_ONLY",
            undoState: "NOT_IMPLEMENTED"
        };

        const recordBuiltAt = Date.now();
        next[index] = record;
        entries = next;
        const entriesPublishedAt = Date.now();
        const saved = persist(record);
        const persistedAt = Date.now();
        if (!saved) {
            markMutationProfile("FAIL_FAILED", mutationStarted,
                recordBuiltAt, entriesPublishedAt, persistedAt, persistedAt);
            return false;
        }
        operationFinished(operationId, false, cloneValue(record));
        markMutationProfile("FAIL", mutationStarted,
            recordBuiltAt, entriesPublishedAt, persistedAt, Date.now());
        return true;
    }

    function load() {
        // The two FileViews use blocking initial loads. Never interpret a
        // malformed sidecar as an empty record set and start new mutations.
        storageReady = false;
        storageError = "";
        encodedEntries = [];
        encodedDeltaRecords = [];
        const raw = String(journalFile.text() || "").trim();
        const overlayRaw = String(deltaFile.text() || "").trim();
        let source = [];

        try {
            const base = raw ? JSON.parse(raw) : {
                schemaVersion: schemaVersion,
                entries: []
            };
            if (!base || !Array.isArray(base.entries))
                throw new Error("INVALID LEGACY JOURNAL CHECKPOINT");
            checkpointGeneration = DeltaCodec.checkGeneration(
                typeof base.checkpointGeneration === "undefined"
                ? 0
                : base.checkpointGeneration
            );
            const overlay = DeltaCodec.readSidecar(
                overlayRaw, checkpointGeneration
            );
            deltaRecords = overlay.rows;
            deltaActive = deltaRequested || overlay.present;
            source = DeltaCodec.overlay(
                base.entries, overlay.rows, maxEntries
            );
        } catch (error) {
            storageError = "JOURNAL STORAGE BLOCKED // "
                + String(error);
            console.warn(storageError);
            return;
        }

        const next = [];
        let repairedInterrupted = false;

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const status = String(row.status || "UNKNOWN");
            const metadata = cloneValue(row.metadata || {}) || {};
            const durableRunning =
                status === "RUNNING"
                && Boolean(metadata.durableSession);
            const interrupted =
                status === "RUNNING"
                && !durableRunning;
            // Preserve future/optional fields (Undo provenance included).
            // Only normalize interruption status and required legacy fields.
            const record = Object.assign({}, row, {
                schemaVersion: Number(row.schemaVersion || schemaVersion),
                id: String(row.id || ""),
                repository: String(row.repository || ""),
                kind: String(row.kind || "UNKNOWN"),
                status:
                    interrupted
                    ? "INTERRUPTED"
                    : status,
                startedAt: String(row.startedAt || ""),
                completedAt:
                    interrupted
                    ? nowIso()
                    : String(row.completedAt || ""),
                before: cloneValue(row.before),
                after: cloneValue(row.after),
                metadata: metadata,
                detail:
                    interrupted
                    ? "APPLICATION EXITED BEFORE OPERATION COMPLETION WAS RECORDED"
                    : String(row.detail || ""),
                recoveryClass:
                    interrupted
                    ? "EVIDENCE_ONLY"
                    : String(row.recoveryClass || "EVIDENCE_ONLY"),
                undoState: String(row.undoState || "NOT_IMPLEMENTED")
            });

            if (interrupted)
                repairedInterrupted = true;

            next.push(record);

            if (next.length >= maxEntries)
                break;
        }

        entries = next;
        storageReady = true;

        // Interruption repairs checkpoint both partitions before another
        // operation can be accepted.
        if (repairedInterrupted)
            persist();
    }

    function markUndoResult(
            operationId,
            undoOperationId,
            success,
            detail) {
        const index = entryIndex(operationId);

        if (index < 0)
            return false;

        const next = entries.slice();
        const record = cloneValue(next[index] || {}) || {};

        record.undoState = success ? "UNDONE" : "UNDO_FAILED";
        record.undoOperationId = String(undoOperationId || "");
        record.undoDetail = String(detail || "");
        record.undoneAt = success ? nowIso() : "";

        next[index] = record;
        entries = next;
        return persist();
    }

    function blockStorage(reason) {
        storageReady = false;
        storageError = "JOURNAL STORAGE BLOCKED // " + String(reason);
        console.warn(storageError);
        return false;
    }

    function requireWriteAck(channel) {
        const checkpoint = channel === "CHECKPOINT";
        const status = checkpoint ? journalWriteStatus : deltaWriteStatus;
        const error = checkpoint ? journalWriteError : deltaWriteError;
        if (status !== 1)
            return blockStorage(channel + " WRITE FAILED // "
                + (error || "NO SYNCHRONOUS SAVED SIGNAL"));
        return true;
    }

    function persist(record) {
        if (!storageReady)
            return false;

        try {
        const deltaEligible = record
            && (record.kind === "CONTROL/FETCH"
                || record.kind === "CONTROL/PULL");
        if (deltaActive && deltaEligible) {
            const start = Date.now();
            const revised = DeltaCodec.upsert(deltaRecords, record);
            if (revised.length < maxDeltaRecords) {
                const encoded = DeltaCodec.encodeSidecarCached(
                    checkpointGeneration, revised, encodedDeltaRecords
                );
                const serialized = encoded.text;
                const writeStarted = Date.now();
                deltaWriteStatus = 0;
                deltaWriteError = "";
                deltaFile.setText(serialized);
                if (!requireWriteAck("DELTA"))
                    return false;
                const written = Date.now();
                deltaRecords = revised;
                // Publish cache only after the synchronous sidecar save ack.
                encodedDeltaRecords = encoded.cache;
                lastPersistSerializationMs = writeStarted - start;
                lastPersistWriteMs = written - writeStarted;
                lastPersistReusedCount = encoded.reusedCount;
                return true;
            }
        }

        // Existing behavior remains the default. A delta-active checkpoint
        // writes the full base FIRST and clears the sidecar SECOND. If the
        // app crashes between writes, generation rules ignore the stale
        // overlay because all of its rows are already in the new base.
        const start = Date.now();
        const encoded = JournalCodec.serializeJournal(
            schemaVersion, entries, encodedEntries
        );
        const nextGeneration = deltaActive
            ? checkpointGeneration + 1
            : checkpointGeneration;
        const data = deltaActive
            ? JSON.stringify({
                schemaVersion: schemaVersion,
                checkpointGeneration: nextGeneration,
                entries: entries
            })
            : encoded.text;
        const writeStarted = Date.now();
        journalWriteStatus = 0;
        journalWriteError = "";
        journalFile.setText(data);
        if (!requireWriteAck("CHECKPOINT"))
            return false;
        if (deltaActive) {
            deltaWriteStatus = 0;
            deltaWriteError = "";
            deltaFile.setText(
                DeltaCodec.encodeSidecar(nextGeneration, [])
            );
            if (!requireWriteAck("DELTA"))
                return false;
            checkpointGeneration = nextGeneration;
            deltaRecords = [];
            encodedDeltaRecords = [];
        }
        const written = Date.now();
        encodedEntries = encoded.cache;
        lastPersistSerializationMs = writeStarted - start;
        lastPersistWriteMs = written - writeStarted;
        lastPersistReusedCount = encoded.reusedCount;
        return true;
        } catch (error) {
            return blockStorage("PERSIST EXCEPTION // " + String(error));
        }
    }

    FileView {
        id: journalFile

        path: Qt.resolvedUrl("../../git-operation-journal.json")
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        printErrors: false
        onSaved: root.journalWriteStatus = 1
        onSaveFailed: function(error) {
            root.journalWriteStatus = -1;
            root.journalWriteError = String(error);
        }
    }

    FileView {
        id: deltaFile
        path: Qt.resolvedUrl("../../git-operation-journal-delta.json")
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        printErrors: false
        onSaved: root.deltaWriteStatus = 1
        onSaveFailed: function(error) {
            root.deltaWriteStatus = -1;
            root.deltaWriteError = String(error);
        }
    }

    Component.onCompleted: {
        if (!storageReady)
            load();
    }
}
