.pragma library

// TASKS geometry is presentation-only. Keep one mapped PanelWindow alive
// across size changes; the Hub's sole task store and editors remain mounted.
var levels = ["compact", "expanded", "large"];

function normalize(level) {
    return levels.indexOf(level) >= 0 ? level : "compact";
}

function step(level, direction) {
    var index = levels.indexOf(normalize(level));
    return levels[Math.max(0, Math.min(levels.length - 1,
        index + (direction < 0 ? -1 : 1)))];
}

function viewportPixels(value, fallback) {
    var n = Number(value);
    return isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

function frame(level, viewportWidth, viewportHeight, gutter, topInset, bottomGap) {
    var inset = Math.max(0, Math.floor(Number(gutter) || 0));
    var top = Math.max(0, Math.floor(Number(topInset) || 0));
    var bottom = Math.max(0, Math.floor(Number(bottomGap) || 0));
    var availableWidth = Math.max(1, viewportPixels(viewportWidth, 456) - 2 * inset);
    var availableHeight = Math.max(1, viewportPixels(viewportHeight, 768) - top - bottom);
    var mode = normalize(level);
    var targetWidth = mode === "large" ? 760 : mode === "expanded" ? 560 : 432;
    var targetHeight = mode === "large" ? 1345 : mode === "expanded" ? 1020 : 790;
    var height = Math.min(availableHeight, targetHeight);

    // Portrait even when the screen is shorter than the requested chassis.
    // Compact's original 432 x 790 frame is unchanged on full-size displays.
    return {
        width: Math.max(1, Math.min(availableWidth, targetWidth,
                                     Math.floor(height * 0.58))),
        height: height
    };
}

function leftMargin(dockCenterX, screenWidth, panelWidth) {
    var room = Math.max(0, Number(screenWidth) - Number(panelWidth));
    var position = Number(dockCenterX) - Number(panelWidth) / 2;
    return Math.max(0, Math.min(room, Math.round(isFinite(position) ? position : 0)));
}

function topMargin(chassisTopY, screenHeight, panelHeight, gutter) {
    var room = Math.max(0, Number(screenHeight) - Number(panelHeight));
    var position = Number(chassisTopY) - Number(gutter);
    return Math.max(0, Math.min(room, Math.round(isFinite(position) ? position : 0)));
}
