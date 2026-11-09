.pragma library

// CPU++ V2: a *display-only* journey view, never authentication or consent.
// Source is the existing IdentityCenterOrganizationDisplayReader snapshot.
// Its same-UID Unix socket and projected organization context cannot attest
// the installed host or authorize sign-in, even when it says "READY".
var SCHEMA = "post-apollo.identity.desktop-context-display.v0";
var STATES = ["READY", "NO_MEMBERSHIPS", "SIGNED_OUT",
              "NOT_CONNECTED", "UNAVAILABLE"];

function exact(value, keys) {
    return value !== null && typeof value === "object"
           && !Array.isArray(value)
           && Object.keys(value).length === keys.length
           && keys.every(function (key) {
               return Object.prototype.hasOwnProperty.call(value, key);
           });
}

function valid(snapshot) {
    if (!exact(snapshot, ["schema", "status", "organizations",
                          "portfolios", "canSwitchOrganization"])
            || snapshot.schema !== SCHEMA
            || STATES.indexOf(snapshot.status) < 0
            || snapshot.canSwitchOrganization !== false
            || !Array.isArray(snapshot.organizations)
            || !Array.isArray(snapshot.portfolios)
            || snapshot.organizations.length > 100
            || snapshot.portfolios.length > 100)
        return false;
    // Only the underlying existing reader validates organization contents.
    // This view never uses those contents or treats membership as permission.
    if (snapshot.status !== "READY" && snapshot.status !== "NO_MEMBERSHIPS")
        return snapshot.organizations.length === 0
               && snapshot.portfolios.length === 0;
    if (snapshot.status === "READY")
        return snapshot.organizations.length > 0;
    return snapshot.organizations.length === 0;
}

function project(snapshot, active) {
    var observed = "CONTEXT VIEW // NOT OPEN";
    var guidance = "OPEN STATUS TO QUERY THE EXISTING READ-ONLY IDENTITY DISPLAY.";
    if (active === true) {
        if (snapshot === null || snapshot === undefined) {
            observed = "CONTEXT VIEW // NO VALID RESPONSE YET";
            guidance = "THE HOST MAY BE ABSENT, BUSY OR UNAVAILABLE. NO LOGIN HAS STARTED.";
        } else if (!valid(snapshot)) {
            observed = "CONTEXT VIEW // INVALID RESPONSE";
            guidance = "UNTRUSTED DISPLAY DATA IS IGNORED. NO IDENTITY CLAIM ACCEPTED.";
        } else {
            switch (snapshot.status) {
                case "READY":
                    observed = "CONTEXT VIEW // DATA RETURNED (UNVERIFIED)";
                    guidance = "READ-ONLY ORGANIZATION DISPLAY IS NOT AUTHENTICATED SIGN-IN.";
                    break;
                case "NO_MEMBERSHIPS":
                    observed = "CONTEXT VIEW // NO MEMBERSHIPS REPORTED";
                    guidance = "NO HOST ORGANIZATIONS REPORTED. NO BUSINESS ACCESS INFERRED.";
                    break;
                case "SIGNED_OUT":
                    observed = "CONTEXT VIEW // SIGNED OUT REPORTED";
                    guidance = "THE READ-ONLY DISPLAY REPORTS SIGNED OUT; NO LOGIN COMMAND EXISTS HERE.";
                    break;
                case "NOT_CONNECTED":
                    observed = "CONTEXT VIEW // NOT CONNECTED";
                    guidance = "NO REACHABLE IDENTITY DISPLAY IS VERIFIED.";
                    break;
                case "UNAVAILABLE":
                    observed = "CONTEXT VIEW // UNAVAILABLE";
                    guidance = "NO USEABLE HOST DISPLAY IS AVAILABLE.";
                    break;
            }
        }
    }
    // Never return raw organization IDs, tokens, user names, credentials,
    // claims, errors, URLs or a success-like authenticated flag.
    return {
        displayStatus: observed,
        displayGuidance: guidance,
        hostStep: "01 // TRUSTED SIGN-IN HOST REQUIRED",
        signInStep: "02 // SIGN-IN NOT AVAILABLE",
        identityStep: "03 // AUTHENTICATED IDENTITY NOT VERIFIED",
        providerStep: "04 // PROVIDER CONNECTIONS LOCKED",
        signInButtonLabel: "SIGN IN // HOST REQUIRED",
        canBeginSignIn: false,
        canReconnect: false,
        canDisconnect: false,
        canConnectAll: false
    };
}
