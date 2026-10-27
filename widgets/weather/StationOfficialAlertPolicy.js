.pragma library

function rankSeverity(raw) {
    switch (String(raw || "").toLowerCase()) {
    case "extreme": return 4;
    case "severe": return 3;
    case "moderate": return 2;
    case "minor": return 1;
    default: return 0;
    }
}

function rankUrgency(raw) {
    switch (String(raw || "").toLowerCase()) {
    case "immediate": return 4;
    case "expected": return 3;
    case "future": return 2;
    case "past": return 1;
    default: return 0;
    }
}

function colorToken(raw) {
    switch (String(raw || "").toLowerCase()) {
    case "extreme": return "red";
    case "severe": return "orange";
    case "moderate": return "yellow";
    case "minor": return "cyan";
    default: return "white";
    }
}

function utcLabel(raw) {
    const millis = Date.parse(String(raw || ""));
    if (!isFinite(millis))
        return "--";
    const iso = new Date(millis).toISOString();
    return iso.slice(0, 10) + " " + iso.slice(11, 16) + "Z";
}

function compareAlerts(a, b) {
    const severity = rankSeverity(b.severity) - rankSeverity(a.severity);
    if (severity !== 0)
        return severity;

    const urgency = rankUrgency(b.urgency) - rankUrgency(a.urgency);
    if (urgency !== 0)
        return urgency;

    // At equal official severity/urgency, prefer a currently listed alert
    // over one retained for the one-check RECHECK PENDING safety window.
    const aPending = String(a.listingState || "") === "RECHECK PENDING";
    const bPending = String(b.listingState || "") === "RECHECK PENDING";
    if (aPending !== bPending)
        return aPending ? 1 : -1;

    const aExpiry = Date.parse(String(a.expires || ""));
    const bExpiry = Date.parse(String(b.expires || ""));
    if (isFinite(aExpiry) && isFinite(bExpiry) && aExpiry !== bExpiry)
        return aExpiry - bExpiry;

    return String(a.event || "").localeCompare(String(b.event || ""));
}

function summary(alerts) {
    const source = Array.isArray(alerts) ? alerts : [];
    const rows = [];
    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (!row || !String(row.event || "").trim())
            continue;
        rows.push(row);
    }

    if (rows.length === 0) {
        return {
            available: false,
            count: 0,
            colorToken: "white",
            event: "",
            headline: "",
            area: "",
            issuer: "",
            severity: "",
            urgency: "",
            certainty: "",
            listingState: "",
            recheckPending: false,
            expires: "",
            expiresLabel: "--",
            headerText: "",
            dockText: ""
        };
    }

    rows.sort(compareAlerts);
    const top = rows[0];
    const severity = String(top.severity || "UNKNOWN").toUpperCase();
    const urgency = String(top.urgency || "UNKNOWN").toUpperCase();
    const listingState = String(top.listingState || "ACTIVE").toUpperCase();
    const pending = listingState === "RECHECK PENDING";

    return {
        available: true,
        count: rows.length,
        colorToken: colorToken(top.severity),
        event: String(top.event || "NWS ALERT").toUpperCase(),
        headline: String(top.headline || top.event || "NWS ALERT"),
        area: String(top.area || "AREA NOT PROVIDED"),
        issuer: String(top.issuer || "NWS"),
        severity: severity,
        urgency: urgency,
        certainty: String(top.certainty || "UNKNOWN").toUpperCase(),
        listingState: listingState,
        recheckPending: pending,
        expires: String(top.expires || ""),
        expiresLabel: utcLabel(top.expires),
        headerText: "NWS " + severity + " // " + (pending ? "?" : rows.length),
        dockText: rows.length > 1 ? String(Math.min(rows.length, 9)) : "!"
    };
}
