.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function monthKeyFromMs(value) {
    const ms = Number(value);
    if (!isFinite(ms) || ms <= 0)
        return "";
    const date = new Date(ms);
    if (!isFinite(date.getTime()))
        return "";
    const month = date.getUTCMonth() + 1;
    return date.getUTCFullYear() + "-"
         + (month < 10 ? "0" + month : String(month));
}

function validMonth(value) {
    const text = String(value || "").trim();
    return /^\d{4}-(0[1-9]|1[0-2])$/.test(text) ? text : "";
}

function normalizeRow(row) {
    if (!row || typeof row !== "object")
        return null;

    const month = validMonth(row["time-tag"]);
    const predictedSsn = finite(row.predicted_ssn);
    const lowSsn = finite(row.low_ssn);
    const highSsn = finite(row.high_ssn);
    const predictedFlux = finite(row["predicted_f10.7"]);
    const lowFlux = finite(row["low_f10.7"]);
    const highFlux = finite(row["high_f10.7"]);

    if (!month || predictedSsn === null || predictedFlux === null)
        return null;

    return {
        month: month,
        predictedSsn: predictedSsn,
        lowSsn: lowSsn,
        highSsn: highSsn,
        ssnRangeValid: lowSsn !== null && highSsn !== null
                       && lowSsn <= highSsn,
        predictedFlux: predictedFlux,
        lowFlux: lowFlux,
        highFlux: highFlux,
        fluxRangeValid: lowFlux !== null && highFlux !== null
                        && lowFlux <= highFlux
    };
}

function parseRows(root) {
    if (!Array.isArray(root))
        throw new Error("Invalid NOAA solar-cycle prediction");

    const rows = [];
    const seen = {};
    for (let i = 0; i < root.length; i++) {
        const row = normalizeRow(root[i]);
        if (!row || seen[row.month])
            continue;
        seen[row.month] = true;
        rows.push(row);
    }

    rows.sort(function(a, b) {
        return a.month < b.month ? -1 : a.month > b.month ? 1 : 0;
    });

    if (rows.length === 0)
        throw new Error("NOAA solar-cycle prediction has no usable rows");
    return rows;
}

function selectModelRow(rows, targetMonth) {
    if (!Array.isArray(rows) || rows.length === 0)
        return {row:null, index:-1, exact:false};

    const target = validMonth(targetMonth);
    if (!target)
        return {row:null, index:-1, exact:false};

    let lastPast = -1;
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].month === target)
            return {row:rows[i], index:i, exact:true};
        if (rows[i].month < target)
            lastPast = i;
        if (rows[i].month > target) {
            const index = lastPast >= 0 ? lastPast : i;
            return {row:rows[index], index:index, exact:false};
        }
    }

    const index = rows.length - 1;
    return {row:rows[index], index:index, exact:false};
}

function peakRow(rows) {
    if (!Array.isArray(rows) || rows.length === 0)
        return null;

    let peak = null;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row || !isFinite(row.predictedSsn))
            continue;
        if (!peak || row.predictedSsn > peak.predictedSsn)
            peak = row;
    }
    return peak;
}

function emptySummary() {
    return {
        available:false,
        targetMonth:"",
        modelMonth:"",
        exactMonth:false,
        predictedSsn:-1,
        lowSsn:null,
        highSsn:null,
        ssnRangeValid:false,
        predictedFlux:-1,
        lowFlux:null,
        highFlux:null,
        fluxRangeValid:false,
        nextMonth:"",
        nextPredictedSsn:-1,
        peakMonth:"",
        peakPredictedSsn:-1,
        rowCount:0
    };
}

function summarize(root, nowMs) {
    const rows = parseRows(root);
    const target = monthKeyFromMs(nowMs);
    const selected = selectModelRow(rows, target);
    if (!selected.row)
        throw new Error("No NOAA model row for target month");

    const peak = peakRow(rows);
    const next = selected.index >= 0 && selected.index + 1 < rows.length
        ? rows[selected.index + 1] : null;

    return {
        available:true,
        targetMonth:target,
        modelMonth:selected.row.month,
        exactMonth:selected.exact,
        predictedSsn:selected.row.predictedSsn,
        lowSsn:selected.row.lowSsn,
        highSsn:selected.row.highSsn,
        ssnRangeValid:selected.row.ssnRangeValid,
        predictedFlux:selected.row.predictedFlux,
        lowFlux:selected.row.lowFlux,
        highFlux:selected.row.highFlux,
        fluxRangeValid:selected.row.fluxRangeValid,
        nextMonth:next ? next.month : "",
        nextPredictedSsn:next ? next.predictedSsn : -1,
        peakMonth:peak ? peak.month : "",
        peakPredictedSsn:peak ? peak.predictedSsn : -1,
        rowCount:rows.length
    };
}

function numberText(value, digits) {
    const number = finite(value);
    return number === null ? "--" : number.toFixed(digits);
}

function rangeText(low, high, digits) {
    const a = finite(low);
    const b = finite(high);
    if (a === null || b === null || a > b)
        return "RANGE INVALID";
    return a.toFixed(digits) + "–" + b.toFixed(digits);
}
