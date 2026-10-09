// Hi-Fi evidence-only audio target resolver.
//
// A PipeWire sink-input index is an ephemeral coordinate, not a browser-tab ID.
// We auto-select ONLY for a unique exact MPRIS-title = PipeWire media.name match.
// Otherwise a user must explicitly select a stream. No fallback to "first stream".
//
// This has no write operations; three-second experiments remain separately armed.

function textKey(value) {
    return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function fingerprint(input) {
    const props = input && input.properties || {};
    return {
        index: Number(input && input.index),
        pid: String(props["application.process.id"] || ""),
        binary: String(props["application.process.binary"] || ""),
        applicationId: String(props["application.id"] || ""),
        mediaName: String(props["media.name"] || "")
    };
}

function hasProcessEvidence(input) {
    const id = fingerprint(input);
    return isFinite(id.index) && id.index >= 0
           && (!!id.pid || !!id.binary);
}

function sameFingerprint(input, expected) {
    if (!input || !expected || !hasProcessEvidence(input))
        return false;

    const actual = fingerprint(input);
    return actual.index === expected.index
           && actual.pid === expected.pid
           && actual.binary === expected.binary
           && actual.applicationId === expected.applicationId
           && actual.mediaName === expected.mediaName;
}

function titleMatches(title, inputs) {
    const key = textKey(title);
    const generic = ["playback", "audio", "unknown", "untitled",
                     "media", "no track metadata", "default"];
    if (key.length < 5 || generic.indexOf(key) !== -1)
        return [];

    return (inputs || []).filter(function(input) {
        const props = input && input.properties || {};
        return hasProcessEvidence(input)
               && textKey(props["media.name"]) === key;
    });
}

function bindManual(busName, title, input) {
    if (!String(busName || "") || !hasProcessEvidence(input))
        return null;

    return {
        busName: String(busName),
        title: String(title || ""),
        fingerprint: fingerprint(input)
    };
}

function resolve(busName, title, inputs, manualBinding) {
    const source = inputs || [];
    const bus = String(busName || "");
    const track = String(title || "");
    if (!bus)
        return {input: null, mode: "NONE", status: "NO MPRIS PLAYER"};

    if (manualBinding) {
        if (manualBinding.busName !== bus || manualBinding.title !== track)
            return {input: null, mode: "STALE", status: "MEDIA CHANGED / SELECT AGAIN"};

        const matches = source.filter(function(input) {
            return sameFingerprint(input, manualBinding.fingerprint);
        });
        return matches.length === 1
            ? {input: matches[0], mode: "MANUAL", status: "MANUAL STREAM / UNVERIFIED TAB"}
            : {input: null, mode: "STALE", status: "STREAM MISSING / SELECT AGAIN"};
    }

    const matches = titleMatches(track, source);
    if (matches.length === 1)
        return {input: matches[0], mode: "AUTO_TITLE",
                status: "EXACT MEDIA TITLE / TAB UNVERIFIED"};
    if (matches.length > 1)
        return {input: null, mode: "AMBIGUOUS",
                status: "MULTIPLE TITLE MATCHES / SELECT STREAM"};
    return {input: null, mode: "UNMATCHED",
            status: "NO EXACT TITLE MATCH / SELECT STREAM"};
}
