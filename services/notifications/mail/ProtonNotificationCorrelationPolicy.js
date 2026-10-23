.pragma library

// OFFLINE CORRELATION POLICY, NOT AN IDENTITY SOURCE.
// The existing browser readiness probe, notification text, Web Notification
// tag and selected Proton DOM row do NOT attest native event-to-email identity.
// Both witnesses must be independently obtained and authenticated by future
// trusted components. Neither is available from the current browser companion.
//
// makeVerifier(...) returns the callback expected by
// ProtonMailBindingLedger.createLedger(verifyFromTrustedAdapter, isLiveEvent).
// Do not wire it to NotificationsService before actual trusted producers exist.
function makeVerifier(nativeDeliveryFor, providerMessageFor, isLiveEvent, now) {
    const maxAgeMs = 120000;
    const protonOrigin = "https://mail.proton.me";

    function opaque(value) {
        return typeof value === "string"
            && value.length >= 8 && value.length <= 160
            && /^[A-Za-z0-9._:~-]+$/.test(value);
    }

    function when(value) {
        return Number.isSafeInteger(value) && value >= 0;
    }

    return function verify(proposal) {
        if (typeof nativeDeliveryFor !== "function"
                || typeof providerMessageFor !== "function"
                || typeof isLiveEvent !== "function"
                || typeof now !== "function")
            return null;
        if (!proposal || typeof proposal !== "object"
                || Array.isArray(proposal)
                || Object.keys(proposal).length !== 2
                || !opaque(proposal.eventId) || !opaque(proposal.adapterTicket))
            return null;

        let current, live, delivery, message;
        try {
            current = now();
            live = isLiveEvent(proposal.eventId);
            // These MUST read separate, authenticated in-memory registries.
            // No raw event text/URL/DOM IDs may be promoted into either.
            delivery = nativeDeliveryFor(proposal.eventId);
            message = providerMessageFor(proposal.adapterTicket);
        } catch (_) {
            return null;
        }
        if (!when(current) || live !== true
                || !delivery || !message
                || delivery === proposal || message === proposal
                || delivery === message)
            return null;

        // A native delivery witness must have been minted while the actual
        // notification was delivered by an authorized provider producer.
        // The current Brave/Proton DBus intake does not supply this witness.
        if (delivery.kind !== "TRUSTED_PROTON_DELIVERY_V1"
                || delivery.eventId !== proposal.eventId
                || delivery.provider !== "proton-mail"
                || delivery.origin !== protonOrigin
                || delivery.grouped !== false
                || !opaque(delivery.sourceEventKey)
                || !opaque(delivery.accountKey)
                || !opaque(delivery.messageKey)
                || !when(delivery.deliveredAtMs))
            return null;

        // A second authenticated account/message observation must be linked
        // to the SAME origin event by the provider adapter, not inferred from
        // the user's selection or subject equality. Conversations are barred.
        if (message.kind !== "TRUSTED_PROTON_MESSAGE_V1"
                || message.provider !== "proton-mail"
                || message.origin !== protonOrigin
                || message.messageKind !== "message"
                || !opaque(message.sourceEventKey)
                || !opaque(message.accountKey)
                || !opaque(message.messageKey)
                || !when(message.observedAtMs))
            return null;

        if (delivery.sourceEventKey !== message.sourceEventKey
                || delivery.accountKey !== message.accountKey
                || delivery.messageKey !== message.messageKey
                || delivery.deliveredAtMs > current
                || message.observedAtMs > current
                || current - delivery.deliveredAtMs > maxAgeMs
                || current - message.observedAtMs > maxAgeMs)
            return null;

        const expiresAtMs = Math.min(
            delivery.deliveredAtMs + maxAgeMs,
            message.observedAtMs + maxAgeMs
        );
        if (expiresAtMs <= current)
            return null;

        // All values are taken from independently verified witness registries,
        // not from proposal fields. The ledger still validates TTL,
        // uniqueness, liveness and event revocation before admitting this.
        return {
            eventId: delivery.eventId,
            accountKey: delivery.accountKey,
            attested: true,
            expiresAtMs: expiresAtMs,
            references: {
                browser: {
                    attested: true,
                    accountKey: message.accountKey,
                    origin: protonOrigin,
                    messageKey: message.messageKey
                }
            }
        };
    };
}
