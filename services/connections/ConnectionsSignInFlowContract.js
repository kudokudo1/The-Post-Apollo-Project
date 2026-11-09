.pragma library

// CPU++ V3 sign-in lifecycle CONTRACT, not a transport, identity verifier,
// OAuth client, consent grant, or authority source. The runtime view is fixed
// offline until a separately approved protected Identity host adapter exists.
var SCHEMA = "post-apollo.identity.signin-event.v0";
var PHASES = ["REQUESTED", "WAITING_FOR_USER", "VERIFYING",
              "AUTHENTICATED", "DENIED", "CANCELLED", "EXPIRED",
              "FAILED", "HOST_LOST"];
var TERMINAL = ["AUTHENTICATED", "DENIED", "CANCELLED", "EXPIRED",
                "FAILED", "HOST_LOST"];
var TRANSITIONS = {
    REQUESTED: ["WAITING_FOR_USER", "VERIFYING", "CANCELLED", "FAILED",
                "EXPIRED", "HOST_LOST"],
    WAITING_FOR_USER: ["VERIFYING", "DENIED", "CANCELLED", "FAILED",
                       "EXPIRED", "HOST_LOST"],
    VERIFYING: ["AUTHENTICATED", "FAILED", "EXPIRED", "HOST_LOST"]
};
var REASONS = {
    AUTHENTICATED: "NONE",
    DENIED: "CONSENT_DENIED",
    CANCELLED: "USER_CANCELLED",
    EXPIRED: "EXPIRED",
    FAILED: "AUTH_FAILED",
    HOST_LOST: "HOST_LOST"
};
var STAGES = [
    "01 // REQUEST SUBMITTED TO TRUSTED HOST",
    "02 // WAITING FOR USER AUTHENTICATION",
    "03 // HOST VERIFYING CALLBACK AND SESSION",
    "04 // HOST RECEIPT OR GUARDED FAILURE",
    "CANCEL // REQUEST OWNER MUST ACKNOWLEDGE",
    "RECOVERY // FRESH HOST-ISSUED REQUEST"
];

function ownExact(x, names) {
    return x !== null && typeof x === "object" && !Array.isArray(x)
           && Object.keys(x).length === names.length
           && names.every(function(k) {
               return Object.prototype.hasOwnProperty.call(x, k);
           });
}

function validEvent(e) {
    if (!ownExact(e, ["schema", "requestId", "sequence", "phase", "reason"])
        || e.schema !== SCHEMA
        || typeof e.requestId !== "string"
        || !/^[A-Za-z0-9_-]{16,96}$/.test(e.requestId)
        || !Number.isSafeInteger(e.sequence) || e.sequence < 1
        || PHASES.indexOf(e.phase) < 0
        || typeof e.reason !== "string")
        return false;
    if (TERMINAL.indexOf(e.phase) >= 0)
        return e.reason === REASONS[e.phase];
    return e.reason === "NONE";
}

// Contract transition EXERCISE for CI only. It never confers login authority.
// The future trusted owner must authenticate event provenance, sender, host,
// operator consent and receipt independently BEFORE using any event.
function simulate(prev, event) {
    if (!validEvent(event))
        return null;
    if (prev === null) {
        if (event.phase !== "REQUESTED" || event.sequence !== 1)
            return null;
    } else {
        if (!ownExact(prev, ["requestId", "sequence", "phase", "simulated"])
            || prev.simulated !== true
            || prev.requestId !== event.requestId
            || !Number.isSafeInteger(prev.sequence)
            || event.sequence !== prev.sequence + 1
            || !Object.prototype.hasOwnProperty.call(TRANSITIONS, prev.phase)
            || TRANSITIONS[prev.phase].indexOf(event.phase) < 0)
            return null;
    }
    return {
        requestId: event.requestId,
        sequence: event.sequence,
        phase: event.phase,
        simulated: true
    };
}

function offline() {
    return {
        label: "SIGN-IN COMMAND CHANNEL // NOT CONNECTED",
        requestLabel: "REQUEST // NONE (NO TRUSTED HOST)",
        explanation: "NO SIGN-IN COMMAND, PROGRESS RECEIPT OR CANCEL ACK IS AVAILABLE.",
        stages: STAGES.slice(),
        canRequest: false,
        canCancel: false,
        canRetry: false,
        canConnect: false,
        canConnectAll: false
    };
}
