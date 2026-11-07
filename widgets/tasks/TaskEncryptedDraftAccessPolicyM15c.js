.pragma library

// TASKS M15c // Fixed-scoped operator review for future encrypted draft UX.
// This is a presentation/preflight contract, NOT a consent provider.
// Current Connections C2a has no TASKS credential provider or trusted host.
// Never import test-only M13p/M13t fixtures into production QML.
var OPERATIONS = {
    capture: {
        scope: "tasks.draft.capture.encrypted",
        title: "CAPTURE ENCRYPTED DRAFT",
        actionLabel: "SAVE ENCRYPTED DRAFT",
        description: "Protect one unfinished TASKS editor draft in a private encrypted checkpoint. Requires a separately authenticated opt-in and authorized encryption host."
    },
    preview: {
        scope: "tasks.draft.preview.unlocked",
        title: "UNLOCK + PREVIEW RECOVERY",
        actionLabel: "UNLOCK DRAFT PREVIEW",
        description: "Unlock and review a candidate without writing over saved TASKS. Requires its own trusted authorization, key release, and source conflict check."
    },
    clear: {
        scope: "tasks.draft.clear.encrypted",
        title: "CLEAR ENCRYPTED CHECKPOINT",
        actionLabel: "DELETE ENCRYPTED DRAFT",
        description: "Delete one specifically verified encrypted checkpoint after separate explicit confirmation. Never delete a saved task or automatically clear an editor."
    }
};
var STATES = {
    "SERVICE_ACQUIRED": "OS KEYRING FOUND // UNLOCK UNKNOWN",
    "SERVICE_NOT_RUNNING": "OS KEYRING NOT RUNNING",
    "SESSION_BUS_UNAVAILABLE": "OS SESSION BUS UNAVAILABLE",
    "DBUS_PROBE_TOOL_MISSING": "KEYRING PROBE TOOL MISSING",
    "UNEXPECTED_DBUS_RESPONSE": "KEYRING RESPONSE UNVERIFIED",
    "UNVERIFIED": "KEYRING RESPONSE UNVERIFIED",
    "NOT CHECKED": "OS KEYRING NOT CHECKED",
    "NOT_CHECKED": "OS KEYRING NOT CHECKED",
    "CHECKING": "KEYRING CHECK IN PROGRESS"
};
function safeText(x) {
    return typeof x === "string" && x.length <= 160;
}
function result(op, label, details) {
    return {
        scope: op.scope,
        title: op.title,
        actionLabel: op.actionLabel,
        description: op.description,
        status: label,
        explanation: details,
        requiredOwner: "CPU++ // SETTINGS // CONNECTIONS",
        previewRoute: "TASKS // SYNC // RECOVERY",
        draftDisposition: "KEEP UNSAVED DRAFT",
        confirmation: "SEPARATE CONFIRMATION REQUIRED",
        operationAvailable: false,
        hostAuthenticated: false,
        userConsentAuthenticated: false,
        keyReleaseAuthorized: false,
        encryptedCaptureAuthorized: false,
        encryptedPreviewAuthorized: false,
        encryptedClearAuthorized: false,
        sourceWriteAuthorized: false,
        automaticReplayAuthorized: false,
        draftClearAuthorized: false,
        realCheckpointInspected: false,
        draftTextRead: false,
        draftTextTransferred: false
    };
}
// This policy never sees usernames, file paths, keys, draft text or IDs.
function view(input, mode, inspected) {
    if(!Object.prototype.hasOwnProperty.call(OPERATIONS, mode))
        mode = "capture";
    var op = OPERATIONS[mode];
    if(!input || typeof input !== "object" || Array.isArray(input))
        return result(op,"ACCESS STATE NOT VERIFIED","No broker or editor readiness signals were supplied. Nothing was captured or unlocked.");
    var keys = Object.keys(input).sort().join(",");
    if(keys !== ["providerStatus","providerChecking","credentialActionsEnabled",
             "brokerKnown","brokerGrantEnabled","recoveryEnabled",
             "storageAuthorized","unlockAuthorized","draftHostEnabled",
             "draftHostWriteAuthorized","editorStatus"].sort().join(",")
        || typeof input.providerChecking !== "boolean"
        || typeof input.credentialActionsEnabled !== "boolean"
        || typeof input.brokerKnown !== "boolean"
        || typeof input.brokerGrantEnabled !== "boolean"
        || typeof input.recoveryEnabled !== "boolean"
        || typeof input.storageAuthorized !== "boolean"
        || typeof input.unlockAuthorized !== "boolean"
        || typeof input.draftHostEnabled !== "boolean"
        || typeof input.draftHostWriteAuthorized !== "boolean"
        || !safeText(input.providerStatus)
        || !Object.prototype.hasOwnProperty.call(STATES,input.providerStatus)
        || !safeText(input.editorStatus)
        || ["EDITOR STATUS // NOT VERIFIED",
            "EDITOR SAVE // PENDING / NOT CONFIRMED",
            "UNSAVED EDITOR CHANGE // OBSERVED",
            "NO UNSAVED CHANGES IN MONITORED EDITORS"
           ].indexOf(input.editorStatus) < 0)
        return result(op,"ACCESS STATE NOT VERIFIED","The permission or editor metadata was not recognized. No authority can be inferred.");
    if(input.credentialActionsEnabled || input.brokerGrantEnabled
        || input.recoveryEnabled || input.storageAuthorized
        || input.unlockAuthorized || input.draftHostEnabled
        || input.draftHostWriteAuthorized)
        return result(op,"UNEXPECTED AUTHORITY STATE // REVIEW REQUIRED",
            "One or more previously disabled authority flags changed. This screen refuses to promote a status report into permission. Independent host verification is required.");
    if(inspected !== true)
        return result(op,"ACCESS NOT CHECKED",
            "Select CHECK REQUIREMENTS to review this operation's fixed permission scope and current read-only status. This does not request a key or persist any draft.");
    if(input.providerChecking)
        return result(op,"KEYRING CHECK IN PROGRESS",
            "A presence-only probe is running. It does not unlock the keyring or authenticate consent.");
    if(!input.brokerKnown)
        return result(op,"TASKS CREDENTIAL PROVIDER // NOT REGISTERED",
            "The shared Connections broker does not register TASKS encrypted draft credentials. The keyring presence probe cannot provide capture, preview or deletion authority.");
    if(input.editorStatus === "EDITOR STATUS // NOT VERIFIED" && mode === "capture")
        return result(op,"EDITOR STATUS // NOT VERIFIED",
            "No monitored unsaved draft can be verified from the existing status-only editor signals. No draft text was requested.");
    if(input.editorStatus === "NO UNSAVED CHANGES IN MONITORED EDITORS" && mode === "capture")
        return result(op,"NO MONITORED UNSAVED DRAFT",
            "The monitored editors do not currently report unsaved changes. Other TASKS and Planner editor surfaces are outside this view.");
    return result(op,"TRUSTED CONSENT + KEY HOST // NOT CONNECTED",
        "The OS provider status is " + STATES[input.providerStatus] +
        ". The production trusted consent, key-release and encrypted-checkpoint host are still disabled.");
}
