.pragma library

// Weather Station geometry only; one mapped panel survives all size changes.
// Compact preserves the existing 1000 x 700 frame.
var levels = ["compact", "medium", "large", "fullscreen"];

function normalize(level) {
    return levels.indexOf(level) >= 0 ? level : "compact";
}
function step(level, direction) {
    var i = levels.indexOf(normalize(level));
    return levels[Math.max(0, Math.min(levels.length - 1,
                   i + (direction < 0 ? -1 : 1)))];
}
function viewportPixels(value, fallback) {
    var n = Number(value);
    return isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}
function frame(level, screenWidth, screenHeight, topInset, bottomGap, rightMargin) {
    var mode = normalize(level);
    var top = Math.max(0, Math.floor(Number(topInset) || 0));
    var bottom = Math.max(0, Math.floor(Number(bottomGap) || 0));
    var right = Math.max(0, Math.floor(Number(rightMargin) || 0));
    var availableWidth = Math.max(1, viewportPixels(screenWidth, 2560) - right);
    var availableHeight = Math.max(1, viewportPixels(screenHeight, 1440) - top - bottom);
    var w = mode === "fullscreen" ? availableWidth
        : mode === "large" ? 1500 : mode === "medium" ? 1200 : 1000;
    var h = mode === "fullscreen" ? availableHeight
        : mode === "large" ? 1030 : mode === "medium" ? 850 : 700;
    return {
        width: Math.max(1, Math.min(availableWidth, w)),
        height: Math.max(1, Math.min(availableHeight, h))
    };
}
