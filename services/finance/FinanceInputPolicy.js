// FinanceW reusable input normalization. Pure UI rules, no Actual access.
function validDate(year,month,day) {
    if(!Number.isInteger(year)||year<1900||year>2099
        ||!Number.isInteger(month)||month<1||month>12
        ||!Number.isInteger(day)||day<1||day>31)return false;
    const d=new Date(Date.UTC(year,month-1,day));
    return d.getUTCFullYear()===year && d.getUTCMonth()===month-1 && d.getUTCDate()===day;
}
function parseDate(date) {
    const m=/^((?:19|20)\d{2})-(\d{2})-(\d{2})$/.exec(String(date||""));
    if(!m)return null;
    const year=Number(m[1]),month=Number(m[2]),day=Number(m[3]);
    return validDate(year,month,day)?{year,month,day}:null;
}
function isoDate(year,month,day){
    if(!validDate(year,month,day))return "";
    return String(year).padStart(4,"0")+"-"+String(month).padStart(2,"0")+"-"+String(day).padStart(2,"0");
}
function daysInMonth(year,month){
    return new Date(Date.UTC(year,month,0)).getUTCDate();
}
function editDatePart(date,fallback,part,value){
    const base=parseDate(date)||parseDate(fallback);
    if(!base || !/^\d{1,4}$/.test(String(value)))return "";
    const x=Number(value);
    if(!Number.isInteger(x))return "";
    const next={year:base.year,month:base.month,day:base.day};
    if(part==="year"&&x>=1900&&x<=2099)next.year=x;
    else if(part==="month"&&x>=1&&x<=12)next.month=x;
    else if(part==="day"&&x>=1&&x<=31)next.day=x;
    else return "";
    if(part!=="day")next.day=Math.min(next.day,daysInMonth(next.year,next.month));
    return isoDate(next.year,next.month,next.day);
}
function stepDatePart(date,fallback,part,direction){
    const base=parseDate(date)||parseDate(fallback);
    if(!base || (direction!==1&&direction!==-1))return "";
    if(part==="day") {
        const d=new Date(Date.UTC(base.year,base.month-1,base.day+direction));
        return isoDate(d.getUTCFullYear(),d.getUTCMonth()+1,d.getUTCDate());
    }
    if(part==="month"){
        const year=base.year+(base.month+direction<1?-1:base.month+direction>12?1:0);
        const month=base.month+direction<1?12:base.month+direction>12?1:base.month+direction;
        if(year<1900||year>2099)return isoDate(base.year,base.month,base.day);
        return isoDate(year,month,Math.min(base.day,daysInMonth(year,month)));
    }
    if(part==="year"){
        const year=Math.max(1900,Math.min(2099,base.year+direction));
        return isoDate(year,base.month,Math.min(base.day,daysInMonth(year,base.month)));
    }
    return "";
}
function normalizeAmount(text){
    const raw=String(text===undefined||text===null?"":text).trim().replace(/^\$/,"");
    if(!/^\d{1,9}(?:\.\d{1,2})?$/.test(raw))return null;
    const parts=raw.split(".");
    const cents=Number(parts[0])*100+Number((parts[1]||"").padEnd(2,"0"));
    return Number.isSafeInteger(cents)?String(parts[0])+"."+String(parts[1]||"").padEnd(2,"0"):null;
}
