.pragma library

// SUN C16 // Pure image viewport math. Never changes panel geometry or
// image URL. All zoom/pan stays inside the clipped SUVI image window.
var MIN_ZOOM = 1;
var MAX_ZOOM = 5;

function numberOr(value, fallback) {
    var n = Number(value);
    return isFinite(n) ? n : fallback;
}

function zoom(value) {
    return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, numberOr(value, MIN_ZOOM)));
}

function clampPan(z, px, py, viewportWidth, viewportHeight,
                  paintedWidth, paintedHeight) {
    var scale = zoom(z);
    var vw = Math.max(1, numberOr(viewportWidth, 1));
    var vh = Math.max(1, numberOr(viewportHeight, 1));
    var cw = Math.max(0, numberOr(paintedWidth, 0));
    var ch = Math.max(0, numberOr(paintedHeight, 0));
    var maxX = Math.max(0, (cw * scale - vw) / 2);
    var maxY = Math.max(0, (ch * scale - vh) / 2);
    return {
        x: Math.max(-maxX, Math.min(maxX, numberOr(px, 0))),
        y: Math.max(-maxY, Math.min(maxY, numberOr(py, 0)))
    };
}

function zoomAt(oldZoom, factor, px, py, fx, fy,
                viewportWidth, viewportHeight, paintedWidth, paintedHeight) {
    var before = zoom(oldZoom);
    var after = zoom(before * numberOr(factor, 1));
    var ratio = after / before;
    var cx = Math.max(1, numberOr(viewportWidth, 1)) / 2;
    var cy = Math.max(1, numberOr(viewportHeight, 1)) / 2;
    // Preserve the point under the pointer, not merely the image center.
    var nextX = numberOr(px, 0) * ratio
                + (numberOr(fx, cx) - cx) * (1 - ratio);
    var nextY = numberOr(py, 0) * ratio
                + (numberOr(fy, cy) - cy) * (1 - ratio);
    var pan = clampPan(after, nextX, nextY,
                       viewportWidth, viewportHeight, paintedWidth, paintedHeight);
    return { zoom: after, x: pan.x, y: pan.y };
}
