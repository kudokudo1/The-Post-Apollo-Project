.pragma library

// CPU++ Universal Sign-In presentation V1. This is not an authentication
// controller. It projects strict, separately owned authority booleans and
// exposes no credential-changing action, no session state, and no secrets.
function project(input) {
    var x = input && typeof input === "object" && !Array.isArray(input)
            ? input : {};
    var ownerConnected = x.identityHostConnected === true;
    var verifiedIdentity = ownerConnected
                           && x.identityAuthenticated === true;
    var credentialHost = x.credentialHostAuthenticated === true
                         && x.credentialActionsEnabled === true;
    var operatorConsent = x.operatorConsentAuthenticated === true;
    var readyForProviderActions = verifiedIdentity
                                  && credentialHost && operatorConsent;

    // UI is an integration bridge ONLY. Production actions are unavailable
    // until a separately reviewed owner registers and exposes them. Even a
    // malicious fixture with all input bits true cannot arm a Connect button.
    return {
        identityStatus: verifiedIdentity
                        ? "VERIFIED IDENTITY // OWNER REPORTED"
                        : "SIGN-IN HOST // NOT VERIFIED",
        identityNote: verifiedIdentity
                      ? "OPEN ID MANAGEMENT TO INSPECT HOST-OWNED MEMBERSHIPS."
                      : "THE EXISTING IDENTITY HOST HAS NO VERIFIED SIGN-IN ROUTE IN CPU++.",
        connectionStatus: x.localObservationSeen === true
                          ? "LOCAL HOST OBSERVED // NOT AUTHENTICATED"
                          : "LOCAL CONNECTIONS HOST // NOT VERIFIED",
        connectionNote: "SOCKET OBSERVATION IS NOT SIGNED HOST TRUST OR PROVIDER ACCESS.",
        providerStatus: "CONNECT / RECONNECT / DISCONNECT // UNAVAILABLE",
        providerNote: "INDIVIDUAL PROVIDER CONSENT AND CREDENTIAL OPERATIONS REMAIN DISABLED.",
        batchStatus: "CONNECT ALL // UNAVAILABLE",
        // These are policy gates, not a substitute for owner authorization.
        identityVerified: verifiedIdentity,
        hostCandidateReady: credentialHost,
        operatorConsentObserved: operatorConsent,
        prerequisitesObserved: readyForProviderActions,
        canBeginSignIn: false,
        canConnect: false,
        canReconnect: false,
        canDisconnect: false,
        canConnectAll: false
    };
}
