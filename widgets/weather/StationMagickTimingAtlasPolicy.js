.pragma library

// M7a // Source calendar picker + ruler frequency chart for existing M6d
// Chaldean civil-clock reference hours. The ONE source for hour boundaries,
// weekday rulers and DST caveat remains StationMagickPlanetaryHoursPolicy.
var FORMAT="post-apollo.weather.magick-timing.m7a.v1";
function availableDates(daily,validDate,nextDate){
    if(!Array.isArray(daily)||daily.length<2||daily.length>14||
       typeof validDate!=="function"||typeof nextDate!=="function")
        return [];
    var out=[],seen={};
    for(var i=0;i<daily.length;i++){
        var row=daily[i];
        if(!row||!row.date||validDate(row.date)===null||
           seen[row.date])return [];
        seen[row.date]=true;
    }
    for(var j=0;j<daily.length;j++){
        var item=daily[j],following=nextDate(item.date);
        if(seen[following])out.push(item.date);
    }
    return out;
}
function histogram(plan){
    if(!plan||!plan.ready||!Array.isArray(plan.hours)||
       plan.hours.length!==24)return null;
    var counts={saturn:0,jupiter:0,mars:0,sun:0,
                venus:0,mercury:0,moon:0};
    var phases={day:0,night:0};
    for(var i=0;i<plan.hours.length;i++){
        var item=plan.hours[i];
        if(!item||!Object.prototype.hasOwnProperty.call(counts,item.ruler)||
           !Object.prototype.hasOwnProperty.call(phases,item.phase))
            return null;
        counts[item.ruler]++;phases[item.phase]++;
    }
    return phases.day===12&&phases.night===12
        ? {format:FORMAT,counts:counts,phases:phases}:null;
}
function choose(plan,index){
    return plan && plan.ready && Array.isArray(plan.hours) &&
        Number.isInteger(index)&&index>=0&&index<plan.hours.length
        ? plan.hours[index]:null;
}
