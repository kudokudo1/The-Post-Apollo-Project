.pragma library

// C2i presentation accepts only bounded observations from the fixed local
// Unix socket reader. It is NOT cryptographic/production host attestation.
// Same-user processes can impersonate a socket server; never enable grants.
var STATUS = {
    NOT_CHECKED:"LOCAL HOST NOT INSPECTED",
    CHECKING:"CHECKING LOCAL STATUS SOCKET",
    RUNTIME_UNAVAILABLE:"LOCAL RUNTIME UNAVAILABLE",
    RUNTIME_UNSAFE:"LOCAL STATUS SOCKET UNSAFE",
    HOST_NOT_FOUND:"NO LOCAL CONNECTIONS HOST",
    HOST_UNAVAILABLE:"LOCAL HOST NOT RESPONDING",
    PEER_UNVERIFIED:"LOCAL HOST PEER NOT VERIFIED",
    RESPONSE_INVALID:"LOCAL STATUS RESPONSE INVALID",
    OBSERVED_UNVERIFIED:"LOCAL HOST OBSERVED // NOT AUTHENTICATED"
};
var VALID_STATES = [
    "IDLE","PENDING","APPROVED","DENIED","CANCELLED",
    "EXPIRED","COMPLETED","FAILED"
];

function project(raw) {
    var status = "RESPONSE_INVALID";
    var state = "";
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
        var keys = Object.keys(raw);
        var wanted = ["status","provider","state","hostAuthenticated",
                      "credentialPresent","grantActive","canApprove"];
        if (keys.length === wanted.length &&
                wanted.every(function(k) {
                    return Object.prototype.hasOwnProperty.call(raw,k);
                }) &&
                typeof raw.status === "string" &&
                Object.prototype.hasOwnProperty.call(STATUS,raw.status) &&
                raw.provider === "nasa-firms" &&
                raw.hostAuthenticated === false &&
                raw.credentialPresent === false &&
                raw.grantActive === false &&
                raw.canApprove === false &&
                typeof raw.state === "string") {
            if (raw.status === "OBSERVED_UNVERIFIED") {
                if (VALID_STATES.indexOf(raw.state) >= 0) {
                    status = raw.status;
                    state = raw.state;
                }
            } else if (raw.state === "") {
                status = raw.status;
            }
        }
    }
    return {
        status:status,
        label:STATUS[status],
        state:state,
        stateLabel:state ? "OBSERVED // "+state+" // UNVERIFIED" : "",
        hostAuthenticated:false,grantActive:false,canApprove:false,
        observationOnly:true
    };
}

function offline() {
    return {
        status:"NOT_CHECKED",label:STATUS.NOT_CHECKED,state:"",
        stateLabel:"",hostAuthenticated:false,grantActive:false,
        canApprove:false,observationOnly:true
    };
}
