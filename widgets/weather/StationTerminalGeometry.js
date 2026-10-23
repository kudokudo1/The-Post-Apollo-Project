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
