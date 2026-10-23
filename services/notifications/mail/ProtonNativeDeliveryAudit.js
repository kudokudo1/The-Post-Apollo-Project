.pragma library

// Opt-in, count-and-presence-only diagnosis of the OS notification boundary.
// This NEVER turns browser metadata into a trusted Proton message witness.
// No message text, URLs, hint values, browser tags, accounts or IDs escape.
function isBrowserNotification(appName, desktopEntry) {
    const a = String(appName === undefined || appName === null ? "" : appName)
        .trim().toLowerCase();
    const d = String(desktopEntry === undefined || desktopEntry === null ? "" : desktopEntry)
        .trim().toLowerCase();
    const allow = /^(brave|brave-browser|chromium|google-chrome|chrome|firefox)(?:[ ._-](?:browser|beta|dev|nightly|stable|canary))?$/;
    return allow.test(a) || allow.test(d) || d === "com.brave.browser";
}

function collect(notification) {
    if (!notification || !isBrowserNotification(notification.appName,
                                                 notification.desktopEntry))
        return null;

    const hints = notification.hints &&
        typeof notification.hints === "object" && !Array.isArray(notification.hints)
        ? notification.hints : {};
    const owns = key => Object.prototype.hasOwnProperty.call(hints, key);
    // Never log hint keys. Check only a fixed allowlist of names, and return
    // booleans for their presence, NEVER their values.
    const tagHintPresent = owns("tag") || owns("notification-tag")
        || owns("x-chromium-notification-id")
        || owns("x-chromium-tag");
    const actionCount = notification.actions &&
        Number.isSafeInteger(notification.actions.length)
        ? notification.actions.length : 0;
    return {
        browserCandidate: true,
        hintCount: Math.min(99, Object.keys(hints).length),
        categoryHint: owns("category"),
        desktopEntryHint: owns("desktop-entry"),
        kdeOriginHint: owns("x-kde-origin-name"),
        tagHint: tagHintPresent,
        actionCount: Math.min(9, Math.max(0, actionCount)),
        // The OS API does not provide provider-attested message/event binding.
        messageIdentityVerified: false,
        canMutate: false
    };
}

function safeLine(observation) {
    if (!observation || observation.browserCandidate !== true
            || observation.messageIdentityVerified !== false
            || observation.canMutate !== false)
        return "";
    const count = (value, cap) => Number.isSafeInteger(value)
        && value >= 0 && value <= cap;
    const flag = value => typeof value === "boolean";
    if (!count(observation.hintCount, 99)
            || !count(observation.actionCount, 9)
            || !flag(observation.categoryHint)
            || !flag(observation.desktopEntryHint)
            || !flag(observation.kdeOriginHint)
            || !flag(observation.tagHint)
            || Object.keys(observation).length !== 9)
        return "";
    return "PA_PROTON_DELIVERY_AUDIT"
        + " hintCount=" + observation.hintCount
        + " categoryHint=" + observation.categoryHint
        + " desktopEntryHint=" + observation.desktopEntryHint
        + " kdeOriginHint=" + observation.kdeOriginHint
        + " tagHint=" + observation.tagHint
        + " actionCount=" + observation.actionCount
        + " identity NOT verified";
}
