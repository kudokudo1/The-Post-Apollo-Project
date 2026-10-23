.pragma library

// PLANNER M1: pure, read-only calendar projection over the existing task snapshot.
// Civil dates use local YYYY-MM-DD labels. No storage, timers, or remote services.
function pad(n) { return n < 10 ? "0" + n : String(n); }
function key(y,m,d) { return ("0000" + y).slice(-4) + "-" + pad(m) + "-" + pad(d); }
function civilDate(y,m,d) {
    // setUTCFullYear preserves literal years 0001..0099 instead of 1901..1999.
    var date = new Date(0);
    date.setUTCFullYear(y,m-1,d);
    date.setUTCHours(0,0,0,0);
    return date;
}
function valid(y,m,d) {
    return Number.isInteger(y) && y >= 1 && y <= 9999
        && Number.isInteger(m) && m >= 1 && m <= 12
        && Number.isInteger(d) && d >= 1
        && d <= civilDate(y, m+1, 0).getUTCDate();
}
function parse(s) {
    if (typeof s !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(s))
        return null;
    var y=Number(s.slice(0,4)), m=Number(s.slice(5,7)), d=Number(s.slice(8,10));
    return valid(y,m,d) ? {year:y,month:m,day:d} : null;
}
function moveMonth(monthKey, delta) {
    var p=parse(monthKey);
    if (!p || !Number.isInteger(delta)) return monthKey;
    var index=(p.year-1)*12+p.month-1+delta;
    if (index < 0 || index >= 9999*12) return monthKey;
    return key(Math.floor(index/12)+1, index%12+1, 1);
}
// M4: civil-day navigation and a seven-day read-only task projection.
function moveDay(dateKey, delta) {
    var p=parse(dateKey);
    if (!p || !Number.isInteger(delta)) return dateKey;
    var d=civilDate(p.year,p.month,p.day);
    d.setUTCDate(d.getUTCDate()+delta);
    var y=d.getUTCFullYear();
    if (y < 1 || y > 9999) return dateKey;
    return key(y,d.getUTCMonth()+1,d.getUTCDate());
}
function weekDays(snapshot, selectedKey, todayKey) {
    var p=parse(selectedKey);
    if (!p || !snapshot || !Array.isArray(snapshot.items)
        || (snapshot.state!=="ready" && snapshot.state!=="empty"
            && snapshot.state!=="saving")) return [];
    var counts={};
    snapshot.items.forEach(function(t) {
        if (!t || typeof t.id!=="string" || typeof t.title!=="string"
            || typeof t.done!=="boolean") return;
        var due=parse(t.dueDate);
        if (!due) return;
        var k=key(due.year,due.month,due.day);
        if (!counts[k]) counts[k]={total:0,remaining:0};
        counts[k].total++;
        if (!t.done) counts[k].remaining++;
    });
    var first=civilDate(p.year,p.month,p.day);
    first.setUTCDate(first.getUTCDate()-((first.getUTCDay()+6)%7));
    var names=["MO","TU","WE","TH","FR","SA","SU"];
    var days=[];
    for (var i=0;i<7;i++) {
        var d=civilDate(first.getUTCFullYear(),first.getUTCMonth()+1,first.getUTCDate());
        d.setUTCDate(d.getUTCDate()+i);
        var y=d.getUTCFullYear();
        var date=y>=1 && y<=9999
            ? key(y,d.getUTCMonth()+1,d.getUTCDate()) : "";
        var count=counts[date] || {total:0,remaining:0};
        days.push({weekday:names[i],date:date,day:date ? d.getUTCDate() : "",
            total:count.total,remaining:count.remaining,
            selected:date!=="" && date===selectedKey,
            today:date!=="" && date===todayKey});
    }
    return days;
}
function view(snapshot, monthKey, selectedKey, todayKey) {
    var m=parse(monthKey), selected=parse(selectedKey), today=parse(todayKey);
    var state=snapshot && snapshot.state ? String(snapshot.state) : "unavailable";
    var available=(state==="ready" || state==="empty" || state==="saving")
                  && snapshot && Array.isArray(snapshot.items);
    if (!m || m.day!==1) return {available:false,state:state,days:[],agenda:[],scheduled:0,undated:0};
    var byDate={}, undated=0, scheduled=0;
    if (available) snapshot.items.forEach(function(t) {
        if (!t || typeof t.id!=="string" || typeof t.title!=="string" || typeof t.done!=="boolean") return;
        var due=parse(t.dueDate);
        if (!due) { if (!t.done) undated++; return; }
        scheduled++;
        var k=key(due.year,due.month,due.day);
        if (!byDate[k]) byDate[k]=[];
        byDate[k].push({id:t.id,title:t.title,done:t.done,dueDate:k,
            priority:typeof t.priority==="string"?t.priority:"none",
            projectId:typeof t.projectId==="string"?t.projectId:""});
    });
    var count=civilDate(m.year,m.month+1,0).getUTCDate(), days=[];
    // Monday-first, unlike JS's Sunday-first weekday.
    var offset=(civilDate(m.year,m.month,1).getUTCDay()+6)%7;
    for(var cell=0;cell<42;cell++) {
        var day=cell-offset+1, inMonth=day>=1 && day<=count;
        var date=inMonth?key(m.year,m.month,day):"";
        var tasks=inMonth?(byDate[date]||[]):[];
        var remaining=tasks.filter(function(t){return !t.done;}).length;
        days.push({day:inMonth?day:"",date:date,inMonth:inMonth,
            total:tasks.length,remaining:remaining,
            selected:date!=="" && date===selectedKey,
            today:date!=="" && date===todayKey});
    }
    var agenda=selected?(byDate[selectedKey]||[]):[];
    agenda=agenda.slice().sort(function(a,b) {
        if (a.done!==b.done) return a.done?1:-1;
        return a.id<b.id?-1:a.id>b.id?1:0;
    });
    return {available:!!available,state:state,days:days,agenda:agenda,
        scheduled:scheduled,undated:undated,month:monthKey,
        selected:selected?selectedKey:"",today:today?todayKey:""};
}
