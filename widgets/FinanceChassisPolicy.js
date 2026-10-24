.pragma library

// FinanceW M0: geometry is presentation state, never financial data state.
// A single mapped PanelWindow survives every transition.
var levels = ["compact", "expanded", "fullscreen"];

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
    // Frame and mapped PanelWindow share exactly the same vertical budget:
    // screen height = top inset + frame height + bottom gap (when saturated).
    var inset = Math.max(0, Math.floor(Number(gutter) || 0));
    var top = Math.max(0, Math.floor(Number(topInset) || 0));
    var bottom = Math.max(0, Math.floor(Number(bottomGap) || 0));
    var width = Math.max(1, viewportPixels(viewportWidth, 456) - 2 * inset);
    var height = Math.max(1, viewportPixels(viewportHeight, 768) - top - bottom);
    var mode = normalize(level);
    return {
        width: mode === "fullscreen" ? width
             : Math.min(width, mode === "expanded" ? 1000 : 432),
        // Large now uses Social's default 1355px frame height minus 14px.
        // The 8px bottom gap remains the minimum on smaller displays.
        height: Math.min(height, mode === "fullscreen" ? 1341
                                   : mode === "expanded" ? 900 : 790)
    };
}

function leftMargin(level, dockCenterX, screenWidth, panelWidth) {
    if (normalize(level) === "fullscreen")
        return 0;
    var room = Math.max(0, Number(screenWidth) - Number(panelWidth));
    var position = Number(dockCenterX) - Number(panelWidth) / 2;
    return Math.max(0, Math.min(room, Math.round(isFinite(position) ? position : 0)));
}

function topMargin(level, chassisTopY, screenHeight, panelHeight, gutter) {
    if (normalize(level) === "fullscreen")
        return 0;
    var room = Math.max(0, Number(screenHeight) - Number(panelHeight));
    var position = Number(chassisTopY) - Number(gutter);
    return Math.max(0, Math.min(room, Math.round(isFinite(position) ? position : 0)));
}
