.pragma library

// C6 // All existing calibrated twilight / photo-light windows, selectable
// in four fixed pages. No new astronomy calculations or timezone inference.
var MODES=["DAWN","DAY","DUSK","PHOTO"];
function text(value) {
    return value === null || value === undefined || value === ""
        ? "--" : String(value);
}
function metric(name,value) {
    return {name:name,value:text(value)};
}
function span(start,end) {
    return text(start)+" → "+text(end);
}
function rows(mode,twilight,astronomy) {
    var t=twilight||{},a=astronomy||{};
    if(mode==="DAWN") return [
        metric("ASTRONOMICAL DAWN",t.astronomicalDawn),
        metric("NAUTICAL DAWN",t.nauticalDawn),
        metric("CIVIL DAWN",t.civilDawn),
        metric("SUNRISE // WEATHER",a.sunrise)
    ];
    if(mode==="DAY") return [
        metric("SUNRISE // WEATHER",a.sunrise),
        metric("SOLAR NOON",t.solarNoon),
        metric("SUNSET // WEATHER",a.sunset),
        metric("DAYLIGHT",a.daylightLabel)
    ];
    if(mode==="DUSK") return [
        metric("SUNSET // WEATHER",a.sunset),
        metric("CIVIL DUSK",t.civilDusk),
        metric("NAUTICAL DUSK",t.nauticalDusk),
        metric("ASTRONOMICAL DUSK",t.astronomicalDusk)
    ];
    return [
        metric("BLUE HOUR // AM",span(t.blueMorningStart,t.blueMorningEnd)),
        metric("GOLDEN HOUR // AM",span(t.goldenMorningStart,t.goldenMorningEnd)),
        metric("GOLDEN HOUR // PM",span(t.goldenEveningStart,t.goldenEveningEnd)),
        metric("BLUE HOUR // PM",span(t.blueEveningStart,t.blueEveningEnd))
    ];
}
