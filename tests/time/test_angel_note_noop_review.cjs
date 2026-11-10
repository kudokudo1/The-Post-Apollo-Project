// Execute the actual Angel QML JS handlers in a fake in-memory environment.
// This test touches no Quickshell data, no Linux time, and no filesystem writes
// except reading the repository source under test.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const store = fs.readFileSync(
    path.join(root, "services/time/AngelObservationsStore.qml"), "utf8");
const pane = fs.readFileSync(
    path.join(root, "widgets/AngelPane.qml"), "utf8");

function handler(source, start, end) {
    const a = source.indexOf(start);
    const b = source.indexOf(end, a + start.length);
    assert.ok(a !== -1 && b > a, "Cannot locate QML handler: " + start);
    return source.slice(a, b);
}

const row = {id: "a199", digits: "624", observedAtMs: 1794280906000};
let draftRequests = 0;
let stagedWrites = 0;
let watchdogStarts = 0;
const storage = vm.createContext({
    writable: true,
    observations: [row],
    document: {observations: [row]},
    lastNoteUnchanged: false,
    feedback: "",
    pendingDocument: null,
    pendingKind: "",
    pendingNoteId: "",
    pendingNoteDraft: null,
    draftState: "empty",
    storageState: "ready",
    writePhase: "",
    errorCode: "",
    Journal: {
        setNote(doc, id, note) {
            if (id !== row.id || typeof note !== "string")
                return {ok: false, reason: "UNKNOWN_ID"};
            if (note.length > 280)
                return {ok: false, reason: "INVALID_NOTE"};
            return {ok: true, document: {
                observations: [{...row, note: note.trim()}]
            }};
        }
    },
    Draft: {
        create(item, note) {
            draftRequests++;
            return {ok: true, document: {draft: {
                id: item.id, before: item.note || "", after: note.trim()
            }}};
        }
    },
    saveWatchdog: {restart() {watchdogStarts++;}},
    draftFile: {setText() {stagedWrites++;}},
    Date
});
vm.runInContext(handler(store,
    "    function saveObservationNote(id, note) {",
    "    function acceptDraftLoaded(raw) {"), storage);

// A blank note on a blank observation: no draft, journal or watchdog.
assert.equal(storage.saveObservationNote("a199", ""), false);
assert.equal(storage.lastNoteUnchanged, true);
assert.match(storage.feedback, /UNCHANGED.*NO WRITE/);
assert.equal(draftRequests, 0);
assert.equal(stagedWrites, 0);
assert.equal(watchdogStarts, 0);
assert.equal(storage.writePhase, "");
assert.equal(storage.storageState, "ready");

// A note unchanged after whitespace normalization must also skip all writes.
row.note = "existing";
assert.equal(storage.saveObservationNote("a199", "  existing  "), false);
assert.equal(storage.lastNoteUnchanged, true);
assert.equal(stagedWrites, 0);
assert.equal(draftRequests, 0);
assert.equal(storage.writePhase, "");

// Invalid data cannot be mistaken for a successful no-op.
assert.equal(storage.saveObservationNote("a199", "x".repeat(281)), false);
assert.equal(storage.lastNoteUnchanged, false);
assert.equal(stagedWrites, 0);
assert.equal(draftRequests, 0);

// Genuine changes still stage one draft before the journal writer.
assert.equal(storage.saveObservationNote("a199", "new text"), true);
assert.equal(storage.lastNoteUnchanged, false);
assert.equal(storage.writePhase, "draft");
assert.equal(storage.storageState, "drafting");
assert.equal(draftRequests, 1);
assert.equal(stagedWrites, 1);
assert.equal(watchdogStarts, 1);

// A blocked writer never stages a new write, even if text is unchanged.
storage.writable = false;
assert.equal(storage.saveObservationNote("a199", "existing"), false);
assert.equal(storage.lastNoteUnchanged, false);
assert.equal(stagedWrites, 1);

// REVIEW and CANCEL are UI-only operations; they cannot touch the writer.
const draft = {id: "a189", after: "recoverable draft"};
const ui = vm.createContext({
    pane: {
        noteInFlightId: "", reviewingDraft: false,
        editingNoteId: "", selectedId: "", pendingDeleteId: "",
        noteSaveFeedback: ""
    },
    AngelObservationsStore: {noteDraft: draft, storageState: "stalled"},
    noteField: {
        text: "", focus: false, focused: 0,
        forceActiveFocus() {this.focused++;}
    }
});
vm.runInContext(handler(pane,
    "    function closeNoteEditor() {",
    "    function saveNote() {"), ui);
vm.runInContext(handler(pane,
    "    function reviewNoteDraft() {",
    "    function closeNoteEditor() {"), ui);
ui.pane.closeNoteEditor = ui.closeNoteEditor;
ui.reviewNoteDraft();
assert.equal(ui.pane.reviewingDraft, true);
assert.equal(ui.pane.editingNoteId, "a189");
assert.equal(ui.noteField.text, draft.after);
assert.equal(ui.noteField.focused, 1);
ui.reviewNoteDraft(); // same button again toggles closed
assert.equal(ui.pane.reviewingDraft, false);
assert.equal(ui.pane.editingNoteId, "");
assert.match(ui.pane.noteSaveFeedback, /NO WRITE/);

ui.reviewNoteDraft();
ui.closeNoteEditor(); // CANCEL while writer remains STALLED
assert.equal(ui.pane.reviewingDraft, false);
assert.equal(ui.pane.editingNoteId, "");
assert.equal(ui.AngelObservationsStore.storageState, "stalled");

// A real in-flight edit remains protected from accidental dismissal.
ui.pane.editingNoteId = "a199";
ui.pane.reviewingDraft = false;
ui.pane.noteInFlightId = "a199";
ui.closeNoteEditor();
assert.equal(ui.pane.editingNoteId, "a199");
assert.equal(ui.pane.noteInFlightId, "a199");

console.log("ANGEL_NOTE_NOOP_AND_REVIEW_HANDLERS_PASS");
