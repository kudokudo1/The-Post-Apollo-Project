.pragma library

// ApolloHub configuration is data, not QML source. The shell never writes its
// own widget tree when a user rearranges a tile.
var MODULE_IDS = ["time", "calendar", "todo", "notes", "weather", "uptime",
                  "media", "apps", "cpu", "network"];
var LAYOUT_VERSION = 2;
var MAX_MODES = 6;
var MAX_SUBMODES = 6;
var MAX_TILES = 8;
var MAX_ROW_SPAN = 3;
var MAX_TILE_ID = 1000000000;

function validIndex(value, limit) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= 0 && value < limit;
}

function tileNumber(value) {
    if (typeof value !== "string" || !/^tile-[1-9][0-9]*$/.test(value))
        return -1;
    var number = Number(value.slice(5));
    return isFinite(number) && Math.floor(number) === number
           && number >= 1 && number < MAX_TILE_ID ? number : -1;
}

function validRowSpan(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= 1
           && value <= MAX_ROW_SPAN;
}

function defaultLayout() {
    return normalizeCore({
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
    });
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

// Core normalization migrates v1's {module,size} tiles into stable v2
// identities + row spans. It NEVER mutates the caller's saved object.
function normalizeCore(data) {
    var highest = 0;
    if (data.version === LAYOUT_VERSION) {
        for (var m = 0; m < data.modes.length; m++) {
            var groups = data.modes[m] && data.modes[m].subModes;
            if (!Array.isArray(groups))
                continue;
            for (var g = 0; g < groups.length; g++) {
                var tiles = groups[g] && groups[g].tiles;
                if (!Array.isArray(tiles))
                    continue;
                for (var t = 0; t < tiles.length; t++)
                    highest = Math.max(highest, tileNumber(tiles[t] && tiles[t].id));
            }
        }
    }
    var nextId = highest + 1;
    if (data.version === LAYOUT_VERSION
            && validIndex(data.nextTileId, MAX_TILE_ID)
            && data.nextTileId > nextId)
        nextId = data.nextTileId;
    var used = {};
    function assignId(input) {
        var number = data.version === LAYOUT_VERSION
                     ? tileNumber(input && input.id) : -1;
        var preserved = number > 0 ? "tile-" + number : "";
        if (preserved && !Object.prototype.hasOwnProperty.call(used,preserved)) {
            used[preserved] = true;
            return preserved;
        }
        if (nextId >= MAX_TILE_ID)
            return null;
        var generated = "tile-" + nextId++;
        used[generated] = true;
        return generated;
    }
    var result = { version: LAYOUT_VERSION, nextTileId: 1, modes: [] };
    for (var i = 0; i < Math.min(MAX_MODES, data.modes.length); ++i) {
        var inputMode = data.modes[i];
        if (!inputMode || !Array.isArray(inputMode.subModes))
            continue;
        var mode = {
            id: String(inputMode.id || ("mode-" + i)).slice(0, 40),
            name: String(inputMode.name || ("Mode " + (i + 1))).slice(0, 20),
            icon: String(inputMode.icon || "✦").slice(0, 4),
            subModes: []
        };
        for (var j = 0; j < Math.min(MAX_SUBMODES, inputMode.subModes.length); ++j) {
            var inputSub = inputMode.subModes[j];
            if (!inputSub || !Array.isArray(inputSub.tiles))
                continue;
            var sub = {
                id: String(inputSub.id || ("sub-" + j)).slice(0, 40),
                name: String(inputSub.name || ("Group " + (j + 1))).slice(0, 20),
                tiles: []
            };
            for (var k = 0; k < Math.min(MAX_TILES, inputSub.tiles.length); ++k) {
                var t = inputSub.tiles[k];
                if (!t || !validModule(t.module))
                    continue;
                var id = assignId(t);
                if (!id)
                    continue;
                sub.tiles.push({
                    id: id,
                    module: String(t.module),
                    size: t.size === "wide" ? "wide" : "half",
                    rowSpan: data.version === LAYOUT_VERSION && validRowSpan(t.rowSpan)
                             ? t.rowSpan : 1
                });
            }
            mode.subModes.push(sub);
        }
        if (mode.subModes.length > 0)
            result.modes.push(mode);
    }
    result.nextTileId = nextId;
    return result;
}

function normalize(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)
            || !Array.isArray(data.modes)
            || (data.version !== 1 && data.version !== LAYOUT_VERSION))
        return defaultLayout();
    var next = normalizeCore(data);
    return next.modes.length > 0 ? next : defaultLayout();
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
    if (next.modes.length >= MAX_MODES)
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
    if (groups.length < MAX_SUBMODES)
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
    if (tiles.length >= MAX_TILES)
        return next;
    var candidate = MODULE_IDS.find(function(id) {
        return !tiles.some(function(t) { return t.module === id; });
    }) || MODULE_IDS[0];
    if (next.nextTileId >= MAX_TILE_ID)
        return next;
    tiles.push({ id: "tile-" + next.nextTileId++,
                 module: candidate, size: "half", rowSpan: 1 });
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

// Remove only the requested TILE PLACEMENT, never the module's own data.
// Explicit UI activation owns removal and records an undo snapshot.
function removeTile(layout, modeIndex, subIndex, tileIndex) {
    var next = normalize(clone(layout));
    if (!validIndex(modeIndex, next.modes.length))
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (!validIndex(subIndex, groups.length))
        return next;
    var tiles = groups[subIndex].tiles;
    if (!validIndex(tileIndex, tiles.length))
        return next;
    tiles.splice(tileIndex, 1);
    return next;
}

// Backing shape for future sizing controls. The live UI currently renders
// 2 columns; rowSpan: 1 retains the original 140px card height.
function resizeTile(layout, modeIndex, subIndex, tileIndex, size, rowSpan) {
    var next = normalize(clone(layout));
    if (!validIndex(modeIndex, next.modes.length))
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (!validIndex(subIndex, groups.length))
        return next;
    var tiles = groups[subIndex].tiles;
    if (!validIndex(tileIndex, tiles.length)
            || (size !== "half" && size !== "wide")
            || !validRowSpan(rowSpan))
        return next;
    tiles[tileIndex].size = size;
    tiles[tileIndex].rowSpan = rowSpan;
    return next;
}
