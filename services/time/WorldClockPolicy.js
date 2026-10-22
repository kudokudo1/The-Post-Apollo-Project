.pragma library

// TimeW: read-only projection of an instant into an explicitly supplied
// UTC offset. Zone-name -> offset lookup is owned by the UI adapter using the
// host's IANA tzdata (GNU date with an allowlisted TZ value).
// This formatter has no subprocess, timer, persistence or system clock writes.
var MIN_YEAR = 1900;
var MAX_YEAR = 2100;

function pad2(value) {
    return value < 10 ? "0" + String(value) : String(value);
}

function unavailable(reason) {
    return {
        state: "unavailable", error: reason,
        readout: "--:--:--//--", localDate: "",
        utcOffsetMinutes: null, utcOffsetLabel: "UTC OFFSET UNKNOWN",
        hour24: -1, meridiem: ""
    };
}

function parseOffset(raw) {
    if (typeof raw !== "string")
        return null;
    // GNU date %z is ±HHMM, without colon or zone abbreviations.
    var match = /^([+-])(\d{2})(\d{2})$/.exec(raw.trim());
    if (match === null)
        return null;
    var hours = Number(match[2]);
    var minutes = Number(match[3]);
    if (hours > 14 || minutes > 59 || (hours === 14 && minutes !== 0))
        return null;
    var value = (hours * 60 + minutes) * (match[1] === "-" ? -1 : 1);
    return value === 0 ? 0 : value;
}

function offsetLabel(minutes) {
    var sign = minutes < 0 ? "-" : "+";
    var absolute = Math.abs(minutes);
    return "UTC" + sign + pad2(Math.floor(absolute / 60))
           + ":" + pad2(absolute % 60);
}

function snapshot(epochMs, rawOffset, use24Hour) {
    if (typeof epochMs !== "number" || !isFinite(epochMs)
            || (use24Hour !== true && use24Hour !== false))
        return unavailable("INVALID_INPUT");
    var minutes = parseOffset(rawOffset);
    if (minutes === null)
        return unavailable("OFFSET_UNAVAILABLE");

    // Interpret offset-shifted milliseconds using UTC getters. Local getters
    // would accidentally apply the operator's own zone a second time.
    var instant = new Date(epochMs + minutes * 60000);
    if (!isFinite(instant.getTime()))
        return unavailable("INVALID_DATE");
    var year = instant.getUTCFullYear();
    if (year < MIN_YEAR || year > MAX_YEAR)
        return unavailable("UNSUPPORTED_YEAR");

    var hour = instant.getUTCHours();
    var displayHour = use24Hour ? hour : (hour % 12 || 12);
    var meridiem = hour < 12 ? "AM" : "PM";
    var clock = pad2(displayHour) + ":" + pad2(instant.getUTCMinutes())
                + ":" + pad2(instant.getUTCSeconds()) + "//" + meridiem;
    return {
        state: "ready", error: "",
        readout: clock,
        localDate: String(year) + "-" + pad2(instant.getUTCMonth() + 1)
                   + "-" + pad2(instant.getUTCDate()),
        utcOffsetMinutes: minutes,
        utcOffsetLabel: offsetLabel(minutes),
        hour24: hour, meridiem: meridiem
    };
}
