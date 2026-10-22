.pragma library

// B9: read-only local civil calendar projection. No event source, network,
// appointment storage, date mutation, or separate clock/polling process.
// Use UTC only for grid arithmetic to avoid DST shifting calendar days;
// "today" is taken from the consumer's existing local wall-clock reading.
var MIN_YEAR = 1900;
var MAX_YEAR = 2100;
var MAX_MONTH_OFFSET = 120;
var DAY_MS = 86400000;
var MONTH_NAMES = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"];
var DAY_NAMES = ["SUN","MON","TUE","WED","THU","FRI","SAT"];

function integer(value,min,max) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= min && value <= max;
}

function pad(value) {
    return value < 10 ? "0" + value : String(value);
}

function key(year,month,day) {
    return String(year) + "-" + pad(month) + "-" + pad(day);
}

function noCalendar(reason) {
    return {
        state:"unavailable",
        error:reason,
        source:"local-clock",
        today:"",
        month:"",
        year:-1,
        monthNumber:-1,
        monthLabel:"",
        weekStartsOn:0,
        weekdayLabels:[],
        weeks:0,
        daysInMonth:-1,
        cells:[],
        eventsState:"not-connected",
        eventCount:-1
    };
}

function snapshot(nowMs, monthOffset, weekStartsOn) {
    var now = Number(nowMs);
    // Do not coerce null/empty strings into a fake Unix epoch date.
    if (typeof nowMs !== "number" || !isFinite(now)
            || !integer(monthOffset,-MAX_MONTH_OFFSET,MAX_MONTH_OFFSET)
            || (weekStartsOn !== 0 && weekStartsOn !== 1))
        return noCalendar("INVALID_INPUT");

    var localToday = new Date(now);
    if (!isFinite(localToday.getTime()))
        return noCalendar("INVALID_DATE");
    var todayYear=localToday.getFullYear();
    var todayMonth=localToday.getMonth()+1;
    var todayDay=localToday.getDate();
    if (!integer(todayYear,MIN_YEAR,MAX_YEAR))
        return noCalendar("UNSUPPORTED_YEAR");

    // Target month arithmetic is calendar-based, never 30 days per month.
    var monthIndex=todayYear*12+(todayMonth-1)+monthOffset;
    var year=Math.floor(monthIndex/12);
    var month=monthIndex%12+1;
    if (!integer(year,MIN_YEAR,MAX_YEAR))
        return noCalendar("UNSUPPORTED_YEAR");

    var firstUtc=Date.UTC(year,month-1,1);
    var nextMonthUtc=Date.UTC(year,month,1);
    var daysInMonth=Math.round((nextMonthUtc-firstUtc)/DAY_MS);
    var firstWeekday=new Date(firstUtc).getUTCDay();
    var leading=(firstWeekday-weekStartsOn+7)%7;
    var weeks=Math.ceil((leading+daysInMonth)/7);
    // Real month geometry is four, five, or six complete weeks.
    var cells=[];
    for (var i=0;i<weeks*7;i++) {
        var civil=new Date(firstUtc+(i-leading)*DAY_MS);
        var cy=civil.getUTCFullYear();
        var cm=civil.getUTCMonth()+1;
        var cd=civil.getUTCDate();
        var weekday=civil.getUTCDay();
        cells.push({
            date:key(cy,cm,cd),
            year:cy,
            month:cm,
            day:cd,
            weekday:weekday,
            row:Math.floor(i/7),
            column:i%7,
            inMonth:cy===year && cm===month,
            isToday:cy===todayYear && cm===todayMonth && cd===todayDay
        });
    }
    var weekdayLabels=[];
    for(var j=0;j<7;j++)
        weekdayLabels.push(DAY_NAMES[(weekStartsOn+j)%7]);
    return {
        state:"ready",
        error:"",
        source:"local-clock",
        today:key(todayYear,todayMonth,todayDay),
        month:key(year,month,1).slice(0,7),
        year:year,
        monthNumber:month,
        monthLabel:MONTH_NAMES[month-1]+" "+year,
        weekStartsOn:weekStartsOn,
        weekdayLabels:weekdayLabels,
        weeks:weeks,
        daysInMonth:daysInMonth,
        cells:cells,
        // Not 0: there is no event provider, so "no appointments" is unknown.
        eventsState:"not-connected",
        eventCount:-1
    };
}
