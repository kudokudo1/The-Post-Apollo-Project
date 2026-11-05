.pragma library

// M31 // Geometry-only bounds guard for the ONE currently visible MEDIA
// player. QML owns the actual Item.mapToItem() translation at every seam.
// Never use these four numbers as a native wl_surface or a playback grant.
var FORMAT = "post-apollo.weather.subjects-media-viewport.m31.v1";

function within(rect, width, height) {
    if (!rect)
        return false;
    var x = Number(rect.x);
    var y = Number(rect.y);
    var w = Number(rect.width);
    var h = Number(rect.height);
    var maxW = Number(width);
    var maxH = Number(height);
    return isFinite(x) && isFinite(y)
        && isFinite(w) && isFinite(h)
        && isFinite(maxW) && isFinite(maxH)
        && x >= 0 && y >= 0 && w > 0 && h > 0
        && maxW > 0 && maxH > 0
        && x + w <= maxW && y + h <= maxH;
}

// Index and ordinary workspace are distinct presentation owners. Exactly one
// is permitted to publish a player rectangle for the requested route.
// A hidden/closed station, terminal takeover, or non-MEDIA route returns NONE.
function owner(menuOpen, subjectsOpen, terminalRequested,
               navigatorVisible, mediaActive, indexOpen) {
    if (!menuOpen || !subjectsOpen || terminalRequested
            || !navigatorVisible || !mediaActive)
        return "none";
    return indexOpen ? "index" : "workspace";
}
