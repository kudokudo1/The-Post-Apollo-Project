.pragma library

// Display-only identity for website notifications from recognized browsers.
// Do not change the real appName/desktopEntry, notification source policies,
// category facets, action targets, or stored original message.
function token(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function chromiumFamily(appName, desktopEntry) {
    const app = token(appName).toLowerCase();
    const desktop = token(desktopEntry).toLowerCase();
    return /^(brave(?: browser| web browser|-browser)?(?:-(?:beta|nightly))?|chromium|chromium-browser|google-chrome(?:-(?:stable|beta|unstable))?)$/.test(app)
        || /^(brave(?:-browser)?(?:-(?:beta|nightly))?|com\\.brave\\.browser|chromium|chromium-browser|google-chrome(?:-(?:stable|beta|unstable))?)$/.test(desktop);
}

// Treat only syntactically valid domain origins as site identities.
// Arbitrary mentions of a brand in a title or a notification body are NOT
// evidence of the notification's origin.
function hostnameFor(value) {
    let text = token(value).toLowerCase();
    if (text === "" || text.length > 300 || /[\s<>"'@\\]/.test(text))
        return "";
    text = text.replace(/^https?:\/\//, "");
    const slash = text.indexOf("/");
    if (slash >= 0)
        text = text.substring(0, slash);
    const colon = text.indexOf(":");
    if (colon >= 0) {
        if (!/^:[0-9]{1,5}$/.test(text.substring(colon)))
            return "";
        text = text.substring(0, colon);
    }
    if (text.length > 253 || !/^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/.test(text)
            || text.indexOf("..") !== -1)
        return "";
    const segments = text.split(".");
    if (segments.length < 2 || segments.some(s => s.length === 0 || s.length > 63
            || s.startsWith("-") || s.endsWith("-"))
            || !/^[a-z]{2,24}$/.test(segments[segments.length - 1]))
        return "";
    return text;
}

function siteFromChromiumBody(body) {
    // Chromium's native Linux bridge inserts "origin.example\n\n" at the
    // beginning of the body when x-kde-origin-name is not advertised.
    // Never scan notification titles or arbitrary body text for URLs.
    const text = String(body || "");
    const match = /^([^\r\n]{1,300})\r?\n\r?\n/.exec(text);
    return match ? hostnameFor(match[1]) : "";
}

function labelFor(host) {
    if (host === "youtube.com" || host.endsWith(".youtube.com")
            || host === "youtu.be")
        return "YouTube";
    if (host === "github.com" || host.endsWith(".github.com"))
        return "GitHub";
    if (host === "reddit.com" || host.endsWith(".reddit.com"))
        return "Reddit";
    if (host === "twitch.tv" || host.endsWith(".twitch.tv"))
        return "Twitch";
    // Unknown websites are represented by their actual host, not guessed
    // brand names. The UI can elide an unusually long hostname.
    return host.startsWith("www.") ? host.substring(4) : host;
}

function fromNotification(notification) {
    const blank = { host: "", label: "", icon: "" };
    if (!notification || !chromiumFamily(notification.appName, notification.desktopEntry))
        return blank;

    const hints = notification.hints || {};
    const fromHint = hostnameFor(hints["x-kde-origin-name"]);
    const host = fromHint || siteFromChromiumBody(notification.body);
    if (host === "")
        return blank;

    // Chromium's image-path for a web notification often contains the
    // sender's site icon. It is presentation media, never a navigation URL.
    return {
        host: host,
        label: labelFor(host),
        icon: token(notification.image)
    };
}
