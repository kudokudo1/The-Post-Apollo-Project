// Forest opens at the old largest (930x610) size. Stage 2 grows taller,
// stage 3 fills Git's permitted height while retaining 930px width, and
// stage 4 grows wider to Git-bounded fullscreen without growing taller.
// Each stage is clamped to its own screen plus Git's fullscreen maximum.
var stages = [
    { width: 930, height: 610 },
    { width: 930, height: 790 },
    { width: 930, height: 99999 },
    { width: 99999, height: 99999 }
];

function step(level, delta) {
    var current = Math.max(0, Math.min(stages.length - 1, Number(level) || 0));
    var next = current + (delta > 0 ? 1 : delta < 0 ? -1 : 0);
    return Math.max(0, Math.min(stages.length - 1, next));
}

function frame(level, screenWidth, screenHeight, gutter, topInset, bottomGap,
               gitMaxWidth, gitMaxHeight) {
    var index = Math.max(0, Math.min(stages.length - 1, Number(level) || 0));
    var width = Math.max(1, Number(screenWidth) || 1366);
    var height = Math.max(1, Number(screenHeight) || 768);
    var leftRightAllowance = Math.max(0, 2 * (Number(gutter) || 0)) + 12;
    // Other top-row menus start at the compositor workarea top.
    // Only the frame's 9px optical inset precedes visible content.
    var heightAllowance = Math.max(0, Number(topInset) || 0)
                        + Math.max(0, Number(bottomGap) || 0) + 12;
    // Match Git's 14px left/right fullscreen gutters and 9px top inset
    // as the fallback. ForestW passes Git's measured caps at runtime.
    var gitWidth = Number(gitMaxWidth);
    if (!isFinite(gitWidth) || gitWidth <= 0)
        gitWidth = Math.max(1, width - 28);
    var gitHeight = Number(gitMaxHeight);
    if (!isFinite(gitHeight) || gitHeight <= 0)
        gitHeight = Math.max(1, height - 22);
    return {
        width: Math.max(1, Math.min(stages[index].width,
                                     width - leftRightAllowance, gitWidth)),
        height: Math.max(1, Math.min(stages[index].height,
                                      height - heightAllowance, gitHeight))
    };
}

function topMargin(screenHeight, windowHeight) {
    // Zero matches Git/Tasks/Time's workarea-aligned top edge. Frame owns 9px.
    // Keep this accessor for existing ForestW geometry bindings and tests.
    return 0;
}

function leftMargin(screenWidth, windowWidth, dockCenterX) {
    var width = Math.max(1, Number(screenWidth) || 1366);
    var windowSize = Math.max(1, Number(windowWidth) || 1);
    var center = Number(dockCenterX) || 0;
    if (center <= 0)
        center = windowSize / 2 + 8;
    return Math.max(0, Math.min(Math.round(center - windowSize / 2),
                                Math.max(0, width - windowSize)));
}
