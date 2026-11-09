.pragma library

// CPU++ V5 PROPOSAL, not a command transport.
// Identity Center and C3e/C4b/C5 owners must approve the final wire schema.
// This accepts only a no-secret intent SHAPE for negotiation/review. It never
// creates, dispatches, authorizes, or infers a successful login operation.
var PROPOSED_SCHEMA = "post-apollo.identity.command-intent.proposed-v0";
var REQUEST_ID_PATTERN = /^[A-Za-z0-9_-]{16,96}$/;

function exactKeys(value, names) {
    return value !== null && typeof value === "object"
           && !Array.isArray(value)
           && Object.keys(value).length === names.length
           && names.every(function(key) {
               return Object.prototype.hasOwnProperty.call(value, key);
           });
}

function compatibleShape(value) {
    if (!exactKeys(value, ["schema", "action", "requestId"])
            || value.schema !== PROPOSED_SCHEMA
            || typeof value.action !== "string")
        return false;
    // BEGIN gets a new ID *only* from the trusted host; the UI never
    // chooses or recycles a host-minted request identifier.
    if (value.action === "BEGIN")
        return value.requestId === null;
    // CANCEL or RECOVER names an existing host-owned request. The host must
    // independently verify its ownership/liveness/terminal status; a string
    // with this shape never proves possession or grant.
    if (value.action === "CANCEL" || value.action === "RECOVER")
        return typeof value.requestId === "string"
               && REQUEST_ID_PATTERN.test(value.requestId);
    return false;
}

function review(value) {
    return {
        shape: compatibleShape(value) ? "CANDIDATE_ONLY" : "REJECTED",
        authority: "NONE",
        hostAuthenticated: false,
        operatorConsentVerified: false,
        canDispatch: false,
        canBeginSignIn: false,
        canCancel: false,
        canRecover: false,
        canConnectProvider: false,
        note: "OWNER-REVIEWED HOST COMMAND INTERFACE NOT INSTALLED"
    };
}
