.pragma library

// FinanceW M0: geometry is presentation state, never financial data state.
// A single mapped PanelWindow survives every transition.
var levels = ["compact", "expanded", "tall", "large", "fullscreen"];

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
    // One width-only increase, two height-only increases, then full width.
    // The 1345px portrait ceiling matches TASKS' largest visible frame.
    // Viewport clamps remain active on every level.
    var targetWidth = mode === "fullscreen" ? width
                    : mode === "compact" ? 432 : 1000;
    var targetHeight = mode === "compact" || mode === "expanded" ? 790
                     : mode === "tall" ? 1020 : 1345;
    return {
        width: Math.min(width, targetWidth),
        height: Math.min(height, targetHeight)
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
