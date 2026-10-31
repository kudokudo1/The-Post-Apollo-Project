.pragma library

// A structured, display-only selection contract for an internal Weather
// Station viewer. GDELT supplies discovery metadata, NOT article body text.
function shortText(value, maxLength) {
    return String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .trim().replace(/\s+/g, " ").slice(0, maxLength);
}

function safeArticleUrl(value) {
    if (typeof value !== "string") return "";
    const url = value.trim();
    if (!url || url.length > 2048 || /[\s\\<>"']/.test(url)) return "";
    // Only publicly named HTTPS article hosts. Do not permit credentials,
    // arbitrary ports, raw IPs, localhost, or any shell/JS/file URL scheme.
    const match = /^https:\/\/([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?:\/|\?|#|$)/i.exec(url);
    if (!match) return "";
    const host = match[1].toLowerCase();
    if (/^\d+(?:\.\d+){3}$/.test(host)
            || host.endsWith(".localhost") || host.endsWith(".local"))
        return "";
    return url;
}

function articleHost(value) {
    const safe = safeArticleUrl(value);
    if (!safe) return "";
    const match = /^https:\/\/([^\/?#]+)/i.exec(safe);
    return match ? match[1].toLowerCase().replace(/^www\./, "") : "";
}

function normalizeNews(row) {
    if (!row || typeof row !== "object") return null;
    const title = shortText(row.title, 180);
    if (!title) return null;
    return {
        kind: "news",
        title: title,
        source: shortText(row.detail, 110) || "SOURCE NOT PROVIDED",
        time: shortText(row.time, 60) || "TIME NOT PROVIDED",
        rawTime: shortText(row.rawTime, 40),
        language: shortText(row.language, 48),
        domain: shortText(row.domain, 100),
        url: safeArticleUrl(row.url)
    };
}
