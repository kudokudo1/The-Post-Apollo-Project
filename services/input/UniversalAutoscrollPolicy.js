.pragma library

// Pure Windows-style autoscroll state machine.
// This module does NOT observe global input or inject Wayland events.
// A future compositor-authorized worker may feed it middle-click, pointer
// displacement, Escape, and target-loss messages.
var DEADZONE = 15;
var MAX_PIXELS_PER_SECOND = 2800;
var BASE_RATE_PER_MS = 0.000008; // Windows-style distance curve
var CURVE_POWER = 2.2;

function initial() {
    return {phase:"idle", x:0, y:0, dx:0, dy:0, target:"",
            generation:0};
}

function begin(state, x, y, target) {
    if (!state || state.phase !== "idle"
            || !Number.isFinite(x) || !Number.isFinite(y)
            || !target || typeof target !== "string")
        return {ok:false, reason:"INVALID_START",state:state};
    return {ok:true,state:{phase:"active",x:x,y:y,dx:0,dy:0,
                           target:target,generation:state.generation+1}};
}
function stop(state, reason) {
    if (!state || state.phase !== "active") return state;
    return {phase:"idle",x:0,y:0,dx:0,dy:0,target:"",
            generation:state.generation+1};
}
function move(state,x,y) {
    if (!state || state.phase !== "active"
            || !Number.isFinite(x) || !Number.isFinite(y))
        return state;
    return {phase:state.phase,x:state.x,y:state.y,
            dx:x-state.x,dy:y-state.y,target:state.target,
            generation:state.generation};
}
function speed(distance) {
    if (!Number.isFinite(distance) || Math.abs(distance) <= DEADZONE)
        return 0;
    var excess = Math.abs(distance) - DEADZONE;
    var perSecond = BASE_RATE_PER_MS * Math.pow(excess, CURVE_POWER) * 1000;
    return Math.sign(distance) * Math.min(MAX_PIXELS_PER_SECOND, perSecond);
}
function tick(state, dtMs, target) {
    // Never scroll across target changes, stale samples or lost focus.
    if (!state || state.phase !== "active" || target !== state.target
            || !Number.isFinite(dtMs) || dtMs <= 0 || dtMs > 100)
        return {ok:false,x:0,y:0,reason:"STALE_OR_FOREIGN_TARGET"};
    return {ok:true,x:speed(state.dx) * dtMs / 1000,
            y:speed(state.dy) * dtMs / 1000,
            reason:"ENGINE_ONLY"};
}
function input(state, event, x, y, target) {
    if (!state || ["idle","active"].indexOf(state.phase) < 0)
        return {ok:false,reason:"INVALID_STATE",state:state};
    if (event === "middle") {
        return state.phase === "active"
            ? {ok:true,state:stop(state,"middle")}
            : begin(state,x,y,target);
    }
    if (event === "escape" || event === "target_lost"
            || event === "device_removed" || event === "service_stopped")
        return {ok:true,state:stop(state,event)};
    if (event === "move")
        return {ok:state.phase === "active",state:move(state,x,y)};
    return {ok:false,reason:"UNKNOWN_EVENT",state:state};
}
