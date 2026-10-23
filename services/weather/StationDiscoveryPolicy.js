.pragma library

// Temporary normalized source records for the three unpopulated station
// domains. These are discovery records, not claims of media playback/maps.
function safeUrl(value) {
    const text = String(value || "").trim();
    return /^https?:\/\/[^\s<>"']+$/i.test(text) ? text : "";
}
function shortText(value, limit) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, limit);
}
function formatDate(value) {
    const raw = String(value || "");
    const match = raw.match(/^(\d{8})T(\d{4})/);
    return match ? match[1].slice(4, 6) + "-" + match[1].slice(6, 8)
            + " " + match[2].slice(0, 2) + ":" + match[2].slice(2) + " UTC"
          : raw.slice(0, 16).replace("T", " ");
}
function parseEvents(root) {
    if (!root || !Array.isArray(root.events))
        throw new Error("Invalid NASA EONET response");
    const rows = [];
    const seen = {};
    for (let i = 0; i < root.events.length; ++i) {
        const event = root.events[i];
        if (!event || !event.id || !event.title || seen[event.id])
            continue;
        seen[event.id] = true;
        const cat = Array.isArray(event.categories) && event.categories.length
                    ? shortText(event.categories[0].title, 60) : "NATURAL EVENT";
        const points = Array.isArray(event.geometry) ? event.geometry : [];
        const latest = points.length ? points[points.length - 1] : null;
        let coords = "";
        if (latest && latest.type === "Point"
                && Array.isArray(latest.coordinates)
                && latest.coordinates.length >= 2) {
            const lon = Number(latest.coordinates[0]);
            const lat = Number(latest.coordinates[1]);
            if (isFinite(lon) && isFinite(lat)
                    && Math.abs(lon) <= 180 && Math.abs(lat) <= 90)
                coords = lat.toFixed(2) + ", " + lon.toFixed(2);
        }
        rows.push({
            title: shortText(event.title, 160),
            detail: cat + (coords ? " // " + coords : ""),
            time: latest ? shortText(latest.date, 22) : "",
            url: safeUrl(event.link),
            action: "OPEN NASA EVENT"
        });
    }
    return rows.slice(0, 20);
}
function parseNews(root) {
    if (!root || !Array.isArray(root.articles))
        throw new Error("Invalid GDELT article list");
    const seen = {};
    const rows = [];
    for (let i = 0; i < root.articles.length; ++i) {
        const a = root.articles[i];
        const url = a ? safeUrl(a.url) : "";
        if (!url || seen[url] || !a.title)
            continue;
        seen[url] = true;
        rows.push({
            title: shortText(a.title, 180),
            detail: shortText(a.domain, 45)
                    + (a.sourcecountry ? " // " + shortText(a.sourcecountry, 36) : ""),
            time: formatDate(a.seendate),
            url: url,
            action: "READ ARTICLE"
        });
    }
    return rows.slice(0, 20);
}
function parseRadio(payload) {
    if (!Array.isArray(payload))
        throw new Error("Invalid Radio Browser station list");
    const rows = [];
    const seen = {};
    for (let i = 0; i < payload.length; ++i) {
        const station = payload[i];
        if (!station || !station.stationuuid || !station.name
                || station.lastcheckok === false || station.lastcheckok === 0)
            continue;
        if (seen[station.stationuuid])
            continue;
        seen[station.stationuuid] = true;
        const url = safeUrl(station.url_resolved || station.url);
        if (!url)
            continue;
        rows.push({
            title: shortText(station.name, 140),
            detail: shortText(station.country, 44)
                + " // " + shortText(station.codec, 18)
                + (Number(station.bitrate) > 0 ? " " + station.bitrate + "kbps" : ""),
            time: shortText(station.language, 32),
            url: url,
            action: "OPEN STREAM URL"
        });
    }
    return rows.slice(0, 20);
}
function parse(kind, root) {
    if (kind === "map") return parseEvents(root);
    if (kind === "news") return parseNews(root);
    if (kind === "radio") return parseRadio(root);
    throw new Error("Unknown station discovery domain");
}
