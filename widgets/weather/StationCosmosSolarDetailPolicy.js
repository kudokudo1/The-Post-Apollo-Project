.pragma library

// Focused NOAA readings. No independent collector, cache, or estimate.
function num(value, digits) {
    if (value === undefined || value === null || value === ""
            || !isFinite(Number(value)) || Number(value) < 0)
        return "--";
    return Number(value).toFixed(digits);
}
function value(label, raw) {
    return {label:label, value:raw === undefined || raw === null
        || raw === "" ? "--" : String(raw)};
}
function range(low,high,valid) {
    return valid ? num(low,1)+" - "+num(high,1) : "INVALID SOURCE RANGE";
}
function cyclePage(summary,page,liveFlux) {
    var s=summary||{};
    if (page===0)
        return [
          value("MONTH // MODEL",s.modelMonth),
          value("SUNSPOT NUMBER",num(s.predictedSsn,1)),
          value("PREDICTED F10.7",num(s.predictedFlux,1)+" SFU"),
          value("TARGET // UTC MONTH",s.targetMonth)
        ];
    if (page===1)
        return [
          value("SSN LOW - HIGH",range(s.lowSsn,s.highSsn,s.ssnRangeValid)),
          value("F10.7 LOW - HIGH",range(s.lowFlux,s.highFlux,s.fluxRangeValid)),
          value("MODEL MONTH EXACT",s.exactMonth?"YES":"NO // NEAREST"),
          value("MODEL MONTHS",s.rowCount)
        ];
    return [
        value("NEXT MODEL MONTH",s.nextMonth),
        value("NEXT PREDICTED SSN",num(s.nextPredictedSsn,1)),
        value("PREDICTED CYCLE PEAK",num(s.peakPredictedSsn,1)),
        value("PEAK MONTH",s.peakMonth)
    ];
}
function flareCount(source) {
    if(!source || !source.ready || !source.events) return 0;
    var len=Number(source.events.length);
    return isFinite(len) && len>=0 && len<=48 ? Math.floor(len) : 0;
}
function flareAt(source,index) {
    var len=flareCount(source),n=Number(index);
    return len && isFinite(n) ? source.events[Math.min(len-1,Math.max(0,Math.floor(n)))] : null;
}
function flarePage(event,page) {
    var e=event||{};
    if (page===0)
        return [
          value("GOES CLASS",e.classLabel),
          value("SATELLITE",e.satellite),
          value("START // UTC",e.beginUtc),
          value("PEAK // UTC",e.peakUtc)
        ];
    return [
        value("END // UTC",e.endUtc),
        value("PEAK FLUX // W/M²",num(e.flux,9)),
        value("ENDED",e.ended===true?"YES":e.ended===false?"NO":"--"),
        value("TYPE","OBSERVED X-RAY FLARE")
    ];
}
function xrayPage(source,page) {
    var s=source||{};
    if(page===0)
        return [
          value("LONG BAND // 0.1-0.8NM",num(s.fluxLong,9)+" W/M²"),
          value("SHORT BAND // 0.05-0.4NM",num(s.fluxShort,9)+" W/M²"),
          value("EQUIVALENT CLASS",s.classEquivalent&&s.classEquivalent.label),
          value("GOES SATELLITE",s.satellite)
        ];
    return [
        value("SAMPLE // UTC",s.sampleUtc),
        value("FRESHNESS",s.sampleFresh?"CURRENT":"STALE OR UNKNOWN"),
        value("TREND SAMPLES",s.trend?s.trend.length:0),
        value("FETCH",s.failed?"FAILED // CHECK SOURCE":s.loading?"RECEIVING":s.ready?"RECEIVED":"WAITING")
    ];
}
