.pragma library

// ApolloHub configuration is data, not QML source. The shell never writes its
// own widget tree when a user rearranges a tile.
var MODULE_IDS = ["time", "calendar", "todo", "notes", "weather", "uptime",
                  "media", "apps", "cpu", "network", "social", "audio"];
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
        network: "NETWORK", social: "SOCIAL", audio: "SYSTEM AUDIO"
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
            || (data.version !== undefined && data.version !== 1
                && data.version !== LAYOUT_VERSION))
        return defaultLayout();
    var next = normalizeCore(data);
    return next.modes.length > 0 ? next : defaultLayout();
}

function storageIssue(text) {
    if (typeof text !== "string" || !text.trim())
        return "";
    var data;
    try { data = JSON.parse(text); }
    catch (e) { return "INVALID_JSON"; }
    if (!data || typeof data !== "object" || Array.isArray(data))
        return "INVALID_LAYOUT";
    if (data.version !== undefined && data.version !== 1
            && data.version !== LAYOUT_VERSION)
        return "UNSUPPORTED_VERSION";
    return Array.isArray(data.modes) ? "" : "INVALID_LAYOUT";
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

// Stage 4: search only the installed HUB module catalogue, not the
// applications catalogue or the user's stored notes/tasks. Empty search
// intentionally shows every supported module.
function moduleChoices(layout, modeIndex, subIndex, tileIndex, rawQuery) {
    var query = typeof rawQuery === "string"
                ? rawQuery.trim().slice(0, 80).toLowerCase() : "";
    var state = {state: "unavailable", query: query, total: MODULE_IDS.length,
                 matchCount: 0, availableCount: 0, items: []};
    if (!layout || !Array.isArray(layout.modes)
            || !validIndex(modeIndex, layout.modes.length))
        return state;
    var groups = layout.modes[modeIndex].subModes;
    if (!Array.isArray(groups) || !validIndex(subIndex, groups.length))
        return state;
    var tiles = groups[subIndex].tiles;
    if (!Array.isArray(tiles) || !validIndex(tileIndex, tiles.length))
        return state;

    var currentId = tiles[tileIndex].module;
    var used = {};
    for (var i = 0; i < tiles.length; ++i) {
        if (i !== tileIndex)
            used["$" + tiles[i].module] = true;
    }
    var items = [];
    var availableCount = 0;
    for (var j = 0; j < MODULE_IDS.length; ++j) {
        var id = MODULE_IDS[j];
        var title = tileTitle(id);
        if (query && id.indexOf(query) < 0
                && title.toLowerCase().indexOf(query) < 0)
            continue;
        var selected = id === currentId;
        var available = !selected
                        && !Object.prototype.hasOwnProperty.call(used, "$" + id);
        if (available)
            availableCount++;
        items.push({id: id, title: title, selected: selected,
                    available: available,
                    inUse: !selected && !available});
    }
    return {state: "ready", query: query, total: MODULE_IDS.length,
            matchCount: items.length, availableCount: availableCount,
            items: items};
}

// Change one specific tile to a selected module, never by cycling through
// intermediate ones. Reject stale tile IDs and duplicate modules in the same
// group; retain all existing tile identity and size metadata.
function setTileModule(layout, modeIndex, subIndex, tileIndex,
                       expectedTileId, moduleId) {
    var next = normalize(clone(layout));
    if (!validIndex(modeIndex, next.modes.length))
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (!validIndex(subIndex, groups.length))
        return next;
    var tiles = groups[subIndex].tiles;
    if (!validIndex(tileIndex, tiles.length)
            || typeof expectedTileId !== "string"
            || tiles[tileIndex].id !== expectedTileId
            || typeof moduleId !== "string" || !validModule(moduleId))
        return next;
    if (tiles.some(function(tile, i) {
        return i !== tileIndex && tile.module === moduleId;
    }))
        return next;
    tiles[tileIndex].module = moduleId;
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

// Stage 3: mode/group deletion only changes saved Hub layout. The widget
// services and their separate persisted user data are never deleted.
// Require an explicit confirmation and exact stable ID so a stale UI cannot
// accidentally remove a different selected mode or group.
function removeMode(layout, modeIndex, expectedModeId, confirmed) {
    var next = normalize(clone(layout));
    if (confirmed !== true || next.modes.length <= 1
            || !validIndex(modeIndex, next.modes.length)
            || typeof expectedModeId !== "string"
            || !expectedModeId.length
            || next.modes[modeIndex].id !== expectedModeId)
        return next;
    next.modes.splice(modeIndex, 1);
    return next;
}

function removeSubMode(layout, modeIndex, subIndex, expectedGroupId, confirmed) {
    var next = normalize(clone(layout));
    if (confirmed !== true || !validIndex(modeIndex, next.modes.length))
        return next;
    var groups = next.modes[modeIndex].subModes;
    if (groups.length <= 1 || !validIndex(subIndex, groups.length)
            || typeof expectedGroupId !== "string"
            || !expectedGroupId.length
            || groups[subIndex].id !== expectedGroupId)
        return next;
    groups.splice(subIndex, 1);
    return next;
}

// P1 Stage 5: a destination is any OTHER group, including groups in the
// same main mode. Capacity and same-group module uniqueness are enforced
// both in this preview and again at the final transfer boundary.
function moveTargets(layout, fromMode, fromGroup, fromIndex) {
    var failure = {state:"unavailable", total:0, availableCount:0, items:[]};
    if (!layout || !Array.isArray(layout.modes)
            || !validIndex(fromMode, layout.modes.length))
        return failure;
    var sourceGroups = layout.modes[fromMode].subModes;
    if (!Array.isArray(sourceGroups) || !validIndex(fromGroup, sourceGroups.length))
        return failure;
    var fromTiles = sourceGroups[fromGroup].tiles;
    if (!Array.isArray(fromTiles) || !validIndex(fromIndex, fromTiles.length))
        return failure;
    var moduleId = fromTiles[fromIndex].module;
    var targets = [];
    var availableCount = 0;
    for (var m = 0; m < layout.modes.length; m++) {
        var mode = layout.modes[m];
        if (!mode || !Array.isArray(mode.subModes))
            continue;
        for (var g = 0; g < mode.subModes.length; g++) {
            if (m === fromMode && g === fromGroup)
                continue;
            var group = mode.subModes[g];
            if (!group || !Array.isArray(group.tiles))
                continue;
            var full = group.tiles.length >= MAX_TILES;
            var duplicate = group.tiles.some(function(tile) {
                return tile.module === moduleId;
            });
            var available = !full && !duplicate;
            if (available)
                availableCount++;
            targets.push({
                modeIndex:m, groupIndex:g, modeId:mode.id, groupId:group.id,
                label:mode.name + " / " + group.name,
                available:available,
                reason:full ? "FULL" : duplicate ? "IN USE" : "",
                count:group.tiles.length
            });
        }
    }
    return {state:"ready", total:targets.length,
            availableCount:availableCount, items:targets};
}

// Transfer the original tile record, not a new tile. Never allocate an ID,
// destroy its dimensions, or mutate either source/destination on rejection.
// Source and destination stable IDs are both checked against a fresh layout.
function transferTile(layout, fromMode, fromGroup, fromIndex, expectedTileId,
                      expectedModeId, expectedGroupId,
                      toMode, toGroup, expectedDestinationModeId,
                      expectedDestinationGroupId) {
    var next = normalize(clone(layout));
    if (!validIndex(fromMode,next.modes.length)
            || !validIndex(toMode,next.modes.length))
        return next;
    var sourceMode = next.modes[fromMode];
    var destinationMode = next.modes[toMode];
    if (sourceMode.id !== expectedModeId
            || destinationMode.id !== expectedDestinationModeId
            || !validIndex(fromGroup,sourceMode.subModes.length)
            || !validIndex(toGroup,destinationMode.subModes.length)
            || (fromMode === toMode && fromGroup === toGroup))
        return next;
    var source = sourceMode.subModes[fromGroup];
    var destination = destinationMode.subModes[toGroup];
    if (source.id !== expectedGroupId
            || destination.id !== expectedDestinationGroupId
            || !validIndex(fromIndex,source.tiles.length)
            || source.tiles[fromIndex].id !== expectedTileId
            || destination.tiles.length >= MAX_TILES
            || destination.tiles.some(function(tile) {
                return tile.module === source.tiles[fromIndex].module;
            }))
        return next;
    var moved = source.tiles.splice(fromIndex,1)[0];
    destination.tiles.push(moved);
    return next;
}

// P1 Stage 6: deterministic, read-only 2-column packing. This is computed
// presentation geometry, not a layout migration or a saved tile reorder.
// Place each tile at the first available row/column rectangle. Short tiles
// may fill otherwise wasted cells beside taller half-width tiles.
function packTiles(tiles) {
    var invalid = {state:"unavailable", columns:2, rows:0, items:[]};
    if (!Array.isArray(tiles) || tiles.length > MAX_TILES)
        return invalid;
    var occupied = [];
    var positions = [];
    var highestRow = 0;
    for (var i=0;i<tiles.length;i++) {
        var tile = tiles[i];
        if (!tile || typeof tile !== "object" || !validModule(tile.module)
                || (tile.size !== "wide" && tile.size !== "half")
                || !validRowSpan(tile.rowSpan))
            return invalid;
        var width = tile.size === "wide" ? 2 : 1;
        var placed = false;
        // Eight tiles each at most three rows high always fit within 24 rows.
        for (var row=0;row<MAX_TILES*MAX_ROW_SPAN && !placed;row++) {
            for (var column=0;column<=2-width && !placed;column++) {
                var free = true;
                for (var dy=0;dy<tile.rowSpan && free;dy++) {
                    for (var dx=0;dx<width;dx++) {
                        if (occupied[row+dy] && occupied[row+dy][column+dx]) {
                            free = false;
                            break;
                        }
                    }
                }
                if (!free)
                    continue;
                for (var markY=0;markY<tile.rowSpan;markY++) {
                    var occupiedRow = row+markY;
                    if (!occupied[occupiedRow])
                        occupied[occupiedRow] = [false,false];
                    for (var markX=0;markX<width;markX++)
                        occupied[occupiedRow][column+markX] = true;
                }
                positions.push({
                    id:tile.id,
                    column:column,
                    row:row,
                    columnSpan:width,
                    rowSpan:tile.rowSpan
                });
                highestRow = Math.max(highestRow,row+tile.rowSpan);
                placed = true;
            }
        }
        if (!placed)
            return invalid;
    }
    return {state:"ready", columns:2, rows:highestRow, items:positions};
}

// P1 Stage 7: arrow navigation follows the rectangles from packTiles.
// This is a pure view selection helper; it never changes tile order or data.
// A candidate must be beyond the source's edge in the requested direction.
// Prefer the nearest edge, then an overlapping perpendicular span, then
// proximity to the source center, with stable index for ties.
function navigationTarget(grid, selectedIndex, direction) {
    if (!grid || grid.state !== "ready" || !Array.isArray(grid.items)
            || !validIndex(selectedIndex, grid.items.length)
            || ["left","right","up","down"].indexOf(direction) === -1)
        return selectedIndex;
    var source = grid.items[selectedIndex];
    if (!source || typeof source.column !== "number"
            || typeof source.row !== "number"
            || typeof source.columnSpan !== "number"
            || typeof source.rowSpan !== "number")
        return selectedIndex;
    function intervalGap(a0,a1,b0,b1) {
        return Math.max(0,Math.max(a0,b0)-Math.min(a1,b1));
    }
    var sx0=source.column, sx1=source.column+source.columnSpan;
    var sy0=source.row, sy1=source.row+source.rowSpan;
    var best=selectedIndex;
    var bestScore=null;
    for (var i=0;i<grid.items.length;i++) {
        if (i===selectedIndex)
            continue;
        var candidate=grid.items[i];
        if (!candidate || typeof candidate.column !== "number"
                || typeof candidate.row !== "number"
                || typeof candidate.columnSpan !== "number"
                || typeof candidate.rowSpan !== "number")
            continue;
        var cx0=candidate.column,cx1=cx0+candidate.columnSpan;
        var cy0=candidate.row,cy1=cy0+candidate.rowSpan;
        var primary=-1, crossGap=0, centerOffset=0;
        if (direction==="left" && cx1<=sx0) {
            primary=sx0-cx1;
            crossGap=intervalGap(sy0,sy1,cy0,cy1);
            centerOffset=Math.abs((sy0+sy1)-(cy0+cy1));
        } else if (direction==="right" && cx0>=sx1) {
            primary=cx0-sx1;
            crossGap=intervalGap(sy0,sy1,cy0,cy1);
            centerOffset=Math.abs((sy0+sy1)-(cy0+cy1));
        } else if (direction==="up" && cy1<=sy0) {
            primary=sy0-cy1;
            crossGap=intervalGap(sx0,sx1,cx0,cx1);
            centerOffset=Math.abs((sx0+sx1)-(cx0+cx1));
        } else if (direction==="down" && cy0>=sy1) {
            primary=cy0-sy1;
            crossGap=intervalGap(sx0,sx1,cx0,cx1);
            centerOffset=Math.abs((sx0+sx1)-(cx0+cx1));
        }
        if (primary<0)
            continue;
        var score=[crossGap,primary,centerOffset,i];
        var wins=bestScore===null;
        if (!wins) {
            for (var k=0;k<score.length;k++) {
                if (score[k]===bestScore[k])
                    continue;
                wins=score[k]<bestScore[k];
                break;
            }
        }
        if (wins) {
            best=i;
            bestScore=score;
        }
    }
    return best;
}
