.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function validViewport(width, height) {
    return isFinite(Number(width)) && Number(width) > 0
        && isFinite(Number(height)) && Number(height) > 0;
}

function normalizeZoom(value) {
    const zoom = finite(value);
    return clamp(zoom === null ? 1 : zoom, 1, 8);
}

function clampView(zoomValue, centerLonValue, centerLatValue) {
    const zoom = normalizeZoom(zoomValue);
    const centerLon = finite(centerLonValue);
    const centerLat = finite(centerLatValue);
    const lonLimit = 180 - 180 / zoom;
    const latLimit = 90 - 90 / zoom;
    return {
        zoom: zoom,
        centerLon: clamp(centerLon === null ? 0 : centerLon, -lonLimit, lonLimit),
        centerLat: clamp(centerLat === null ? 0 : centerLat, -latLimit, latLimit)
    };
}

function project(longitudeValue, latitudeValue, widthValue, heightValue,
                 zoomValue, centerLonValue, centerLatValue) {
    const lon = finite(longitudeValue);
    const lat = finite(latitudeValue);
    const width = Number(widthValue);
    const height = Number(heightValue);
    if (lon === null || lat === null || Math.abs(lon) > 180 || Math.abs(lat) > 90
            || !validViewport(width, height)) {
        return {valid: false, visible: false, x: 0, y: 0};
    }

    const view = clampView(zoomValue, centerLonValue, centerLatValue);
    const x = width / 2 + ((lon - view.centerLon) / 360) * width * view.zoom;
    const y = height / 2 - ((lat - view.centerLat) / 180) * height * view.zoom;
    return {
        valid: true,
        visible: x >= 0 && x <= width && y >= 0 && y <= height,
        x: x,
        y: y
    };
}

function unproject(xValue, yValue, widthValue, heightValue,
                   zoomValue, centerLonValue, centerLatValue) {
    const x = finite(xValue);
    const y = finite(yValue);
    const width = Number(widthValue);
    const height = Number(heightValue);
    if (x === null || y === null || !validViewport(width, height))
        return {valid: false, longitude: 0, latitude: 0};

    const view = clampView(zoomValue, centerLonValue, centerLatValue);
    const lon = view.centerLon + ((x - width / 2) / (width * view.zoom)) * 360;
    const lat = view.centerLat - ((y - height / 2) / (height * view.zoom)) * 180;
    return {
        valid: isFinite(lon) && isFinite(lat),
        longitude: lon,
        latitude: lat
    };
}

function pan(zoomValue, centerLonValue, centerLatValue,
             deltaXValue, deltaYValue, widthValue, heightValue) {
    const dx = finite(deltaXValue);
    const dy = finite(deltaYValue);
    const width = Number(widthValue);
    const height = Number(heightValue);
    const view = clampView(zoomValue, centerLonValue, centerLatValue);
    if (dx === null || dy === null || !validViewport(width, height))
        return view;

    return clampView(
        view.zoom,
        view.centerLon - (dx / (width * view.zoom)) * 360,
        view.centerLat + (dy / (height * view.zoom)) * 180
    );
}

function zoomAt(zoomValue, centerLonValue, centerLatValue,
                cursorXValue, cursorYValue, widthValue, heightValue,
                directionValue) {
    const width = Number(widthValue);
    const height = Number(heightValue);
    if (!validViewport(width, height))
        return clampView(zoomValue, centerLonValue, centerLatValue);

    const current = clampView(zoomValue, centerLonValue, centerLatValue);
    const cursor = unproject(
        cursorXValue, cursorYValue, width, height,
        current.zoom, current.centerLon, current.centerLat
    );
    if (!cursor.valid)
        return current;

    const direction = Number(directionValue);
    const nextZoom = clamp(
        current.zoom * (direction > 0 ? 1.25 : direction < 0 ? 0.8 : 1),
        1, 8
    );

    const x = Number(cursorXValue);
    const y = Number(cursorYValue);
    const centerLon = cursor.longitude
        - ((x - width / 2) / (width * nextZoom)) * 360;
    const centerLat = cursor.latitude
        + ((y - height / 2) / (height * nextZoom)) * 180;
    return clampView(nextZoom, centerLon, centerLat);
}

function plottable(rows) {
    if (!Array.isArray(rows))
        return [];
    const result = [];
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row)
            continue;
        const lon = finite(row.longitude);
        const lat = finite(row.latitude);
        if (lon === null || lat === null
                || Math.abs(lon) > 180 || Math.abs(lat) > 90)
            continue;
        result.push(row);
    }
    return result;
}
