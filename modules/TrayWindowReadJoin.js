// The stdout collector and Process.exited are independent Qt signals.
// Only publish an IPC snapshot after BOTH are complete. Pure transitions
// allow the signal order to be tested without a compositor or host process.
function freshRead() {
    return {exited:false, exitCode:null, streamFinished:false, stdout:""};
}

function withExit(state, code) {
    return {
        exited:true,
        exitCode:code,
        streamFinished:state.streamFinished,
        stdout:state.stdout
    };
}

function withStdout(state, text) {
    return {
        exited:state.exited,
        exitCode:state.exitCode,
        streamFinished:true,
        stdout:typeof text === "string" ? text : ""
    };
}

function outcome(state) {
    if (!state || !state.exited || !state.streamFinished)
        return {ready:false, success:false, reason:"incomplete", stdout:""};
    if (state.exitCode !== 0)
        return {ready:true, success:false, reason:"exit", stdout:""};
    if (state.stdout.trim().length === 0)
        return {ready:true, success:false, reason:"empty-stdout", stdout:""};
    return {ready:true, success:true, reason:"ok", stdout:state.stdout};
}
