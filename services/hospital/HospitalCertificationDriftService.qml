import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: driftProbe

    property bool busy: false
    property string lastError: ""
    property string status: "IDLE"
    property var expectedSnapshot: ({})
    property var currentSnapshot: ({})
    property var lastResult: ({})

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal checked(var result)

    function clone(value) {
        if (value === undefined || value === null)
            return ({});

        return JSON.parse(JSON.stringify(value));
    }

    function textValue(value) {
        if (value === undefined || value === null)
            return "";

        return String(value);
    }

    function check(repository, team, expected) {
        if (busy)
            return false;

        const repo = textValue(repository).trim();
        const room = textValue(team).trim();
        const snapshot = clone(expected || ({}));

        if (!repo || !room) {
            lastError = "DRIFT CHECK // ROOM IDENTITY MISSING";
            status = "ERROR";
            return false;
        }

        if (!textValue(snapshot.branch)
                || !textValue(snapshot.head)
                || !textValue(snapshot.base)
                || !textValue(snapshot.baseHead)) {
            lastError = "DRIFT CHECK // EXPECTED SNAPSHOT INCOMPLETE";
            status = "ERROR";
            return false;
        }

        busy = true;
        lastError = "";
        status = "CHECKING";
        expectedSnapshot = snapshot;
        currentSnapshot = ({});
        lastResult = ({});

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        probeProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" room "$1" "$2" prepare',
            "px-certification-drift",
            repo,
            room
        ]);

        watchdog.restart();
        return true;
    }

    function finishError(reason) {
        busy = false;
        watchdog.stop();
        status = "ERROR";
        lastError = textValue(reason) || "DRIFT CHECK FAILED";

        lastResult = {
            status: status,
            error: lastError,
            expected: clone(expectedSnapshot),
            current: clone(currentSnapshot),
            differences: []
        };

        checked(lastResult);
    }

    function maybeFinish() {
        if (!busy
                || !exitSeen
                || !stdoutSeen
                || !stderrSeen)
            return;

        if (exitCode !== 0) {
            finishError(
                textValue(stderrText)
                || textValue(stdoutText)
                || ("PX DRIFT CHECK EXIT " + exitCode)
            );
            return;
        }

        try {
            const data =
                JSON.parse(textValue(stdoutText).trim());
            const current = {
                repository: textValue(data.repository),
                team: textValue(data.team),
                branch: textValue(data.branch),
                head: textValue(data.head),
                base: textValue(data.base),
                baseHead: textValue(data.base_head),
                mode: textValue(data.mode).toUpperCase(),
                relation: textValue(data.relation).toUpperCase()
            };
            const expected = expectedSnapshot || ({});
            const differences = [];

            if (current.repository !== textValue(expected.repository))
                differences.push("REPOSITORY");

            if (current.team !== textValue(expected.team))
                differences.push("TEAM");

            if (current.branch !== textValue(expected.branch))
                differences.push("BRANCH");

            if (current.head !== textValue(expected.head))
                differences.push("ROOM_HEAD");

            if (current.base !== textValue(expected.base))
                differences.push("BASE");

            if (current.baseHead !== textValue(expected.baseHead))
                differences.push("BASE_HEAD");

            currentSnapshot = current;
            busy = false;
            watchdog.stop();
            lastError = "";
            status =
                differences.length === 0
                ? "MATCH"
                : "DRIFT";

            lastResult = {
                status: status,
                expected: clone(expected),
                current: clone(current),
                differences: differences,
                checkedAt: new Date().toISOString()
            };

            checked(lastResult);
        } catch (error) {
            finishError(
                "DRIFT CHECK PARSE // " + String(error)
            );
        }
    }

    Process {
        id: probeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                driftProbe.stdoutText = this.text;
                driftProbe.stdoutSeen = true;
                driftProbe.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                driftProbe.stderrText = this.text;
                driftProbe.stderrSeen = true;
                driftProbe.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            driftProbe.exitCode = Number(code);
            driftProbe.exitSeen = true;
            driftProbe.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!driftProbe.busy)
                return;

            if (probeProcess.running)
                probeProcess.running = false;

            driftProbe.finishError(
                "PX DRIFT CHECK TIMEOUT"
            );
        }
    }
}
