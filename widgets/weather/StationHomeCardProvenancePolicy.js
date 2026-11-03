.pragma library

// W2b: inspect only *current* ranked observations. A favorite is a stable
// identity, never a cached measurement, success flag or forced watch rank.
function cardKey(candidate) {
    var row = candidate || {};
    var source = String(row.source || "");
    var id = String(row.id || "");
    if (!/^(weather|sky|ground|space)$/.test(source)
        || !/^[a-z][a-z0-9-]{0,63}$/.test(id))
        return "";
    return source + "|" + id;
}

function sourceIdFor(candidate) {
    var row = candidate || {};
    var id = String(row.id || "");
    var source = String(row.source || "");
    if (source === "weather" || source === "sky")
        return "weather";
    if (source === "ground")
        return "aqi";
    if (source === "space") {
        if (id === "geomagnetic" || id === "kp-trend")
            return "kp";
        if (id === "solar-wind" || id === "solar-wind-trend")
            return "solar-wind";
        if (id === "imf-bz" || id === "bz-trend")
            return "imf";
        // SPACE STACK/BASELINE/FEED span multiple observing instruments:
        // one source clock would be false precision.
        return "";
    }
    return "";
}

function healthRowFor(candidate, sourceRows) {
    var wanted = sourceIdFor(candidate);
    if (!wanted) return null;
    var rows = Array.isArray(sourceRows) ? sourceRows : [];
    for (var i=0; i<rows.length; i++) {
        if (rows[i] && rows[i].id === wanted) return rows[i];
    }
    return null;
}

function provenance(candidate, sourceRows) {
    var row = candidate || {};
    var rank = Number(row.rank);
    var score = isFinite(rank) ? rank.toFixed(0) : "--";
    var source = String(row.source || "UNKNOWN").toUpperCase();
    var health = healthRowFor(row, sourceRows);
    var parts = ["SRC " + source,"SCORE " + score];
    if (!health) {
        parts.push("FRESHNESS UNVERIFIED");
    } else {
        parts.push(String(health.state || "UNKNOWN").toUpperCase());
        var age = Number(health.sampleAgeMinutes);
        if (!isFinite(age) || age < 0)
            age = Number(health.lastSuccessAgeMinutes);
        if (isFinite(age) && age >= 0)
            parts.push("AGE " + Math.floor(age) + "m");
        else
            parts.push("AGE UNKNOWN");
        if (health.provider)
            parts.push(String(health.provider).toUpperCase());
    }
    return parts.join(" // ");
}

function pinnedRows(cardKeys, currentWatch) {
    var stored = Array.isArray(cardKeys) ? cardKeys : [];
    var current = Array.isArray(currentWatch) ? currentWatch : [];
    var output = [];
    for (var i=0;i<stored.length;i++) {
        var key = String(stored[i] || "");
        if (!/^(weather|sky|ground|space)\|[a-z][a-z0-9-]{0,63}$/.test(key))
            continue;
        var active = false;
        for (var j=0;j<current.length;j++) {
            if (cardKey(current[j]) === key) {
                active = true;
                break;
            }
        }
        output.push({
            key:key,
            source:key.split("|")[0],
            id:key.split("|")[1],
            active:active,
            // Never fill a missing card using a saved value or old status.
            status:active ? "CURRENT WATCH" : "NOT CURRENTLY PROMOTED"
        });
    }
    return output;
}
