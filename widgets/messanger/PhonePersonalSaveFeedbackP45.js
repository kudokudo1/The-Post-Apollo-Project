// PHONE P45 // Content-free save feedback pending real authenticated service.
// This is presentation only. QML can forge any input, so success and durable
// SAVED states are intentionally impossible in this reducer.
var STATES = {
    HOST_UNAVAILABLE: "HOST UNAVAILABLE // NOT SAVED",
    KEY_LOCKED: "PERSONAL KEY LOCKED // NOT SAVED",
    CONSENT_REVOKED: "CONSENT REVOKED // NOT SAVED",
    CONTACT_STALE: "CONTACT CHANGED // NOT SAVED",
    PARTIAL_UNCONFIRMED: "PARTIAL CHANGE // VERIFY WITH TRUSTED HOST",
    COMMIT_UNCERTAIN: "WRITE RESULT UNCERTAIN // DO NOT RETRY",
    INVALID_EDIT: "NO VALID CHANGE TO SAVE"
};
function classify(value) {
    var code = value && typeof value === "object" && !Array.isArray(value)
               && Object.keys(value).length === 1
               && typeof value.status === "string"
               ? value.status : "HOST_UNAVAILABLE";
    if (!Object.prototype.hasOwnProperty.call(STATES, code))
        code = "HOST_UNAVAILABLE";
    return {
        status: code,
        text: STATES[code],
        saved: false,
        retryAuthorized: false,
        productionEnabled: false
    };
}
