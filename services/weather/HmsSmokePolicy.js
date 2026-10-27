.pragma library

function normalizeDensity(raw) {
    const value = String(raw === undefined || raw === null ? "" : raw)
        .trim().toLowerCase();
    if (value === "heavy" || value === "21")
        return "heavy";
    if (value === "medium" || value === "16")
        return "medium";
    if (value === "light" || value === "5")
        return "light";
    return "unknown";
}

function densityRank(raw) {
    switch (normalizeDensity(raw)) {
    case "heavy": return 3;
    case "medium": return 2;
    case "light": return 1;
    default: return 0;
    }
}

function fillStyle(raw) {
    switch (normalizeDensity(raw)) {
    case "heavy": return "rgba(237,152,26,0.25)";
    case "medium": return "rgba(242,190,78,0.18)";
    case "light": return "rgba(85,207,202,0.12)";
    default: return "rgba(220,243,250,0.08)";
    }
}

function strokeStyle(raw) {
    switch (normalizeDensity(raw)) {
    case "heavy": return "rgba(237,152,26,0.95)";
    case "medium": return "rgba(242,190,78,0.82)";
    case "light": return "rgba(85,207,202,0.72)";
    default: return "rgba(220,243,250,0.55)";
    }
}

function unwrapRing(ring) {
    if (!Array.isArray(ring) || ring.length < 3)
        return [];

    const result = [];
    let previous = null;
    for (let i = 0; i < ring.length; i++) {
        const point = ring[i];
        if (!Array.isArray(point) || point.length < 2)
            continue;
        let longitude = Number(point[0]);
        const latitude = Number(point[1]);
        if (!isFinite(longitude) || !isFinite(latitude)
                || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
            continue;

        if (previous !== null) {
            while (longitude - previous > 180)
                longitude -= 360;
            while (longitude - previous < -180)
                longitude += 360;
        }
        result.push([longitude, latitude]);
        previous = longitude;
    }

    if (result.length < 3)
        return [];

    const first = result[0];
    const last = result[result.length - 1];
    if (Math.abs(first[0] - last[0]) > 1e-9
            || Math.abs(first[1] - last[1]) > 1e-9)
        result.push([first[0], first[1]]);
    return result;
}

function summary(rows) {
    const input = Array.isArray(rows) ? rows : [];
    const result = {
        count: 0,
        light: 0,
        medium: 0,
        heavy: 0,
        unknown: 0,
        vertices: 0
    };

    for (let i = 0; i < input.length; i++) {
        const row = input[i];
        if (!row || !Array.isArray(row.ring))
            continue;
        const density = normalizeDensity(row.density);
        result.count++;
        result.vertices += row.ring.length;
        if (density === "light")
            result.light++;
        else if (density === "medium")
            result.medium++;
        else if (density === "heavy")
            result.heavy++;
        else
            result.unknown++;
    }
    return result;
}
