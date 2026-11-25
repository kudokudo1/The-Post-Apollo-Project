import QtQuick
import Quickshell
import Quickshell.Io

// Disposable API observation only. Not a wire parser or a Runtime endpoint.
ShellRoot {
    id: witness
    readonly property var modes: ["fragments","boundary","overflow","trailing",
        "partial","nonascii","stderr","terminate"]
    property int index: 0
    property var active: null
    property bool failed: false
    property bool complete: false

    function fail(reason) {
        if (failed) return;
        failed = true;
        console.error("R6_API_FAIL " + reason);
        if (active && active.running) active.signal(9);
        else Qt.quit();
    }
    function startCase() {
        if (failed || active !== null || index >= modes.length) {
            fail("invalid start"); return;
        }
        const p = childType.createObject(witness, {mode:modes[index]});
        if (!p) { fail("create"); return; }
        active = p;
        p.clock.restartMs();
        p.running = true;
    }
    function finishCase(p, code, status) {
        if (p !== active || p.exitedSeen) { fail("stale or repeated exit"); return; }
        p.exitedSeen = true;
        if (failed) { Qt.quit(); return; }
        if (!p.startedSeen || p.clock.elapsedMs() < 0 || p.clock.elapsedMs() > 10000) {
            fail("startup/deadline"); return;
        }
        if (p.mode !== "terminate" && (code !== 0 || status !== 0)) {
            fail("unexpected exit " + p.mode); return;
        }
        // Observe whether all stdout/stderr was delivered BEFORE exited.
        // Only small fixed examples retained; bulk cases count characters.
        let ok = false;
        switch (p.mode) {
        case "fragments":
            ok = p.sample === "FRAGMENT\nPAIR1\nPAIR2\n"
                && p.contSent && p.chunks >= 2 && !p.errorSeen;
            break;
        case "boundary":
            ok = p.total === 16384 && p.lineFeeds === 1 && !p.badAscii
                && p.lastCode === 10 && !p.errorSeen;
            break;
        case "overflow":
            ok = p.total === 16384 && p.lineFeeds === 0 && !p.badAscii
                && !p.errorSeen;
            break;
        case "trailing":
            ok = p.sample === "CLOSE\nEXTRA\n" && !p.errorSeen;
            break;
        case "partial":
            ok = p.sample === "PARTIAL" && p.lineFeeds === 0 && !p.errorSeen;
            break;
        case "nonascii":
            ok = p.badAscii && !p.errorSeen;
            break;
        case "stderr":
            ok = p.errorSeen && p.total === 0;
            break;
        case "terminate":
            ok = p.sample === "READY\n" && p.termSent && p.killSent
                && status !== 0 && p.readyAt >= 0 && !p.errorSeen
                && p.clock.elapsedMs() >= p.killAt;
            break;
        }
        if (!ok) { fail("incomplete exit evidence " + p.mode); return; }
        console.info("R6_API_CASE_PASS " + index + " " + p.mode
            + " chunks=" + p.chunks + " chars=" + p.total
            + " multiLF=" + p.multiLF + " elapsedMs=" + p.clock.elapsedMs());
        settle.restart();
    }

    Component {
        id: childType
        Process {
            id: child
            required property string mode
            property ElapsedTimer clock: ElapsedTimer {}
            property bool startedSeen: false
            property bool exitedSeen: false
            property var originalPid: null
            property int chunks: 0
            property int total: 0
            property int lineFeeds: 0
            property int lastCode: -1
            property bool multiLF: false
            property bool badAscii: false
            property bool errorSeen: false
            property bool contSent: false
            property bool termSent: false
            property bool killSent: false
            property real readyAt: -1
            property real termAt: -1
            property real killAt: -1
            property string sample: ""
            command: ["/usr/bin/python3", "-I", "-B", "-u",
                Quickshell.shellPath("child.py"), mode]
            clearEnvironment: true
            workingDirectory: Quickshell.shellPath("private")
            environment: ({HOME:workingDirectory,TMPDIR:workingDirectory,
                LANG:"C.UTF-8",FOREST_PROBE_ONLY:"1"})
            stdinEnabled: true
            onStarted: {
                if (witness.active !== child || startedSeen || exitedSeen || !processId) {
                    witness.fail("unexpected started"); return;
                }
                startedSeen = true;
                originalPid = processId;
                write("GO\n");
            }
            stdout: SplitParser {
                splitMarker: ""
                onRead: function(data) {
                    if (witness.active !== child || child.exitedSeen || !child.startedSeen) {
                        witness.fail("stdout outside original lifetime"); return;
                    }
                    // No raw output logging. Bounded probe accounting only,
                    // not the R6 canonical frame parser.
                    if (typeof data !== "string" || data.length > 16384
                        || child.total + data.length > 16384) {
                        witness.fail("probe cap"); return;
                    }
                    child.chunks++;
                    child.total += data.length;
                    let lf = 0;
                    for (let i = 0; i < data.length; ++i) {
                        const c = data.charCodeAt(i);
                        child.lastCode = c;
                        if (c === 10) { lf++; child.lineFeeds++; }
                        else if (c < 32 || c > 126) child.badAscii = true;
                    }
                    if (lf > 1) child.multiLF = true;
                    if (["fragments","trailing","partial","terminate"].indexOf(child.mode) >= 0) {
                        if (child.sample.length + data.length > 64) {
                            witness.fail("small probe cap"); return;
                        }
                        child.sample += data;
                    }
                    if (child.mode === "fragments" && !child.contSent && child.sample === "FRAG") {
                        child.contSent = true;
                        child.write("CONT\n");
                    }
                    if (child.mode === "terminate" && child.sample === "READY\n" && child.readyAt < 0)
                        child.readyAt = child.clock.elapsedMs();
                }
            }
            stderr: SplitParser {
                splitMarker: ""
                onRead: function(data) {
                    if (witness.active !== child || child.exitedSeen || !child.startedSeen) {
                        witness.fail("stderr outside original lifetime"); return;
                    }
                    // Error bit only, not an accumulated string.
                    if (data.length > 0) child.errorSeen = true;
                }
            }
            onExited: function(code,status) { witness.finishCase(child,code,status); }
        }
    }
    // Timer schedules observations. ElapsedTimer measures actual elapsed time.
    Timer {
        interval: 50
        repeat: true
        running: true
        onTriggered: {
            const p = witness.active;
            if (!p || p.exitedSeen || witness.failed) return;
            const now = p.clock.elapsedMs();
            if (!p.startedSeen && now > 5000) witness.fail("startup timeout");
            else if (now > 6000) witness.fail("action timeout");
            else if (p.mode === "terminate" && p.readyAt >= 0) {
                if (!p.running || p.processId !== p.originalPid) {
                    witness.fail("lost tracked child"); return;
                }
                if (!p.termSent && now - p.readyAt >= 300) {
                    p.termSent = true;
                    p.termAt = now;
                    p.signal(15);
                } else if (p.termSent && !p.killSent && now - p.termAt >= 300) {
                    p.killSent = true;
                    p.killAt = now;
                    p.signal(9);
                }
            }
        }
    }
    Timer {
        id: settle
        interval: 100
        repeat: false
        onTriggered: {
            if (witness.failed) { Qt.quit(); return; }
            const p = witness.active;
            if (!p || !p.exitedSeen || p.running) {
                witness.fail("exit/reap barrier"); return;
            }
            witness.active = null;
            p.destroy();
            witness.index++;
            if (witness.index === witness.modes.length) {
                witness.complete = true;
                console.info("R6_API_NATIVE_PASS");
                Qt.quit();
            } else witness.startCase();
        }
    }
    Timer {
        interval: 25000
        running: true
        onTriggered: witness.fail("trial timeout")
    }
    Component.onCompleted: Qt.callLater(startCase)
}
