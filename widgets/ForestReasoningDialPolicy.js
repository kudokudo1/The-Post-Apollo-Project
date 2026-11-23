// Forest-local, presentation-only reasoning dial policy.
// Clockwise degrees: 0=top, 90=right, 180=bottom, 270=left.
// The 15-degree bottom sector (172.5..187.5) is physically unreachable.
// NONE starts just left of bottom; HIGH finishes just right of bottom.
var labels = ["NONE", "LOW", "MED", "HIGH"];
var deadHalfAngle = 7.5;
var arcStart = 180 + deadHalfAngle;
var arcEnd = 540 - deadHalfAngle;
var detentSeparation = (arcEnd - arcStart) / (labels.length - 1);

function clampStep(value) {
    if (!isFinite(value))
        return 0;
    return Math.max(0, Math.min(labels.length - 1, Math.round(value)));
}

function labelForStep(index) {
    return labels[clampStep(index)];
}

function angleForStep(index) {
    return arcStart + clampStep(index) * detentSeparation;
}

function stepFromAngle(degrees) {
    if (!isFinite(degrees))
        return -1;
    var angle = ((degrees % 360) + 360) % 360;
    // Reject the open gap, never snap across it or move through it.
    if (angle > 180 - deadHalfAngle && angle < 180 + deadHalfAngle)
        return -1;
    var unwrapped = angle < arcStart ? angle + 360 : angle;
    return clampStep((unwrapped - arcStart) / detentSeparation);
}

function stepFromPoint(x, y, width, height) {
    var dx = x - width / 2;
    var dy = y - height / 2;
    // Avoid selecting a detent from the label in the center of the dial.
    if (!isFinite(dx) || !isFinite(dy) || dx * dx + dy * dy < 64)
        return -1;
    return stepFromAngle(Math.atan2(dx, -dy) * 180 / Math.PI);
}
