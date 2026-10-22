.pragma library

// Proton Bridge IMAP adapter contract. This module intentionally performs
// NO socket I/O and stores NO Bridge credentials. Installation and validated
// local STARTTLS/SSL (including Bridge's certificate) are separate approvals.
var actions = ["mark-read", "trash", "archive", "spam", "star"];

function safeEndpoint(settings) {
    if (!settings || settings.host !== "127.0.0.1")
        return false;
    const port = Number(settings.port);
    return Number.isSafeInteger(port) && port >= 1 && port <= 65535
        && (settings.tlsMode === "starttls" || settings.tlsMode === "ssl")
        && settings.bridgeCertificateVerified === true;
}

function stateFromSession(session, settings) {
    if (!safeEndpoint(settings) || !session
            || session.authenticated !== true
            || session.messageIdentityVerified !== true
            || typeof session.accountKey !== "string"
            || !/^[A-Za-z0-9._:~-]{8,160}$/.test(session.accountKey))
        return { ready: false, capabilities: [] };
    const supported = Array.isArray(session.capabilities)
        ? session.capabilities : [];
    return {
        ready: true,
        attested: true,
        accountKey: session.accountKey,
        capabilities: actions.filter(function(op) {
            return supported.indexOf(op) !== -1;
        })
    };
}

function dormant() {
    return { ready: false, capabilities: [] };
}
