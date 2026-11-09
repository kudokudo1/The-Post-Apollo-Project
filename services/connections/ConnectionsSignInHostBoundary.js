.pragma library

// CPU++ V4 presentation-only bridge boundary.
// This file intentionally has NO transport, host trust, operator-consent,
// credential or auth state input. The C4b/C3e evidence reader is not an
// Identity Center Sign In command channel. An authenticated owner adapter
// must be separately approved, installed and reviewed before actuators exist.
function offline() {
    return {
        heading: "SIGN IN LOCKED // TRUSTED HOST REQUIRED",
        hostStatus: "HOST // NOT ENROLLED",
        commandStatus: "SIGN-IN CHANNEL // NOT CONNECTED",
        consentStatus: "CONSENT // NOT VERIFIED",
        helpText: "STATUS INSPECTION IS READ-ONLY. NO LOGIN REQUEST CAN BE SENT.",
        canBeginSignIn: false,
        canCancel: false,
        canRetry: false,
        canConnect: false,
        canDisconnect: false,
        canConnectAll: false
    };
}
