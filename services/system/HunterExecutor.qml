import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: hunterExecutor

    // Execution engine only. Candidate selection, favorites protection,
    // confirmation UI, and report presentation remain with AppControl.
    property bool running: false
    property bool completionVerified: false
    property var expectedTarget: null
    property bool timedOut: false
    property bool exited: false
    property bool stdoutDone: false
    property bool stderrDone: false
    property int helperExitCode: -1
    property int helperExitStatus: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal resultReady(var result)
    signal finished()
    signal errorRaised(string message)

    function script() {
        return "import json\nimport os\nimport select\nimport signal\nimport sys\n\ntargets = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []\n\ndef emit(payload):\n    print(json.dumps(payload), flush=True)\n\ndef result(pid, name, status, detail):\n    emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":status,\"detail\":detail})\n\ndef snapshot(pid):\n    try:\n        with open(f\"/proc/{pid}/stat\", \"r\", encoding=\"utf-8\") as handle:\n            stat = handle.read().strip()\n        first = stat.index(\"(\")\n        close = stat.rindex(\")\")\n        rest = stat[close + 2:].split()\n        return stat[first + 1:close], rest[0], int(rest[19])\n    except (OSError, ValueError, IndexError):\n        return None, None, None\n\ndef run_target(target):\n    pid = target.get(\"pid\")\n    born = target.get(\"startTicks\")\n    name = target.get(\"name\")\n    if (type(pid) is not int or pid <= 1 or pid == os.getpid()\n            or type(born) is not int or born <= 0\n            or not isinstance(name, str) or not name):\n        result(pid, name, \"escaped\", \"INVALID OR MISSING BIRTH IDENTITY\")\n        return\n    if not hasattr(os, \"pidfd_open\") or not hasattr(signal, \"pidfd_send_signal\"):\n        result(pid, name, \"escaped\", \"PIDFD UNAVAILABLE • NO SIGNAL\")\n        return\n    try:\n        fd = os.pidfd_open(pid)\n    except ProcessLookupError:\n        result(pid, name, \"gone\", \"ALREADY GONE\")\n        return\n    except OSError:\n        result(pid, name, \"escaped\", \"PIDFD OPEN REFUSED • NO SIGNAL\")\n        return\n    try:\n        comm, state, ticks = snapshot(pid)\n        if comm is None:\n            result(pid, name, \"escaped\", \"PROCESS IDENTITY UNOBSERVABLE\")\n            return\n        if ticks != born:\n            result(pid, name, \"gone\", \"ORIGINAL PROCESS GONE; BIRTH CHANGED\")\n            return\n        if comm != name:\n            result(pid, name, \"escaped\", \"PROCESS NAME CHANGED; NO SIGNAL\")\n            return\n        if state == \"Z\":\n            result(pid, name, \"gone\", \"ORIGINAL PROCESS EXITED\")\n            return\n        try:\n            if os.stat(f\"/proc/{pid}\").st_uid != os.getuid():\n                result(pid, name, \"escaped\", \"PROCESS OWNER CHANGED • NO SIGNAL\")\n                return\n            # The handle pins the observed process; never fall back to numeric\n            # PID signaling if that process exits or the PID is recycled.\n            signal.pidfd_send_signal(fd, signal.SIGTERM)\n        except ProcessLookupError:\n            result(pid, name, \"gone\", \"ALREADY GONE\")\n            return\n        except OSError:\n            result(pid, name, \"escaped\", \"SIGNAL REFUSED\")\n            return\n        poll = select.poll()\n        poll.register(fd, select.POLLIN)\n        events = poll.poll(1600)\n        if any(mask & (select.POLLIN | select.POLLHUP) and not mask & (select.POLLERR | select.POLLNVAL)\n               for _, mask in events):\n            result(pid, name, \"killed\", \"EXIT OBSERVED AFTER TERM\")\n        else:\n            result(pid, name, \"escaped\", \"GOT AWAY • STILL RUNNING\")\n    finally:\n        os.close(fd)\n\nseen = set()\nfor target in targets:\n    if not isinstance(target, dict):\n        continue\n    key = (str(target.get(\"pid\")), str(target.get(\"startTicks\")), str(target.get(\"name\")))\n    if key in seen:\n        continue\n    seen.add(key)\n    run_target(target)\n\nemit({\"type\":\"done\",\"count\":len(targets)})\n";
    }

    function start(targets) {
        if (running || process.running)
            return false;

        const captured = Array.isArray(targets) ? targets.slice() : [];

        // The owner dispatches exactly one reviewed target at a time.
        if (captured.length !== 1)
            return false;

        expectedTarget = captured[0];
        completionVerified = false;
        timedOut = false;
        exited = false;
        stdoutDone = false;
        stderrDone = false;
        helperExitCode = -1;
        helperExitStatus = -1;
        stdoutText = "";
        stderrText = "";
        running = true;
        watchdog.restart();

        process.exec([
            "/usr/bin/python3",
            "-u",
            "-c",
            script(),
            JSON.stringify(captured)
        ]);

        return true;
    }

    // No intermediate stdout line confers authority. Validate the complete
    // transcript only after both streams drain and the helper actually exits.
    function validatedResult(target, output, errors, code, status, timeout) {
        if (!target || timeout || code !== 0 || status !== 0 || errors.length !== 0)
            return null;
        const lines = output.trim().split("\n");
        if (lines.length !== 2) return null;
        try {
            const result = JSON.parse(lines[0]);
            const done = JSON.parse(lines[1]);
            if (!result || result.type !== "result" || result.pid !== target.pid
                    || result.name !== target.name
                    || ["killed", "gone", "escaped"].indexOf(result.status) < 0
                    || typeof result.detail !== "string" || !result.detail
                    || !done || done.type !== "done" || done.count !== 1)
                return null;
            return result;
        } catch (error) {
            return null;
        }
    }

    function maybeFinish() {
        if (!running || !exited || !stdoutDone || !stderrDone) return;
        watchdog.stop();
        const result = validatedResult(expectedTarget, stdoutText, stderrText,
            helperExitCode, helperExitStatus, timedOut);
        completionVerified = result !== null;
        if (result) resultReady(result);
        else errorRaised("HUNTER HELPER COMPLETION UNVERIFIED");
        running = false;
        expectedTarget = null;
        finished();
    }

    Process {
        id: process

        onExited: function(exitCode, exitStatus) {
            hunterExecutor.exited = true;
            hunterExecutor.helperExitCode = exitCode;
            hunterExecutor.helperExitStatus = exitStatus;
            hunterExecutor.maybeFinish();
        }

        stdout: StdioCollector {
            onStreamFinished: {
                hunterExecutor.stdoutText = String(text || "");
                hunterExecutor.stdoutDone = true;
                hunterExecutor.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                hunterExecutor.stderrText = String(text || "");
                hunterExecutor.stderrDone = true;
                hunterExecutor.maybeFinish();
            }
        }
    }

    Timer {
        id: watchdog
        interval: 23000
        repeat: false

        // Stop the helper, but do not publish completion or admit a new
        // dispatch until its exit is observed.
        onTriggered: {
            hunterExecutor.timedOut = true;
            process.running = false;
            hunterExecutor.maybeFinish();
        }
    }
}
