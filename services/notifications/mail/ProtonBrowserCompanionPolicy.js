.pragma library

// The browser companion cannot identify an email from a desktop push
// notification or its subject. Until a message observation is authenticated
// and linked by a trusted adapter, it advertises NO mailbox actions.
var actions = ["mark-read", "trash", "archive", "snooze", "spam", "star"];
var approvedOrigin = "https://mail.proton.me";

function validOrigin(origin) {
    return origin === approvedOrigin;
}

function stateFromHandshake(handshake) {
    if (!handshake || handshake.protocol !== 1
            || handshake.kind !== "PONG"
            || handshake.origin !== approvedOrigin
            || handshake.mailboxAccess !== true
            || handshake.messageIdentityVerified !== true
            || typeof handshake.accountKey !== "string"
            || !/^[A-Za-z0-9._:~-]{8,160}$/.test(handshake.accountKey))
        return { ready: false, capabilities: [] };
    const claimed = Array.isArray(handshake.capabilities)
        ? handshake.capabilities : [];
    return {
        ready: true,
        attested: true,
        accountKey: handshake.accountKey,
        capabilities: actions.filter(function(action) {
            return claimed.indexOf(action) !== -1;
        })
    };
}

function dormant() {
    return { ready: false, capabilities: [] };
}
