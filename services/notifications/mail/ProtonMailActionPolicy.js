.pragma library

// POST-APOLLO MAIL // pure routing policy, not a mailbox client.
// Notification title/body/host are NEVER accepted as message identifiers.
// Browser and Bridge independently attest their own account+message binding.
// Actual connection/authentication and receipts belong to the adapter boundary.

var operations = ["mark-read", "trash", "archive", "snooze", "spam", "star"];
var bridgeOperations = ["mark-read", "trash", "archive", "spam", "star"];
var browserOperations = operations.slice();

function token(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function opaqueId(value) {
    const id = token(value);
    // Opaque adapter-generated IDs only, not account email addresses, URLs
    // or subjects. We do not log, persist or display these references.
    return id.length >= 8 && id.length <= 160
        && /^[A-Za-z0-9._:~-]+$/.test(id);
}

function positiveId(value) {
    const n = Number(value);
    return Number.isSafeInteger(n) && n > 0;
}

function validRef(kind, ref, accountKey) {
    if (!ref || ref.attested !== true || ref.accountKey !== accountKey)
        return false;
    if (kind === "browser")
        return ref.origin === "https://mail.proton.me"
            && opaqueId(ref.messageKey);
    if (kind === "bridge")
        return opaqueId(ref.mailboxKey)
            && positiveId(ref.uidValidity) && positiveId(ref.uid);
    return false;
}

function allowed(kind, operation) {
    if (kind === "bridge")
        return bridgeOperations.indexOf(operation) >= 0;
    if (kind === "browser")
        return browserOperations.indexOf(operation) >= 0;
    return false;
}

function routeFor(eventId, operation, binding, adapters, options) {
    const id = token(eventId);
    const action = token(operation);
    if (!opaqueId(id))
        return { status: "invalid-event" };
    if (operations.indexOf(action) === -1)
        return { status: "unsupported-operation" };
    if (!binding || binding.eventId !== id
            || !opaqueId(binding.accountKey)
            || binding.attested !== true)
        return { status: "unverified-message" };

    // The binding is a short-lived private adapter record, never a saved
    // notification. Browser data must not automatically bind Bridge UIDs.
    const now = options && Number.isFinite(options.nowMs)
        ? options.nowMs : Date.now();
    if (!Number.isFinite(binding.expiresAtMs)
            || binding.expiresAtMs <= now)
        return { status: "expired-binding" };

    // Bridge is preferred for supported operations. Browser is required
    // for native Proton Snooze; never attempt both for one click.
    const order = action === "snooze"
        ? ["browser"] : ["bridge", "browser"];
    for (let i = 0; i < order.length; i++) {
        const kind = order[i];
        const live = adapters && adapters[kind];
        const ref = binding.references && binding.references[kind];
        if (!allowed(kind, action) || !live || live.ready !== true
                || live.accountKey !== binding.accountKey
                || live.attested !== true || !Array.isArray(live.capabilities)
                || live.capabilities.indexOf(action) < 0
                || !validRef(kind, ref, binding.accountKey))
            continue;
        if ((action === "trash" || action === "spam")
                && !(options && options.confirmed === true))
            return { status: "confirmation-required", adapter: kind };
        return {
            status: "ready",
            adapter: kind,
            eventId: id,
            accountKey: binding.accountKey,
            operation: action,
            // Opaque adapter locator, never a URL, shell command or token.
            reference: ref
        };
    }
    return { status: "not-connected-or-not-matched" };
}

// Transport ACK != completed mailbox operation. Only a result from the
// selected adapter matching an issued request ID + exact target may confirm.
function receiptStatus(plan, requestId, receipt) {
    if (!plan || plan.status !== "ready" || !opaqueId(requestId))
        return "not-confirmed";
    if (!receipt || receipt.requestId !== requestId
            || receipt.adapter !== plan.adapter
            || receipt.accountKey !== plan.accountKey
            || receipt.operation !== plan.operation
            || receipt.eventId !== plan.eventId)
        return "not-confirmed";
    if (receipt.status === "applied" && receipt.verified === true)
        return "confirmed";
    if (receipt.status === "accepted")
        return "pending-provider";
    return "not-confirmed";
}
