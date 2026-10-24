.pragma library

// Sway get_outputs rect values are compositor-global logical pixels.
// A layer-shell anchored panel's Qt mapToGlobal coordinates are NOT
// authoritative on Wayland. The station is anchored top/right with a
// right margin; the terminal bay lives after its rail/header offsets.
function position(outputs, outputName, stationWidth, rightMargin,
                  headerHeight, railWidth, bayX, bayY, bayWidth, bayHeight) {
    if (!Array.isArray(outputs) || typeof outputName !== "string"
            || !outputName)
        return null;
    const output = outputs.find(function(item) {
        return item && item.name === outputName && item.active === true;
    });
    if (!output || !output.rect)
        return null;
    const rect = output.rect;
    const fields = [rect.x, rect.y, rect.width, rect.height, stationWidth,
                    rightMargin, headerHeight, railWidth, bayX, bayY,
                    bayWidth, bayHeight].map(Number);
    if (fields.some(function(v) { return !isFinite(v); }))
        return null;
    const [ox, oy, ow, oh, sw, rm, hh, rw, bx, by, bw, bh] = fields;
    if (ow <= 0 || oh <= 0 || sw <= 0 || bw <= 0 || bh <= 0
            || rm < 0 || hh < 0 || rw < 0 || bx < 0 || by < 0
            || sw + rm > ow || hh + by + bh > oh
            || rw + bx + bw > sw)
        return null;
    const x = Math.round(ox + ow - rm - sw + rw + bx);
    const y = Math.round(oy + hh + by);
    const width = Math.round(bw);
    const height = Math.round(bh);
    const maxX = ox + ow;
    const maxY = oy + oh;
    if (x < ox || y < oy || width < 1 || height < 1
            || x + width > maxX + 0.5 || y + height > maxY + 0.5)
        return null;
    return {x: x, y: y, width: width, height: height};
}


// Inspect compositor OBSERVED geometry rather than treating a successful
// swaymsg resize exit as proof Kitty accepted the requested pixel size.
// get_tree is a nested Sway tree; no shell interpolation or app-id patterns.
function observedWindow(tree, appId) {
    if (!tree || typeof tree !== "object"
            || typeof appId !== "string" || !/^weather-screen(?:-[a-z]+)?$/.test(appId))
        return null;
    function scan(node) {
        if (!node || typeof node !== "object") return null;
        if (node.app_id === appId && node.rect && node.visible !== false) {
            const r = node.rect;
            if ([r.x, r.y, r.width, r.height].every(function(v) {
                return typeof v === "number" && isFinite(v);
            }) && r.width > 0 && r.height > 0)
                return {x: r.x, y: r.y, width: r.width, height: r.height};
        }
        const children = []
            .concat(Array.isArray(node.nodes) ? node.nodes : [])
            .concat(Array.isArray(node.floating_nodes) ? node.floating_nodes : []);
        for (let i = 0; i < children.length; ++i) {
            const found = scan(children[i]);
            if (found) return found;
        }
        return null;
    }
    return scan(tree);
}

// Return only Kitty's actual pixels that intersect the requested bay.
// The rest of the layer-shell chassis must REMAIN painted so the desktop
// does not leak through when a terminal refuses Sway's resize request.
function visibleIntersection(desired, actual) {
    if (!desired || !actual) return null;
    const a = [desired.x, desired.y, desired.width, desired.height,
               actual.x, actual.y, actual.width, actual.height];
    if (!a.every(function(v) { return typeof v === "number" && isFinite(v); })
            || desired.width <= 0 || desired.height <= 0
            || actual.width <= 0 || actual.height <= 0)
        return null;
    const left = Math.max(desired.x, actual.x);
    const top = Math.max(desired.y, actual.y);
    const right = Math.min(desired.x + desired.width, actual.x + actual.width);
    const bottom = Math.min(desired.y + desired.height, actual.y + actual.height);
    if (right <= left || bottom <= top) return null;
    return {x: left - desired.x, y: top - desired.y,
            width: right - left, height: bottom - top,
            exact: desired.x === actual.x && desired.y === actual.y
                   && desired.width === actual.width
                   && desired.height === actual.height};
}
