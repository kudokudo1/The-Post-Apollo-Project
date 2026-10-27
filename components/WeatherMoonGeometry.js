.pragma library

// Deterministic 40x40 lunar terminator contours. We build one east-lit
// hemisphere and reflect every x coordinate for waning phases. This avoids
// Qt PathArc clockwise/counterclockwise rasterization asymmetry, while
// retaining the existing eight flat, symbolic phases.
function contour(phase) {
    const name = String(phase || "");
    const waxing = name.indexOf("waxing-") === 0 || name === "first-quarter";
    const waning = name.indexOf("waning-") === 0 || name === "last-quarter";
    if (!waxing && !waning)
        return [];

    const terminator = name.indexOf("crescent") !== -1 ? 31
                     : name.indexOf("gibbous") !== -1 ? 9
                     : 20;
    const steps = 32;
    const points = [];

    function add(x, y) {
        points.push([waning ? 40 - x : x, y]);
    }

    // Right/east-facing circular limb, from top to bottom.
    for (let i = 0; i <= steps; i++) {
        const angle = -Math.PI / 2 + Math.PI * i / steps;
        add(20 + 14 * Math.cos(angle), 20 + 14 * Math.sin(angle));
    }

    // Return along an elliptical terminator (cubic Bezier), bottom to top.
    // Mirroring the same sampled points guarantees equal symbolic lit area.
    for (let i = 1; i <= steps; i++) {
        const t = i / steps;
        const u = 1 - t;
        const x = u * u * u * 20
                + 3 * u * u * t * terminator
                + 3 * u * t * t * terminator
                + t * t * t * 20;
        const y = u * u * u * 34
                + 3 * u * u * t * 29
                + 3 * u * t * t * 11
                + t * t * t * 6;
        add(x, y);
    }
    return points;
}

function litPath(phase) {
    const points = contour(phase);
    if (!points.length)
        return "";
    let path = "";
    for (let i = 0; i < points.length; i++) {
        const point = points[i];
        path += (i ? " L " : "M ") + point[0].toFixed(3) + " " + point[1].toFixed(3);
    }
    return path + " Z";
}
