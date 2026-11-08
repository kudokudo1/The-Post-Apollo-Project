// HOSPITAL // Exact PX Session attachment capability detection.
// This checks a command surface only. It grants no staff authority, runtime
// permission, provider heartbeat or browser attachment.
function evaluate(exitCode, stdoutText, stderrText) {
    const out = String(stdoutText || "");
    const err = String(stderrText || "");
    const code = exitCode;
    const usage = out.toLowerCase();
    const required = [
        "px agent session-attach",
        "--assignment-id",
        "--doctor-id",
        "--provider-id",
        "--working-directory",
        "--mode",
        "--confirm"
    ];
    let matching = typeof code === "number"
        && Number.isFinite(code) && code === 0;
    for (let i = 0; i < required.length; ++i)
        matching = matching && usage.indexOf(required[i]) !== -1;

    return {
        supported: !!matching,
        source: "LOCAL PX CLI HELP // NOT PROVIDER REACHABILITY",
        reason: matching
            ? "PX SESSION-ATTACH COMMAND AVAILABLE // NOT AUTHORIZED"
            : (code !== 0
                ? "PX SESSION-ATTACH UNAVAILABLE // INSTALL MATCHING PX PR #123"
                : "PX HELP DID NOT IDENTIFY THE ATOMIC ATTACH CONTRACT"),
        errorDetail: matching ? "" : String(err || out).trim().slice(0, 180)
    };
}
