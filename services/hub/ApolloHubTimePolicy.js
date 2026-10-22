.pragma library

// B10: Pure, read-only local time presentation. Caller owns its clock tick.
// No SystemClock, Timer, process, timezone database, IO or TimeW controls.
var YEAR_MIN = 1900;
var YEAR_MAX = 2100;
var WEEKDAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"];

function pad2(value) {
    return value < 10 ? "0" + value : String(value);
}

function unavailable(reason) {
    return {
        state: "unavailable", error: reason,
        source: "local-clock",
        is24Hour: true,
        hour24: -1, hour12: -1, minute: -1, second: -1,
        meridiem: "",
        time24: "--:--:--", time12: "--:--:--",
        displayTime: "--:--:--",
        localDate: "", dateLabel: "",
        weekday: "", month: -1, day: -1, year: -1,
        utcOffsetMinutes: null, utcOffsetLabel: "UTC OFFSET UNKNOWN"
    };
}

function snapshot(epochMs, use24Hour) {
    // Unlike Number(value), this cannot accidentally interpret null as the
    // Unix epoch. Zero and negative epoch milliseconds are legitimate.
    if (typeof epochMs !== "number" || !isFinite(epochMs)
            || (use24Hour !== true && use24Hour !== false))
        return unavailable("INVALID_INPUT");

    var date = new Date(epochMs);
    if (!isFinite(date.getTime()))
        return unavailable("INVALID_DATE");

    var year = date.getFullYear();
    if (year < YEAR_MIN || year > YEAR_MAX)
        return unavailable("UNSUPPORTED_YEAR");

    var month = date.getMonth() + 1;
    var day = date.getDate();
    var weekday = WEEKDAYS[date.getDay()];
    var hour24 = date.getHours();
    var minute = date.getMinutes();
    var second = date.getSeconds();
    var hour12 = hour24 % 12 || 12;
    var meridiem = hour24 < 12 ? "AM" : "PM";
    var time24 = pad2(hour24) + ":" + pad2(minute) + ":" + pad2(second);
    var time12 = pad2(hour12) + ":" + pad2(minute) + ":" + pad2(second)
                 + " " + meridiem;

    // Date.getTimezoneOffset returns minutes WEST of UTC. Expose the
    // conventional east-positive offset as a signed integer instead.
    // It is an offset at this instant, NOT an IANA time-zone identifier.
    var utcOffsetMinutes = -date.getTimezoneOffset();
    // Canonicalize negative zero: UTC is +00:00 with integer offset 0.
    if (utcOffsetMinutes === 0)
        utcOffsetMinutes = 0;
    var sign = utcOffsetMinutes < 0 ? "-" : "+";
    var absMinutes = Math.abs(utcOffsetMinutes);
    var offsetLabel = "UTC" + sign
                      + pad2(Math.floor(absMinutes / 60))
                      + ":" + pad2(absMinutes % 60);

    return {
        state: "ready", error: "",
        source: "local-clock",
        is24Hour: use24Hour,
        hour24: hour24, hour12: hour12,
        minute: minute, second: second,
        meridiem: meridiem,
        time24: time24, time12: time12,
        displayTime: use24Hour ? time24 : time12,
        localDate: String(year) + "-" + pad2(month) + "-" + pad2(day),
        dateLabel: weekday + ", " + day + " " + MONTHS[month - 1]
                   + " " + year,
        weekday: weekday, month: month, day: day, year: year,
        utcOffsetMinutes: utcOffsetMinutes,
        utcOffsetLabel: offsetLabel
    };
}
