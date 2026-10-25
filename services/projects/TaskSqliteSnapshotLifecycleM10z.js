.pragma library

// M10z: pure subprocess event join for the unmounted snapshot reader.
// Quickshell may emit onExited or StdioCollector.onStreamFinished first.
// Do not parse success until both are observed. A cancelled read NEVER
// publishes its response, even if the child already prepared valid stdout.
var MAX_TEXT = 1048576;

function idle() {
    return {generation:0, active:false, exited:false, streamed:false,
        cancelled:false, exitCode:null, stdout:""};
}
function begin(old) {
    if (!old || old.active) return null;
    return {generation:old.generation+1, active:true,
        exited:false, streamed:false, cancelled:false,
        exitCode:null, stdout:""};
}
function cancel(old) {
    if (!old || !old.active) return old;
    return {generation:old.generation, active:true,
        exited:old.exited, streamed:old.streamed,
        cancelled:true, exitCode:old.exitCode, stdout:""};
}
function onExit(old, code) {
    if (!old || !old.active || old.exited) return old;
    return {generation:old.generation,active:true,exited:true,
        streamed:old.streamed,cancelled:old.cancelled,
        exitCode:Number.isInteger(code) ? code : -1,
        stdout:old.cancelled ? "" : old.stdout};
}
function onStreamFinished(old, text) {
    if (!old || !old.active || old.streamed) return old;
    var payload=typeof text==="string" ? text : "";
    return {generation:old.generation,active:true,exited:old.exited,
        streamed:true,cancelled:old.cancelled,exitCode:old.exitCode,
        stdout:old.cancelled ? "" : payload};
}
function outcome(old) {
    if (!old || !old.active) return {kind:"idle"};
    if (!old.exited || !old.streamed) return {kind:"waiting"};
    if (old.cancelled) return {kind:"cancelled"};
    if (old.exitCode !== 0 || old.stdout.length > MAX_TEXT
            || old.stdout.length === 0) return {kind:"failed"};
    return {kind:"response",text:old.stdout};
}
function settle(old) {
    var result=outcome(old);
    if (result.kind==="idle" || result.kind==="waiting") return old;
    return {generation:old.generation,active:false,exited:true,
        streamed:true,cancelled:old.cancelled,
        exitCode:old.exitCode,stdout:""};
}
