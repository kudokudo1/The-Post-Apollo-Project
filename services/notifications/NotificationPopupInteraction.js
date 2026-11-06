.pragma library

// Transient popup-only input policy. Keep this separate from notification
// persistence, provider callbacks, and historical Hub navigation.
function nextOpenIntent(pendingIntent, armedAtMs, requestedIntent, nowMs, confirmWindowMs) {
    const intent = String(requestedIntent || "");
    const previous = String(pendingIntent || "");
    const armedAt = Number(armedAtMs);
    const now = Number(nowMs);
    const limit = Number(confirmWindowMs);
    if (intent === "" || !isFinite(now) || now <= 0
            || !isFinite(limit) || limit <= 0)
        return {confirmed: false, pendingIntent: "", armedAtMs: 0};
    if (previous === intent && isFinite(armedAt) && armedAt > 0
            && now >= armedAt && now - armedAt <= limit)
        return {confirmed: true, pendingIntent: "", armedAtMs: 0};
    return {confirmed: false, pendingIntent: intent, armedAtMs: now};
}

// Native non-default buttons may themselves open a destination. Keep regular
// reply/snooze/other native actions independent and unchanged.
function opensDestination(identifier, label) {
    if (String(identifier || "").toLowerCase() === "default")
        return true;
    const command = String(label || "").trim();
    return /^(?:open|view|visit|show|go to)(?:\b|\s|$)/i.test(command);
}
