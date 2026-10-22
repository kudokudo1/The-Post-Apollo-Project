.pragma library

// B6: a read-only projection of Quickshell's already-indexed desktop entries.
// This module never launches a process or returns commands, working
// directories, QML objects, environment, or privileged app-control handles.
var MAX_ITEMS = 24;
var MAX_QUERY_LENGTH = 80;

function clean(value, limit) {
    return typeof value === "string"
           ? value.replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, limit)
           : "";
}

function normalize(entry) {
    if (!entry || typeof entry !== "object" || entry.noDisplay === true)
        return null;
    var id = clean(entry.id, 180);
    var name = clean(entry.name, 120);
    if (!id || !name)
        return null;
    return {
        id: id,
        name: name,
        genericName: clean(entry.genericName, 120),
        icon: clean(entry.icon, 180)
    };
}

function byName(a, b) {
    var one = a.name.toLowerCase();
    var two = b.name.toLowerCase();
    if (one < two) return -1;
    if (one > two) return 1;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

function snapshot(applications, requestedQuery) {
    var query = clean(requestedQuery, MAX_QUERY_LENGTH).toLowerCase();
    if (!Array.isArray(applications)) {
        return {
            state: "unavailable",
            source: "desktop-entries",
            query: query,
            installedCount: 0,
            matchCount: 0,
            shownCount: 0,
            truncated: false,
            items: []
        };
    }

    var items = [];
    var seen = {};
    for (var i = 0; i < applications.length; ++i) {
        var item = normalize(applications[i]);
        if (!item)
            continue;
        // Desktop files can share a display name; IDs, not names, distinguish.
        var key = "$" + item.id;
        if (Object.prototype.hasOwnProperty.call(seen, key))
            continue;
        seen[key] = true;
        items.push(item);
    }
    var installedCount = items.length;
    if (query)
        items = items.filter(function(item) {
            return item.name.toLowerCase().indexOf(query) >= 0
                || item.genericName.toLowerCase().indexOf(query) >= 0
                || item.id.toLowerCase().indexOf(query) >= 0;
        });
    items.sort(byName);
    var matchCount = items.length;
    var visible = items.slice(0, MAX_ITEMS);
    return {
        state: installedCount > 0 ? "ready" : "empty",
        source: "desktop-entries",
        query: query,
        installedCount: installedCount,
        matchCount: matchCount,
        shownCount: visible.length,
        truncated: matchCount > visible.length,
        items: visible
    };
}
