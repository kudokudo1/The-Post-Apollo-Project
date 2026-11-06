.pragma library

// Company M18: candidate geometry only. This is not a compositor permission,
// native wl_surface identity, window movement or clipping request.
var FORMAT = "post-apollo.company.vector-viewport.m18.v1";

function within(rect, width, height) {
    if (!rect) return false;
    var x = Number(rect.x), y = Number(rect.y);
    var w = Number(rect.width), h = Number(rect.height);
    var maxW = Number(width), maxH = Number(height);
    return isFinite(x) && isFinite(y) && isFinite(w) && isFinite(h)
        && isFinite(maxW) && isFinite(maxH)
        && x >= 0 && y >= 0 && w > 0 && h > 0
        && maxW > 0 && maxH > 0
        && x + w <= maxW && y + h <= maxH;
}

// Only the visible native-map presentation may publish a candidate.
// Consent/editor/raster modes are competing presentation owners.
function owner(coverageVisible, nativeRunning, consentOpen,
               editorOpen, rasterActive, placementArmed, streetConsentOpen) {
    if (!coverageVisible || !nativeRunning || consentOpen || editorOpen
            || rasterActive || placementArmed || streetConsentOpen)
        return "none";
    return "native";
}
