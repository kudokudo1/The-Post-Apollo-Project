.pragma library

function clean(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .trim()
        .slice(0, limit);
}

function stationId(value) {
    const id = String(value || "").trim().toLowerCase();
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id)
        ? id : "";
}

function normalize(item) {
    if (!item || !item.ref || item.ref.source !== "radio-browser")
        return null;
    const id = stationId(item.ref.id);
    const title = clean(item.title, 100);
    if (!id || !title)
        return null;
    const bitrateRaw = Number(item.bitrate);
    const bitrate = isFinite(bitrateRaw)
        ? Math.max(0, Math.min(4096, Math.floor(bitrateRaw))) : 0;
    return {
        ref: {
            source: "radio-browser",
            kind: "station",
            id: id
        },
        title: title,
        artist: clean(item.artist, 16),
        genre: clean(item.genre || item.album, 100),
        codec: clean(item.codec, 16) || "MP3",
        bitrate: bitrate
    };
}

function key(item) {
    const row = normalize(item);
    return row ? row.ref.id : "";
}

function encode(item) {
    const row = normalize(item);
    return row ? JSON.stringify(row) : "";
}

function decode(value) {
    try {
        const raw = JSON.parse(String(value || ""));
        return normalize(raw);
    } catch (error) {
        return null;
    }
}

function decodeList(entries, limit) {
    if (!Array.isArray(entries))
        return [];
    const maximum = Math.max(0, Math.min(50, Number(limit) || 20));
    const seen = {};
    const result = [];
    for (let i = 0; i < entries.length && result.length < maximum; i++) {
        const row = decode(entries[i]);
        const id = row ? row.ref.id : "";
        if (!id || seen[id])
            continue;
        seen[id] = true;
        result.push(row);
    }
    return result;
}

function isFavorite(entries, item) {
    const id = key(item);
    if (!id || !Array.isArray(entries))
        return false;
    for (let i = 0; i < entries.length; i++) {
        const row = decode(entries[i]);
        if (row && row.ref.id === id)
            return true;
    }
    return false;
}

function addFavorite(entries, item, limit) {
    const row = normalize(item);
    if (!row)
        return Array.isArray(entries) ? entries.slice() : [];
    const current = Array.isArray(entries) ? entries.slice() : [];
    const encoded = JSON.stringify(row);
    const result = [encoded];
    const seen = {};
    seen[row.ref.id] = true;

    for (let i = 0; i < current.length; i++) {
        const existing = decode(current[i]);
        if (!existing || seen[existing.ref.id])
            continue;
        seen[existing.ref.id] = true;
        result.push(JSON.stringify(existing));
    }
    return result.slice(0, Math.max(1, Math.min(40, Number(limit) || 20)));
}

function removeFavorite(entries, itemOrId) {
    const id = typeof itemOrId === "string"
        ? stationId(itemOrId) : key(itemOrId);
    if (!id || !Array.isArray(entries))
        return Array.isArray(entries) ? entries.slice() : [];
    const result = [];
    for (let i = 0; i < entries.length; i++) {
        const existing = decode(entries[i]);
        if (!existing || existing.ref.id === id)
            continue;
        result.push(JSON.stringify(existing));
    }
    return result;
}

function touchRecent(entries, item, limit) {
    const row = normalize(item);
    if (!row)
        return Array.isArray(entries) ? entries.slice() : [];
    const current = Array.isArray(entries) ? entries.slice() : [];
    const result = [JSON.stringify(row)];
    const seen = {};
    seen[row.ref.id] = true;
    for (let i = 0; i < current.length; i++) {
        const existing = decode(current[i]);
        if (!existing || seen[existing.ref.id])
            continue;
        seen[existing.ref.id] = true;
        result.push(JSON.stringify(existing));
    }
    return result.slice(0, Math.max(1, Math.min(30, Number(limit) || 12)));
}
