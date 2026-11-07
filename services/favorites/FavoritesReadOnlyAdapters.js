.pragma library
.import "FavoritesResourcePolicy.js" as Policy

// U0: snapshots of EXISTING owner data only. No FileView, writes, polling,
// provider execution or direct access to Quickshell services.
function result() {
    return {items:[],invalidCount:0};
}

function add(out, provider, kind, resourceId, capabilities, label) {
    const candidate = {
        provider:provider, kind:kind, resourceId:resourceId,
        capabilities:capabilities
    };
    if (label !== undefined)
        candidate.label = label;
    const parsed = Policy.normalize(candidate);
    if (!parsed.ok) {
        out.invalidCount++;
        return;
    }
    out.items.push(parsed.record);
}

function addKeys(out, input, provider, kind, capabilities) {
    if (!Array.isArray(input)) {
        out.invalidCount++;
        return;
    }
    for (let i = 0; i < input.length; ++i)
        add(out, provider, kind, input[i], capabilities);
}

// AppControl's four persisted collections remain owned by FavoritesStore.
// A task favorite's HUNTER policy remains in HUNTER, NOT this projection.
function appControl(snapshot) {
    const out = result();
    if (!snapshot || typeof snapshot !== "object") {
        out.invalidCount++;
        return out;
    }
    addKeys(out,snapshot.favoriteKeys,"appcontrol","item",["favorite"]);
    addKeys(out,snapshot.favoriteDetailActionKeys,"appcontrol",
            "preferred-action",["preferred-action"]);
    addKeys(out,snapshot.favoriteMonitorBoxKeys,"appcontrol",
            "monitor-watch",["watch"]);
    addKeys(out,snapshot.favoriteTaskMetricKeys,"appcontrol",
            "task-watch",["watch"]);
    return out;
}

// HOME never stores measurements or fabricates current-source freshness.
function weatherHome(snapshot) {
    const out = result();
    if (!snapshot || typeof snapshot !== "object") {
        out.invalidCount++;
        return out;
    }
    addKeys(out,snapshot.panelRoutes,"weather-home","panel",
            ["favorite","rotate"]);
    addKeys(out,snapshot.cardKeys,"weather-home","card",
            ["favorite","pin"]);
    return out;
}

function worldClock(snapshot) {
    const out = result();
    if (!snapshot || typeof snapshot !== "object") {
        out.invalidCount++;
        return out;
    }
    addKeys(out,snapshot.zones,"time","timezone",["favorite","recall"]);
    return out;
}

function places(savedPlaces) {
    const out = result();
    if (!Array.isArray(savedPlaces)) {
        out.invalidCount++;
        return out;
    }
    for (let i = 0; i < savedPlaces.length; ++i) {
        const row = savedPlaces[i];
        if (!row || !Number.isSafeInteger(row.id) || row.id < 1
                || !row.place || typeof row.place.label !== "string") {
            out.invalidCount++;
            continue;
        }
        add(out,"places","saved-place",String(row.id),
            ["favorite","recall"],row.place.label);
    }
    return out;
}

// Callers must supply a snapshot array of NotificationsService.favoriteSources.
// This does not inspect or save notification message bodies.
function notifications(sources) {
    const out = result();
    if (!Array.isArray(sources)) {
        out.invalidCount++;
        return out;
    }
    for (let i = 0; i < sources.length; ++i) {
        const item = sources[i];
        if (!item || typeof item.appKey !== "string") {
            out.invalidCount++;
            continue;
        }
        const name = typeof item.source === "string" && item.source
            ? item.source : item.appKey;
        add(out,"notifications","source",item.appKey,["favorite"],name);
    }
    return out;
}

// The Receptionist retains archive priority and pruning protections.
function hospital(pinnedKeys) {
    const out = result();
    addKeys(out,pinnedKeys,"hospital","activity",["favorite","pin"]);
    return out;
}

// Radio Browser UUIDs only. URL/stream and playback metadata never enter
// the common registry. A station in both lists is one resource descriptor.
function radio(favorites, recents) {
    const out = result();
    const found = Object.create(null);
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    function ingest(rows, cap) {
        if (!Array.isArray(rows)) {
            out.invalidCount++;
            return;
        }
        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i];
            const ref = row && row.ref;
            if (!ref || ref.source !== "radio-browser"
                    || typeof ref.id !== "string" || !uuid.test(ref.id)
                    || typeof row.title !== "string") {
                out.invalidCount++;
                continue;
            }
            const key = ref.id;
            const previous = found[key];
            if (previous !== undefined) {
                const old = out.items[previous];
                if (old.capabilities.indexOf(cap) < 0) {
                    const combined = old.capabilities.concat([cap]);
                    const normalized = Policy.normalize({
                        provider:"radio", kind:"station", resourceId:key,
                        label:old.label, capabilities:combined
                    });
                    if (normalized.ok)
                        out.items[previous] = normalized.record;
                }
                continue;
            }
            const before = out.items.length;
            add(out,"radio","station",key,[cap,"recall"],row.title);
            if (out.items.length > before)
                found[key] = before;
        }
    }
    ingest(favorites,"favorite");
    ingest(recents,"recent");
    return out;
}
