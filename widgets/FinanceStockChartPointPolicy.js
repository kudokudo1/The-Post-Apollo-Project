// Finance M12: pure hit testing / coordinates for actual returned EOD sessions.
// Geometry exactly matches the existing native QML Canvas plot. No IO/fetch.
function pointAt(bars, width, height, index) {
    if (!Array.isArray(bars) || bars.length < 2
            || !Number.isInteger(index) || index < 0 || index >= bars.length
            || !Number.isFinite(width) || !Number.isFinite(height)
            || width < 5 || height < 5)
        return null;
    let low = Infinity, high = -Infinity;
    for (let i = 0; i < bars.length; i++) {
        const row = bars[i];
        if (!row || typeof row.price !== "number"
                || !Number.isFinite(row.price) || row.price <= 0)
            return null;
        low = Math.min(low, row.price);
        high = Math.max(high, row.price);
    }
    const range = Math.max(high - low, 0.00001);
    return {
        x: index * (width - 1) / (bars.length - 1),
        y: (height - 1) - (bars[index].price - low) / range * (height - 1)
    };
}
function nearestPoint(bars, width, height, x, y, radius) {
    const hitRadius = radius === undefined ? 18 : radius;
    if (!Array.isArray(bars) || bars.length < 2
            || !Number.isFinite(x) || !Number.isFinite(y)
            || !Number.isFinite(hitRadius) || hitRadius <= 0
            || x < 0 || x > width || y < 0 || y > height)
        return -1;
    let nearest = -1, distanceSquared = hitRadius * hitRadius;
    for (let i = 0; i < bars.length; i++) {
        const point = pointAt(bars, width, height, i);
        if (!point) return -1;
        const dx = point.x - x, dy = point.y - y;
        const d2 = dx * dx + dy * dy;
        if (d2 <= distanceSquared) {
            distanceSquared = d2;
            nearest = i;
        }
    }
    return nearest;
}
function selectedBar(bars, index) {
    if (!Array.isArray(bars) || !Number.isInteger(index)
            || index < 0 || index >= bars.length)
        return null;
    const bar = bars[index];
    if (!bar || typeof bar.date !== "string"
            || !/^\d{4}-\d{2}-\d{2}$/.test(bar.date)
            || typeof bar.price !== "number"
            || !Number.isFinite(bar.price) || bar.price <= 0)
        return null;
    return {date:bar.date, price:bar.price, index:index};
}
