.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function validTimeTag(value) {
    const text = String(value || "").trim();
    return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(text)
        ? text : "";
}

function state(value) {
    const text = String(value || "").trim().toLowerCase();
    return text === "observed" || text === "estimated" || text === "predicted"
        ? text : "";
}

function noaaScale(value) {
    const text = String(value || "").trim().toUpperCase();
    return /^G[1-5]$/.test(text) ? text : "";
}

function scaleLevel(value) {
    const text = noaaScale(value);
    return text ? Number(text.slice(1)) : 0;
}

function timeLabel(value) {
    const tag = validTimeTag(value);
    return tag ? tag.slice(5, 10) + " " + tag.slice(11, 16) : "--";
}

function normalizeRow(row) {
    if (!row || typeof row !== "object")
        return null;

    const tag = validTimeTag(row.time_tag);
    const kp = finite(row.kp);
    const kind = state(row.observed);
    if (!tag || kp === null || kp < 0 || kp > 9 || !kind)
        return null;

    const scale = noaaScale(row.noaa_scale);
    return {
        timeTag: tag,
        timeLabel: timeLabel(tag),
        kp: kp,
        level: Math.max(0, Math.min(1, kp / 9)),
        state: kind,
        noaaScale: scale
    };
}

function parseRows(root) {
    if (!Array.isArray(root))
        throw new Error("Invalid NOAA planetary K forecast");

    const rows = [];
    const seen = {};
    for (let i = 0; i < root.length; i++) {
        const row = normalizeRow(root[i]);
        if (!row || seen[row.timeTag])
            continue;
        seen[row.timeTag] = true;
        rows.push(row);
    }

    rows.sort(function(a, b) {
        return a.timeTag < b.timeTag ? -1
             : a.timeTag > b.timeTag ? 1 : 0;
    });

    if (rows.length === 0)
        throw new Error("NOAA K forecast has no usable rows");
    return rows;
}

function predictedRows(root) {
    return parseRows(root).filter(function(row) {
        return row.state === "predicted";
    });
}

function summarize(root, limit) {
    const predicted = predictedRows(root);
    if (predicted.length === 0)
        throw new Error("NOAA K forecast has no predicted rows");

    const count = Math.max(1, Math.min(16, Math.floor(Number(limit) || 8)));
    const rows = predicted.slice(0, count);
    let maxKp = -1;
    let maxScale = "";
    let maxScaleLevel = 0;

    for (let i = 0; i < rows.length; i++) {
        if (rows[i].kp > maxKp)
            maxKp = rows[i].kp;
        const level = scaleLevel(rows[i].noaaScale);
        if (level > maxScaleLevel) {
            maxScaleLevel = level;
            maxScale = rows[i].noaaScale;
        }
    }

    return {
        available: true,
        rows: rows,
        totalPredicted: predicted.length,
        displayedBins: rows.length,
        maxKp: maxKp,
        maxNoaaScale: maxScale,
        firstTimeTag: rows[0].timeTag,
        lastTimeTag: rows[rows.length - 1].timeTag,
        firstTimeLabel: rows[0].timeLabel,
        lastTimeLabel: rows[rows.length - 1].timeLabel
    };
}

function emptySummary() {
    return {
        available:false,
        rows:[],
        totalPredicted:0,
        displayedBins:0,
        maxKp:-1,
        maxNoaaScale:"",
        firstTimeTag:"",
        lastTimeTag:"",
        firstTimeLabel:"--",
        lastTimeLabel:"--"
    };
}
