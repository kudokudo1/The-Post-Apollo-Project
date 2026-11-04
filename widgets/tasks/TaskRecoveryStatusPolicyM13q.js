.pragma library

// TASKS M13q // display-only projection of shared C2 keyring probe and
// literal-false TASKS recovery gates. This is NOT the M13p fake review
// fixture, a consent token, an authenticated host receipt or a key client.
// Any future enabled flag makes readiness UNVERIFIED, never actionable.
// No QML import of credential material, request IDs or draft contents.

var PROVIDERS = {
    "SERVICE_ACQUIRED": "KEYRING FOUND // UNLOCK UNKNOWN",
    "SERVICE_NOT_RUNNING": "KEYRING SERVICE NOT RUNNING",
    "SESSION_BUS_UNAVAILABLE": "SESSION BUS UNAVAILABLE",
    "DBUS_PROBE_TOOL_MISSING": "DBUS PROBE TOOL MISSING",
    "UNEXPECTED_DBUS_RESPONSE": "KEYRING RESPONSE UNVERIFIED",
    "UNVERIFIED": "KEYRING RESPONSE UNVERIFIED",
    "NOT CHECKED": "KEYRING NOT CHECKED",
    "NOT_CHECKED": "KEYRING NOT CHECKED"
};

function view(data) {
    var x = data || {};
    var checking = x.providerChecking === true;
    var status = typeof x.providerStatus === "string" ? x.providerStatus : "";
    var known = Object.prototype.hasOwnProperty.call(PROVIDERS, status);
    var providerStatus = checking ? "CHECKING" : known ? status : "UNVERIFIED";
    var providerLabel = checking ? "CHECKING LOCAL KEYRING"
        : known ? PROVIDERS[status] : "KEYRING STATUS UNVERIFIED";
    var providerPresent = !checking && status === "SERVICE_ACQUIRED";
    var unexpectedActivation = x.brokerCredentialActionsEnabled !== false
        || x.recoveryEnabled !== false
        || x.recoveryStorageAuthorized !== false
        || x.recoveryUnlockAuthorized !== false
        || x.draftHostEnabled !== false
        || x.draftHostWriteAuthorized !== false;
    return {
        providerStatus: providerStatus,
        providerLabel: providerLabel,
        providerPresent: providerPresent,
        recoveryStatus: unexpectedActivation
            ? "RECOVERY // STATE REQUIRES REVIEW"
            : "RECOVERY // OFF",
        hostStatus: "TRUSTED RECOVERY APPROVAL // NOT CONNECTED",
        checkpointStatus: "ENCRYPTED CHECKPOINT // NOT INSPECTED",
        captureStatus: "DRAFT CAPTURE // DISABLED",
        previewStatus: "UNLOCK + PREVIEW // DISABLED",
        clearStatus: "CHECKPOINT DELETE // DISABLED",
        sourceStatus: "SAVED TASKS // EXISTING WRITER ONLY",
        nextStep: "CPU++ > SETTINGS > CONNECTIONS // SHARED KEYRING STATUS",
        explanation: providerPresent
            ? "The OS keyring service is present. That does not prove a key is unlocked, consent exists, or TASKS recovery is enabled."
            : "This is a shared read-only keyring check. No draft or key is inspected. TASKS recovery remains off.",
        statusOnly: true,
        realGrantActive: false,
        keyringUnlocked: false,
        canCapture: false,
        canDecrypt: false,
        canPreview: false,
        canClear: false,
        canRestore: false,
        canWriteTasks: false
    };
}
