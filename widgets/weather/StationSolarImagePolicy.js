.pragma library

var _base = "https://services.swpc.noaa.gov/images/animations/suvi/primary/";

function cleanMode(value) {
    const mode = String(value || "").trim().toLowerCase();
    return mode === "map" ? "map" : "195";
}

function modeInfo(value) {
    const mode = cleanMode(value);
    if (mode === "map") {
        return {
            id: "map",
            label: "THERMAL MAP",
            shortLabel: "MAP",
            path: "map/latest.png",
            title: "SUVI // THERMAL MAP",
            detail: "NOAA SWPC SUVI TEMPERATURE-MAP PRODUCT",
            accent: "cyan"
        };
    }
    return {
        id: "195",
        label: "195 Å",
        shortLabel: "195 Å",
        path: "195/latest.png",
        title: "SUVI // 195 Å",
        detail: "WARM CORONAL PLASMA // GLOBAL STRUCTURE + ACTIVE REGIONS + CORONAL HOLES",
        accent: "magenta"
    };
}

function refreshToken(nowMs) {
    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0)
        return 0;
    // Five-minute buckets avoid generating a unique URL on every binding
    // evaluation while still defeating stale latest.png cache reuse.
    return Math.floor(now / 300000);
}

function imageUrl(modeValue, nowMs) {
    const info = modeInfo(modeValue);
    return _base + info.path + "?v=" + refreshToken(nowMs);
}

function safeImageUrl(value) {
    const raw = String(value || "");
    return /^https:\/\/services\.swpc\.noaa\.gov\/images\/animations\/suvi\/primary\/(195|map)\/latest\.png\?v=\d+$/.test(raw);
}

function localAgeMinutes(lastLoadedMs, nowMs) {
    const loaded = Number(lastLoadedMs);
    const now = Number(nowMs);
    if (!isFinite(loaded) || loaded <= 0 || !isFinite(now) || now < loaded)
        return -1;
    return Math.floor((now - loaded) / 60000);
}
