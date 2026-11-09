// Hospital // PX atomic Doctor succession capability probe, READ ONLY.
// A CLI help signature proves only that a command surface is installed.
// It does not authenticate the caller, verify Session liveness or enable writes.
function evaluate(exitCode, stdoutText, stderrText) {
    const stdout = String(stdoutText || "");
    const stderr = String(stderrText || "");
    const usage = stdout.toLowerCase();
    const required = [
        "--room-id", "--previous-session-id", "--new-session-id",
        "--previous-doctor-id", "--previous-provider-id",
        "--successor-doctor-id", "--successor-provider-id",
        "--assignment-id", "--repository", "--branch",
        "--working-directory", "--confirm", "--json"
    ];
    const validExit = typeof exitCode === "number"
        && Number.isFinite(exitCode) && exitCode === 0;
    const exactCommand = /(?:^|\s)px agent session-succeed(?:\s|$)/.test(usage);
    const supported = validExit && exactCommand
        && required.every(function(flag) { return usage.indexOf(flag) !== -1; });
    const detail = supported ? "" : String(stderr || stdout)
        .trim().slice(0, 180);
    return {
        supported: supported,
        authorityVerified: false,
        replacementAuthorized: false,
        source: "INSTALLED LOCAL PX --HELP // NO SESSION MUTATION",
        reason: supported
            ? "PX SUCCESSION COMMAND PRESENT // OPERATOR AUTHORITY NOT VERIFIED"
            : !validExit
                ? "PX SUCCESSION COMMAND UNAVAILABLE // CHECK PX INSTALLATION"
                : "PX SUCCESSION COMMAND CONTRACT INCOMPLETE",
        detail: detail
    };
}
