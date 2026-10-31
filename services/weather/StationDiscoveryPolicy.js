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

function newsExactSourceGroups(articles) {
    const source = Array.isArray(articles) ? articles : [];
    const groups = {};

    function addUnique(list, value) {
        const text = shortText(value, 80);
        if (text && list.indexOf(text) < 0)
            list.push(text);
    }

    for (let i = 0; i < source.length; i++) {
        const article = source[i];
        if (!article)
            continue;

        const title = shortText(article.title, 180);
        const key = newsTitleKey(title);
        const url = safeUrl(article.url);
        const canonicalUrl = canonicalNewsUrl(url);
        if (key.length < 12 || !canonicalUrl)
            continue;

        const domain = shortText(article.domain, 80);
        const country = shortText(article.sourcecountry, 48);
        const language = shortText(
            article.language || article.lang || article.sourcelang,
            48
        );

        if (!groups[key]) {
            groups[key] = {
                titleKey:key,
                articleCount:0,
                urls:[],
                domains:[],
                countries:[],
                languages:[]
            };
        }

        const group = groups[key];
        if (group.urls.indexOf(canonicalUrl) < 0) {
            group.urls.push(canonicalUrl);
            group.articleCount++;
        }
        addUnique(group.domains, domain);
        addUnique(group.countries, country);
        addUnique(group.languages, language);
    }

    const keys = Object.keys(groups);
    for (let i = 0; i < keys.length; i++) {
        const group = groups[keys[i]];
        group.sourceCount = group.domains.length;
        group.multiSource = group.sourceCount >= 2;
    }
    return groups;
}

function gdeltSeenMillis(value) {
    const raw = String(value || "").trim();
    const compact = raw.match(
        /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z?$/
    );
    if (compact) {
        const millis = Date.UTC(
            Number(compact[1]), Number(compact[2]) - 1,
            Number(compact[3]), Number(compact[4]),
            Number(compact[5]), Number(compact[6])
        );
        return isFinite(millis) ? millis : -1;
    }
    const millis = Date.parse(raw);
    return isFinite(millis) ? millis : -1;
}

function newsBatchSummary(rows) {
    const source = Array.isArray(rows) ? rows : [];
    const domains = {};
    const countries = {};
    const languages = {};
    let timedRows = 0;
    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (!row)
            continue;
        const domain = String(row.domain || "").trim().toLowerCase();
        const country = String(row.country || "").trim().toLowerCase();
        const language = String(row.language || "").trim().toLowerCase();
        if (domain)
            domains[domain] = true;
        if (country)
            countries[country] = true;
        if (language)
            languages[language] = true;
        if (Number(row.seenMillis) > 0)
            timedRows++;
    }
    return {
        articles:source.length,
        publishers:Object.keys(domains).length,
        countries:Object.keys(countries).length,
        languages:Object.keys(languages).length,
        timedRows:timedRows
    };
}

function newsSourceRegionGroups(rows) {
    const source = Array.isArray(rows) ? rows : [];
    const groups = {};

    function addUnique(list, value, limit) {
        const text = shortText(value, limit);
        if (text && list.indexOf(text) < 0)
            list.push(text);
    }

    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (!row)
            continue;

        const country = shortText(row.country, 48) || "UNLISTED";
        const key = country.toLowerCase();
        if (!groups[key]) {
            groups[key] = {
                id:country,
                country:country,
                articles:0,
                domains:[],
                languages:[],
                topics:[],
                latestSeenMillis:-1
            };
        }

        const group = groups[key];
        group.articles++;
        addUnique(group.domains, row.domain, 80);
        addUnique(group.languages, row.language, 48);

        const topics = Array.isArray(row.topics) ? row.topics : [];
        for (let j = 0; j < topics.length; j++)
            addUnique(group.topics, topics[j], 24);

        const seen = Number(row.seenMillis);
        if (isFinite(seen) && seen > group.latestSeenMillis)
            group.latestSeenMillis = seen;
    }

    const output = Object.keys(groups).map(function(key) {
        const group = groups[key];
        group.publishers = group.domains.length;
        return group;
    });

    output.sort(function(a, b) {
        if (a.articles !== b.articles)
            return b.articles - a.articles;
        if (a.publishers !== b.publishers)
            return b.publishers - a.publishers;
        return a.country.localeCompare(b.country);
    });
    return output;
}


function newsStoryTokens(value) {
    const stop = {
        "the":true, "and":true, "for":true, "from":true, "with":true,
        "that":true, "this":true, "into":true, "over":true, "after":true,
        "before":true, "about":true, "amid":true, "near":true, "across":true,
        "new":true, "latest":true, "update":true, "updates":true,
        "report":true, "reports":true, "live":true, "watch":true,
        "says":true, "say":true, "news":true
    };
    const parts = newsTitleKey(value).split(" ");
    const out = [];
    for (let i = 0; i < parts.length; i++) {
        const token = String(parts[i] || "").trim();
        if (!token || stop[token])
            continue;
        if (token.length < 3 && !/^\d{2,}$/.test(token))
            continue;
        if (out.indexOf(token) < 0)
            out.push(token);
    }
    return out;
}

function newsStoryScore(left, right) {
    const a = newsStoryTokens(left && left.title);
    const b = newsStoryTokens(right && right.title);
    if (a.length < 3 || b.length < 3)
        return {match:false, common:0, overlap:0, jaccard:0};

    const topicsA = left && Array.isArray(left.topics) ? left.topics : [];
    const topicsB = right && Array.isArray(right.topics) ? right.topics : [];
    if (topicsA.length > 0 && topicsB.length > 0) {
        let sharedTopic = false;
        for (let i = 0; i < topicsA.length; i++) {
            if (topicsB.indexOf(topicsA[i]) >= 0) {
                sharedTopic = true;
                break;
            }
        }
        if (!sharedTopic)
            return {match:false, common:0, overlap:0, jaccard:0};
    }

    let common = 0;
    for (let i = 0; i < a.length; i++) {
        if (b.indexOf(a[i]) >= 0)
            common++;
    }
    const minimum = Math.min(a.length, b.length);
    const union = a.length + b.length - common;
    const overlap = minimum > 0 ? common / minimum : 0;
    const jaccard = union > 0 ? common / union : 0;

    // Conservative by design. Three generic shared words are not enough.
    // Require strong set agreement so nearby-but-different events stay apart.
    const match = common >= 3 && overlap >= 0.75 && jaccard >= 0.62;
    return {
        match:match,
        common:common,
        overlap:overlap,
        jaccard:jaccard
    };
}

function newsStoryFamilies(rows) {
    const source = Array.isArray(rows) ? rows : [];
    const groups = [];

    function addUnique(list, value, limit) {
        const text = shortText(value, limit);
        if (text && list.indexOf(text) < 0)
            list.push(text);
    }

    function addRow(group, row, score) {
        group.rows.push(row);
        addUnique(group.titleVariants, row.title, 180);
        group.variantCount = group.rows.length;
        const sourceGroup = row.sourceGroup || {};
        const records = Number(sourceGroup.articleCount);
        group.articleRecords += isFinite(records) && records > 0 ? records : 1;

        const domains = Array.isArray(sourceGroup.domains)
            ? sourceGroup.domains : [row.domain];
        const countries = Array.isArray(sourceGroup.countries)
            ? sourceGroup.countries : [row.country];
        const languages = Array.isArray(sourceGroup.languages)
            ? sourceGroup.languages : [row.language];
        const topics = Array.isArray(row.topics) ? row.topics : [];

        for (let i = 0; i < domains.length; i++)
            addUnique(group.domains, domains[i], 80);
        for (let i = 0; i < countries.length; i++)
            addUnique(group.countries, countries[i], 48);
        for (let i = 0; i < languages.length; i++)
            addUnique(group.languages, languages[i], 48);
        for (let i = 0; i < topics.length; i++)
            addUnique(group.topics, topics[i], 24);

        const seen = Number(row.seenMillis);
        if (isFinite(seen) && seen > group.latestSeenMillis)
            group.latestSeenMillis = seen;
        if (group.rows.length > 1
                && score && score.jaccard > group.strongestJaccard)
            group.strongestJaccard = score.jaccard;
    }

    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (!row || !row.title)
            continue;

        let bestIndex = -1;
        let bestScore = null;
        for (let j = 0; j < groups.length; j++) {
            const score = newsStoryScore(groups[j].representative, row);
            if (!score.match)
                continue;
            if (!bestScore
                    || score.jaccard > bestScore.jaccard
                    || (score.jaccard === bestScore.jaccard
                        && score.overlap > bestScore.overlap)) {
                bestIndex = j;
                bestScore = score;
            }
        }

        if (bestIndex < 0) {
            const group = {
                representative:row,
                title:shortText(row.title, 180),
                rows:[],
                titleVariants:[],
                variantCount:0,
                articleRecords:0,
                domains:[],
                countries:[],
                languages:[],
                topics:[],
                latestSeenMillis:-1,
                strongestJaccard:1,
                sourceCount:0
            };
            addRow(group, row, {jaccard:1});
            groups.push(group);
        } else {
            addRow(groups[bestIndex], row, bestScore);
        }
    }

    const families = [];
    for (let i = 0; i < groups.length; i++) {
        const group = groups[i];
        group.sourceCount = group.domains.length;
        if (group.variantCount >= 2)
            families.push(group);
    }

    families.sort(function(a, b) {
        if (a.variantCount !== b.variantCount)
            return b.variantCount - a.variantCount;
        if (a.sourceCount !== b.sourceCount)
            return b.sourceCount - a.sourceCount;
        if (a.articleRecords !== b.articleRecords)
            return b.articleRecords - a.articleRecords;
        return b.latestSeenMillis - a.latestSeenMillis;
    });
    return families;
}

function newsReportingTrend(rows, nowMs, bucketHours, bucketCount) {
    const source = Array.isArray(rows) ? rows : [];
    const hours = Math.max(1, Math.min(12, Math.floor(Number(bucketHours) || 4)));
    const count = Math.max(3, Math.min(12, Math.floor(Number(bucketCount) || 6)));
    let now = Number(nowMs);

    if (!isFinite(now) || now <= 0) {
        now = -1;
        for (let i = 0; i < source.length; i++) {
            const seen = Number(source[i] ? source[i].seenMillis : -1);
            if (isFinite(seen) && seen > now)
                now = seen;
        }
        if (now <= 0)
            return {
                buckets:[], timedRows:0, maxArticles:0, maxSources:0,
                direction:"NO TIME DATA", recentArticles:0, previousArticles:0
            };
    }

    const bucketMs = hours * 3600000;
    const buckets = [];
    for (let i = 0; i < count; i++) {
        const older = (count - i) * hours;
        const newer = (count - i - 1) * hours;
        buckets.push({
            label: newer === 0
                ? "0-" + older + "H"
                : newer + "-" + older + "H",
            articles:0,
            domains:[],
            sources:0
        });
    }

    let timedRows = 0;
    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        const seen = Number(row ? row.seenMillis : -1);
        if (!isFinite(seen) || seen <= 0 || seen > now)
            continue;
        const age = now - seen;
        if (age < 0 || age >= bucketMs * count)
            continue;

        const recentIndex = Math.floor(age / bucketMs);
        const index = count - 1 - recentIndex;
        if (index < 0 || index >= count)
            continue;

        const bucket = buckets[index];
        bucket.articles++;
        timedRows++;
        const domain = shortText(row.domain, 80);
        if (domain && bucket.domains.indexOf(domain) < 0)
            bucket.domains.push(domain);
    }

    let maxArticles = 0;
    let maxSources = 0;
    for (let i = 0; i < buckets.length; i++) {
        buckets[i].sources = buckets[i].domains.length;
        maxArticles = Math.max(maxArticles, buckets[i].articles);
        maxSources = Math.max(maxSources, buckets[i].sources);
    }

    const recentStart = Math.max(0, count - 2);
    const previousStart = Math.max(0, count - 4);
    let recentArticles = 0;
    let previousArticles = 0;
    for (let i = recentStart; i < count; i++)
        recentArticles += buckets[i].articles;
    for (let i = previousStart; i < recentStart; i++)
        previousArticles += buckets[i].articles;

    let direction = "STEADY";
    if (timedRows < 3) {
        direction = "SPARSE";
    } else if (recentArticles >= previousArticles + 2
            && (previousArticles === 0
                || recentArticles >= previousArticles * 1.35)) {
        direction = "RISING";
    } else if (previousArticles >= recentArticles + 2
            && (recentArticles === 0
                || previousArticles >= recentArticles * 1.35)) {
        direction = "FALLING";
    }

    return {
        buckets:buckets,
        timedRows:timedRows,
        maxArticles:maxArticles,
        maxSources:maxSources,
        direction:direction,
        recentArticles:recentArticles,
        previousArticles:previousArticles,
        bucketHours:hours,
        bucketCount:count
    };
}

function filterNewsRows(rows, topic, sourceQuery, languageQuery, maxAgeHours, nowMs, sourceRegion) {
    if (!Array.isArray(rows))
        return [];

    const wanted = String(topic || "all").toLowerCase();
    const query = shortText(sourceQuery, 80).toLowerCase();
    const language = shortText(languageQuery, 48).toLowerCase();
    const region = shortText(sourceRegion, 48).toLowerCase();
    const hours = Number(maxAgeHours);
    const timeLimited = isFinite(hours) && hours > 0;
    const now = Number(nowMs);
    const cutoff = timeLimited && isFinite(now) && now > 0
        ? now - hours * 3600000 : -1;
    const result = [];

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row)
            continue;

        const topics = Array.isArray(row.topics) ? row.topics : [];
        if (wanted !== "all" && topics.indexOf(wanted) < 0)
            continue;

        if (query) {
            const domain = String(row.domain || "").toLowerCase();
            const country = String(row.country || "").toLowerCase();
            if (domain.indexOf(query) < 0 && country.indexOf(query) < 0)
                continue;
        }

        if (language) {
            const rowLanguage = String(row.language || "").toLowerCase();
            if (rowLanguage.indexOf(language) < 0)
                continue;
        }

        if (region) {
            const rowCountry = String(row.country || "UNLISTED")
                .trim().toLowerCase();
            if (rowCountry !== region)
                continue;
        }

        if (cutoff > 0) {
            const seen = Number(row.seenMillis);
            if (!isFinite(seen) || seen <= 0 || seen < cutoff || seen > now)
                continue;
        }

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

    const sourceGroups = newsExactSourceGroups(root.articles);
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
        const language = shortText(
            article.language || article.lang || article.sourcelang,
            48
        );
        const rawTime = shortText(article.seendate, 32);
        const seenMillis = gdeltSeenMillis(rawTime);
        const topics = newsTopics(title);
        const sourceGroup = sourceGroups[titleKey] || {
            articleCount:1,
            sourceCount:domain ? 1 : 0,
            multiSource:false,
            urls:[canonicalUrl],
            domains:domain ? [domain] : [],
            countries:country ? [country] : [],
            languages:language ? [language] : []
        };
        rows.push({
            title: title,
            detail: domain
                + (country ? " // " + country : "")
                + (language ? " // " + language.toUpperCase() : ""),
            domain: domain,
            country: country,
            language: language,
            time: formatDate(article.seendate),
            rawTime: rawTime,
            seenMillis: seenMillis,
            url: url,
            canonicalUrl: canonicalUrl,
            sourceGroup: {
                articleCount: sourceGroup.articleCount,
                sourceCount: sourceGroup.sourceCount,
                multiSource: sourceGroup.multiSource,
                domains: sourceGroup.domains.slice(0, 8),
                countries: sourceGroup.countries.slice(0, 8),
                languages: sourceGroup.languages.slice(0, 8)
            },
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
