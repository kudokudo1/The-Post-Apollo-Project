.pragma library

// C2g display-only projection of the C2f *simulated* status record.
// Nothing here grants access, verifies a host, or authenticates a caller.
// Reject extra fields, forged live/credential flags, wrong scope and unknown
// lifecycle combinations. The default is always HOST NOT CONNECTED.
var STATES = {
    PENDING: {reasons:["AWAITING_SIMULATED_REVIEW"],text:"SIMULATED // PENDING"},
    APPROVED: {reasons:["SIMULATED_HOST_APPROVED"],text:"SIMULATED // APPROVED"},
    DENIED: {reasons:["OPERATOR_DENIED"],text:"SIMULATED // DENIED"},
    CANCELLED: {reasons:["HOST_CANCELLED","HOST_SHUTDOWN"],text:"SIMULATED // CANCELLED"},
    EXPIRED: {reasons:["REQUEST_EXPIRED"],text:"SIMULATED // EXPIRED"},
    COMPLETED: {reasons:["SYNTHETIC_OPERATION_COMPLETE"],text:"SIMULATED // COMPLETED"},
    FAILED: {reasons:["HOST_DISCONNECTED","FAKE_BROKER_APPROVAL_FAILED",
                      "FAKE_OPERATION_FAILED"],text:"SIMULATED // FAILED"}
};
var EXPECTED = [
    "ok","requestId","state","provider","consumer","operation","profile",
    "reason","expiresInMs","credentialPresent","realGrantActive",
    "canApproveInProduction","simulated"
];

function offline(provider) {
    return {known:provider === "nasa-firms" || provider === "proton-mail",
            state:"OFFLINE",title:"HOST NOT CONNECTED",
            explanation:"NO VERIFIED CONNECTIONS REQUEST CHANNEL",
            reviewOnly:true,live:false,canApprove:false,grantActive:false,
            expiresInMs:0,requestId:"",provider:provider || ""};
}

function project(record, selectedProvider) {
    var missing = offline(selectedProvider);
    // Only NASA has a simulated host contract in C2f. Proton must not inherit
    // fake NASA state just because the user switches the selected provider.
    if (selectedProvider !== "nasa-firms" || !record ||
            typeof record !== "object" || Array.isArray(record))
        return missing;
    var keys = Object.keys(record);
    if (keys.length !== EXPECTED.length) return missing;
    for (var i=0;i<EXPECTED.length;i++)
        if (!Object.prototype.hasOwnProperty.call(record,EXPECTED[i]))
            return missing;
    if (record.ok !== true || record.simulated !== true ||
            record.credentialPresent !== false ||
            record.realGrantActive !== false ||
            record.canApproveInProduction !== false ||
            record.provider !== "nasa-firms" ||
            record.consumer !== "weather-earth" ||
            record.operation !== "fires.hotspots.read" ||
            record.profile !== "ci-only-profile" ||
            typeof record.requestId !== "string" ||
            !/^[0-9a-f]{32}$/.test(record.requestId))
        return missing;
    if (typeof record.state !== "string" ||
            !Object.prototype.hasOwnProperty.call(STATES,record.state))
        return missing;
    var state = STATES[record.state];
    if (typeof record.reason !== "string" ||
            state.reasons.indexOf(record.reason) < 0)
        return missing;
    if (typeof record.expiresInMs !== "number" ||
            !isFinite(record.expiresInMs) ||
            record.expiresInMs < 0 || record.expiresInMs > 60000 ||
            Math.floor(record.expiresInMs) !== record.expiresInMs)
        return missing;
    if (record.state !== "PENDING" && record.state !== "APPROVED"
            && record.expiresInMs !== 0)
        return missing;
    // Do not display raw requestId or arbitrary payload text in QML. The
    // status is useful for inspection but NEVER represents a live grant.
    return {known:true,state:record.state,title:state.text,
            explanation:"FAKE HOST TEST ONLY // NO REAL PERMISSION",
            reviewOnly:true,live:false,canApprove:false,grantActive:false,
            expiresInMs:record.expiresInMs,requestId:"",provider:"nasa-firms"};
}

function canAuthorize(_view,_action) {
    return false;
}
