.pragma library

// W2a: session-only HOME workspace rotation and stable panel bookmarks.
// Data collection, ranked AUTO watch, saved records and source ownership
// remain with StationHome and the existing services.
var FORMAT = "post-apollo.weather.home-deck.w2a.v1";
var ROTATABLE = [
    "home/auto", "home/quick", "home/snapshot",
    "home/history", "home/runtime", "home/health"
];
var MODES = ["mixed", "auto", "pinned"];

function isRotatable(path) {
    return ROTATABLE.indexOf(String(path || "")) >= 0;
}
function normalizedFavorites(paths) {
    var input = Array.isArray(paths) ? paths : [];
    var unique = [];
    for (var i = 0; i < input.length; i++) {
        var key = String(input[i] || "");
        if (isRotatable(key) && unique.indexOf(key) < 0)
            unique.push(key);
    }
    return unique;
}
function favorite(paths, path) {
    return normalizedFavorites(paths).indexOf(String(path || "")) >= 0;
}
function toggleFavorite(paths, path) {
    var list = normalizedFavorites(paths);
    var key = String(path || "");
    if (!isRotatable(key))
        return list;
    var index = list.indexOf(key);
    if (index >= 0)
        list.splice(index, 1);
    else
        list.push(key);
    return list;
}
function normalizedMode(mode) {
    return MODES.indexOf(mode) >= 0 ? mode : "mixed";
}
function nextMode(mode) {
    var idx = MODES.indexOf(normalizedMode(mode));
    return MODES[(idx + 1) % MODES.length];
}
function candidates(current, paths, mode) {
    var pins = normalizedFavorites(paths);
    var selectedMode = normalizedMode(mode);
    var pool = selectedMode === "pinned"
        ? ROTATABLE.filter(function(path) { return pins.indexOf(path) >= 0; })
        : ROTATABLE.slice();
    // Never immediately repeat the current panel. If there is only one
    // pinned panel selected, hold it until the operator pins another one.
    return pool.filter(function(path) { return path !== current; });
}
function nextRoute(current, paths, mode, randomValue) {
    var pool = candidates(String(current || ""), paths, mode);
    if (pool.length === 0)
        return "";
    var pins = normalizedFavorites(paths);
    var weighted = [];
    var selectedMode = normalizedMode(mode);
    for (var i = 0; i < pool.length; i++) {
        var weight = selectedMode === "mixed" && pins.indexOf(pool[i]) >= 0 ? 3 : 1;
        for (var j = 0; j < weight; j++)
            weighted.push(pool[i]);
    }
    var sample = Number(randomValue);
    if (!isFinite(sample)) sample = 0;
    sample = Math.max(0, Math.min(0.999999999, sample));
    return weighted[Math.floor(sample * weighted.length)];
}
function mayRotate(family, visible, enabled, held, indexOpen) {
    return family === "home" && !!visible && !!enabled && !held && !indexOpen;
}
