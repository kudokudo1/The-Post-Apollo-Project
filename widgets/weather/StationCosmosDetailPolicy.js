.pragma library

// C6 // Source-backed detail projection for fixed, non-scrolling COSMOS views.
// This adapter does not fetch, synthesize, or persist observations.
function list(value) {
    if (!value || typeof value === "string") return [];
    var length = Number(value.length);
    if (!isFinite(length) || length < 0 || length > 512
            || Math.floor(length) !== length) return [];
    var result = [];
    for (var i=0; i<length; i++) result.push(value[i]);
    return result;
}
function text(value, fallback) {
    return value === null || value === undefined || value === ""
        ? (fallback || "--") : String(value);
}
function degrees(value) {
    if (value === null || value === undefined || value === ""
            || !isFinite(Number(value))) return "--";
    return Number(value).toFixed(1) + "°";
}
function datum(label, value) { return {label:label,value:text(value)}; }
function records(kind, snapshot, iss, eclipse, starsAsNav) {
    if (kind === "planets") return list(snapshot && snapshot.planets);
    if (kind === "stars")
        return list(snapshot && (starsAsNav ? snapshot.stars : snapshot.constellations));
    if (kind === "iss") return list(iss && iss.passes);
    if (kind === "eclipses") return list(eclipse && eclipse.events);
    return [];
}
function rowName(kind, row, starsAsNav) {
    if (!row) return "--";
    if (kind === "iss") return "ISS // GEOMETRIC PASS";
    if (kind === "eclipses") return text(row.event, "ECLIPSE EVENT");
    if (kind === "stars" && !starsAsNav)
        return text(row.name, "CONSTELLATION ANCHOR");
    return text(row.name);
}
function fields(kind, row, context, starsAsNav) {
    if (!row) return [];
    var s=context && context.snapshot || {};
    if (kind === "planets") {
        return [
            datum("ALTITUDE // HC",degrees(row.altitude)),
            datum("AZIMUTH // ZN",degrees(row.azimuth)),
            datum("COMPASS",row.direction),
            datum("SOURCE DATE",s.date),
            datum("UTC SAMPLE",s.time),
            datum("NAV STAR #",row.navStarNumber),
            datum("OBSERVATION", "CURRENT SKY FIX"),
            datum("CATALOG", "USNO CELESTIAL NAV"),
            datum("HORIZON RULE", "DISPLAY THRESHOLD"),
            datum("VISIBILITY", "NOT VERIFIED"),
            datum("LOCAL WEATHER", "NOT MODELED"),
            datum("COORDINATES", "SHARED WEATHER FIX")
        ];
    }
    if (kind === "stars" && starsAsNav) {
        return [
            datum("ALTITUDE // HC",degrees(row.altitude)),
            datum("AZIMUTH // ZN",degrees(row.azimuth)),
            datum("DIRECTION",row.direction),
            datum("CONSTELLATION",row.constellation),
            datum("NAV STAR NUMBER",row.navStarNumber),
            datum("SOURCE DATE",s.date),
            datum("UTC SAMPLE",s.time),
            datum("CATALOG", "USNO NAV STARS"),
            datum("LOCAL WEATHER","NOT MODELED"),
            datum("VISIBILITY","NOT GUARANTEED"),
            datum("SKY LIMIT","USNO SAMPLE"),
            datum("POSITION","GEOCENTRIC")
        ];
    }
    if (kind === "stars") {
        return [
            datum("ANCHOR STAR",row.anchorStar),
            datum("ANCHOR ALT",degrees(row.anchorAltitude)),
            datum("ANCHOR AZ",degrees(row.anchorAzimuth)),
            datum("ANCHOR DIR",row.anchorDirection),
            datum("NAV STAR COUNT",row.count),
            datum("NAV STARS",list(row.starNames).join(" / ") || "--"),
            datum("DIRECTIONS",list(row.directions).join(" / ") || "--"),
            datum("SOURCE DATE",s.date),
            datum("UTC SAMPLE",s.time),
            datum("BOUNDARIES", "NOT MODELED"),
            datum("CATALOG", "USNO NAV STARS"),
            datum("SCOPE", "ANCHOR GROUPS ONLY")
        ];
    }
    if (kind === "iss") {
        var rise=row.rise||{}, peak=row.culminate||{}, set=row.set||{};
        return [
            datum("RISE // UTC",rise.timeUtc),
            datum("PEAK // UTC",peak.timeUtc),
            datum("SET // UTC",set.timeUtc),
            datum("PEAK ELEVATION",degrees(peak.degrees)),
            datum("RISE DIRECTION",rise.direction),
            datum("SET DIRECTION",set.direction),
            datum("RISE AZIMUTH",degrees(rise.azimuth)),
            datum("PEAK AZIMUTH",degrees(peak.azimuth)),
            datum("SET AZIMUTH",degrees(set.azimuth)),
            datum("DURATION",row.durationLabel),
            datum("MINUTES TO RISE",row.minutesUntilRise !== undefined
                ? Number(row.minutesUntilRise).toFixed(1) : "--"),
            datum("VISIBILITY", "GEOMETRIC ONLY")
        ];
    }
    if (kind === "eclipses") {
        return [
            datum("EVENT",row.event),
            datum("DATE // UTC",row.date),
            datum("BODY",row.body),
            datum("TYPE / PHASE",row.phase),
            datum("DAYS UNTIL",row.daysUntil),
            datum("SOURCE",context && context.eclipse
                ? context.eclipse.sourceName : "NASA GSFC"),
            datum("DATE SCOPE",context && context.eclipse
                ? context.eclipse.dateScope : "--"),
            datum("EVENT WINDOW",context && context.eclipse
                ? context.eclipse.eventCount : "--"),
            datum("LOCAL VISIBILITY", "NOT CALCULATED"),
            datum("CONTACT TIMES", "NOT PROVIDED"),
            datum("MAGNITUDE", "NOT PROVIDED"),
            datum("MAXIMUM UTC", "NOT PROVIDED")
        ];
    }
    return [];
}
function page(fieldsList, pageIndex) {
    return list(fieldsList).slice(Math.max(0,Math.min(2,Number(pageIndex)||0))*4,
                                  Math.max(0,Math.min(2,Number(pageIndex)||0))*4+4);
}
function disclaimer(kind, starsAsNav) {
    if (kind==="planets")
        return "USNO CURRENT SKY // ABOVE-HORIZON CATALOG IS NOT AN OPTICAL VISIBILITY CLAIM";
    if (kind==="stars")
        return starsAsNav ? "USNO NAVIGATIONAL STARS // NOT A COMPLETE SKY CATALOG"
            : "GROUPED USNO NAVIGATION STARS // NOT IAU CONSTELLATION BOUNDARIES";
    if (kind==="iss")
        return "ISS-IN.SPACE + CELESTRAK // GEOMETRIC PASS, NOT OPTICAL VISIBILITY";
    return "NASA GSFC GLOBAL DATES // LOCAL VISIBILITY + CONTACTS NOT CALCULATED";
}
