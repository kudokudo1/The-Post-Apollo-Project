.pragma library

// FinanceW M0: geometry is presentation state, never financial data state.
// A single mapped PanelWindow survives every transition.
// The original three stages remain the default for CameraW, which also
// imports this policy. Only FinanceW explicitly opts into five stages.
var levels = ["compact", "expanded", "fullscreen"];
var financeLevels = ["compact", "expanded", "tall", "large", "fullscreen"];

function normalize(level, profile) {
    var ladder = profile === "finance" ? financeLevels : levels;
    return ladder.indexOf(level) >= 0 ? level : "compact";
}

function step(level, direction, profile) {
    var ladder = profile === "finance" ? financeLevels : levels;
    var index = ladder.indexOf(normalize(level, profile));
    return ladder[Math.max(0, Math.min(ladder.length - 1,
                                    index + (direction < 0 ? -1 : 1)))];
}

function viewportPixels(value, fallback) {
    var n = Number(value);
    return isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

function frame(level, viewportWidth, viewportHeight, gutter, topInset, bottomGap, profile) {
    // Frame and mapped PanelWindow share exactly the same vertical budget:
    // screen height = top inset + frame height + bottom gap (when saturated).
    var inset = Math.max(0, Math.floor(Number(gutter) || 0));
    var top = Math.max(0, Math.floor(Number(topInset) || 0));
    var bottom = Math.max(0, Math.floor(Number(bottomGap) || 0));
    var width = Math.max(1, viewportPixels(viewportWidth, 456) - 2 * inset);
    var height = Math.max(1, viewportPixels(viewportHeight, 768) - top - bottom);
    var mode = normalize(level, profile);
    if (profile !== "finance") {
        // Preserve Camera's original Compact / Expanded / Fullscreen sizes.
        return {
            width: mode === "fullscreen" ? width
                 : Math.min(width, mode === "expanded" ? 1000 : 432),
            height: Math.min(height, mode === "fullscreen" ? 1345
                                       : mode === "expanded" ? 900 : 790)
        };
    }
    // Finance only: one width-only increase, two height-only, then full width.
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
