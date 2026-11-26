import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: hunterExecutor

    // Execution engine only. Candidate selection, favorites protection,
    // confirmation UI, and report presentation remain with AppControl.
    property bool running: false

    signal resultReady(var result)
    signal finished()
    signal errorRaised(string message)

    function script() {
        return "import json\nimport os\nimport select\nimport signal\nimport sys\n\ntargets = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []\n\ndef emit(payload):\n    print(json.dumps(payload), flush=True)\n\ndef result(pid, name, status, detail):\n    emit({\"type\":\"result\",\"pid\":pid,\"name\":name,\"status\":status,\"detail\":detail})\n\ndef snapshot(pid):\n    try:\n        with open(f\"/proc/{pid}/stat\", \"r\", encoding=\"utf-8\") as handle:\n            stat = handle.read().strip()\n        first = stat.index(\"(\")\n        close = stat.rindex(\")\")\n        rest = stat[close + 2:].split()\n        return stat[first + 1:close], rest[0], int(rest[19])\n    except (OSError, ValueError, IndexError):\n        return None, None, None\n\ndef run_target(target):\n    pid = target.get(\"pid\")\n    born = target.get(\"startTicks\")\n    name = target.get(\"name\")\n    if (type(pid) is not int or pid <= 1 or pid == os.getpid()\n            or type(born) is not int or born <= 0\n            or not isinstance(name, str) or not name):\n        result(pid, name, \"escaped\", \"INVALID OR MISSING BIRTH IDENTITY\")\n        return\n    if not hasattr(os, \"pidfd_open\") or not hasattr(signal, \"pidfd_send_signal\"):\n        result(pid, name, \"escaped\", \"PIDFD UNAVAILABLE • NO SIGNAL\")\n        return\n    try:\n        fd = os.pidfd_open(pid)\n    except ProcessLookupError:\n        result(pid, name, \"gone\", \"ALREADY GONE\")\n        return\n    except OSError:\n        result(pid, name, \"escaped\", \"PIDFD OPEN REFUSED • NO SIGNAL\")\n        return\n    try:\n        comm, state, ticks = snapshot(pid)\n        if comm is None or state == \"Z\":\n            result(pid, name, \"gone\", \"ORIGINAL PROCESS GONE OR UNOBSERVABLE\")\n            return\n        if comm != name or ticks != born:\n            result(pid, name, \"gone\", \"ORIGINAL PROCESS GONE; IDENTITY CHANGED\")\n            return\n        try:\n            if os.stat(f\"/proc/{pid}\").st_uid != os.getuid():\n                result(pid, name, \"escaped\", \"PROCESS OWNER CHANGED • NO SIGNAL\")\n                return\n            # The handle pins the observed process; never fall back to numeric\n            # PID signaling if that process exits or the PID is recycled.\n            signal.pidfd_send_signal(fd, signal.SIGTERM)\n        except ProcessLookupError:\n            result(pid, name, \"gone\", \"ALREADY GONE\")\n            return\n        except OSError:\n            result(pid, name, \"escaped\", \"SIGNAL REFUSED\")\n            return\n        poll = select.poll()\n        poll.register(fd, select.POLLIN)\n        if poll.poll(1600):\n            result(pid, name, \"killed\", \"EXIT OBSERVED AFTER TERM\")\n        else:\n            result(pid, name, \"escaped\", \"GOT AWAY • STILL RUNNING\")\n    finally:\n        os.close(fd)\n\nseen = set()\nfor target in targets:\n    if not isinstance(target, dict):\n        continue\n    key = (str(target.get(\"pid\")), str(target.get(\"startTicks\")), str(target.get(\"name\")))\n    if key in seen:\n        continue\n    seen.add(key)\n    run_target(target)\n\nemit({\"type\":\"done\",\"count\":len(targets)})\n";
    }

    function start(targets) {
        if (running || process.running)
            return false;

        const captured = Array.isArray(targets) ? targets.slice() : [];

        // The owner dispatches exactly one reviewed target at a time.
        if (captured.length !== 1)
            return false;

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

    function finish() {
        if (!running)
            return;

        running = false;
        watchdog.stop();
        finished();
    }

    function consumeLine(line) {
        const raw = String(line || "").trim();

        if (!raw || !running)
            return;

        try {
            const payload = JSON.parse(raw);

            if (payload.type === "result")
                resultReady(payload);
            // A "done" line is not proof that the child has exited.
            // Keep the executor occupied until Process.onExited.
        } catch (error) {
            errorRaised("HUNTER progress parse: " + String(error));
        }
    }

    Process {
        id: process

        onExited: function(exitCode, exitStatus) {
            hunterExecutor.finish();
        }

        stdout: SplitParser {
            onRead: function(line) {
                hunterExecutor.consumeLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    hunterExecutor.errorRaised(message);
            }
        }
    }

    Timer {
        id: watchdog
        interval: 23000
        repeat: false

        // Stop the helper, but do not publish completion or admit a new
        // dispatch until its exit is observed.
        onTriggered: process.running = false
    }
}
