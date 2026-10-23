.pragma library

// PRIVATE, MEMORY-ONLY staging for a future authenticated mail adapter.
// Not a transport and not an authenticator. There is intentionally no
// live NotificationsService caller yet. Without BOTH injected functions,
// this ledger refuses every admission.
//
// verifyFromTrustedAdapter(proposal) must independently authenticate the
// adapter, account, exact message AND its binding to the native event ID.
// It must return a VERIFIED record built inside that boundary, not a copied
// client-provided "attested": true assertion or a subject/URL guess.
// isLiveEvent(eventId) must consult NotificationsService's transient event
// registry, NOT saved history. Both functions belong to a separately
// reviewed trusted boundary. Do not expose ledger contents to QML models.
function createLedger(verifyFromTrustedAdapter, isLiveEvent) {
    const entries = Object.create(null);
    // Rejected/revoked event leases cannot be replayed before their expiry.
    const revoked = Object.create(null);
    const maxEntries = 64;
    const maxAgeMs = 2 * 60 * 1000;
    const origin = "https://mail.proton.me";

    function opaque(value) {
        return typeof value === "string" && value.length >= 8
            && value.length <= 160 && /^[A-Za-z0-9._:~-]+$/.test(value);
    }

    function positive(value) {
        return Number.isSafeInteger(value) && value > 0;
    }

    function clock(value) {
        return Number.isSafeInteger(value) && value >= 0;
    }

    function normalized(record, nowMs) {
        if (!record || typeof record !== "object"
                || record.attested !== true
                || !opaque(record.eventId) || !opaque(record.accountKey)
                || !clock(record.expiresAtMs)
                || record.expiresAtMs <= nowMs
                || record.expiresAtMs - nowMs > maxAgeMs
                || !record.references || typeof record.references !== "object")
            return null;

        const refs = record.references;
        const keys = Object.keys(refs);
        if (!keys.length || keys.length > 2
                || keys.some(key => key !== "browser" && key !== "bridge"))
            return null;

        const references = {};
        if (refs.browser !== undefined) {
            const b = refs.browser;
            if (!b || b.attested !== true
                    || b.accountKey !== record.accountKey
                    || b.origin !== origin || !opaque(b.messageKey))
                return null;
            references.browser = {
                attested: true, accountKey: record.accountKey,
                origin: origin, messageKey: b.messageKey
            };
        }
        if (refs.bridge !== undefined) {
            const b = refs.bridge;
            if (!b || b.attested !== true
                    || b.accountKey !== record.accountKey
                    || !opaque(b.mailboxKey)
                    || !positive(b.uidValidity) || !positive(b.uid))
                return null;
            references.bridge = {
                attested: true, accountKey: record.accountKey,
                mailboxKey: b.mailboxKey,
                uidValidity: b.uidValidity, uid: b.uid
            };
        }
        return {
            eventId: record.eventId,
            accountKey: record.accountKey,
            attested: true,
            expiresAtMs: record.expiresAtMs,
            references: references
        };
    }

    function clone(record) {
        const r = record.references;
        const refs = {};
        if (r.browser)
            refs.browser = Object.assign({}, r.browser);
        if (r.bridge)
            refs.bridge = Object.assign({}, r.bridge);
        return {
            eventId: record.eventId,
            accountKey: record.accountKey,
            attested: record.attested,
            expiresAtMs: record.expiresAtMs,
            references: refs
        };
    }

    function live(eventId) {
        if (typeof isLiveEvent !== "function")
            return false;
        try {
            return isLiveEvent(eventId) === true;
        } catch (_) {
            return false;
        }
    }

    function purge(nowMs) {
        if (!clock(nowMs))
            return 0;
        let removed = 0;
        for (const id of Object.keys(revoked)) {
            if (revoked[id] <= nowMs || !live(id))
                delete revoked[id];
        }
        for (const id of Object.keys(entries)) {
            if (entries[id].expiresAtMs <= nowMs || !live(id)) {
                delete entries[id];
                removed++;
            }
        }
        return removed;
    }

    function aliases(record) {
        const refs = record.references, keys = [];
        if (refs.browser)
            keys.push("browser|" + record.accountKey + "|" + refs.browser.messageKey);
        if (refs.bridge)
            keys.push("bridge|" + record.accountKey + "|"
                + refs.bridge.mailboxKey + "|"
                + refs.bridge.uidValidity + "|" + refs.bridge.uid);
        return keys;
    }

    function admit(proposal, nowMs) {
        // Never take source identity from a page-probe result or desktop card.
        if (typeof verifyFromTrustedAdapter !== "function"
                || typeof isLiveEvent !== "function")
            return "transport-not-connected";
        if (!clock(nowMs))
            return "invalid-clock";
        purge(nowMs);

        let verified;
        try {
            verified = verifyFromTrustedAdapter(proposal);
        } catch (_) {
            return "untrusted-binding";
        }
        const candidate = normalized(verified, nowMs);
        if (!candidate)
            return "untrusted-binding";
        if (!live(candidate.eventId))
            return "event-not-live";
        if (Object.prototype.hasOwnProperty.call(revoked, candidate.eventId))
            return "event-revoked";
        if (Object.prototype.hasOwnProperty.call(entries, candidate.eventId))
            return "event-already-bound";
        if (Object.keys(entries).length >= maxEntries
                || Object.keys(revoked).length >= maxEntries)
            return "capacity-exceeded";

        const incomingAliases = aliases(candidate);
        for (const id of Object.keys(entries)) {
            const occupied = aliases(entries[id]);
            if (incomingAliases.some(alias => occupied.indexOf(alias) !== -1))
                return "message-already-bound";
        }
        entries[candidate.eventId] = candidate;
        return "accepted";
    }

    // Private backend read only; NEVER feed this value to a UI ListModel,
    // notification history, log, or untrusted browser/desktop sender.
    function lookup(eventId, nowMs) {
        if (!clock(nowMs) || !opaque(eventId))
            return null;
        purge(nowMs);
        if (!Object.prototype.hasOwnProperty.call(entries, eventId)
                || !live(eventId))
            return null;
        return clone(entries[eventId]);
    }

    function revoke(eventId) {
        if (!opaque(eventId)
                || !Object.prototype.hasOwnProperty.call(entries, eventId))
            return false;
        revoked[eventId] = entries[eventId].expiresAtMs;
        delete entries[eventId];
        return true;
    }

    function reset() {
        // Transport disconnect revokes, rather than frees for reuse, every
        // current lease. A reconnect must never reuse an old event binding.
        for (const id of Object.keys(entries)) {
            revoked[id] = entries[id].expiresAtMs;
            delete entries[id];
        }
    }

    function size(nowMs) {
        purge(nowMs);
        return Object.keys(entries).length;
    }

    return { admit, lookup, revoke, reset, size };
}
