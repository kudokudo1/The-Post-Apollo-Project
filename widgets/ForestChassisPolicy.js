// FOREST V0: bounded visual geometry. No host/workarea mutation.
// 0 compact -> 1 wider -> 2 taller -> 3 wider again.
var stages = [
    { width: 480, height: 340 },
    { width: 660, height: 340 },
    { width: 660, height: 540 },
    { width: 930, height: 610 }
];

function step(level, delta) {
    var current = Math.max(0, Math.min(stages.length - 1, Number(level) || 0));
    var next = current + (delta > 0 ? 1 : delta < 0 ? -1 : 0);
    return Math.max(0, Math.min(stages.length - 1, next));
}

function frame(level, screenWidth, screenHeight, gutter, topInset, bottomGap) {
    var index = Math.max(0, Math.min(stages.length - 1, Number(level) || 0));
    var width = Math.max(1, Number(screenWidth) || 1366);
    var height = Math.max(1, Number(screenHeight) || 768);
    var leftRightAllowance = Math.max(0, 2 * (Number(gutter) || 0)) + 12;
    var topAllowance = height >= 300 ? 80 : 12;
    var heightAllowance = topAllowance + Math.max(0, Number(topInset) || 0)
                        + Math.max(0, Number(bottomGap) || 0) + 12;
    return {
        width: Math.max(1, Math.min(stages[index].width, width - leftRightAllowance)),
        height: Math.max(1, Math.min(stages[index].height, height - heightAllowance))
    };
}

function topMargin(screenHeight, windowHeight) {
    var height = Math.max(1, Number(screenHeight) || 768);
    var windowSize = Math.max(1, Number(windowHeight) || 1);
    return Math.max(0, Math.min(height >= 300 ? 80 : 12, height - windowSize - 12));
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
