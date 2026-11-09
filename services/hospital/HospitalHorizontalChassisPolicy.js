// HOSPITAL // horizontal-only size steps for the permanently mapped Surgery window.
// Left border remains anchored at panelLeftMargin; height/focus/Session state do not change.
// Width budget reserves the visible left inset plus the frame's right glow gutter.
const HOSPITAL_WIDTH_STEPS = [744, 984, 1224, 1464];

function levelIndex(value) {
    const n = Number(value);
    return Number.isInteger(n)
        ? Math.max(0, Math.min(HOSPITAL_WIDTH_STEPS.length - 1, n)) : 0;
}

function displayBudget(screenWidth, leftMargin, glowGutter) {
    const screen = Number(screenWidth);
    if (!Number.isFinite(screen) || screen <= 0)
        return HOSPITAL_WIDTH_STEPS[0];
    const inset = Math.max(0, Number(leftMargin) || 0);
    const glow = Math.max(0, Number(glowGutter) || 0);
    return Math.max(1, Math.floor(screen) - inset - glow);
}

function panelWidth(level, screenWidth, leftMargin, glowGutter) {
    return Math.min(HOSPITAL_WIDTH_STEPS[levelIndex(level)],
        displayBudget(screenWidth, leftMargin, glowGutter));
}

// Skip duplicate effective widths on narrow outputs instead of offering dead clicks.
function step(level, direction, screenWidth, leftMargin, glowGutter) {
    const current = levelIndex(level);
    const delta = Number(direction) < 0 ? -1 : 1;
    const baseWidth = panelWidth(current, screenWidth, leftMargin, glowGutter);
    for (let i = current + delta;
            i >= 0 && i < HOSPITAL_WIDTH_STEPS.length; i += delta) {
        if (panelWidth(i, screenWidth, leftMargin, glowGutter) !== baseWidth)
            return i;
    }
    return current;
}

function canStep(level, direction, screenWidth, leftMargin, glowGutter) {
    return step(level, direction, screenWidth, leftMargin, glowGutter)
        !== levelIndex(level);
}
