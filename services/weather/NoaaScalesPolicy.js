.pragma library

function shortText(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .trim()
        .replace(/\s+/g, " ")
        .slice(0, limit);
}

function scaleNumber(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const number = Number(value);
    if (!isFinite(number) || Math.floor(number) !== number
            || number < 0 || number > 5)
        return -1;
    return number;
}

function fallbackDescriptor(level) {
    switch (Number(level)) {
    case 0: return "NONE";
    case 1: return "MINOR";
    case 2: return "MODERATE";
    case 3: return "STRONG";
    case 4: return "SEVERE";
    case 5: return "EXTREME";
    default: return "UNAVAILABLE";
    }
}

function normalizeScale(block, prefix, category) {
    const level = scaleNumber(block ? block.Scale : null);
    const providerText = shortText(block ? block.Text : "", 48);
    return {
        prefix: prefix,
        category: category,
        available: level >= 0,
        level: level,
        code: level >= 0 ? prefix + level : prefix + "--",
        providerText: providerText !== ""
                      ? providerText.toUpperCase()
                      : fallbackDescriptor(level)
    };
}

function parseCurrent(root) {
    if (!root || typeof root !== "object" || Array.isArray(root))
        throw new Error("Invalid NOAA scales response");

    const current = root["0"];
    if (!current || typeof current !== "object")
        throw new Error("NOAA current scale slot missing");

    const dateStamp = shortText(current.DateStamp, 16);
    const timeStamp = shortText(current.TimeStamp, 16);
    const geomagnetic = normalizeScale(
        current.G, "G", "GEOMAGNETIC STORM"
    );
    const radio = normalizeScale(
        current.R, "R", "RADIO BLACKOUT"
    );
    const radiation = normalizeScale(
        current.S, "S", "SOLAR RADIATION STORM"
    );

    if (!geomagnetic.available && !radio.available && !radiation.available)
        throw new Error("NOAA current scales unavailable");

    return {
        available: true,
        dateStamp: dateStamp,
        timeStamp: timeStamp,
        productStamp:
            dateStamp !== "" && timeStamp !== ""
            ? dateStamp + " " + timeStamp
            : dateStamp || timeStamp || "--",
        G: geomagnetic,
        R: radio,
        S: radiation
    };
}

function emptyCurrent() {
    return {
        available: false,
        dateStamp: "",
        timeStamp: "",
        productStamp: "--",
        G: normalizeScale(null, "G", "GEOMAGNETIC STORM"),
        R: normalizeScale(null, "R", "RADIO BLACKOUT"),
        S: normalizeScale(null, "S", "SOLAR RADIATION STORM")
    };
}
