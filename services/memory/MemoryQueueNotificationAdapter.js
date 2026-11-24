// Unregistered CPU++ queue adapter. Call synchronously with the existing
// NotificationsService singleton; do not save or replay a reservation packet.
function offer(hub, packet, nowMs) {
    const kinds = {
        DEFERRED: ["DEFERRED", "warning"],
        ATTENTION: ["ATTENTION REQUIRED", "warning"],
        READY_ADVISORY: ["READY CHECK", "normal"],
        EXPIRED: ["EXPIRED", "normal"],
        CANCELLED: ["CANCELLED", "normal"]
    };
    const codes = {
        DEFERRED: ["BASE_OR_EXTENSION_INACTIVE", "UNEXPECTED_SWAP_IDENTITY",
            "UNEXPECTED_CAPACITY", "UNSUPPORTED_TARGET", "EXTENSION_OCCUPIED",
            "RAM_HEADROOM", "BASE_HEADROOM", "MEMORY_PRESSURE",
            "OPERATION_BUSY", "STABILITY_INTERVAL"],
        ATTENTION: ["OBSERVATION_UNAVAILABLE", "BOOT_CHANGED", "SOURCE_CHANGED",
            "OPERATION_AMBIGUOUS", "STALE_OBSERVATION", "INVALID_OBSERVATION",
            "OBSERVATION_ORDER_INVALID"],
        READY_ADVISORY: ["FRESH_AUTH_AND_ROOT_CHECK_REQUIRED"],
        EXPIRED: ["EXPIRED"], CANCELLED: ["CANCELLED"]
    };
    const p = packet;
    if (!p || p.version !== 1 || p.can_execute !== false
            || p.delivery_state !== "ATTEMPT_RESERVED"
            || typeof p.request_id !== "string"
            || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(p.request_id)
            || !Object.prototype.hasOwnProperty.call(kinds, p.kind)
            || codes[p.kind].indexOf(p.code) === -1
            || p.event_id !== "apollo-cpu-memory-" + p.request_id + "-" + p.kind.toLowerCase().replace(/_/g, "-")
            || !Number.isSafeInteger(p.target_gib) || p.target_gib < 0
            || p.target_gib > 64 || p.target_gib % 4 !== 0
            || !Number.isSafeInteger(p.original_actual_kib) || p.original_actual_kib < 0
            || !Number.isSafeInteger(p.observed_at) || p.observed_at < 0
            || !Number.isSafeInteger(p.checked_at_ms)
            || !Number.isSafeInteger(p.valid_before_wall_ms))
        return "INVALID_PACKET";
    if (!Number.isSafeInteger(nowMs) || nowMs < p.checked_at_ms
            || p.checked_at_ms < p.observed_at * 1000
            || nowMs >= p.valid_before_wall_ms)
        return "STALE_PACKET";
    if (!hub || hub.historyReady !== true || hub.policyReady !== true
            || ["ready", "new", "saved", "saving"].indexOf(hub.historyStatus) === -1
            || ["ready", "new", "saved", "saving"].indexOf(hub.policyStatus) === -1
            || !hub.notifications || typeof hub.notifications.get !== "function"
            || !Number.isInteger(hub.notifications.count)
            || hub.notifications.count < 0 || hub.notifications.count > 5000
            || typeof hub.pushRich !== "function"
            || typeof hub.normalize !== "function"
            || typeof hub.shouldBlockNotification !== "function")
        return "HUB_NOT_READY";

    function present() {
        for (let i = 0; i < hub.notifications.count; ++i)
            if (hub.notifications.get(i).id === p.event_id)
                return true;
        return false;
    }
    if (present())
        return "HISTORY_PRESENT";

    // Never present historical READY as current authorization or guaranteed
    // capacity. Existing Hub owns popup suppression, history and preferences.
    let message = "Requested managed NVMe target: " + p.target_gib + " GiB. ";
    if (p.kind === "READY_ADVISORY")
        message += "Conditions appeared eligible at the last check. Open CPU++ to recheck and authorize.";
    else if (p.kind === "EXPIRED" || p.kind === "CANCELLED")
        message += "Request " + p.kind.toLowerCase() + ". No adjustment is verified.";
    else
        message += "Last check: " + p.code.replace(/_/g, " ") + ". Review CPU++.";
    const entry = {
        id: p.event_id, source: "CPU++", sourceId: "cpu-plus-memory-queue",
        category: "internal", severity: kinds[p.kind][1],
        title: "CPU++ // MEMORY " + kinds[p.kind][0],
        message: message, tags: ["cpu-plus", "memory", "adjustment-queue"],
        metrics: { targetGiB: p.target_gib, originalActualKiB: p.original_actual_kib },
        context: { origin: "apollo", domain: "system", resourceId: "memory",
                   eventType: "memory-queue-" + p.kind.toLowerCase().replace(/_/g, "-"),
                   requestId: p.request_id, observedAt: p.observed_at,
                   advisoryOnly: true }
    };
    if (hub.shouldBlockNotification(hub.normalize(entry)))
        return "BLOCKED";
    hub.pushRich(entry);
    // Model presence is not disk persistence, popup delivery or operator read.
    return present() ? "HISTORY_OBSERVED" : "OFFER_OUTCOME_UNKNOWN";
}
