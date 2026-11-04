.pragma library

// C2e: visible review of the planned grant contract. This is a *display*
// policy, never a consent token, active session, permission grant or secret.
// Only frozen broker-defined requirements are accepted; no caller-supplied
// scope, consumer, provider URL or account is a source of authority.
function preview(requirement) {
    var r = requirement || {};
    var allowlisted = r.provider === "nasa-firms" || r.provider === "proton-mail";
    if (r.known !== true || r.grantEnabled !== false || !allowlisted ||
            !Array.isArray(r.operations) || !Array.isArray(r.consumers))
        return {known:false,phase:"UNAVAILABLE",provider:"",operations:[],
                consumers:[],authentication:"",canApprove:false,
                status:"REVIEW UNAVAILABLE // NO VALID PROVIDER"};
    var operations = [];
    var consumers = [];
    if (r.provider === "nasa-firms") {
        if (r.credentialKind !== "api-key" ||
                r.operations.length !== 1 || r.operations[0] !== "fires.hotspots.read" ||
                r.consumers.length !== 1 || r.consumers[0] !== "weather-earth")
            return preview(null);
        operations = ["fires.hotspots.read"];
        consumers = ["weather-earth"];
    } else {
        if (r.credentialKind !== "mail-session" ||
                r.operations.length !== 3 ||
                r.operations[0] !== "mail.read" ||
                r.operations[1] !== "mail.send" ||
                r.operations[2] !== "mail.modify" ||
                r.consumers.length !== 2 ||
                r.consumers[0] !== "social-mail" ||
                r.consumers[1] !== "notifications-mail")
            return preview(null);
        operations = ["mail.read", "mail.send", "mail.modify"];
        consumers = ["social-mail", "notifications-mail"];
    }
    return {known:true,phase:"REVIEW_ONLY",provider:r.provider,
            operations:operations,consumers:consumers,
            authentication:"HOST IDENTITY + OPERATOR CONSENT REQUIRED",
            canApprove:false,hasActiveGrant:false,
            status:"NOT AUTHORIZED // HOST APPROVAL NOT CONNECTED"};
}

// This function never grants an operation, regardless of UI acknowledgement,
// keyring availability, caller IDs or request booleans.
function decision(previewState, requested) {
    var r = previewState || {};
    if (!r.known) return {allowed:false,reason:"NO_VERIFIED_REVIEW"};
    if (requested === "deny" || requested === "close")
        return {allowed:false,reason:"REVIEW_DISMISSED"};
    return {allowed:false,reason:"HOST_CONSENT_NOT_CONNECTED"};
}
