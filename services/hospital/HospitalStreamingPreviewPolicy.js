// Surgery streaming text preview contract. Pure QML-compatible JavaScript.
// Provisional words are NEVER placed in a saved/editor field. Only confirmed
// segments pass through HospitalDictationTextPolicy.appendTranscription.
// This is an in-memory presentation controller, not microphone/model IO.

const STREAMING_FIELDS = Object.freeze({
    intake: "SETUP", goal: "JOB", constraints: "JOB",
    done: "JOB", checklist: "JOB"
});
const MAX_REVISIONS = 300;
const MAX_TEXT = 4000;
const TOKEN = /^[A-Za-z0-9_-]{8,128}$/;
const CONTROLS = /[\x00-\x1f\x7f]/;
const PLACEHOLDER = /^\[\s*(?:BLANK_AUDIO|NO_SPEECH|NO_AUDIO|SILENCE|MUSIC)\s*\]$/i;

function begin(field, mode, original, maxLength, token) {
    if (!Object.prototype.hasOwnProperty.call(STREAMING_FIELDS, field)
            || STREAMING_FIELDS[field] !== mode
            || typeof original !== "string"
            || typeof token !== "string" || !TOKEN.test(token)
            || !Number.isInteger(maxLength) || maxLength < 1
            || maxLength > 16000 || original.length > maxLength)
        return null;
    return {
        active: true, field: field, mode: mode, token: token,
        maxLength: maxLength, original: original, draft: original,
        provisional: "", revision: 0
    };
}

function receive(state, token, event, insertConfirmed) {
    function reject(reason) {
        return {accepted: false, reason: reason, state: state,
                changedDraft: false};
    }
    if (!state || !state.active || typeof token !== "string"
            || token !== state.token)
        return reject("INVALID STREAMING OWNER");
    if (!event || typeof event !== "object" || Array.isArray(event)
            || Object.keys(event).length !== 4
            || !Object.prototype.hasOwnProperty.call(event, "kind")
            || !Object.prototype.hasOwnProperty.call(event, "text")
            || !Object.prototype.hasOwnProperty.call(event, "revision")
            || !Object.prototype.hasOwnProperty.call(event, "clear_provisional")
            || (event.kind !== "hypothesis" && event.kind !== "commit")
            || typeof event.text !== "string"
            || event.text.length > MAX_TEXT || CONTROLS.test(event.text)
            || typeof event.clear_provisional !== "boolean"
            || event.clear_provisional !== (event.kind === "commit")
            || !Number.isInteger(event.revision)
            || event.revision < 1 || event.revision > MAX_REVISIONS
            || event.revision !== state.revision + 1)
        return reject("INVALID STREAMING REVISION OR SHAPE");
    if (typeof insertConfirmed !== "function")
        return reject("NO CONFIRMED TEXT INSERTION POLICY");
    const text = event.text.trim();
    if (text.length && PLACEHOLDER.test(text))
        return reject("PLACEHOLDER STREAMING SPEECH");
    if (event.kind === "hypothesis") {
        const joiner = state.draft.length > 0
            && !/\s$/.test(state.draft) ? " " : "";
        if (state.draft.length + joiner.length + text.length > state.maxLength)
            return reject("STREAMING TEXT LIMIT");
        return {accepted: true, state: Object.assign({}, state, {
                    provisional: text, revision: event.revision
                }), changedDraft: false, reason: "REPLACEABLE PREVIEW"};
    }
    // A final segment is the only event authorized to modify editor text.
    let draft = state.draft;
    if (text) {
        const inserted = insertConfirmed(state.draft, text, state.maxLength);
        if (!inserted || inserted.accepted !== true
                || typeof inserted.text !== "string"
                || inserted.text.length > state.maxLength)
            return reject("STREAMING CONFIRMED TEXT LIMIT");
        draft = inserted.text;
    }
    return {accepted: true, state: Object.assign({}, state, {
                draft: draft, provisional: "", revision: event.revision
            }), changedDraft: draft !== state.draft,
            reason: "CONFIRMED WORDS ONLY"};
}

function finish(state, token) {
    if (!state || !state.active || token !== state.token)
        return null;
    // A final empty hypothesis never becomes permanent. Committed text stays.
    return Object.assign({}, state, {active: false, provisional: ""});
}

function cancel(state) {
    if (!state || !state.active)
        return null;
    return {original: state.original, draft: state.draft, field: state.field,
            mode: state.mode, active: false};
}
