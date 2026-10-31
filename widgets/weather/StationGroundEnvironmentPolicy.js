.pragma library

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function heatBand(valueRaw) {
    const value = finite(valueRaw);
    if (value === null)
        return {id:"unavailable", label:"UNAVAILABLE"};
    if (value < 80)
        return {id:"below", label:"BELOW CAUTION"};
    if (value < 90)
        return {id:"caution", label:"CAUTION"};
    if (value < 103)
        return {id:"extreme-caution", label:"EXTREME CAUTION"};
    if (value < 125)
        return {id:"danger", label:"DANGER"};
    return {id:"extreme-danger", label:"EXTREME DANGER"};
}

function heatIndex(tempFRaw, humidityRaw) {
    const temperature = finite(tempFRaw);
    const humidity = finite(humidityRaw);
    if (temperature === null || humidity === null
            || humidity < 0 || humidity > 100)
        return {
            available:false, valueF:null, method:"",
            band:heatBand(null)
        };

    const simpleRaw = 0.5 * (
        temperature + 61
        + (temperature - 68) * 1.2
        + humidity * 0.094
    );
    const simple = (simpleRaw + temperature) / 2;

    let value = simple;
    let method = "STEADMAN SIMPLE";
    if (simple >= 80) {
        value =
            -42.379
            + 2.04901523 * temperature
            + 10.14333127 * humidity
            - 0.22475541 * temperature * humidity
            - 0.00683783 * temperature * temperature
            - 0.05481717 * humidity * humidity
            + 0.00122874 * temperature * temperature * humidity
            + 0.00085282 * temperature * humidity * humidity
            - 0.00000199 * temperature * temperature
              * humidity * humidity;
        method = "ROTHFUSZ";

        if (humidity < 13 && temperature >= 80 && temperature <= 112) {
            const root = Math.max(
                0,
                (17 - Math.abs(temperature - 95)) / 17
            );
            value -= (13 - humidity) / 4 * Math.sqrt(root);
        } else if (humidity > 85
                && temperature >= 80 && temperature <= 87) {
            value += (humidity - 85) / 10
                * (87 - temperature) / 5;
        }
    }

    return {
        available:isFinite(value),
        valueF:isFinite(value) ? value : null,
        method:method,
        band:heatBand(value)
    };
}

function fireWeatherAlerts(alerts) {
    const source = Array.isArray(alerts) ? alerts : [];
    const rows = [];
    const seen = {};
    const pattern =
        /\b(red flag warning|fire weather watch|fire danger statement|fire weather special weather statement)\b/i;

    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (!row)
            continue;
        const event = String(row.event || row.headline || "").trim();
        if (!pattern.test(event))
            continue;

        const key = String(row.id || row.identifier || "")
            || event + "|" + String(row.effective || "");
        if (seen[key])
            continue;
        seen[key] = true;
        rows.push(row);
    }
    return rows;
}
