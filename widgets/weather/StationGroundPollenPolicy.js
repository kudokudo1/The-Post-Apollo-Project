.pragma library

// Existing Open-Meteo current pollen concentrations. These are raw
// grains/m³ (gr/m³), NOT AQI scores or pollen-risk categories.
// A provider's missing species is never interpreted as a measured zero.
function species(ready, values) {
    if (!ready)
        return [];
    const readings = values || {};
    const sources = [
        ["ALDER", "alderPollen"],
        ["BIRCH", "birchPollen"],
        ["GRASS", "grassPollen"],
        ["MUGWORT", "mugwortPollen"],
        ["OLIVE", "olivePollen"],
        ["RAGWEED", "ragweedPollen"]
    ];
    return sources.map(function(source) {
        const raw = readings[source[1]];
        const n = raw === null || raw === undefined || String(raw).trim() === ""
                  ? -1 : Number(raw);
        const valid = isFinite(n) && n >= 0;
        return {name: source[0], available: valid,
                value: valid ? n : -1,
                label: valid ? n.toFixed(1) + " gr/m³" : "--"};
    });
}
