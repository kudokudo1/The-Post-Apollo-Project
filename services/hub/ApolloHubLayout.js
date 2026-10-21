.pragma library

// ApolloHub configuration is data, not QML source. The shell never writes its
// own widget tree when a user rearranges a tile.
var MODULE_IDS = ["time", "calendar", "todo", "notes", "weather", "uptime",
                  "media", "apps", "cpu", "network"];

function defaultLayout() {
    return {
        version: 1,
        modes: [
            { id: "dashboard", name: "Dashboard", icon: "✦", subModes: [
                { id: "overview", name: "Overview", tiles: [
                    { module: "time", size: "half" },
                    { module: "todo", size: "half" },
                    { module: "calendar", size: "half" },
                    { module: "weather", size: "half" },
                    { module: "notes", size: "half" },
                    { module: "uptime", size: "half" }
                ]}
            ]},
            { id: "console", name: "Console", icon: "⌘", subModes: [
                { id: "quick", name: "Quick", tiles: [
                    { module: "apps", size: "wide" },
                    { module: "cpu", size: "half" },
                    { module: "network", size: "half" }
                ]}
            ]},
            { id: "media", name: "Media", icon: "♫", subModes: [
                { id: "player", name: "Player", tiles: [
                    { module: "media", size: "wide" },
                    { module: "time", size: "half" }
                ]}
            ]}
        ]
    };
}

function validModule(id) {
    return MODULE_IDS.indexOf(String(id)) !== -1;
}

function tileTitle(id) {
    var names = {
        time: "TIME", calendar: "CALENDAR", todo: "TO-DO",
        notes: "NOTES", weather: "WEATHER", uptime: "UPTIME",
        media: "MEDIA", apps: "APP LAUNCHER", cpu: "CPU++",
        network: "NETWORK"
    };
    return names[String(id)] || "UNKNOWN";
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function normalize(data) {
    if (!data || typeof data !== "object" || !Array.isArray(data.modes))
        return defaultLayout();
    var result = { version: 1, modes: [] };
    for (var i = 0; i < Math.min(6, data.modes.length); ++i) {
        var inputMode = data.modes[i];
        if (!inputMode || !Array.isArray(inputMode.subModes))
            continue;
        var mode = {
            id: String(inputMode.id || ("mode-" + i)).slice(0, 40),
            name: String(inputMode.name || ("Mode " + (i + 1))).slice(0, 20),
            icon: String(inputMode.icon || "✦").slice(0, 4),
            subModes: []
        };
        for (var j = 0; j < Math.min(6, inputMode.subModes.length); ++j) {
            var inputSub = inputMode.subModes[j];
            if (!inputSub || !Array.isArray(inputSub.tiles))
                continue;
            var sub = {
                id: String(inputSub.id || ("sub-" + j)).slice(0, 40),
                name: String(inputSub.name || ("Group " + (j + 1))).slice(0, 20),
                tiles: []
            };
            for (var k = 0; k < Math.min(8, inputSub.tiles.length); ++k) {
                var t = inputSub.tiles[k];
                if (!t || !validModule(t.module))
                    continue;
                sub.tiles.push({
                    module: String(t.module),
                    size: t.size === "wide" ? "wide" : "half"
                });
            }
            mode.subModes.push(sub);
        }
        if (mode.subModes.length > 0)
            result.modes.push(mode);
    }
    return result.modes.length > 0 ? result : defaultLayout();
}

function parse(text) {
    try {
        if (!text)
            return defaultLayout();
        return normalize(JSON.parse(text));
    } catch (e) {
        return defaultLayout();
    }
}

function swapTiles(layout, modeIndex, subIndex, first, second) {
    var next = normalize(clone(layout));
    var modes = next.modes;
    if (modeIndex < 0 || modeIndex >= modes.length)
        return next;
    var groups = modes[modeIndex].subModes;
    if (subIndex < 0 || subIndex >= groups.length)
        return next;
    var tiles = groups[subIndex].tiles;
    if (first < 0 || second < 0 || first >= tiles.length || second >= tiles.length)
        return next;
    var temp = tiles[first];
    tiles[first] = tiles[second];
    tiles[second] = temp;
    return next;
}

function renameMode(layout, index, name) {
    var next = normalize(clone(layout));
    if (index >= 0 && index < next.modes.length) {
        var clean = String(name).trim().slice(0, 20);
        if (clean.length)
            next.modes[index].name = clean;
    }
    return next;
}

function addMode(layout) {
    var next = normalize(clone(layout));
    if (next.modes.length >= 6)
        return next;
    var stamp = Date.now();
    next.modes.push({
        id: "mode-" + stamp,
        name: "Mode " + (next.modes.length + 1),
        icon: "✦",
        subModes: [{ id: "group-" + stamp, name: "Overview", tiles: [] }]
    });
    return next;
}

function addSubMode(layout, modeIndex) {
    var next = normalize(clone(layout));
    if (modeIndex < 0 || modeIndex >= next.modes.length)
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (groups.length < 6)
        groups.push({ id: "group-" + Date.now(), name: "Group " + (groups.length + 1), tiles: [] });
    return next;
}

function addTile(layout, modeIndex, subIndex) {
    var next = normalize(clone(layout));
    if (modeIndex < 0 || modeIndex >= next.modes.length)
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (subIndex < 0 || subIndex >= groups.length)
        return next;
    var tiles = groups[subIndex].tiles;
    if (tiles.length >= 8)
        return next;
    var candidate = MODULE_IDS.find(function(id) {
        return !tiles.some(function(t) { return t.module === id; });
    }) || MODULE_IDS[0];
    tiles.push({ module: candidate, size: "half" });
    return next;
}

function cycleTile(layout, modeIndex, subIndex, tileIndex) {
    var next = normalize(clone(layout));
    if (modeIndex < 0 || modeIndex >= next.modes.length)
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (subIndex < 0 || subIndex >= groups.length)
        return next;
    var tiles = groups[subIndex].tiles;
    if (tileIndex < 0 || tileIndex >= tiles.length)
        return next;
    var current = MODULE_IDS.indexOf(tiles[tileIndex].module);
    for (var step = 1; step <= MODULE_IDS.length; ++step) {
        var candidate = MODULE_IDS[(current + step) % MODULE_IDS.length];
        if (!tiles.some(function(t, i) { return i !== tileIndex && t.module === candidate; })) {
            tiles[tileIndex].module = candidate;
            break;
        }
    }
    return next;
}
