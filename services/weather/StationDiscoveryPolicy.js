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

function formatEventTime(value) {
    const millis = Date.parse(String(value || ""));
    if (!isFinite(millis))
        return String(value || "").slice(0, 22);
    const iso = new Date(millis).toISOString();
    return iso.slice(0, 10) + " " + iso.slice(11, 16) + " UTC";
}

function magnitudeLabel(event) {
    if (!event)
        return "";
    const value = Number(event.magnitudeValue);
    if (!isFinite(value))
        return "";
    const unit = shortText(event.magnitudeUnit, 24);
    const description = shortText(event.magnitudeDescription, 80);
    let label = String(value);
    if (unit)
        label += " " + unit;
    if (description)
        label += " // " + description;
    return label;
}

function sourceLabel(event) {
    const source = event && Array.isArray(event.sources) ? event.sources : [];
    const ids = [];
    for (let i = 0; i < source.length; i++) {
        const id = shortText(source[i] ? source[i].id : "", 40);
        if (id && ids.indexOf(id) < 0)
            ids.push(id);
    }
    return ids.slice(0, 6).join(" / ");
}
function formatDate(value) {
    const raw = String(value || "");
    const match = raw.match(/^(\d{8})T(\d{4})/);
    return match ? match[1].slice(4, 6) + "-" + match[1].slice(6, 8)
            + " " + match[2].slice(0, 2) + ":" + match[2].slice(2) + " UTC"
          : raw.slice(0, 16).replace("T", " ");
}

function canonicalNewsUrl(value) {
    const safe = safeUrl(value);
    if (!safe)
        return "";

    const withoutFragment = safe.split("#")[0];
    const match = withoutFragment.match(
        /^([a-z][a-z0-9+.-]*):\/\/([^\/?#]+)([^?#]*)(?:\?([^#]*))?$/i
    );
    if (!match)
        return withoutFragment;

    const scheme = String(match[1] || "").toLowerCase();
    let host = String(match[2] || "").toLowerCase();
    let path = String(match[3] || "");
    const query = String(match[4] || "");

    if (host.indexOf("www.") === 0)
        host = host.slice(4);
    if (path.length > 1 && path[path.length - 1] === "/")
        path = path.slice(0, -1);

    const kept = [];
    const parts = query ? query.split("&") : [];
    for (let i = 0; i < parts.length; i++) {
        const part = String(parts[i] || "").trim();
        if (!part)
            continue;
        const name = part.split("=")[0].toLowerCase();
        if (/^utm_/.test(name)
                || name === "fbclid"
                || name === "gclid"
                || name === "dclid"
                || name === "mc_cid"
                || name === "mc_eid")
            continue;
        kept.push(part);
    }
    kept.sort();

    return scheme + "://" + host + (path || "/")
         + (kept.length ? "?" + kept.join("&") : "");
}

function newsTitleKey(value) {
    return shortText(value, 180)
        .toLowerCase()
        .replace(/&amp;/g, "&")
        .replace(/&quot;|&#34;/g, '"')
        .replace(/&#39;|&apos;/g, "'")
        .replace(/[.,!?;:'"()[\]{}|/_—–-]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function headlineHas(text, pattern) {
    return pattern.test(String(text || "").toLowerCase());
}

function newsTopics(value) {
    const title = String(value || "").toLowerCase();
    const topics = [];

    const spaceWeather = headlineHas(title,
        /\b(aurora|geomagnetic|solar|sunspot|space weather|solar flare|coronal mass|cme)\b/);
    if (spaceWeather)
        topics.push("space");

    if (headlineHas(title,
            /\b(earthquake|quake|seismic|volcano|volcanic|eruption|tsunami|landslide)\b/))
        topics.push("earth");

    if (headlineHas(title,
            /\b(wildfire|wild fire|bushfire|forest fire|brush fire|fire|blaze|smoke)\b/))
        topics.push("fire");

    const ordinaryWeather = headlineHas(title,
        /\b(weather|forecast|storm|hurricane|cyclone|typhoon|tornado|rain|snow|blizzard|flood|drought|heatwave|heat wave|cold snap|temperature|winds?)\b/);
    const spaceStormOnly =
        /\b(geomagnetic|solar)\s+storm\b/.test(title)
        && !headlineHas(title,
            /\b(weather|forecast|hurricane|cyclone|typhoon|tornado|rain|snow|blizzard|flood|drought|heatwave|heat wave|cold snap|temperature|winds?)\b/);
    if (ordinaryWeather && !spaceStormOnly)
        topics.push("weather");

    return topics;
}

function filterNewsRows(rows, topic) {
    if (!Array.isArray(rows))
        return [];
    const wanted = String(topic || "all").toLowerCase();
    if (wanted === "all")
        return rows.slice();

    const result = [];
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const topics = row && Array.isArray(row.topics) ? row.topics : [];
        if (topics.indexOf(wanted) >= 0)
            result.push(row);
    }
    return result;
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

        const categories = Array.isArray(event.categories) ? event.categories : [];
        const category = categories.length && categories[0] ? categories[0] : {};
        const categoryId = shortText(category.id, 48);
        const categoryTitle = shortText(category.title, 60) || "NATURAL EVENT";

        const points = Array.isArray(event.geometry) ? event.geometry : [];
        const latest = points.length ? points[points.length - 1] : null;
        const geometryType = latest ? shortText(latest.type, 24) : "";
        let latitude = null;
        let longitude = null;
        let coordinateText = geometryType || "LOCATION UNAVAILABLE";

        if (latest && latest.type === "Point"
                && Array.isArray(latest.coordinates)
                && latest.coordinates.length >= 2) {
            const lon = Number(latest.coordinates[0]);
            const lat = Number(latest.coordinates[1]);
            if (isFinite(lon) && isFinite(lat)
                    && Math.abs(lon) <= 180 && Math.abs(lat) <= 90) {
                latitude = lat;
                longitude = lon;
                coordinateText = lat.toFixed(2) + ", " + lon.toFixed(2);
            }
        }

        const sources = sourceLabel(event);
        const magnitude = magnitudeLabel(event);
        rows.push({
            id: shortText(event.id, 80),
            title: shortText(event.title, 160),
            description: shortText(event.description, 360),
            category: categoryTitle,
            categoryId: categoryId,
            detail: categoryTitle + " // " + coordinateText,
            time: latest ? formatEventTime(latest.date) : "",
            rawTime: latest ? shortText(latest.date, 45) : "",
            geometryType: geometryType || "UNKNOWN",
            latitude: latitude,
            longitude: longitude,
            coordinates: coordinateText,
            sourceNames: sources || "SOURCE NOT LISTED",
            magnitude: magnitude || "NOT REPORTED",
            url: safeUrl(event.link),
            action: "INSPECT HERE"
        });
    }
    return rows.slice(0, 40);
}
function parseNews(root) {
    if (!root || !Array.isArray(root.articles))
        throw new Error("Invalid GDELT article list");

    const seenUrl = {};
    const seenTitle = {};
    const rows = [];

    for (let i = 0; i < root.articles.length; ++i) {
        const article = root.articles[i];
        const url = article ? safeUrl(article.url) : "";
        const title = article ? shortText(article.title, 180) : "";
        if (!url || !title)
            continue;

        const canonicalUrl = canonicalNewsUrl(url);
        const titleKey = newsTitleKey(title);
        if (!canonicalUrl)
            continue;

        // URL canonicalization removes only fragments and common tracking
        // parameters. Headline de-dupe is intentionally exact after
        // punctuation/whitespace normalization; this is not story clustering.
        if (seenUrl[canonicalUrl]
                || (titleKey.length >= 12 && seenTitle[titleKey]))
            continue;
        seenUrl[canonicalUrl] = true;
        if (titleKey.length >= 12)
            seenTitle[titleKey] = true;

        const domain = shortText(article.domain, 80);
        const country = shortText(article.sourcecountry, 48);
        const topics = newsTopics(title);
        rows.push({
            title: title,
            detail: domain + (country ? " // " + country : ""),
            domain: domain,
            country: country,
            time: formatDate(article.seendate),
            rawTime: shortText(article.seendate, 32),
            url: url,
            canonicalUrl: canonicalUrl,
            topics: topics,
            primaryTopic: topics.length ? topics[0] : "other",
            action: "READ ARTICLE"
        });
    }
    return rows.slice(0, 30);
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


// NEWS is a page-scoped QML component; the same engine can recreate it every
// time the operator switches tabs. The library's module state is intentionally
// shared between those instances for this one external GDELT endpoint. Never
// request again on remount within a cooldown, and preserve the last good rows.
// This cache is session-only; no disk, background server, or new fetch owner.
var _mapCache = {};
var _mapCacheTtlMs = 900000;

function mapCacheKey(category) {
    const key = String(category || "").trim();
    return key || "all";
}

function storeMapRows(category, rows, nowMs) {
    const now = Number(nowMs);
    if (!Array.isArray(rows) || !isFinite(now) || now <= 0)
        return;
    _mapCache[mapCacheKey(category)] = {
        rows: rows.slice(0, 40),
        updatedAtMs: now
    };
}

function cachedMapRows(category, nowMs) {
    const entry = _mapCache[mapCacheKey(category)];
    if (!entry)
        return {rows: [], updatedAtMs: 0, fresh: false};
    const now = Number(nowMs);
    const age = isFinite(now) && now > 0 ? now - entry.updatedAtMs : Infinity;
    return {
        rows: entry.rows.slice(),
        updatedAtMs: entry.updatedAtMs,
        fresh: age >= 0 && age < _mapCacheTtlMs
    };
}

var _newsNextAllowedMs = 0;
var _newsThrottleUntilMs = 0;
var _newsCachedRows = [];
var _newsCachedAtMs = 0;
var _news429Count = 0;
var _newsNeedsManualRetry = false;

function newsWaitMs(nowMs) {
    return Math.max(0, _newsNextAllowedMs - Number(nowMs));
}
function newsThrottled(nowMs) {
    return Number(nowMs) < _newsThrottleUntilMs;
}
function newsManualRetryRequired() {
    return _newsNeedsManualRetry;
}
function newsThrottleCount() {
    return _news429Count;
}
function reserveNewsRequest(nowMs) {
    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0 || newsWaitMs(now) > 0)
        return false;
    // Provider reports a 5-second minimum. Use a more conservative 30 s
    // across all NEWS remounts and manual retries in this QS engine.
    _newsNextAllowedMs = now + 30000;
    return true;
}
function recordNewsThrottle(nowMs) {
    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0) return 0;
    // The advertised "one request every 5 seconds" is not a guaranteed
    // recovery deadline after 429. Progressively cool down (5m,15m,30m,60m)
    // and never issue automatic GDELT retries after a provider rejection.
    _news429Count = Math.min(4, _news429Count + 1);
    const delays = [300000, 900000, 1800000, 3600000];
    const delayMs = delays[_news429Count - 1];
    _newsThrottleUntilMs = Math.max(_newsThrottleUntilMs, now + delayMs);
    _newsNextAllowedMs = Math.max(_newsNextAllowedMs, _newsThrottleUntilMs);
    _newsNeedsManualRetry = true;
    return delayMs;
}
function storeNewsRows(rows, nowMs) {
    if (!Array.isArray(rows) || !isFinite(nowMs) || Number(nowMs) <= 0)
        return;
    _newsCachedRows = rows.slice(0, 30);
    _newsCachedAtMs = Number(nowMs);
    _newsThrottleUntilMs = 0;
    _news429Count = 0;
    _newsNeedsManualRetry = false;
    // Successful GDELT results are stable enough to reuse in the panel
    // rather than refetching on every NEWS tab remount after 30 seconds.
    _newsNextAllowedMs = Math.max(_newsNextAllowedMs, Number(nowMs) + 900000);
}
function cachedNewsRows() {
    return {rows: _newsCachedRows.slice(), updatedAtMs: _newsCachedAtMs};
}

// curl -w adds a status suffix, including on HTTP errors with non-JSON bodies.
// It is not safe to assume HTTP 429 is a JSON article list or that -f exposes
// its body. Keep the body and HTTP status separate for informative UI states.
function splitHttpResponse(raw) {
    const input = String(raw === undefined || raw === null ? "" : raw);
    const marker = "\n__POST_APOLLO_HTTP__:";
    const i = input.lastIndexOf(marker);
    if (i < 0) return {status: 0, body: ""};
    const statusText = input.slice(i + marker.length).trim();
    if (!/^\d{3}$/.test(statusText)) return {status: 0, body: ""};
    return {status: Number(statusText), body: input.slice(0, i)};
}
